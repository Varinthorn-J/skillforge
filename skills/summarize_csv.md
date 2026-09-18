---
name: Summarize CSV
description: Analyze and summarize CSV data — row count, column types, statistics
input_types: [".csv"]
---

# Summarize CSV Skill

Analyze the provided CSV data and produce a structured summary.

## Instructions

1. Count total rows and columns
2. Identify each column's data type (numeric, text, date, etc.)
3. For numeric columns: provide min, max, mean
4. For text columns: provide unique count and top 3 most frequent values
5. Flag any columns with missing values

## Output Format

Return a clear markdown-formatted summary report.
