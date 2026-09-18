import os
import csv
import io
import uuid
import zipfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from openai import OpenAI
from services.skill_loader import load_skills, Skill
from services.validator import validate_csv_sections

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

skills: list[Skill] = []
llm_client: OpenAI | None = None

SPLIT_MARKERS = ["---SPLIT---", "===SPLIT===", "=== Header ===", "=== Lines ==="]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global skills, llm_client
    skills = load_skills("skills")
    llm_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
    yield


app = FastAPI(title="SkillForge", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/generator", response_class=HTMLResponse)
async def generator():
    with open("templates/generator.html", "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# API — Skills
# ---------------------------------------------------------------------------

@app.get("/api/skills")
async def list_skills():
    return [
        {"id": s.id, "name": s.name, "description": s.description}
        for s in skills
        if not s.id.startswith("_")
    ]


@app.post("/api/reload-skills")
async def reload_skills():
    global skills
    skills = load_skills("skills")
    return {"status": "ok", "count": len(skills)}


# ---------------------------------------------------------------------------
# API — Process
# ---------------------------------------------------------------------------

@app.post("/api/process")
async def process_file(file: UploadFile, skill_id: str = Form(...)):
    skill = next((s for s in skills if s.id == skill_id), None)
    if not skill:
        return JSONResponse({"error": f"Skill '{skill_id}' not found"}, status_code=400)

    job_id = uuid.uuid4().hex[:8]
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    with open(input_path, "wb") as f:
        f.write(await file.read())

    file_content = _read_file_content(input_path)
    llm_output = _call_llm(skill.instructions, file_content)

    detected_marker = _detect_split_marker(llm_output)
    if detected_marker:
        return _handle_multi_output(llm_output, detected_marker, job_id, skill.id)
    return _handle_single_output(llm_output, job_id, skill.id)


# ---------------------------------------------------------------------------
# LLM — Send skill instructions + file content to the model
# ---------------------------------------------------------------------------

def _call_llm(instructions: str, file_content: str) -> str:
    response = llm_client.chat.completions.create(
        model="qwen2.5-coder-3b-instruct",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"=== File Content ===\n{file_content}"},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Common Utilities — I/O helpers with no business logic
# ---------------------------------------------------------------------------

def _read_file_content(path: str, max_chars: int = 50000) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read(max_chars)


def _save_csv(content: str, path: str) -> int:
    """Save CSV text to file. Returns row count."""
    content = content.strip()
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return content.count("\n")


def _csv_preview(content: str, max_rows: int = 10) -> list[dict]:
    """Parse CSV text into a list of dicts for table preview."""
    reader = csv.DictReader(io.StringIO(content.strip()))
    rows = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(dict(row))
    return rows


def _count_csv_rows(content: str) -> int:
    return max(0, content.strip().count("\n"))


def _create_zip(file_paths: list[str], zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            zf.write(fp, os.path.basename(fp))


def _detect_split_marker(text: str) -> str | None:
    for marker in SPLIT_MARKERS:
        if marker in text:
            return marker
    return None


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the LLM wraps output in them."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def _looks_like_csv(text: str) -> bool:
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return False
    return "," in lines[0] and "," in lines[1]


# ---------------------------------------------------------------------------
# Output Handlers
# ---------------------------------------------------------------------------

def _handle_single_output(llm_output: str, job_id: str, skill_id: str) -> dict:
    """Save CSV output with validation, or return plain text as-is."""
    if _looks_like_csv(llm_output):
        filename = f"{job_id}_output.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        _save_csv(llm_output, filepath)
        validation = validate_csv_sections([{"name": filename, "content": llm_output}])

        return {
            "status": "success",
            "skill": skill_id,
            "preview": _csv_preview(llm_output),
            "row_count": _count_csv_rows(llm_output),
            "download": f"/api/download/{filename}",
            "validation": validation.to_dict(),
        }

    return {
        "status": "success",
        "skill": skill_id,
        "result": llm_output,
    }


def _handle_multi_output(llm_output: str, marker: str, job_id: str, skill_id: str) -> dict:
    """Split output by marker, save each section as CSV, bundle into ZIP."""
    sections = [s.strip() for s in llm_output.split(marker) if s.strip()]
    file_names = _generate_file_names(len(sections), job_id)
    saved_files = []
    previews = []

    for section, name in zip(sections, file_names):
        clean = _strip_code_fences(section)
        filepath = os.path.join(OUTPUT_DIR, name)
        _save_csv(clean, filepath)
        saved_files.append(filepath)
        previews.append({
            "file": name,
            "preview": _csv_preview(clean),
            "row_count": _count_csv_rows(clean),
            "download": f"/api/download/{name}",
        })

    zip_name = f"{job_id}_bundle.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_name)
    _create_zip(saved_files, zip_path)

    validation_sections = [
        {"name": name, "content": _strip_code_fences(section)}
        for section, name in zip(sections, file_names)
    ]
    validation = validate_csv_sections(validation_sections)

    return {
        "status": "success",
        "skill": skill_id,
        "files": previews,
        "download_zip": f"/api/download/{zip_name}",
        "validation": validation.to_dict(),
    }


def _generate_file_names(count: int, job_id: str) -> list[str]:
    if count == 2:
        return [f"{job_id}_header.csv", f"{job_id}_lines.csv"]
    return [f"{job_id}_part{i+1}.csv" for i in range(count)]


# ---------------------------------------------------------------------------
# API — Skill Generator
# ---------------------------------------------------------------------------

SKILL_GEN_PROMPT = """You are a skill template generator. You will receive a source CSV (input) and one or more target CSVs (desired output).

Analyze the mapping between input and output, then generate a skill.md file that describes the transformation rules.

Your output MUST follow this EXACT format (including the --- frontmatter delimiters):

---
name: (short descriptive name)
description: (one line description)
input_types: [".csv"]
---

# (Skill Name)

You are a data transformation expert. Your job is to read the source CSV and produce the target output.

## Source Schema

(table describing each input column with | Source Column | Type | Description |)

## Mapping Rules

(table describing how each target column maps from source with | Target Column | Source | Transformation |)

## Special Rules

(any special rules like 1 row to multiple rows, date format changes, default values, etc.)

## Output Format

(specify exact output format. Use ---SPLIT--- between sections if multiple output files are needed)

IMPORTANT:
- Analyze EVERY column in the input and output carefully
- Detect date format changes, default values, concatenations, lookups
- If the output has more rows than input, describe the row multiplication rule
- If there are multiple output files, use ---SPLIT--- separator format
- Be precise about column names, use exact names from the files
- Output ONLY the skill.md content, nothing else"""


@app.post("/api/generate-skill")
async def generate_skill(
    input_file: UploadFile,
    output_files: list[UploadFile],
    skill_name: str = Form(default=""),
):
    job_id = uuid.uuid4().hex[:8]

    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_input_{input_file.filename}")
    with open(input_path, "wb") as f:
        f.write(await input_file.read())
    input_content = _read_file_content(input_path)

    output_parts = []
    for i, output_file in enumerate(output_files):
        output_path = os.path.join(UPLOAD_DIR, f"{job_id}_output{i}_{output_file.filename}")
        with open(output_path, "wb") as f:
            f.write(await output_file.read())
        output_content = _read_file_content(output_path)
        output_parts.append(f"=== Target File {i+1}: {output_file.filename} ===\n{output_content}")

    user_message = f"=== Source CSV (Input) ===\n{input_content}\n\n" + "\n\n".join(output_parts)
    if skill_name:
        user_message += f"\n\nSuggested skill name: {skill_name}"

    response = llm_client.chat.completions.create(
        model="qwen2.5-coder-3b-instruct",
        messages=[
            {"role": "system", "content": SKILL_GEN_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    return {
        "status": "success",
        "skill_content": response.choices[0].message.content.strip(),
    }


@app.post("/api/upload-skill")
async def upload_skill(
    skill_file: UploadFile = None,
    skill_content: str = Form(default=None),
    skill_filename: str = Form(default=""),
):
    if skill_file:
        content = (await skill_file.read()).decode("utf-8")
        filename = skill_file.filename
    elif skill_content:
        content = skill_content
        filename = skill_filename or f"custom_skill_{uuid.uuid4().hex[:6]}.md"
    else:
        return JSONResponse({"error": "No skill content provided"}, status_code=400)

    if not filename.endswith(".md"):
        filename += ".md"

    safe_name = "".join(c for c in filename if c.isalnum() or c in "-_.")
    skill_path = os.path.join("skills", safe_name)

    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(content)

    global skills
    skills = load_skills("skills")

    return {
        "status": "success",
        "filename": safe_name,
        "skill_count": len(skills),
    }


# ---------------------------------------------------------------------------
# API — Download
# ---------------------------------------------------------------------------

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    media = "application/zip" if filename.endswith(".zip") else "text/csv"
    return FileResponse(path, filename=filename, media_type=media)
