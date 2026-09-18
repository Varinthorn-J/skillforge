import os
import re
from dataclasses import dataclass


@dataclass
class Skill:
    id: str
    name: str
    description: str
    input_types: list[str]
    instructions: str


def load_skills(skills_dir: str = "skills") -> list[Skill]:
    skills = []
    if not os.path.isdir(skills_dir):
        return skills

    for filename in sorted(os.listdir(skills_dir)):
        if not filename.endswith(".md"):
            continue

        filepath = os.path.join(skills_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter, body = _parse_frontmatter(content)
        skills.append(Skill(
            id=filename.removesuffix(".md"),
            name=frontmatter.get("name", filename),
            description=frontmatter.get("description", ""),
            input_types=frontmatter.get("input_types", []),
            instructions=body.strip(),
        ))

    return skills


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return {}, content

    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
            meta[key] = val

    return meta, match.group(2)
