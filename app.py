import asyncio
import json
import logging
import os
import csv
import io
import uuid
import zipfile
from collections import deque
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

LOG_BUFFER_SIZE = 500
log_buffer: deque[dict] = deque(maxlen=LOG_BUFFER_SIZE)
log_subscribers: list[asyncio.Queue] = []


class BufferHandler(logging.Handler):
    def emit(self, record):
        entry = {
            "time": self.format(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        log_buffer.append(entry)
        for q in log_subscribers[:]:
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("skillforge")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

buffer_handler = BufferHandler()
buffer_handler.setLevel(logging.DEBUG)
buffer_handler.setFormatter(logging.Formatter("%(asctime)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(buffer_handler)

from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from openai import OpenAI
from services.skill_loader import load_skills, Skill
from services.validator import validate_csv_sections

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder-3b-instruct")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
SKILLS_DIR = os.getenv("SKILLS_DIR", "skills")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "skillforge")
OUTPUT_SUFFIX = os.getenv("OUTPUT_SUFFIX", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

skills: list[Skill] = []
llm_client: OpenAI | None = None

SPLIT_MARKERS = ["---SPLIT---", "===SPLIT===", "=== Header ===", "=== Lines ==="]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global skills, llm_client
    skills = load_skills(SKILLS_DIR)
    logger.info("Loaded %d skills", len(skills))
    llm_client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    logger.info("LLM client connected to %s", LLM_BASE_URL)
    yield


app = FastAPI(title="SkillForge", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


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


@app.get("/logs", response_class=HTMLResponse)
async def logs_page():
    with open("templates/logs.html", "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# API — Config
# ---------------------------------------------------------------------------

@app.get("/api/config")
async def get_config():
    return {"model": LLM_MODEL, "base_url": LLM_BASE_URL}


# ---------------------------------------------------------------------------
# API — Skills
# ---------------------------------------------------------------------------

@app.get("/api/skills")
async def list_skills():
    return [
        {"id": s.id, "name": s.name, "description": s.description, "category": s.category}
        for s in skills
        if not s.id.startswith("_")
    ]


@app.get("/api/skills/{skill_id}")
async def get_skill(skill_id: str):
    skill = next((s for s in skills if s.id == skill_id), None)
    if not skill:
        return JSONResponse({"error": "Skill not found"}, status_code=404)

    filepath = os.path.join(SKILLS_DIR, f"{skill_id}.md")
    with open(filepath, "r", encoding="utf-8") as f:
        raw_content = f.read()

    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "content": raw_content,
    }


@app.put("/api/skills/{skill_id}")
async def update_skill(skill_id: str, skill_content: str = Form(...)):
    filepath = os.path.join(SKILLS_DIR, f"{skill_id}.md")
    if not os.path.exists(filepath):
        return JSONResponse({"error": "Skill not found"}, status_code=404)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(skill_content)

    global skills
    skills = load_skills(SKILLS_DIR)
    logger.info("Skill updated: %s", skill_id)

    return {"status": "success", "skill_id": skill_id}


@app.delete("/api/skills/{skill_id}")
async def delete_skill(skill_id: str):
    filepath = os.path.join(SKILLS_DIR, f"{skill_id}.md")
    if not os.path.exists(filepath):
        return JSONResponse({"error": "Skill not found"}, status_code=404)

    os.remove(filepath)

    global skills
    skills = load_skills(SKILLS_DIR)
    logger.info("Skill deleted: %s", skill_id)

    return {"status": "success", "skill_id": skill_id}


@app.post("/api/reload-skills")
async def reload_skills():
    global skills
    skills = load_skills(SKILLS_DIR)
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

    try:
        logger.info("[%s] Processing with skill '%s'", job_id, skill_id)
        llm_output = await _call_llm(skill.instructions, file_content)
        logger.info("[%s] LLM returned %d chars", job_id, len(llm_output))

        detected_marker = _detect_split_marker(llm_output)
        if detected_marker:
            logger.info("[%s] Multi-output detected (marker: %s)", job_id, detected_marker)
            return _handle_multi_output(llm_output, detected_marker, job_id, skill)
        return _handle_single_output(llm_output, job_id, skill)
    except Exception as e:
        logger.error("[%s] Process failed: %s", job_id, str(e))
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# LLM — Send skill instructions + file content to the model
# ---------------------------------------------------------------------------

def _call_llm_sync(instructions: str, file_content: str) -> str:
    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"=== File Content ===\n{file_content}"},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


async def _call_llm(instructions: str, file_content: str) -> str:
    return await asyncio.to_thread(_call_llm_sync, instructions, file_content)


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


def _deduplicate_csv_headers(text: str) -> str:
    """Remove repeated header rows from CSV output (common with small LLMs)."""
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return text
    header = lines[0]
    cleaned = [header] + [line for line in lines[1:] if line.strip() and line.strip() != header]
    return "\n".join(cleaned)


def _looks_like_csv(text: str) -> bool:
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return False
    return "," in lines[0] and "," in lines[1]


# ---------------------------------------------------------------------------
# Output Handlers
# ---------------------------------------------------------------------------

def _handle_single_output(llm_output: str, job_id: str, skill: Skill) -> dict:
    """Save CSV output with validation, or return plain text as-is."""
    if _looks_like_csv(llm_output):
        filename = _generate_file_names(1, job_id, skill.output_files)[0]
        filepath = os.path.join(OUTPUT_DIR, filename)
        _save_csv(llm_output, filepath)
        validation = validate_csv_sections([{"name": filename, "content": llm_output}])

        return {
            "status": "success",
            "skill": skill.id,
            "preview": _csv_preview(llm_output),
            "row_count": _count_csv_rows(llm_output),
            "download": f"/api/download/{filename}",
            "validation": validation.to_dict(),
        }

    return {
        "status": "success",
        "skill": skill.id,
        "result": llm_output,
    }


def _handle_multi_output(llm_output: str, marker: str, job_id: str, skill: Skill) -> dict:
    """Split output by marker, save each section as CSV, bundle into ZIP."""
    sections = [s.strip() for s in llm_output.split(marker) if s.strip()]
    file_names = _generate_file_names(len(sections), job_id, skill.output_files)
    saved_files = []
    previews = []

    for section, name in zip(sections, file_names):
        clean = _deduplicate_csv_headers(_strip_code_fences(section))
        filepath = os.path.join(OUTPUT_DIR, name)
        _save_csv(clean, filepath)
        saved_files.append(filepath)
        previews.append({
            "file": name,
            "preview": _csv_preview(clean),
            "row_count": _count_csv_rows(clean),
            "download": f"/api/download/{name}",
        })

    zip_name = f"{OUTPUT_PREFIX}_{job_id}_bundle.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_name)
    _create_zip(saved_files, zip_path)

    validation_sections = [
        {"name": name, "content": _strip_code_fences(section)}
        for section, name in zip(sections, file_names)
    ]
    validation = validate_csv_sections(validation_sections)

    return {
        "status": "success",
        "skill": skill.id,
        "files": previews,
        "download_zip": f"/api/download/{zip_name}",
        "validation": validation.to_dict(),
    }


def _generate_file_names(count: int, job_id: str, skill_output_files: list[str] | None = None) -> list[str]:
    suffix = f"_{OUTPUT_SUFFIX}" if OUTPUT_SUFFIX else ""

    if skill_output_files and len(skill_output_files) == count:
        return [f"{OUTPUT_PREFIX}_{job_id}_{name}{suffix}.csv" for name in skill_output_files]

    if count == 1:
        return [f"{OUTPUT_PREFIX}_{job_id}_output{suffix}.csv"]
    if count == 2:
        return [f"{OUTPUT_PREFIX}_{job_id}_header{suffix}.csv", f"{OUTPUT_PREFIX}_{job_id}_lines{suffix}.csv"]
    return [f"{OUTPUT_PREFIX}_{job_id}_part{i+1}{suffix}.csv" for i in range(count)]


# ---------------------------------------------------------------------------
# API — Skill Generator
# ---------------------------------------------------------------------------

SKILL_GEN_PROMPT = """You are a skill template generator. You will receive a source CSV (input) and one or more target CSVs (desired output).

Analyze the mapping between input and output, then generate a skill.md file.

Your output MUST follow this EXACT format:

---
name: (short descriptive name)
description: (one line description)
input_types: [".csv"]
output_files: ["file1_name", "file2_name"]
---

# (Skill Name)

You are a data transformation expert. Your job is to read the source CSV and produce the target output.

## Source Schema

| Source Column | Type | Description |
|---|---|---|
(one row per input column)

## Mapping Rules

If multiple output files, create a separate mapping section for each:

### File 1: (name)
| Target Column | Source | Transformation |
|---|---|---|
(one row per target column)

### File 2: (name)
(same format)

## Special Rules

(row multiplication rules, date format changes, default values, etc.)

## Output Format

CRITICAL RULES FOR THE LLM:
- Output ONLY raw CSV data. No markdown, no explanations, no code fences, no comments.
- Each CSV section has the header row ONLY ONCE at the top. NEVER repeat header rows.
- Process ALL input rows completely.
(if multiple output files):
- Separate files with ---SPLIT--- on its own line.
- Output all rows for file 1, then ---SPLIT---, then all rows for file 2.

Example (showing first 2 rows only):
(paste 2 example rows from each target file, with ---SPLIT--- between them)

RULES FOR GENERATING THIS SKILL:
- Analyze EVERY column in both input and output carefully
- Detect date format changes (e.g. YYYY/MM/DD to YYYY-MM-DD)
- Detect default/constant values, concatenations, lookups
- If output has more rows than input, describe the row multiplication rule
- Use exact column names from the files
- Always include a concrete example in the Output Format section
- The output_files frontmatter must list short names for each output file
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

    logger.info("[%s] Generating skill from %d output file(s)", job_id, len(output_files))

    skill_content = await _call_llm(SKILL_GEN_PROMPT, user_message)
    logger.info("[%s] Skill generated (%d chars)", job_id, len(skill_content))

    return {
        "status": "success",
        "skill_content": skill_content,
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
    skill_path = os.path.join(SKILLS_DIR, safe_name)

    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(content)

    global skills
    skills = load_skills(SKILLS_DIR)
    logger.info("Skill saved: %s (total: %d)", safe_name, len(skills))

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


# ---------------------------------------------------------------------------
# API — Logs
# ---------------------------------------------------------------------------

@app.get("/api/logs")
async def get_logs(limit: int = 100):
    entries = list(log_buffer)[-limit:]
    return {"logs": entries}


@app.get("/api/logs/stream")
async def stream_logs():
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    log_subscribers.append(queue)

    async def event_generator():
        try:
            while True:
                entry = await queue.get()
                yield f"data: {json.dumps(entry)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            log_subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
