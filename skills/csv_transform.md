---
name: CSV Transform
description: Transform CSV file columns to match a target schema
input_types: [".csv"]
---

# CSV Transform Skill

You are an expert Data Engineer. Your job is to analyze the source CSV and generate a JSON mapping plan to transform it into the target schema.

## Rules

1. Map each required target column to the most semantically relevant column in the Source CSV.
2. If action is `DIRECT` or `FORMAT_DATE`, `source_column` MUST be filled with the exact header name from Source CSV (NEVER null).
3. If action is `DEFAULT`, `source_column` MUST be null and `default_value` must be provided.
4. For date conversions, set action=`FORMAT_DATE` and extract the date source column.

## Target Schema

```
Target Schema: Oracle AP Invoice
Columns required:
- INVOICE_NUM (invoice numbers)
- INVOICE_DATE (date, FORMAT_DATE as %Y-%m-%d)
- AMOUNT (invoice amount)
- SOURCE (DEFAULT value 'POS_LEGACY')
```

## Output Format

Output ONLY valid JSON conforming to the MappingPlan schema.
