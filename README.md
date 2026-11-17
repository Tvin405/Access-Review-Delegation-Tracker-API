# Access-Review-Delegation-Tracker API

A cloud-native REST API, built with Python on **Azure Functions**, that tracks who holds privileged and standard access, who approved it, why, and when it expires. It covers **PIM**, **PAM**, **PAW** and **Standard** access, and it **automatically flags expired access that is still marked active** so it can be revoked.

> Built for CS432 / CY-421 Cloud Computing (Final Project), Sacred Heart University. This version extends the midterm API.

📄 **Full documentation** (API reference, Azure deployment and test evidence): [Cloud Computing Midterm - API - Ty Iorfino.pdf](docs/Cloud%20Computing%20Midterm%20-%20API%20-%20Ty%20Iorfino.pdf)

---

## What's new in the final version

| Area | Midterm | Final |
|---|---|---|
| Storage | In-memory dictionary (lost on restart) | **Azure Table Storage** (persistent) |
| Secrets | `apikey` / `adminkey` app settings | **Azure Key Vault**, read with **managed identity** |
| Endpoints | CRUD, count, purge | + `GET /access-reviews/{id}` and **`PATCH /access-reviews/validate`** |
| Automation | None | **Logic App** runs validation daily and emails the result |
| Monitoring | Basic logs | **Application Insights** (requests, dependencies, custom event `ValidationCompleted`), **diagnostic logs** for Key Vault, Table Storage and the Logic App, and an **Azure Dashboard** |
| Process | Git | Azure DevOps work items linked to commits (`AB#`) |

## Architecture

```
            Bruno / client                       Logic App (daily Recurrence)
                  │  x-api-key                        │ 1. Get secret "api-key" (managed identity)
                  ▼                                   │ 2. PATCH /access-reviews/validate
   ┌──────────────────────────────┐ ◄─────────────────┘ 3. Email success or failure
   │ Azure Function App (Python)  │
   │ func-accessreview-dev-eus2-001│── managed identity ──► Key Vault (api-key, admin-key)
   └──────────────┬───────────────┘
                  │ managed identity
                  ▼
        Azure Table Storage (accessreviews)

  Telemetry: Function App → Application Insights → Log Analytics workspace ◄── diagnostic logs
             (Key Vault audit, Table Storage logs, Logic App runtime) → Azure Dashboard
```

## Validation rule

`PATCH /access-reviews/validate` checks every record:

> **If `status` is `active` and `expirationDate` is before today**, the record is updated to `status = "expired"`, `needsRevocation = true`, and `validatedOn = <current UTC time>`.

Records that are revoked, already expired, or not yet past their expiration date are left unchanged. The response reports how many records were updated.

## Access types

| Type | Meaning |
|---|---|
| **PIM** (Privileged Identity Management) | Just-in-time, time-bound access to privileged roles |
| **PAM** (Privileged Access Management) | Securing and monitoring privileged accounts and credentials |
| **PAW** (Privileged Access Workstation) | A dedicated, hardened device used only for admin tasks |
| **Standard** | Normal access that is still tracked and reviewed |

## Tech stack

- Python, Azure Functions (V2 programming model), Flex Consumption plan
- Azure Table Storage, Azure Key Vault, Azure Logic Apps (Consumption)
- Application Insights (Azure Monitor OpenTelemetry), Log Analytics, Azure Dashboard
- Azure Functions Core Tools, Azurite, Bruno, Azure DevOps Boards

---

## Azure resources

| Resource | Name |
|---|---|
| Resource group | `rg-accessreview-dev-eus2-001` (East US 2) |
| Function App | `func-accessreview-dev-eus2-001` |
| Storage account (data) | `staccessreviewdeveus2001`, table `accessreviews` |
| Key Vault | `kv-accrev-dev-eus2-001` (secrets `api-key`, `admin-key`) |
| Logic App | `logic-accessreview-validate-dev-eus2-001` |
| Application Insights | `appi-accessreview-dev-eus2-001` |
| Dashboard | `FinalProject-TyIorfino` |

## Security and access control

- **No secrets in code, app settings, or the repo.** The API key and admin key live only in Key Vault.
- **Managed identities, least privilege:**

| Identity | Role | Scope |
|---|---|---|
| Function App | Key Vault Secrets User | Key Vault |
| Function App | Storage Table Data Contributor | Storage account |
| Logic App | Key Vault Secrets User | Key Vault (reads `api-key` only) |
| Developer (you) | Key Vault Secrets Officer, Storage Table Data Contributor | For local development |

