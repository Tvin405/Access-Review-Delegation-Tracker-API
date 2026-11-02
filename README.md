# Access-Review-Delegation-Tracker API

A cloud-native REST API, built with Python on **Azure Functions**, that tracks who holds privileged and standard access, who approved it, why, and when it expires. It covers **PIM**, **PAM**, **PAW** and **Standard** access, which helps security teams enforce least privilege and run access reviews.

> Built for CS432 / CY-421 Cloud Computing (Midterm Project), Sacred Heart University.

📄 **Full documentation** (API reference, Azure deployment and test evidence): [Cloud-Computing-Midterm-API.pdf](docs/Cloud-Computing-Midterm-API.pdf)

---

## Features

- Create, list, update and delete access review records (full CRUD)
- Count all stored access reviews
- Purge all records, protected by a separate **admin key**
- API key authentication on every endpoint (`x-api-key` header)
- Consistent JSON error responses (400, 401, 404, 500)
- Deployed to Azure Functions on the Flex Consumption plan

## Access Types

| Type | Meaning |
|---|---|
| **PIM** (Privileged Identity Management) | Just-in-time, time-bound access to privileged roles that must be activated and expires automatically |
| **PAM** (Privileged Access Management) | Securing and monitoring privileged accounts and credentials (vaulting, session monitoring, checkout) |
| **PAW** (Privileged Access Workstation) | A dedicated, hardened device used only for admin tasks |
| **Standard** | Normal, non-privileged access that is still tracked and reviewed |

## Tech Stack

- Python, Azure Functions (V2 programming model)
- Azure Functions Core Tools and Azurite for local development
- Bruno for API testing
- Microsoft Azure (Function App, Flex Consumption plan)

---

## Quick Start (Run Locally)

### 1. Prerequisites

- [Python 3](https://www.python.org/downloads/), a version supported by Azure Functions
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- [VS Code](https://code.visualstudio.com/) with the **Azure Functions** and **Azurite** extensions
- A REST client such as Bruno, Postman or Thunder Client

### 2. Clone the repo

```bash
git clone https://github.com/Tvin405/Access-Review-Delegation-Tracker-API.git
cd Access-Review-Delegation-Tracker-API
```

### 3. Create a virtual environment and install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Create `local.settings.json`

This file is git-ignored and holds your secrets. Create it in the project root:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "apikey": "<choose-a-long-random-api-key>",
    "adminkey": "<choose-a-different-admin-key>"
  }
}
```

### 5. Start Azurite and run the API

In VS Code, press `Ctrl+Shift+P` and run **Azurite: Start**. Then:

```bash
func start
```

The API runs at `http://localhost:7071/api`.

### 6. Try it

```bash
curl -X POST http://localhost:7071/api/access-reviews \
  -H "x-api-key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"user":"big.red@shu-demo.edu","role":"Global Administrator","system":"SHU Microsoft Entra ID","accessType":"PIM","assignmentType":"eligible","requiresPAW":true,"grantedBy":"ciso@shu-demo.edu","justification":"Quarterly tenant configuration review","startDate":"2026-10-20","expirationDate":"2026-10-27","status":"active"}'

curl http://localhost:7071/api/access-reviews -H "x-api-key: <your-api-key>"
```

---

## API Endpoints

Base URL (Azure): `https://<your-function-app-domain>/api`

| Method | Route | Description | Auth |
|---|---|---|---|
| GET | `/access-reviews` | Get all access reviews | `x-api-key` |
| POST | `/access-reviews` | Create an access review | `x-api-key` |
| PUT | `/access-reviews/{id}` | Update an access review by id | `x-api-key` |
| DELETE | `/access-reviews/{id}` | Delete an access review by id | `x-api-key` |
| GET | `/access-reviews/count` | Count all access reviews | `x-api-key` |
| DELETE | `/access-reviews` | Purge all access reviews | `x-api-key` + `x-admin-key` |

### Status codes

| Code | When |
|---|---|
| 200 / 201 | Success / record created |
| 400 | Request body missing or not valid JSON |
| 401 | Missing or invalid API key (or admin key on purge) |
| 404 | No access review with that id |
| 500 | Server configuration error or unexpected error |

All errors return JSON in the form `{"error": "<message>"}`.

---

## Deploy to Azure

1. In VS Code, sign in to Azure and run **Azure Functions: Create Function App in Azure (Advanced)**, choosing Python and the Flex Consumption plan.
2. Run **Azure Functions: Deploy to Function App**.
3. In the Azure portal, open the Function App and go to **Settings → Environment variables**. Add `apikey` and `adminkey`.
4. Under **Scale and concurrency**, set the maximum instance count to 1 so the in-memory data stays consistent.
5. Test using `https://<your-function-app-domain>/api/access-reviews`.

---

## Project Structure

```
├── function_app.py        # All API endpoints, auth and error handling
├── requirements.txt       # Python dependencies
├── host.json              # Azure Functions host configuration
├── docs/                  # Project documentation (PDF)
├── .gitignore             # Excludes local.settings.json, .venv, etc.
└── local.settings.json    # Local secrets (NOT committed)
```

## Limitations and Future Work

- Data is stored **in memory**, so it is lost when the app restarts or Azure recycles the instance.
- No field-level input validation, and no get-by-id or filter endpoints yet.
- Planned improvements: persistent storage (Azure Cosmos DB or Table Storage), input validation, filtering, and **Azure Key Vault** for storing the API and admin keys.

## Author

**Ty Iorfino**, Sacred Heart University
