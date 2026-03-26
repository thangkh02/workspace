#!/usr/bin/env python3
import re

ui = open('data/group_snapshot_ui.txt', encoding='utf-8', errors='replace').read()

# Find all button lines
buttons = re.findall(r'- button "([^"]*)"', ui)
print("All buttons found:")
for i, btn in enumerate(buttons[:40], 1):
    short = btn[:70] + ("..." if len(btn) > 70 else "")
    print(f"  {i:2}. {short}")

print(f"\nTotal buttons: {len(buttons)}")

# Check for post-related buttons
print("\nPost indicators:")
print(f"  'bình luận': {sum(1 for b in buttons if 'bình luận' in b.lower())}")
print(f"  'Thích': {sum(1 for b in buttons if 'Thích' in b)}")
print(f"  'Viết bình luận': {sum(1 for b in buttons if 'Viết bình luận' in b)}")
print(f"  'Người tham gia': {sum(1 for b in buttons if 'Người tham gia' in b)}")
