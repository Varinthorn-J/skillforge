---
name: POS to AP FBDI
description: Transform POS transactions to Oracle AP FBDI format (Headers + Lines)
input_types: [".csv"]
output_files: ["ap_headers", "ap_lines"]
category: custom
---

# POS to AP FBDI

You are a data transformation engine. Read the input CSV and output ONLY raw CSV data.

## Rules

For EACH input row, create:
- 1 row in the HEADER file
- 2 rows in the LINES file (1 ITEM row + 1 TAX row)

## Header File Columns

INVOICE_NUM = bill_no (copy as is)
INVOICE_DATE = txn_date (change / to - so 2026/09/10 becomes 2026-09-10)
VENDOR_NAME = customer_name (copy as is)
INVOICE_AMOUNT = net_amt (copy as is)
INVOICE_CURRENCY_CODE = always THB
SOURCE = always POS_LEGACY
PAYMENT_METHOD_CODE = payment_method (copy as is: CASH, CREDIT, TRANSFER, QR_PAY)
DESCRIPTION = "POS Import " + bill_no (example: POS Import INV-9001)

## Lines File Columns

Row 1 (ITEM):
INVOICE_NUM = bill_no
LINE_NUMBER = 1
LINE_TYPE = ITEM
AMOUNT = total_amt
DESCRIPTION = Sale amount
TAX_CLASSIFICATION_CODE = OUTPUT_TAX

Row 2 (TAX):
INVOICE_NUM = bill_no
LINE_NUMBER = 2
LINE_TYPE = TAX
AMOUNT = tax_amt
DESCRIPTION = VAT 7%
TAX_CLASSIFICATION_CODE = OUTPUT_TAX

## Output Format

CRITICAL: Output ONLY CSV data. No markdown. No code fences. No explanations.
Header row appears ONCE per file. NEVER repeat it.
Separate the two files with ---SPLIT--- on its own line.

INVOICE_NUM,INVOICE_DATE,VENDOR_NAME,INVOICE_AMOUNT,INVOICE_CURRENCY_CODE,SOURCE,PAYMENT_METHOD_CODE,DESCRIPTION
INV-9001,2026-09-10,John Smith,5350,THB,POS_LEGACY,CASH,POS Import INV-9001
INV-9002,2026-09-11,Emily Davis,12198,THB,POS_LEGACY,CREDIT,POS Import INV-9002
---SPLIT---
INVOICE_NUM,LINE_NUMBER,LINE_TYPE,AMOUNT,DESCRIPTION,TAX_CLASSIFICATION_CODE
INV-9001,1,ITEM,5000,Sale amount,OUTPUT_TAX
INV-9001,2,TAX,350,VAT 7%,OUTPUT_TAX
INV-9002,1,ITEM,12000,Sale amount,OUTPUT_TAX
INV-9002,2,TAX,798,VAT 7%,OUTPUT_TAX
