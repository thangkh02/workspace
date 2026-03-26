#!/usr/bin/env python3
"""Check snapshot content"""
from pathlib import Path

def check_snapshots():
    ui_path = Path("data/group_snapshot_ui.txt")
    content_path = Path("data/group_snapshot_content.txt")
    
    ui = ui_path.read_text(encoding='utf-8')
    content = content_path.read_text(encoding='utf-8')
    
    print("UI Snapshot:")
    print(f"  Size: {len(ui)} chars")
    print(f'  Has button: {"button" in ui}')
    print(f'  Has Nguoi: {"Người" in ui or "Ng" in ui}')
    print(f"  Line count: {len(ui.splitlines())}")
    
    # Check for posts
    author_count = ui.count("button \"Người tham gia")
    print(f"  Author buttons found: {author_count}")
    
    print()
    print("Content Snapshot:")
    print(f"  Size: {len(content)} chars")
    print(f'  Has generic: {"generic" in content}')
    print(f'  Has button: {"button" in content}')
    print(f"  Line count: {len(content.splitlines())}")
    
    # Look for feed
    feed_matches = content.count("feed")
    print(f"  Feed elements: {feed_matches}")

if __name__ == '__main__':
    check_snapshots()
