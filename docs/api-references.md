# Access-Review-Delegation-Tracker API Reference

## Overview

A REST API hosted on Azure Functions for tracking privileged and standard access grants (PIM, PAM, PAW, Standard). Records are stored in **Azure Table Storage**. All requests and responses use JSON.

## Base URL

```
https://func-accessreview-dev-eus2-001-c7d0gshua7dqh2ff.eastus2-01.azurewebsites.net/api
```

Local: `http://localhost:7071/api`

## Authentication

Every endpoint requires the API key in the `x-api-key` header. Purge also requires the admin key in `x-admin-key`. Both keys are stored in **Azure Key Vault** as the secrets `api-key` and `admin-key`. The Function App reads them at request time with its managed identity. They are never stored in code or app settings.

```
x-api-key: <YOUR_API_KEY>
```

The API key is checked **first** on every endpoint, before the id or body. A request with a bad key always gets 401, even if the id doesn't exist or the body is invalid.

Missing or wrong API key → **401**:

```json
{ "error": "Unauthorized: Invalid or missing API key" }
```

Missing or wrong admin key on purge → **401**:

```json
{ "error": "Unauthorized: Admin key required for purge" }
```

If Key Vault can't be reached, or a secret doesn't exist, the request fails with **500** `{"error": "Internal Server Error"}` and the details are logged to Application Insights.

## Common headers

| Header | Required | Used on |
|---|---|---|
| `x-api-key` | Yes | All endpoints |
| `x-admin-key` | Yes | `DELETE /access-reviews` (purge) only |
| `Content-Type: application/json` | When sending a body | POST, PUT |

## Data model: access review

| Field | Type | Required | Rules |
|---|---|---|---|
| `id` | string (GUID) | Set by server | Generated on create. Any `id` sent by the client is ignored. |
| `user` | string | **Yes** | Not empty |
| `role` | string | **Yes** | Not empty |
| `accessType` | string | **Yes** | One of `PIM`, `PAM`, `PAW`, `Standard` |
| `status` | string | **Yes** | One of `active`, `revoked`, `expired` |
| `startDate` | string | **Yes** | `YYYY-MM-DD` |
| `expirationDate` | string | **Yes** | `YYYY-MM-DD`, on or after `startDate` |
| `system` | string | No | |
| `assignmentType` | string | No | For example `eligible` or `active` |
| `requiresPAW` | boolean | No | |
| `grantedBy` | string | No | Approver |
| `justification` | string | No | |
| `needsRevocation` | boolean | Set by validation | `true` when the record is flagged |
| `validatedOn` | string (UTC timestamp) | Set by validation | When the record was flagged |

All values must be flat (string, number or boolean). Nested objects or arrays are rejected.

## Validation errors (400)

POST and PUT check the body in this order and return the **first** error found:

