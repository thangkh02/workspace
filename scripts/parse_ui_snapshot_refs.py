#!/usr/bin/env python3
"""
parse_ui_snapshot_refs.py

Mục đích: Extract action button references từ UI snapshot.
Input: data/raw/group_snapshot_ui.txt (hoặc từ data/)
Output: JSON với posts + comment_count, like_count, reaction_counts, share_count

Các refs từ UI snapshot:
- Button "Bình luận" -> comment_ref
- Button "Thích" -> like_ref
- Button "Cảm xúc" -> react_ref
- Button "Chia sẻ" hoặc "Gửi" -> share_ref

Heuristic: Tìm author -> time -> action buttons theo dự kiến
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Regex patterns
TIME_RE = re.compile(
    r'\b(?:'
    r'\d+\s*(?:giờ|phút|ngày|tuần|tháng|năm)|'  # Old format: 18 giờ, 7 ngày
    r'vừa xong|hôm qua|'
    r'\d+\s+tháng\s+\d+,?\s*\d*'  # New format: 23 Tháng 12, 2023
    r')\b',
    re.IGNORECASE
)

COMMENT_COUNT_RE = re.compile(r'(\d+)\s*(?:bình luận|lượt|comment)', re.IGNORECASE)
LIKE_COUNT_RE = re.compile(r'(\d+)\s*(?:thích|like)', re.IGNORECASE)
REACTION_COUNT_RE = re.compile(r'(\d+)\s*(?:cảm xúc|reaction)', re.IGNORECASE)
SHARE_COUNT_RE = re.compile(r'(\d+)\s*(?:chia sẻ|share)', re.IGNORECASE)

# UI noise keywords to skip
UI_NOISE = {
    'Facebook', 'Bạn viết gì đi...', 'Quản trị viên', 'Bình luận', 'Chèn', 'Đính kèm',
    'Thích', 'Bày tỏ cảm xúc', 'Viết bình luận', 'Chia sẻ', 'Gửi', 'Xem thêm',
    'Được yêu thích', 'Ẩn bài viết', 'Báo cáo', 'Công khai', 'Bạn bè', 'Chỉ mình tôi',
    'Thêm', 'Chi tiết khác', 'Mở', 'Đóng', 'Menu', 'Xoá', 'Sửa', 'Nút', 'Liên kết',
    'Có thể là hình ảnh', 'Xem đoạn chat', 'Mở đoạn chat', 'Bất ngờ', 'Buồn', 'Tức giận'
}

BANNED_PREFIXES = {
    'Có thể là hình ảnh', 'Có thể là đồ họa', 'Xem', 'Mở đoạn chat',
    'Bình luận liên quan', 'Chia sẻ', 'Gửi'
}


def parse_ui_line(raw: str) -> Dict[str, Any]:
    """
    Parse một dòng từ UI snapshot:
    "- kind "text value" [ref=eXXX]"
    
    Return: { kind, text, ref }
    """
    item = {'kind': None, 'text': None, 'ref': None}
    
    # Match pattern: - kind "text" [ref=eXXX]
    match = re.match(r'-\s+(\w+)\s+"([^"]+)"\s+\[ref=([e\d]+)\]', raw)
    if match:
        item['kind'] = match.group(1)
        item['text'] = match.group(2)
        item['ref'] = match.group(3)
    
    return item


def extract_action_buttons(lines: List[str], start_idx: int, look_ahead: int = 5) -> Dict[str, Optional[str]]:
    """
    Từ vị trí action marker, tìm các action buttons (comment, like, react, share).
    
    Return: { comment_ref, like_ref, react_ref, share_ref, comment_count, like_count, ... }
    """
    actions = {
        'comment_ref': None,
        'like_ref': None,
        'react_ref': None,
        'share_ref': None,
        'comment_count': 0,
        'like_count': 0,
        'reaction_count': 0,
        'share_count': 0
    }
    
    # Search forward từ action marker
    end_idx = min(start_idx + look_ahead, len(lines))
    
    for i in range(start_idx, end_idx):
        line = lines[i]
        item = parse_ui_line(line)
        
        if not item['kind'] or not item['text']:
            continue
        
        text = item['text'].strip()
        
        # Detect action type
        if 'bình luận' in text.lower():
            actions['comment_ref'] = item['ref']
            # Try extract count từ text (e.g., "Bình luận 5")
            match = COMMENT_COUNT_RE.search(text)
            if match:
                actions['comment_count'] = int(match.group(1))
        
        elif 'thích' in text.lower() and 'cảm xúc' not in text.lower():
            actions['like_ref'] = item['ref']
            match = LIKE_COUNT_RE.search(text)
            if match:
                actions['like_count'] = int(match.group(1))
        
        elif 'cảm xúc' in text.lower() or 'reaction' in text.lower():
            actions['react_ref'] = item['ref']
            match = REACTION_COUNT_RE.search(text)
            if match:
                actions['reaction_count'] = int(match.group(1))
        
        elif 'chia sẻ' in text.lower() or 'share' in text.lower():
            actions['share_ref'] = item['ref']
            match = SHARE_COUNT_RE.search(text)
            if match:
                actions['share_count'] = int(match.group(1))
    
    return actions


def is_probable_author(text: str) -> bool:
    """Check if text is likely an author name (not UI noise)."""
    if not text or len(text) < 3:
        return False
    
    # Check against noise list
    if text.strip() in UI_NOISE or any(text.startswith(p) for p in BANNED_PREFIXES):
        return False
    
    # Check if it matches time pattern
    if TIME_RE.match(text):
        return False
    
    # Check for comment count pattern
    if re.match(r'^\d+\s*(?:bình luận|lượt)', text, re.IGNORECASE):
        return False
    
    # Check for URLs
    if text.startswith('http://') or text.startswith('https://') or text.startswith('/'):
        return False
    
    # Length heuristic: author names usually 3-80 characters
    if len(text) > 80:
        return False
    
    return True


def parse_ui_posts(ui_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find post authors and action references from UI snapshot.
    
    Logic: author -> time -> action buttons
    """
    posts = []
    post_idx = 0
    
    i = 0
    while i < len(ui_items):
        item = ui_items[i]
        
        # Look for author (probable_author + next is time)
        if is_probable_author(item.get('text', '')):
            # Check if next items contain time
            time_idx = None
            for j in range(i + 1, min(i + 5, len(ui_items))):
                if TIME_RE.search(ui_items[j].get('text', '')):
                    time_idx = j
                    break
            
            if time_idx is not None:
                # Found author + time sequence
                post_idx += 1
                post = {
                    'post_key': f'post_{post_idx:03d}',
                    'author': item['text'].strip(),
                    'time_label': ui_items[time_idx]['text'].strip(),
                    'author_ref': item['ref'],
                    'time_ref': ui_items[time_idx]['ref']
                }
                
                # Extract action buttons after time
                actions = extract_action_buttons(
                    [item.get('text', '') for item in ui_items],
                    time_idx,
                    look_ahead=5
                )
                post.update(actions)
                
                posts.append(post)
                
                i = time_idx + 1
                continue
        
        i += 1
    
    return posts


