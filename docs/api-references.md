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