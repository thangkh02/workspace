import re
from pathlib import Path

UI_PATH = Path("data/group_snapshot_ui.txt")

def clean(text: str) -> str:
    text = text or ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_ui_line(raw: str):
    line = raw.rstrip("\n")
    m = re.match(r'^\s*-\s*(?P<kind>[a-zA-Z_]+)\s+"(?P<text>.*?)"(?P<rest>.*)$', line)
    if not m:
        return {"kind": None, "text": "", "ref": ""}

    rest = m.group("rest")
    ref_m = re.search(r"\[ref=(e\d+)\]", rest)
    ref = ref_m.group(1) if ref_m else ""

    return {
        "kind": m.group("kind"),
        "text": clean(m.group("text")),
        "ref": ref,
    }

lines = UI_PATH.read_text(encoding="utf-8").splitlines()
items = [parse_ui_line(x) for x in lines]

# Tìm sort anchor
sort_indices = [i for i, x in enumerate(items) if "sắp xếp bảng feed nhóm theo" in x["text"]]
print(f"Sort anchor at indices: {sort_indices}")

# Tìm "Hành động với bài viết này"
action_indices = [i for i, x in enumerate(items) if x["text"] == "Hành động với bài viết này"]
print(f"Action button at indices: {action_indices}")

# Tìm probable authors - text sau sort
if sort_indices:
    start = sort_indices[0] + 1
    print(f"\nItems sau sort anchor (từ index {start}):")
    for i in range(start, min(len(items), start + 20)):
        t = items[i]["text"]
        if t:
            print(f"  [{i}] {repr(t[:60])}")