def main():
    """Main entry point."""
    # Try find UI snapshot file
    snapshot_paths = [
        Path('data/raw/group_snapshot_ui.txt'),
        Path('data/group_snapshot_ui.txt'),
        Path('data/visible_posts.json')  # Fallback: use existing parser output
    ]
    
    ui_file = None
    for path in snapshot_paths:
        if path.exists():
            ui_file = path
            break
    
    if not ui_file:
        print("JSON", json.dumps({
            "error": "No UI snapshot found",
            "checked_paths": [str(p) for p in snapshot_paths],
            "message": "Please run expand + extract JS first, or ensure snapshots in data/"
        }, ensure_ascii=False, indent=2))
        return
    
    # Load and parse UI snapshot
    print(f"Parsing UI snapshot from: {ui_file}", flush=True)
    
    try:
        with open(ui_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse lines into items
        ui_items = [parse_ui_line(line.rstrip()) for line in lines if line.strip()]
        valid_items = [item for item in ui_items if item['kind']]
        
        print(f"Parsed {len(valid_items)} UI items ({len(lines)} lines)", flush=True)
        
        # Find posts
        posts = parse_ui_posts(valid_items)
        
        # Output
        result = {
            "ui_snapshot": str(ui_file),
            "posts": posts,
            "total": len(posts),
            "parsed_at": str(Path.cwd())
        }
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Save to file
        output_file = Path('data/raw/ui_posts_refs.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Saved to: {output_file}", file=sys.stderr, flush=True)
    
    except Exception as e:
        import sys
        print("JSON", json.dumps({
            "error": str(e),
            "file": str(ui_file)
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    import sys
    main()
