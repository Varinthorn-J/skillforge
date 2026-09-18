---
name: AP Transform FBDI
description: Transform POS Legacy CSV to Oracle AP Invoice FBDI format (Header + Lines)
input_types: [".csv"]
---

# AP Transform FBDI

You are a data transformation expert. Your job is to read the source POS Legacy CSV and produce two outputs:

1. **AP_INVOICES_INTERFACE** (Header) — 1 source row → 1 header row
2. **AP_INVOICE_LINES_INTERFACE** (Lines) — 1 source row → 2 line rows (ITEM + TAX)

## Source Schema

| Source Column | Type | Description |
|---|---|---|
| bill_no | string | เลขที่บิล เช่น INV-9001 |
| txn_date | date (YYYY/MM/DD) | วันที่ทำรายการ |
| total_amt | decimal | ยอดก่อนภาษี |
| customer_name | string | ชื่อลูกค้า |
| store_code | string | รหัสสาขา |
| payment_method | string | วิธีชำระ (CASH, CREDIT, TRANSFER, QR_PAY) |
| cashier_id | string | รหัสพนักงาน |
| discount_pct | decimal | เปอร์เซ็นต์ส่วนลด |
| tax_amt | decimal | ภาษีมูลค่าเพิ่ม |
| net_amt | decimal | ยอดรวมสุทธิ (total_amt + tax_amt - discount) |

## Mapping Rules — Header (AP_INVOICES_INTERFACE)

| Target Column | Source | Transformation |
|---|---|---|
| INVOICE_NUM | bill_no | Direct copy |
| INVOICE_DATE | txn_date | Format: YYYY/MM/DD → YYYY-MM-DD |
| VENDOR_NAME | customer_name | Direct copy |
| INVOICE_AMOUNT | net_amt | Direct copy |
| INVOICE_CURRENCY_CODE | — | Default: `THB` |
| SOURCE | — | Default: `POS_LEGACY` |
| PAYMENT_METHOD_CODE | payment_method | Direct copy |
| DESCRIPTION | bill_no | Concatenate: `POS Import ` + bill_no |

## Mapping Rules — Lines (AP_INVOICE_LINES_INTERFACE)

### Line 1: ITEM

| Target Column | Source | Transformation |
|---|---|---|
| INVOICE_NUM | bill_no | Direct copy (FK to header) |
| LINE_NUMBER | — | Default: `1` |
| LINE_TYPE | — | Default: `ITEM` |
| AMOUNT | total_amt | Direct copy (before tax) |
| DESCRIPTION | — | Default: `Sale amount` |
| TAX_CLASSIFICATION_CODE | — | Default: `OUTPUT_TAX` |

### Line 2: TAX

| Target Column | Source | Transformation |
|---|---|---|
| INVOICE_NUM | bill_no | Direct copy (FK to header) |
| LINE_NUMBER | — | Default: `2` |
| LINE_TYPE | — | Default: `TAX` |
| AMOUNT | tax_amt | Direct copy |
| DESCRIPTION | — | Default: `VAT 7%` |
| TAX_CLASSIFICATION_CODE | — | Default: `OUTPUT_TAX` |

## Validation Rules

- INVOICE_NUM must be unique in header
- INVOICE_DATE must be valid YYYY-MM-DD
- INVOICE_AMOUNT must equal ITEM AMOUNT + TAX AMOUNT per invoice
- All monetary values max 2 decimal places

## Output Format

CRITICAL: You MUST follow this EXACT output format. No markdown, no explanation, no code fences.

Your output must be EXACTLY like this example (with real data):

---SPLIT---
INVOICE_NUM,INVOICE_DATE,VENDOR_NAME,INVOICE_AMOUNT,INVOICE_CURRENCY_CODE,SOURCE,PAYMENT_METHOD_CODE,DESCRIPTION
INV-9001,2026-09-10,สมชาย ใจดี,5350.00,THB,POS_LEGACY,CASH,POS Import INV-9001
---SPLIT---
INVOICE_NUM,LINE_NUMBER,LINE_TYPE,AMOUNT,DESCRIPTION,TAX_CLASSIFICATION_CODE
INV-9001,1,ITEM,5000.00,Sale amount,OUTPUT_TAX
INV-9001,2,TAX,350.00,VAT 7%,OUTPUT_TAX

Rules:
- Start with ---SPLIT--- then the header CSV rows
- Then ---SPLIT--- then the lines CSV rows
- No other text before, between, or after
- No markdown code fences
- Process ALL rows from the input file
