# SkillForge

A skill-driven data transformation engine powered by a local LLM. Upload a file, pick a skill, and let the AI handle the rest — all processing stays on your machine.

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Upload File │────▶│  Skill.md   │────▶│  Local LLM   │
│  (CSV, etc.) │     │  (the brain)│     │  (LM Studio) │
└─────────────┘     └─────────────┘     └──────┬───────┘
                                               │
                                               ▼
                                      ┌──────────────┐
                                      │  Validate    │
                                      │  Output      │
                                      └──────┬───────┘
                                               │
                                               ▼
                                      ┌──────────────┐
                                      │  Common I/O  │
                                      │  save / zip  │
                                      └──────┬───────┘
                                               │
                                               ▼
                                      ┌──────────────┐
                                      │  Download     │
                                      │  CSV / ZIP    │
                                      └──────────────┘
```

**Skill.md** controls all transformation logic — mapping rules, business rules, output format.

**Code** only handles common I/O — save CSV, split files, create ZIP, validate output, serve downloads. No business logic in code.

## Features

- **Transform** — Upload a file, pick a skill, get transformed output with validation
- **Skill Generator** — Upload input + desired output(s), AI generates a reusable skill template
- **Validation** — Auto-checks CSV structure, date formats, numeric values, cross-file key consistency
- **Multi-file output** — Skills can produce multiple files (e.g. FBDI header + lines + property), bundled as ZIP

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **LLM:** Qwen 2.5 Coder 3B Instruct via LM Studio (localhost:1234)
- **Frontend:** Single-page HTML (no framework)
- **Architecture:** Skill-driven — add new transforms by writing a `.md` file

## Prerequisites

- Python 3.10+
- LM Studio with Qwen2.5-Coder-3B-Instruct loaded

## Quick Start

### 1. Start LM Studio

1. Open LM Studio
2. Load **Qwen2.5-Coder-3B-Instruct-GGUF** model
3. Go to **Developer / Local Server** tab
4. Start server on port **1234** (`http://127.0.0.1:1234`)

### 2. Setup Project

```bash
cd D:\ai-data-transformer

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the App

```bash
uvicorn app:app --reload --port 8000
```

### 4. Open in Browser

- **Transform page:** `http://localhost:8000`
- **Skill Generator:** `http://localhost:8000/generator`

## Pages

### Transform (`/`)

1. Select a skill from the list
2. Upload your input file (CSV)
3. Click **Transform**
4. View results in table preview with validation report
5. Download output as CSV or ZIP (multi-file)

### Skill Generator (`/generator`)

1. Enter a skill name
2. Upload **input file** (source CSV)
3. Upload **output file(s)** (desired result — click "+ Add file" for multiple outputs like header, lines, property)
4. Click **Generate Skill** — AI analyzes the mapping and creates a skill template
5. Review and edit the generated skill in the editor
6. Click **Save as Skill** — saves to `skills/` folder and becomes available immediately
7. Go to Transform page to use the new skill

## Project Structure

```
ai-data-transformer/
├── app.py                  # FastAPI server (common I/O + validation only)
├── requirements.txt
├── skills/                 # Skill definitions (the brain)
│   ├── _TEMPLATE.md        # Template for writing new skills
│   ├── csv_transform.md
│   ├── summarize_csv.md
│   └── ap_to_fbdi_template.md
├── templates/
│   ├── index.html          # Transform page
│   └── generator.html      # Skill Generator page
├── services/
│   ├── skill_loader.py     # Reads skill.md files
│   └── validator.py        # Output validation (CSV structure, dates, numbers, keys)
├── test_data/
│   ├── legacy_pos.csv                  # Sample input (20 rows POS data)
│   ├── example_output_ap_headers.csv   # Example FBDI header output
│   ├── example_output_ap_lines.csv     # Example FBDI lines output
│   └── spec_ap_invoice_mapping.md      # Mapping specification reference
├── uploads/                # Uploaded files (auto-created)
├── outputs/                # Generated files (auto-created)
├── domain/                 # Pydantic models (legacy)
├── port/                   # Port interfaces (legacy)
└── adapters/               # Adapter implementations (legacy)
```

## Writing a Skill

Create a `.md` file in `skills/` (or use the Skill Generator):

```markdown
---
name: My Skill
description: What this skill does
input_types: [".csv"]
---

# My Skill

(Instructions for the LLM — source schema, mapping rules, output format)
```

The skill.md content becomes the LLM's system prompt. The uploaded file content is sent as the user message.

See `skills/_TEMPLATE.md` for a detailed template.

### Output Conventions

| LLM Output | What Happens |
|---|---|
| CSV text | Saved as single CSV file |
| Sections separated by `---SPLIT---` | Split into multiple CSV files + bundled as ZIP |
| Plain text | Displayed as-is in the UI |

### Validation

Output is automatically validated for:
- CSV structure (consistent column count)
- Empty values (warnings)
- Date format (columns containing "DATE" → must be YYYY-MM-DD)
- Numeric values (columns containing "AMOUNT"/"NUMBER" → must be valid numbers)
- Cross-file key consistency (keys in lines file must exist in header file)

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Transform page |
| GET | `/generator` | Skill Generator page |
| GET | `/api/skills` | List available skills |
| POST | `/api/process` | Upload file + skill_id → transform |
| POST | `/api/generate-skill` | Upload input + output(s) → generate skill.md |
| POST | `/api/upload-skill` | Save skill content to skills/ folder |
| POST | `/api/reload-skills` | Reload skills from disk |
| GET | `/api/download/{filename}` | Download output file (CSV or ZIP) |
