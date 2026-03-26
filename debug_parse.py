import json
from pathlib import Path
import re

CONTENT_PATH = Path("data/group_snapshot_content.txt")

def clean(text: str) -> str:
    text = text or ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_content_line(raw: str):
    line = raw.rstrip("\n")
    stripped = line.lstrip()
    if not stripped.startswith("- "):
        return {"text": "", "kind": None, "raw": line}

    body = stripped[2:]
    after_colon = ""
    if ":" in body:
        after_colon = clean(body.split(":", 1)[1])
    
    quoted_m = re.search(r'"(.*?)"', body)
    quoted_text = clean(quoted_m.group(1)) if quoted_m else ""

    parts = []
    if quoted_text:
        parts.append(quoted_text)
    if after_colon and after_colon != quoted_text:
        parts.append(after_colon)

    text = clean(" ".join(parts))
    return {"text": text, "kind": None, "raw": line}

lines = CONTENT_PATH.read_text(encoding="utf-8").splitlines()
items = [parse_content_line(x) for x in lines]

# Find where post text is
print("Tìm 'Mọi người':")
for i, item in enumerate(items):
    if "Mọi người" in item["text"]:
        print(f"  Found at index {i}: {repr(item['text'][:80])}")
        print(f"  Raw line: {item['raw'][:100]}")

# Find action markers
action_indices = [i for i, item in enumerate(items) if item["text"] == "Hành động với bài viết này"]
print(f"\nAction indices: {action_indices}")

if action_indices:
    action_idx = action_indices[0]
    print(f"\nFirst action at index {action_idx}")
    
    # Check text around it (ngược)
    print("\nNgược tìm từ action_idx (show all có content):")
    for i in range(action_idx - 1, max(-1, action_idx - 50), -1):
        t = items[i]["text"]
        if t and len(t) > 2:
            print(f"  [{i}] len={len(t):4d} text={repr(t[:60])}")
