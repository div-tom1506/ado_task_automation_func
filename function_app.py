import os
import json
import base64
import logging
import requests
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

TASK_TITLES = [
    "Requirements and Grooming",
    "Design & Approach",
    "Implementation",
    "Test & Validation",
    "Documentation & Handover"
]

ORG = os.getenv("ADO_ORG")
PROJECT = os.getenv("ADO_PROJECT")
PAT = os.getenv("ADO_PAT")
API_VERSION = os.getenv("API_VERSION")

def _auth_headers(content_type=None):
    token = base64.b64encode(f":{PAT}".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers

@app.function_name(name="ado_task_automation")
@app.route(route="ado/tasks", methods=["POST"])
def ado_task_automation(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("ADO webhook received")

    try:
        payload = req.get_json()
    except ValueError:
        logging.error("Invalid JSON payload")
        return func.HttpResponse("Invalid payload", status_code=400)

    # Logging full payload for debugging
    logging.info("Full payload: %s", json.dumps(payload))

    resource = payload.get("resource", {})
    story_id = resource.get("id")
    fields = resource.get("fields", {})

    work_item_type = fields.get("System.WorkItemType")
    if isinstance(work_item_type, dict):
        work_item_type = work_item_type.get("newValue")

    if work_item_type != "User Story":
        logging.info("Ignoring non User Story work item")
        return func.HttpResponse(status_code=200)

    # Set defaults if missing
    area_path = fields.get("System.AreaPath")
    iteration_path = fields.get("System.IterationPath")

    if not all([ORG, PROJECT, PAT, story_id]):
        logging.error("Missing required configuration or payload fields")
        return func.HttpResponse("Missing required data", status_code=400)

    parent_url = (
        f"https://dev.azure.com/{ORG}"
        f"/_apis/wit/workitems/{story_id}"
        f"?$expand=relations&api-version={API_VERSION}"
    )

    parent_resp = requests.get(parent_url, headers=_auth_headers(), timeout=15)
    if parent_resp.status_code != 200:
        logging.error("Failed to fetch parent work item")
        return func.HttpResponse("Failed to fetch work item", status_code=500)

    parent_data = parent_resp.json()
    existing_titles = set()

    for relation in parent_data.get("relations", []):
        if relation.get("rel") == "System.LinkTypes.Hierarchy-Forward":
            child_id = relation["url"].split("/")[-1]
            child_resp = requests.get(
                f"https://dev.azure.com/{ORG}/_apis/wit/workitems/{child_id}?api-version={API_VERSION}",
                headers=_auth_headers(),
                timeout=10
            )
            if child_resp.status_code == 200:
                title = child_resp.json().get("fields", {}).get("System.Title")
                if title:
                    existing_titles.add(title)

    created_count = 0

    for title in TASK_TITLES:
        if title in existing_titles:
            logging.info("Task already exists: %s", title)
            continue

        payload = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.AreaPath", "value": area_path},
            {"op": "add", "path": "/fields/System.IterationPath", "value": iteration_path},
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": f"https://dev.azure.com/{ORG}/_apis/wit/workItems/{story_id}"
                }
            }
        ]

        create_resp = requests.post(
            f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workitems/$Task?api-version={API_VERSION}",
            headers=_auth_headers("application/json-patch+json"),
            data=json.dumps(payload),
            timeout=15
        )

        if create_resp.status_code in (200, 201):
            created_count += 1
            logging.info("Task created: %s", title)
        else:
            logging.error("Failed to create task: %s, status_code=%s, response=%s",
                          title, create_resp.status_code, create_resp.text)

    logging.info("Task automation completed. Created %s tasks", created_count)
    return func.HttpResponse("Task automation completed", status_code=200)
