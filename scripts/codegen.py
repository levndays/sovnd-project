#!/usr/bin/env python3
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUT = Path("code.md")
EXCLUDED_DIRS = {"venv", ".git", ".pytest_cache", ".logs", ".pids", "data", "deploy", ".streamlit"}


def get_all_files(root):
    files = {"py": [], "md": [], "html": []}
    for root_path in root.rglob("*"):
        if root_path.is_file():
            rel = root_path.relative_to(root)
            if any(excluded in rel.parts for excluded in EXCLUDED_DIRS):
                continue
            if "__pycache__" in rel.parts:
                continue
            if rel.suffix == ".py":
                files["py"].append(rel)
            elif rel.suffix == ".md":
                files["md"].append(rel)
            elif rel.suffix == ".html":
                files["html"].append(rel)
    return {k: sorted(v) for k, v in files.items()}


def format_file_content(path):
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "    [binary file - skipped]"
    lines = content.splitlines()
    numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
    return numbered


all_files = get_all_files(ROOT)

with OUTPUT.open("w", encoding="utf-8") as out:
    out.write("# Source Code\n\n")

    out.write("## Python\n\n")
    for rel in all_files["py"]:
        full = ROOT / rel
        out.write(f"### {rel}\n\n```python\n")
        out.write(format_file_content(full))
        out.write("\n```\n\n")

    out.write("## Markdown\n\n")
    for rel in all_files["md"]:
        full = ROOT / rel
        ext = "markdown"
        out.write(f"### {rel}\n\n```{ext}\n")
        out.write(format_file_content(full))
        out.write("\n```\n\n")

    out.write("## HTML\n\n")
    for rel in all_files["html"]:
        full = ROOT / rel
        ext = "html"
        out.write(f"### {rel}\n\n```{ext}\n")
        out.write(format_file_content(full))
        out.write("\n```\n\n")

print(f"Wrote {len(all_files['py'])} Python files, {len(all_files['md'])} Markdown files, {len(all_files['html'])} HTML files to {OUTPUT}")