import json
import re
from pathlib import Path

UI_PATH = Path("data/group_snapshot_ui.txt")
CONTENT_PATH = Path("data/group_snapshot_content.txt")
OUT_PATH = Path("data/visible_posts.json")

TIME_RE = re.compile(
    r"^(?:\d+\s*(?:giờ|phút|ngày|tuần|tháng|năm)|vừa xong|hôm qua|\d+\s+tháng\s+\d+,?\s*\d*)$",
    re.IGNORECASE,
)
COMMENT_COUNT_RE = re.compile(r"^(?P<n>\d+)\s+bình luận$", re.IGNORECASE)

SORT_PREFIX = "sắp xếp bảng feed nhóm theo"
SHARE_PREFIX = "Gửi nội dung này cho bạn bè"

UI_NOISE = {
    "Facebook",
    "Trang cá nhân",
    "Bạn viết gì đi...",
    "Bài viết ẩn danh",
    "Cảm xúc/hoạt động",
    "Thăm dò ý kiến",
    "Giới thiệu phần đáng chú ý",
    "Mở rộng/Thu gọn phần đáng chú ý",
    "Tìm kiếm trong nhóm này",
    "Xem thêm",
    "Xem tất cả",
    "Mời",
    "Chia sẻ nhóm",
    "Đã tham gia",
    "Xem các nhóm đề xuất",
    "Giới thiệu",
    "Thảo luận",
    "Đáng chú ý",
    "Mọi người",
    "Sự kiện",
    "File phương tiện",
    "File",
    "Thích",
    "Bày tỏ cảm xúc",
    "Viết bình luận",
    "Chia sẻ",
    "Tin nhắn mới",
    "Đóng đoạn chat",
    "Quản trị viên",
}

CONTENT_NOISE_EXACT = {
    "Facebook",
    "·",
    "Thích",
    "Bình luận",
    "Chia sẻ",
    "Tất cả cảm xúc:",
    "Đáng chú ý",
}

CONTENT_NOISE_PREFIXES = (
    "Đã chia sẻ với ",
    "Xem ai đã bày tỏ cảm xúc",
    "Gửi nội dung này cho bạn bè",
    "sắp xếp bảng feed nhóm theo",
    "Tìm kiếm trong nhóm này",
    "Bạn viết gì đi",
    "Bài viết ẩn danh",
    "Cảm xúc/hoạt động",
    "Thăm dò ý kiến",
    "Giới thiệu phần đáng chú ý",
    "Mở rộng/Thu gọn phần đáng chú ý",
    "Có thể là hình ảnh",
    "Có thể là đồ họa",
    "Mở đoạn chat với ",
)

AUTHOR_BANNED_PREFIXES = (
    "Có thể là hình ảnh",
    "Có thể là đồ họa",
    "Xem ",
    "Mở đoạn chat",
    "Bình luận",
    "Chèn",
    "Đính kèm",
)

def clean(text: str) -> str:
    text = text or ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def looks_like_time(text: str) -> bool:
    return bool(TIME_RE.match(clean(text)))

def parse_comment_count(text: str) -> int:
    m = COMMENT_COUNT_RE.match(clean(text))
    return int(m.group("n")) if m else 0

def is_comment_count_text(text: str) -> bool:
    return COMMENT_COUNT_RE.match(clean(text)) is not None

def is_probable_author(text: str) -> bool:
    t = clean(text)
    if not t:
        return False
    if t in UI_NOISE:
        return False
    if looks_like_time(t):
        return False
    if is_comment_count_text(t):
        return False
    if t.startswith(SHARE_PREFIX):
        return False
    if t.startswith(SORT_PREFIX):
        return False
    if any(t.startswith(p) for p in AUTHOR_BANNED_PREFIXES):
        return False
    if len(t) > 80:
        return False
    if re.fullmatch(r"[\W\d_]+", t):
        return False
    return True

def dedupe_keep_order(values):
    out = []
    seen = set()
    for v in values:
        key = clean(v).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(clean(v))
    return out

def compress_substrings(values):
    values = dedupe_keep_order(values)
    kept = []
    for v in values:
        if any(v != u and v in u for u in values):
            continue
        kept.append(v)
    return kept

def parse_ui_line(raw: str):
    line = raw.rstrip("\n")
    m = re.match(r'^\s*-\s*(?P<kind>[a-zA-Z_]+)\s+"(?P<text>.*?)"(?P<rest>.*)$', line)
    if not m:
        return {
            "kind": None,
            "text": "",
            "ref": "",
            "raw": line,
        }

    rest = m.group("rest")
    ref_m = re.search(r"\[ref=(e\d+)\]", rest)
    ref = ref_m.group(1) if ref_m else ""

    return {
        "kind": m.group("kind"),
        "text": clean(m.group("text")),
        "ref": ref,
        "raw": line,
    }

