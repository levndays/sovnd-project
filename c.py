#!/usr/bin/env python3
import os
from pathlib import Path

ROOT = Path("src")
EBPF = Path("ebpf")
OUTPUT = Path("code.md")

def get_all_files(root):
    files = []
    for root_path in root.rglob("*"):
        if root_path.is_file():
            rel = root_path.relative_to(root)
            if "__pycache__" in rel.parts:
                continue
            if rel.suffix == ".py":
                files.append(rel)
    return sorted(files)

def get_ebpf_files(root):
    files = []
    for root_path in root.rglob("*"):
        if root_path.is_file():
            rel = root_path.relative_to(root)
            if rel.name in ("vmlinux.h", "Makefile"):
                continue
            if rel.suffix in (".c", ".h", ".bpf.c"):
                files.append(rel)
    return sorted(files)

def format_file_content(path):
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "    [binary file - skipped]"
    lines = content.splitlines()
    numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
    return numbered

files = get_all_files(ROOT)
ebpf_files = get_ebpf_files(EBPF)

with OUTPUT.open("w", encoding="utf-8") as out:
    out.write("# Source Code\n\n")
    out.write("## Python (src/)\n\n")
    for rel in files:
        full = ROOT / rel
        out.write(f"### {rel}\n\n```python\n")
        out.write(format_file_content(full))
        out.write("\n```\n\n")

    out.write("## eBPF (ebpf/)\n\n")
    for rel in ebpf_files:
        full = EBPF / rel
        ext = "c" if rel.suffix in (".c", ".bpf.c") else "c"
        out.write(f"### {rel}\n\n```{ext}\n")
        out.write(format_file_content(full))
        out.write("\n```\n\n")

print(f"Wrote {len(files)} Python files, {len(ebpf_files)} eBPF files to {OUTPUT}")