- The Logic App can't read the admin key, so automation can never purge data.
- Logic App Key Vault outputs use **secure inputs/outputs**, so the key never appears in run history.
- Key Vault audit logs record every secret read.

---

## Run locally

### 1. Prerequisites

- Python 3 (a version supported by Azure Functions)
- Azure Functions Core Tools v4
- **Azure CLI**. Sign in with `az login` so `DefaultAzureCredential` can reach Key Vault and Table Storage.
- VS Code with the **Azure Functions** and **Azurite** extensions
- Your account needs **Key Vault Secrets Officer** (or Secrets User) and **Storage Table Data Contributor**.

### 2. Clone and install

```bash
git clone https://github.com/Tvin405/Access-Review-Delegation-Tracker-API.git
cd Access-Review-Delegation-Tracker-API
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Create `local.settings.json`

Copy `local.settings.example.json` to `local.settings.json` (git-ignored) and fill in your values. **No keys go in this file.** They come from Key Vault.

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "STORAGE_TABLE_ENDPOINT": "https://<storage-account>.table.core.windows.net",
    "TABLE_NAME": "accessreviews",
    "KEY_VAULT_URL": "https://<key-vault-name>.vault.azure.net/"
  }
}
```

### 4. Run

```bash
az login
# VS Code: Ctrl+Shift+P → "Azurite: Start"
func start
```

The API runs at `http://localhost:7071/api`. Records are written to the real Azure table, so local and Azure share the same data.

---

## Deploy to Azure

1. **Deploy code:** VS Code → **Azure Functions: Deploy to Function App** → `func-accessreview-dev-eus2-001`.
2. **App settings** (Function App → Settings → Environment variables): `STORAGE_TABLE_ENDPOINT`, `TABLE_NAME`, `KEY_VAULT_URL`, `APPLICATIONINSIGHTS_CONNECTION_STRING`.
3. **Identity:** turn on the system-assigned managed identity and assign the roles in the table above.
4. **Key Vault:** create secrets `api-key` and `admin-key`.
5. **Logic App:** the workflow definition is in [`logic-app/validate-workflow.json`](logic-app/validate-workflow.json).
6. **Monitoring:** link Application Insights, add diagnostic settings (see [docs/monitoring.md](docs/monitoring.md)), and import the dashboard from [`docs/dashboard-FinalProject-TyIorfino.json`](docs/dashboard-FinalProject-TyIorfino.json).

## API endpoints

Base URL: `https://<function-app-domain>/api` · Header: `x-api-key` (plus `x-admin-key` for purge)

| Method | Route | Description |
|---|---|---|
| GET | `/access-reviews` | Get all access reviews |
| GET | `/access-reviews/{id}` | Get one access review |
| POST | `/access-reviews` | Create an access review |
| PUT | `/access-reviews/{id}` | Update an access review |
| DELETE | `/access-reviews/{id}` | Delete an access review |
| GET | `/access-reviews/count` | Count access reviews |
| DELETE | `/access-reviews` | Purge all (requires admin key) |
| PATCH | `/access-reviews/validate` | Flag expired access that is still active |

Full request and response details: [docs/api-reference.md](docs/api-reference.md).

## Project structure

```
├── function_app.py              # API endpoints, Key Vault auth, Table Storage, validation, telemetry
├── requirements.txt             # Python dependencies
├── host.json                    # Azure Functions host configuration
├── local.settings.example.json  # Settings template (no secrets)
├── logic-app/
│   └── validate-workflow.json   # Logic App definition (daily validation + emails)
├── docs/
│   ├── api-reference.md         # Endpoint reference
│   ├── monitoring.md            # Diagnostic settings and KQL queries
│   └── dashboard-FinalProject-TyIorfino.json  # Azure Dashboard export
├── Access Reviewer API/         # Bruno collection (keys stored as secrets, not committed)
└── .gitignore                   # Excludes local.settings.json, .venv, etc.
```

## Work tracking

Work was tracked in Azure DevOps Boards. Each commit references its work item with `AB#<id>`, for example `AB#6` for the validation Logic App.

## Limitations and future work

- One partition key holds all records. That's fine at this scale, but a large tenant would partition by system or access type.
- `validate` reads every record. Very large tables would need paging or a filtered query.
- Future: Microsoft Entra ID (OAuth) instead of API keys, automatic revocation through Microsoft Graph, and an alert rule on Logic App failures.

## Author

**Ty Iorfino**, Sacred Heart University
