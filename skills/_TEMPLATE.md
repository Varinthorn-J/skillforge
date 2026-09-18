---
name: (ชื่อ skill ที่จะโชว์ใน UI)
description: (คำอธิบายสั้นๆ 1 บรรทัด)
input_types: [".csv"]
---

# (ชื่อ Skill)

(บอก LLM ว่ามันคือใคร และต้องทำอะไร เช่น)
You are a data transformation expert. Your job is to read the source CSV and produce the target output.

## Source Schema

(อธิบาย input ที่จะเข้ามา)

| Source Column | Type | Description |
|---|---|---|
| column_a | string | รหัสรายการ |
| column_b | date (YYYY/MM/DD) | วันที่ทำรายการ |
| column_c | decimal | จำนวนเงิน |

## Mapping Rules

(บอกว่า source → target ต้อง map ยังไง)

| Target Column | Source | Transformation |
|---|---|---|
| TARGET_ID | column_a | Direct copy |
| TARGET_DATE | column_b | Format: YYYY/MM/DD → YYYY-MM-DD |
| TARGET_AMT | column_c | Direct copy |
| CURRENCY | — | Default: `THB` |
| NOTE | column_a | Concatenate: `Import ` + column_a |

## Special Rules

(กฎพิเศษ ถ้ามี เช่น 1 row แตกเป็นหลาย rows, validation, etc.)

- (เช่น) 1 source row → 2 output rows (ITEM line + TAX line)
- (เช่น) AMOUNT must have max 2 decimal places

## Output Format

(บอกว่าให้ LLM คืนผลลัพธ์เป็นอะไร)

Return the result as CSV text with headers on the first line.
Do NOT include any explanation, only the CSV content.
