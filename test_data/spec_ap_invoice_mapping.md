# AP Invoice FBDI Mapping Specification

## Source: POS Legacy CSV

| # | Source Column | Type | Example |
|---|---|---|---|
| 1 | bill_no | string | INV-9001 |
| 2 | txn_date | string (YYYY/MM/DD) | 2026/09/10 |
| 3 | total_amt | decimal | 5000 |
| 4 | customer_name | string | สมชาย ใจดี |
| 5 | store_code | string | STR-001 |
| 6 | payment_method | string | CASH, CREDIT, TRANSFER, QR_PAY |
| 7 | cashier_id | string | EMP-101 |
| 8 | discount_pct | decimal | 0, 5, 10, 15, 20 |
| 9 | tax_amt | decimal | 350 |
| 10 | net_amt | decimal | 5350 |

---

## Target 1: AP_INVOICES_INTERFACE (Header)

1 source row → 1 header row

| # | Target Column | Source | Transformation |
|---|---|---|---|
| 1 | INVOICE_NUM | bill_no | Direct copy |
| 2 | INVOICE_DATE | txn_date | Format: YYYY/MM/DD → YYYY-MM-DD |
| 3 | VENDOR_NAME | customer_name | Direct copy |
| 4 | INVOICE_AMOUNT | net_amt | Direct copy (net including tax) |
| 5 | INVOICE_CURRENCY_CODE | — | Default: `THB` |
| 6 | SOURCE | — | Default: `POS_LEGACY` |
| 7 | PAYMENT_METHOD_CODE | payment_method | Direct copy |
| 8 | DESCRIPTION | bill_no | Concatenate: `POS Import ` + bill_no |

---

## Target 2: AP_INVOICE_LINES_INTERFACE (Lines)

1 source row → 2 line rows

### Line 1: ITEM

| # | Target Column | Source | Transformation |
|---|---|---|---|
| 1 | INVOICE_NUM | bill_no | Direct copy (FK to header) |
| 2 | LINE_NUMBER | — | Default: `1` |
| 3 | LINE_TYPE | — | Default: `ITEM` |
| 4 | AMOUNT | total_amt | Direct copy (before tax) |
| 5 | DESCRIPTION | — | Default: `Sale amount` |
| 6 | TAX_CLASSIFICATION_CODE | — | Default: `OUTPUT_TAX` |

### Line 2: TAX

| # | Target Column | Source | Transformation |
|---|---|---|---|
| 1 | INVOICE_NUM | bill_no | Direct copy (FK to header) |
| 2 | LINE_NUMBER | — | Default: `2` |
| 3 | LINE_TYPE | — | Default: `TAX` |
| 4 | AMOUNT | tax_amt | Direct copy |
| 5 | DESCRIPTION | — | Default: `VAT 7%` |
| 6 | TAX_CLASSIFICATION_CODE | — | Default: `OUTPUT_TAX` |

---

## Validation Rules

- INVOICE_NUM must be unique in header
- INVOICE_DATE must be valid date in YYYY-MM-DD format
- INVOICE_AMOUNT must equal sum of ITEM line + TAX line per invoice
- LINE_NUMBER must be sequential per invoice (1, 2)
- All monetary values must have max 2 decimal places
