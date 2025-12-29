# Azure DevOps User Story – Task Automation

## Overview

This project implements an **Azure Function (Python)** that automatically creates a predefined set of **Tasks** whenever a new **User Story** is created in Azure DevOps.  
The function is triggered via **Azure DevOps Service Hooks** and uses **Azure DevOps REST APIs** to create and manage work items.

The automation is **idempotent**, meaning repeated triggers for the same User Story will not create duplicate Tasks.

---

## Objective

When a new **User Story** is created in Azure DevOps:
- Automatically create the following Tasks as **children** of the User Story:
  1. Requirements and Grooming
  2. Design & Approach
  3. Implementation
  4. Test & Validation
  5. Documentation & Handover
- Ensure tasks are linked correctly
- Prevent duplicate task creation on retries or repeated triggers

---

## Architecture

- **Azure DevOps Service Hook**
  - Event: `Work item created`
  - Filter: `User Story`
- **Azure Function (HTTP Trigger)**
  - Runtime: Python
  - Auth Level: Function
- **Azure DevOps REST API**
  - Fetch existing child tasks
  - Create missing tasks
  - Link tasks to User Story

### Environment Variables

Configure the following environment variables in **Azure Function App → Configuration**  
(or in `local.settings.json` for local testing):

| Variable | Description |
|--------|-------------|
| `ADO_ORG` | Azure DevOps organization name |
| `ADO_PROJECT` | Azure DevOps project name |
| `ADO_PAT` | Personal Access Token |
| `API_VERSION` | Azure DevOps API version (e.g. `7.0`) |

Example:

```json
{
  "ADO_ORG": "my-org",
  "ADO_PROJECT": "UserStory-Task-Generator",
  "ADO_PAT": "<your-pat>",
  "API_VERSION": "7.0"
}