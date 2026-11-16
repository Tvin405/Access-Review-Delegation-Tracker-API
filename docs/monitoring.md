# Monitoring and diagnostic logging

All resources send logs to the Log Analytics workspace `workspace-appi-accessreview-dev-eus2-001`.

| Resource | Diagnostic setting | Logs enabled |
|---|---|---|
| Key Vault `kv-accrev-dev-eus2-001` | diag-kv-to-law | AuditEvent (who read which secret) |
| Logic App `logic-accessreview-validate-dev-eus2-001` | diag-logic-to-law | WorkflowRuntime (every run and action) |
| Storage `staccessreviewdeveus2001` (table) | diag-table-to-law | StorageRead, StorageWrite, StorageDelete |

Metrics are not exported, to keep costs low.

## Queries

Key Vault and Logic App activity:
```kusto
AzureDiagnostics
| where TimeGenerated > ago(24h)
| where ResourceProvider in ("MICROSOFT.LOGIC", "MICROSOFT.KEYVAULT")
| project TimeGenerated, ResourceProvider, Resource, OperationName, status_s, ResultType
| order by TimeGenerated desc
```

Table operations:
```kusto
StorageTableLogs
| where TimeGenerated > ago(24h)
| summarize count() by OperationName
```