| Problem | Response body |
|---|---|
| Body isn't valid JSON | `{"error": "HTTP request does not contain valid JSON data"}` |
| Body is JSON but not an object (for example an array) | `{"error": "Request body must be a JSON object"}` |
| A value is an object or array | `{"error": "'role' must be a string, number, or boolean, not a nested object or array"}` (uses the field's name) |
| Required fields missing or empty | `{"error": "Missing required fields: user, role, accessType, status, startDate, expirationDate"}` (lists only the missing ones) |
| Bad `accessType` | `{"error": "accessType must be one of: PIM, PAM, PAW, Standard"}` |
| Bad `status` | `{"error": "status must be one of: active, revoked, expired"}` |
| Bad date format | `{"error": "startDate and expirationDate must be dates in YYYY-MM-DD format"}` |
| Expiration before start | `{"error": "expirationDate must be on or after startDate"}` |

## Endpoint summary

| # | Method | Route | Purpose |
|---|---|---|---|
| 1 | GET | `/access-reviews` | Get all access reviews |
| 2 | GET | `/access-reviews/{id}` | Get one access review **(new)** |
| 3 | POST | `/access-reviews` | Create an access review |
| 4 | PUT | `/access-reviews/{id}` | Replace an access review |
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

**200 OK**: a JSON array of records. It's `[]` when there are none.

| Code | When |
|---|---|
| 200 | Records returned |
| 401 | Missing or invalid API key |

## 2. Get one access review (new)

`GET /access-reviews/{id}`

```bash
curl "https://<base-url>/access-reviews/<id>" -H "x-api-key: <YOUR_API_KEY>"
```

**200 OK**: the record, including `id`.

**404 Not Found**:

```json
{ "error": "Access review with ID does-not-exist not found" }
```

| Code | When |
|---|---|
| 200 | Record returned |
| 401 | Missing or invalid API key |
| 404 | No record with that id |

## 3. Create an access review

`POST /access-reviews`

```bash
curl -X POST "https://<base-url>/access-reviews" \
  -H "x-api-key: <YOUR_API_KEY>" -H "Content-Type: application/json" \
  -d '{"user":"jsmith@contoso.com","role":"Contributor","system":"rg-finance-prod","accessType":"PIM","assignmentType":"active","requiresPAW":false,"grantedBy":"it-director@contoso.com","justification":"Quarter-end finance close","startDate":"2026-09-01","expirationDate":"2026-10-01","status":"active"}'
```

**201 Created**: the record exactly as sent, plus the new `id`:

```json
{
  "user": "jsmith@contoso.com",
  "role": "Contributor",
  "system": "rg-finance-prod",
  "accessType": "PIM",
  "assignmentType": "active",
  "requiresPAW": false,
  "grantedBy": "it-director@contoso.com",
  "justification": "Quarter-end finance close",
  "startDate": "2026-09-01",
  "expirationDate": "2026-10-01",
  "status": "active",
  "id": "3f2b8c1e-6a4d-4e2f-9b7a-1c5d8e9f0a12"
}
```

| Code | When |
|---|---|
| 201 | Created |
| 400 | Any validation error in the table above |
| 401 | Missing or invalid API key |

## 4. Replace an access review

`PUT /access-reviews/{id}`

Replaces the **whole** record with the body. The body must pass the same validation as POST. Fields left out of the body are removed, including `needsRevocation` and `validatedOn`. The `id` always comes from the path.

**200 OK**: the new record, including `id`.

| Code | When |
|---|---|
| 200 | Replaced; returns the record |
| 400 | Any validation error in the table above |
| 401 | Missing or invalid API key |
| 404 | `{"error": "Access review with ID <id> not found"}` (checked before the body) |

## 5. Delete an access review

`DELETE /access-reviews/{id}`

**200 OK**:

```json
{ "message": "Access review with ID 3f2b8c1e-6a4d-4e2f-9b7a-1c5d8e9f0a12 deleted" }
```

| Code | When |
|---|---|
| 200 | Deleted |
| 401 | Missing or invalid API key |
| 404 | `{"error": "Access review with ID <id> not found"}` |

## 6. Count access reviews

`GET /access-reviews/count`

**200 OK**:

```json
{ "count": 3 }
```

| Code | When |
|---|---|
| 200 | Count returned |
| 401 | Missing or invalid API key |

## 7. Purge all access reviews

`DELETE /access-reviews`. Requires **both** `x-api-key` and `x-admin-key`.

```bash
curl -X DELETE "https://<base-url>/access-reviews" \
  -H "x-api-key: <YOUR_API_KEY>" -H "x-admin-key: <YOUR_ADMIN_KEY>"
```

**200 OK**. The count is part of the message text, not a separate field:

```json
{ "message": "All access reviews deleted. Total deleted: 3" }
```

| Code | When |
|---|---|
| 200 | All records deleted (`Total deleted: 0` if the table was already empty) |
| 401 | `Unauthorized: Invalid or missing API key`, or `Unauthorized: Admin key required for purge` |

## 8. Validate access reviews (new)

`PATCH /access-reviews/validate`. No request body.

**Rule:** for every record, **if `status` is `active` and `expirationDate` is before today (UTC)**, the record is updated (merged) with:

```json
{ "status": "expired", "needsRevocation": true, "validatedOn": "2026-11-16T17:06:12+00:00" }
```

Other records are not changed: revoked, already expired, not yet expired, or no `expirationDate`.

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

- `updatedCount` is the number of records this run changed from `active` to `expired`. A second run right away returns `0`, because those records are no longer active. That makes the endpoint safe to run on a schedule.
- `timestamp` is the same value written to each flagged record's `validatedOn`, so a response can be matched to the records it changed.
- Each run also sends the custom event **`ValidationCompleted`** (with `updatedCount`) to Application Insights.
- The Logic App `logic-accessreview-validate-dev-eus2-001` calls this endpoint once a day. It reads `api-key` from Key Vault with its managed identity and emails the result.

| Code | When |
|---|---|
| 200 | Validation ran |
| 401 | Missing or invalid API key |

---

## Error format

Every error returns JSON with a single `error` field:

```json
{ "error": "<message>" }
```

| Code | Cause |
|---|---|
| 400 | Invalid body (see Validation errors) |
| 401 | Missing or wrong `x-api-key`, or missing or wrong `x-admin-key` on purge |
| 404 | No record with that id |
| 500 | Unexpected error, for example Key Vault or Table Storage unreachable. Body is `{"error": "Internal Server Error"}`; details are in Application Insights. |
