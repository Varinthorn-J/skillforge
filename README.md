# SkillForge

Local LLM-powered data transformation framework. Define transformation logic in **skill.md** files (the "brain"), while Python handles only common I/O (the "hands"). Upload input and output examples to auto-generate skills, then transform data through a visual web UI — all processing stays on your machine.

![SkillForge Transform](docs/screenshot.png)

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
                                      │  Download     │
                                      │  CSV / ZIP    │
                                      └──────────────┘
```

**Skill.md** controls all transformation logic — mapping rules, business rules, output format.
**Code** only handles common I/O — save CSV, split files, create ZIP, validate output, serve downloads.

## Features

- **Transform** — Upload a file, pick a skill, get transformed output with validation
- **Skill Generator** — Upload input + desired output(s), AI generates a reusable skill template
- **Multi-file output** — `---SPLIT---` markers for generating multiple files (e.g. AP Headers + Lines), bundled as ZIP
- **Real-time logs** — SSE-powered log panel shows LLM processing as it happens
- **Validation engine** — CSV structure, date formats, numeric values, cross-file key consistency
- **Skill management** — Create, edit, delete, upload skills with category tags (Example/Custom)
- **Configurable** — `.env` for LLM endpoint, model, output naming, directories
- **Keyboard shortcuts** — Ctrl+Enter to transform, Escape to close panels

## Quick Start

### Prerequisites

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) (or any OpenAI-compatible local LLM server)

### Setup

```bash
git clone https://github.com/Varinthorn-J/skillforge.git
cd skillforge
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
```

### Run

1. Start LM Studio and load a model (e.g. Qwen 2.5 Coder 3B Instruct)
2. Start the local server on port 1234

```bash
uvicorn app:app --reload --port 8000
```

3. Open [http://localhost:8000](http://localhost:8000)

## Configuration

Edit `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://127.0.0.1:1234/v1` | OpenAI-compatible API endpoint |
| `LLM_MODEL` | `qwen2.5-coder-3b-instruct` | Model name |
| `OUTPUT_PREFIX` | `skillforge` | Prefix for output filenames |
| `OUTPUT_SUFFIX` | _(empty)_ | Suffix for output filenames |
| `LOG_LEVEL` | `INFO` | Logging level |

## Pages

### Transform (`/`)

1. Select a skill from the list
2. Upload your input file (CSV)
3. Click **Transform** (or Ctrl+Enter)
4. View results in table preview with validation report
5. Download output as CSV or ZIP (multi-file)

### Skill Generator (`/generator`)

1. Enter a skill name
2. Upload **input file** (source CSV)
3. Upload **output file(s)** (click "+ Add file" for multiple outputs)
4. Click **Generate Skill** — AI analyzes the mapping and creates a skill template
5. Review, edit, then **Save as Skill**

## Writing a Skill

Create a `.md` file in `skills/` (or use the Skill Generator):

```markdown
---
name: POS to AP FBDI
description: Transform POS transactions to Oracle AP FBDI format
input_types: [".csv"]
output_files: ["ap_headers", "ap_lines"]
category: custom
---

# Transformation Rules

For EACH input row, create:
- 1 row in the HEADER file
- 2 rows in the LINES file (ITEM + TAX)

## Header File Columns
INVOICE_NUM = bill_no
INVOICE_DATE = txn_date (change / to -)
VENDOR_NAME = customer_name
...
```

The Markdown body becomes the LLM system prompt. The uploaded file is sent as the user message.

### Output Conventions

| LLM Output | What Happens |
|---|---|
| CSV text | Saved as single CSV file |
| Sections separated by `---SPLIT---` | Split into multiple CSV files + bundled as ZIP |
| Plain text | Displayed as-is in the UI |

## Project Structure

```
skillforge/
├── app.py                    # FastAPI server + LLM integration
├── services/
│   ├── skill_loader.py       # Parses .md skills with frontmatter
│   ├── validator.py          # CSV validation engine
│   └── transformer_service.py
├── skills/                   # Skill .md files (the "brain")
├── templates/
│   ├── index.html            # Transform page
│   ├── generator.html        # Skill Generator page
│   └── logs.html             # Standalone logs page
├── static/style.css          # Shared CSS
├── test_data/                # Sample input/output files
├── .env.example              # Configuration template
└── requirements.txt
```

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Transform page |
| `GET` | `/generator` | Skill Generator page |
| `GET` | `/api/skills` | List available skills |
| `GET` | `/api/skills/{id}` | Get skill content |
| `PUT` | `/api/skills/{id}` | Update skill content |
| `DELETE` | `/api/skills/{id}` | Delete a skill |
| `POST` | `/api/process` | Transform: upload file + skill_id |
| `POST` | `/api/generate-skill` | Generate skill from input + output examples |
| `POST` | `/api/upload-skill` | Upload/save a skill file |
| `GET` | `/api/config` | Get current LLM config |
| `GET` | `/api/logs/stream` | SSE real-time log stream |
| `GET` | `/api/download/{filename}` | Download output file |

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **LLM**: Any OpenAI-compatible server (LM Studio, Ollama, vLLM)
- **Frontend**: Vanilla HTML/CSS/JS (no build step)
- **Fonts**: Space Grotesk + Inter + JetBrains Mono
