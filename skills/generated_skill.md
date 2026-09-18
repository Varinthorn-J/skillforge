---
name: Transform Bill Data to AP Headers and Lines
description: Transforms a CSV of bill data into two separate CSV files for Accounts Payable headers and lines.
input_types: [".csv"]
---

# Transform Bill Data to AP Headers and Lines

You are a data transformation expert. Your job is to read the source CSV and produce the target output.

## Source Schema

| Source Column | Type   | Description |
|---------------|--------|-------------|
| bill_no       | string | Invoice number |
| txn_date      | string | Transaction date |
| total_amt     | float  | Total amount |
| customer_name | string | Customer name |
| store_code    | string | Store code |
| payment_method | string | Payment method |
| cashier_id   | string | Cashier ID |
| discount_pct  | float  | Discount percentage |
| tax_amt       | float  | Tax amount |
| net_amt      | float  | Net amount |

## Mapping Rules

| Target Column | Source    | Transformation |
|---------------|-----------|----------------|
| INVOICE_NUM   | bill_no     | Copy            |
| INVOICE_DATE   | txn_date    | Convert to YYYY-MM-DD format |
| VENDOR_NAME   | customer_name | Copy            |
| INVOICE_AMOUNT | net_amt      | Copy            |
| INVOICE_CURRENCY_CODE | THB | Fixed value |
| SOURCE        | bill_no     | POS_LEGACY       |
| PAYMENT_METHOD_CODE | payment_method | CASH, CREDIT, QR_PAY, TRANSFER |
| DESCRIPTION   | customer_name | POS Import INV-<bill_no> |

## Special Rules

- The output has two files: `example_output_ap_headers.csv` and `example_output_ap_lines.csv`.
- Each invoice in the source CSV is transformed into one header row in `example_output_ap_headers.csv` and multiple line rows in `example_output_ap_lines.csv`.

## Output Format

### example_output_ap_headers.csv
CSV text with ---SPLIT--- separator format.

### example_output_ap_lines.csv
CSV text with ---SPLIT--- separator format.