def parse_content_line(raw: str):
    line = raw.rstrip("\n")
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    if not stripped.startswith("- "):
        return {
            "indent": indent,
            "kind": None,
            "text": "",
            "ref": "",
            "raw": line,
        }

    body = stripped[2:]
    kind_m = re.match(r"(?P<kind>[a-zA-Z_]+)", body)
    kind = kind_m.group("kind") if kind_m else None

    ref_m = re.search(r"\[ref=(e\d+)\]", body)
    ref = ref_m.group(1) if ref_m else ""

    quoted_m = re.search(r'"(.*?)"', body)
    quoted_text = clean(quoted_m.group(1)) if quoted_m else ""

    after_colon = ""
    if ":" in body:
        after_colon = clean(body.split(":", 1)[1])

    parts = []
    if quoted_text:
        parts.append(quoted_text)
    if after_colon and after_colon != quoted_text:
        parts.append(after_colon)

    text = clean(" ".join(parts))

    return {
        "indent": indent,
        "kind": kind,
        "text": text,
        "ref": ref,
        "raw": line,
    }

def find_sort_anchor(ui_items):
    for i, item in enumerate(ui_items):
        if item["text"].startswith(SORT_PREFIX):
            return i
    return -1

def parse_ui_posts(ui_items):
    anchor = find_sort_anchor(ui_items)
    start = anchor + 1 if anchor >= 0 else 0

    posts = []
    i = start

    while i < len(ui_items):
        author_item = ui_items[i]

        if not is_probable_author(author_item["text"]):
            i += 1
            continue

        # Tìm time trong range [i+1, i+5] (có thể có middle fields)
        time_item = None
        time_idx = None
        for j in range(i + 1, min(len(ui_items), i + 5)):
            if looks_like_time(ui_items[j]["text"]):
                time_item = ui_items[j]
                time_idx = j
                break

        if not time_item:
            i += 1
            continue

        # Tìm action button sau time
        action_item = None
        count_item = None
        like_item = None
        react_item = None
        comment_item = None
        share_item = None

        j = time_idx + 1
        stop_at = min(len(ui_items), time_idx + 15)

        while j < stop_at:
            t = ui_items[j]["text"]

            if t == "Hành động với bài viết này":
                action_item = ui_items[j]
            elif not count_item and is_comment_count_text(t):
                # Chỉ lấy comment count đầu tiên
                count_item = ui_items[j]
            elif not like_item and t == "Thích":
                # Chỉ lấy like button đầu tiên
                like_item = ui_items[j]
            elif not react_item and t == "Bày tỏ cảm xúc":
                # Chỉ lấy react button đầu tiên
                react_item = ui_items[j]
            elif not comment_item and t == "Viết bình luận":
                # Chỉ lấy comment button đầu tiên
                comment_item = ui_items[j]
            elif not share_item and (t.startswith(SHARE_PREFIX) or t == "Chia sẻ" or t == "Gửi"):
                # Chỉ lấy share button đầu tiên, và stop ở đây
                share_item = ui_items[j]
                j += 1
                break

            j += 1

        # post hợp lệ phải có ít nhất author + time + action + like + comment
        if not (action_item and like_item and comment_item):
            i += 1
            continue

        block_end_candidates = [
            idx for idx, obj in [
                (i, author_item),
                (time_idx, time_item),
                (ui_items.index(action_item), action_item) if action_item else (-1, None),
                (ui_items.index(count_item), count_item) if count_item else (-1, None),
                (ui_items.index(like_item), like_item) if like_item else (-1, None),
                (ui_items.index(react_item), react_item) if react_item else (-1, None),
                (ui_items.index(comment_item), comment_item) if comment_item else (-1, None),
                (ui_items.index(share_item), share_item) if share_item else (-1, None),
            ]
            if idx >= 0
        ]
        block_end = max(block_end_candidates)

        posts.append({
            "author": author_item["text"],
            "is_anonymous": "ẩn danh" in author_item["text"].lower(),
            "time_label": time_item["text"],
            "comment_ref": comment_item["ref"] if comment_item else "",
            "like_ref": like_item["ref"] if like_item else "",
            "react_ref": react_item["ref"] if react_item else "",
            "share_ref": share_item["ref"] if share_item else "",
            "comment_count": parse_comment_count(count_item["text"]) if count_item else 0,
            "raw_block_lines": [x["raw"] for x in ui_items[i:block_end + 1]],
        })

        i = block_end + 1

    return posts

