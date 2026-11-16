# Access-Review-Delegation-Tracker API Reference

## Overview

A REST API hosted on Azure Functions for tracking privileged and standard access grants (PIM, PAM, PAW, Standard). Records are stored in **Azure Table Storage**. All requests and responses use JSON.

## Base URL

```
https://func-accessreview-dev-eus2-001-c7d0gshua7dqh2ff.eastus2-01.azurewebsites.net/api
```

Local: `http://localhost:7071/api`

## Authentication

Every endpoint requires the API key in the `x-api-key` header. Purge also requires the admin key in `x-admin-key`. Both keys are stored in **Azure Key Vault** (`api-key`, `admin-key`) and are never stored in code or settings.

```
x-api-key: <YOUR_API_KEY>
```

A missing or wrong key returns **401**:

```json
{ "error": "Unauthorized: Invalid or missing API key" }
```

## Common headers

| Header | Required | Used on |
|---|---|---|
| `x-api-key` | Yes | All endpoints |
| `x-admin-key` | Yes | `DELETE /access-reviews` (purge) only |
| `Content-Type: application/json` | When sending a body | POST, PUT |

## Data model: access review

| Field | Type | Set by | Notes |
|---|---|---|---|
| `id` | string (GUID) | Server | Generated on create |
| `user` | string | Client | Who holds the access |
| `role` | string | Client | Role or permission granted |
| `system` | string | Client | Target system |
| `accessType` | string | Client | `PIM`, `PAM`, `PAW` or `Standard` |
| `assignmentType` | string | Client | For example `eligible` or `active` |
| `requiresPAW` | boolean | Client | |
| `grantedBy` | string | Client | Approver |
| `justification` | string | Client | Why the access was granted |
| `startDate` | string (YYYY-MM-DD) | Client | |
| `expirationDate` | string (YYYY-MM-DD) | Client | Used by validation |
| `status` | string | Client / validation | `active`, `revoked`, `expired` |
| `needsRevocation` | boolean | Validation | Set to `true` when the record is flagged |
| `validatedOn` | string (UTC timestamp) | Validation | When it was flagged |

Values must be flat (string, number or boolean). Nested objects or arrays return **400**.

## Endpoint summary

| # | Method | Route | Purpose |
|---|---|---|---|
| 1 | GET | `/access-reviews` | Get all access reviews |
| 2 | GET | `/access-reviews/{id}` | Get one access review **(new)** |
| 3 | POST | `/access-reviews` | Create an access review |
| 4 | PUT | `/access-reviews/{id}` | Update an access review |
| 5 | DELETE | `/access-reviews/{id}` | Delete an access review |
| 6 | GET | `/access-reviews/count` | Count access reviews |
| 7 | DELETE | `/access-reviews` | Purge all access reviews (admin key) |
| 8 | PATCH | `/access-reviews/validate` | Flag expired access that is still active **(new)** |

---

## 1. Get all access reviews

`GET /access-reviews`

```bash
curl "https://<base-url>/access-reviews" -H "x-api-key: <YOUR_API_KEY>"
```

**200 OK**: a JSON array of records (empty array if there are none). **401** if the key is missing or invalid.

## 2. Get one access review (new)

`GET /access-reviews/{id}`

```bash
curl "https://<base-url>/access-reviews/<id>" -H "x-api-key: <YOUR_API_KEY>"
```

| Code | When |
|---|---|
| 200 | Record returned |
| 401 | Missing or invalid API key |
| 404 | No record with that id: `{ "error": "Access review with ID <id> not found" }` |

## 3. Create an access review

`POST /access-reviews`

```bash
curl -X POST "https://<base-url>/access-reviews" \
  -H "x-api-key: <YOUR_API_KEY>" -H "Content-Type: application/json" \
  -d '{"user":"jsmith@contoso.com","role":"Contributor","system":"rg-finance-prod","accessType":"PIM","status":"active","expirationDate":"2026-10-01"}'
```

| Code | When |
|---|---|
| 201 | Created; returns the record with its new `id` |
| 400 | Body missing, not valid JSON, or contains nested objects/arrays |
| 401 | Missing or invalid API key |

## 4. Update an access review

`PUT /access-reviews/{id}`. Replaces the record's fields. The `id` comes from the path.

| Code | When |
|---|---|
| 200 | Updated; returns the record |
| 400 | Invalid body |
| 401 | Missing or invalid API key |
| 404 | No record with that id |

## 5. Delete an access review

`DELETE /access-reviews/{id}`

| Code | When |
|---|---|
| 200 | Deleted; returns a confirmation message |
| 401 | Missing or invalid API key |
| 404 | No record with that id |

## 6. Count access reviews

`GET /access-reviews/count` → **200** `{ "count": 3 }`

## 7. Purge all access reviews

`DELETE /access-reviews`. Requires **both** `x-api-key` and `x-admin-key`.

| Code | When |
|---|---|
| 200 | All records deleted; returns how many |
| 401 | Missing/invalid API key, or missing/invalid admin key |

## 8. Validate access reviews (new)

`PATCH /access-reviews/validate`

**What it does:** checks every record. **If `status` is `active` and `expirationDate` is before today (UTC)**, it updates the record to:

```json
{ "status": "expired", "needsRevocation": true, "validatedOn": "2026-11-16T17:06:12+00:00" }
```

All other records are left unchanged. No request body is needed.

```bash
curl -X PATCH "https://<base-url>/access-reviews/validate" -H "x-api-key: <YOUR_API_KEY>"
```

**200 OK**:

```json
{
  "updatedCount": 1,
  "timestamp": "2026-11-16T17:06:12+00:00"
}
```

`updatedCount` is the number of records this run changed from `active` to `expired`. Running it again right away returns `0`, because those records are no longer active. That makes the endpoint safe to run on a schedule.

Each run also sends a custom event, **`ValidationCompleted`** (with `updatedCount`), to Application Insights.

**Automation:** the Logic App `logic-accessreview-validate-dev-eus2-001` calls this endpoint once a day. It reads `api-key` from Key Vault using its managed identity and emails the result (success or failure).

| Code | When |
|---|---|
| 200 | Validation ran; returns `updatedCount` and `timestamp` |
| 401 | Missing or invalid API key |
| 500 | Storage or Key Vault unreachable |

---

## Error format

All errors return JSON: `{ "error": "<message>" }`

| Code | Typical cause |
|---|---|
| 400 | Bad or missing body, nested values |
| 401 | Missing or wrong `x-api-key` (or `x-admin-key` on purge) |
| 404 | No record with that id |
| 500 | Unexpected server error (details are logged in Application Insights) |