def is_content_noise(text: str) -> bool:
    t = clean(text)
    if not t:
        return True
    if t in CONTENT_NOISE_EXACT:
        return True
    if looks_like_time(t):
        return True
    if is_comment_count_text(t):
        return True
    if len(t) < 2:
        return True
    if any(t.startswith(p) for p in CONTENT_NOISE_PREFIXES):
        return True
    return False

def is_content_stop(text: str) -> bool:
    t = clean(text)
    if not t:
        return False
    if t in {"Thích", "Bình luận", "Chia sẻ", "Tất cả cảm xúc:"}:
        return True
    if is_comment_count_text(t):
        return True
    if t.startswith("Xem ai đã bày tỏ cảm xúc"):
        return True
    if t.startswith(SHARE_PREFIX):
        return True
    return False

def parse_content_posts(content_items):
    """Parse posts từ content snapshot.
    
    Strategy: Từ button "Hành động với bài viết này" (action marker)
    - FORWARD từ action_idx để tìm post_text 
    - Post_text là text dài (>= 20 ký tự), không phải URL/link
    - Collect multiple lines nếu cần, stop trước reactions
    """
    action_indices = [
        i for i, item in enumerate(content_items)
        if item["text"] == "Hành động với bài viết này"
    ]

    posts = []

    for pos, action_idx in enumerate(action_indices):
        # Lấy author + time từ ngược (BEFORE action)
        author_text = ""
        time_text = ""
        
        for j in range(action_idx - 1, max(-1, action_idx - 100), -1):
            t = clean(content_items[j]["text"])
            if not t:
                continue
            if is_content_noise(t):
                continue
            
            if not time_text and looks_like_time(t):
                time_text = t
                continue
            
            if time_text and not author_text and is_probable_author(t):
                author_text = t
                break
        
        # Lấy post_text từ FORWARD (AFTER action)
        # Collect text lines, ưu tiên content trước URLs
        post_text_parts = []
        url_pattern = re.compile(r'^https?://|^/[a-z]+/|^/groups/')
        
        for j in range(action_idx + 1, min(len(content_items), action_idx + 30)):
            t = clean(content_items[j]["text"])
            if not t:
                continue
            
            # Stop nếu gặp reaction controls
            if is_content_stop(t):
                break
            
            # Skip noise
            if is_content_noise(t):
                continue
            
            # Skip URLs/links
            if url_pattern.match(t) or t.startswith('drive.google.com'):
                continue
            
            # Skip very short text (likely labels)
            if len(t) < 10:
                continue
            
            # Collect content text
            post_text_parts.append(t)
            
            # Lấy 2-3 dòng content là đủ
            if len(post_text_parts) >= 3:
                break
        
        # Combine multiple parts
        post_text = " ".join(post_text_parts)

        posts.append({
            "author": author_text,
            "time_label": time_text,
            "post_text": post_text,
            "post_text_source": "snapshot" if post_text else "unknown",
        })

    return posts

def merge_posts(ui_posts, content_posts):
    merged = []

    for i, ui_post in enumerate(ui_posts):
        content_post = content_posts[i] if i < len(content_posts) else {}

        post_text = content_post.get("post_text", "")
        post_text_source = content_post.get("post_text_source", "unknown" if not post_text else "snapshot")

        merged.append({
            "post_key": f"post_{i + 1:03d}",
            "comment_ref": ui_post.get("comment_ref", ""),
            "like_ref": ui_post.get("like_ref", ""),
            "react_ref": ui_post.get("react_ref", ""),
            "share_ref": ui_post.get("share_ref", ""),

            "author": ui_post.get("author", "") or content_post.get("author", ""),
            "is_anonymous": ui_post.get("is_anonymous", False),
            "time_label": ui_post.get("time_label", "") or content_post.get("time_label", ""),

            "post_text": post_text,
            "post_text_source": post_text_source,

            "comment_count": ui_post.get("comment_count", 0),
            "raw_block_lines": ui_post.get("raw_block_lines", []),
        })

    return merged

def main():
    if not UI_PATH.exists():
        raise FileNotFoundError(f"Missing file: {UI_PATH}")
    if not CONTENT_PATH.exists():
        raise FileNotFoundError(f"Missing file: {CONTENT_PATH}")

    ui_lines = UI_PATH.read_text(encoding="utf-8").splitlines()
    content_lines = CONTENT_PATH.read_text(encoding="utf-8").splitlines()

    ui_items = [parse_ui_line(x) for x in ui_lines]
    content_items = [parse_content_line(x) for x in content_lines]

    ui_posts = parse_ui_posts(ui_items)
    content_posts = parse_content_posts(content_items)
    posts = merge_posts(ui_posts, content_posts)

    result = {
        "ok": True,
        "count": len(posts),
        "posts": posts,
    }

    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {len(posts)} posts -> {OUT_PATH}")

if __name__ == "__main__":
    main()