#!/usr/bin/env python3
import json
from pathlib import Path

snapshot_file = Path('data/raw/group_snapshot_ui_ttud.txt')
if snapshot_file.exists():
    lines = snapshot_file.read_text(encoding='utf-8').splitlines()
    print(f'✓ Snapshot file: {len(lines)} lines')
    
    # Check for 'Xem thêm' button
    xem_them_count = sum(1 for line in lines if 'xem thêm' in line.lower())
    print(f'Found {xem_them_count} "Xem thêm" references')
    
    print(f'\nFirst 50 lines summary:')
    for i, line in enumerate(lines[:50], 1):
        if line.strip():
            print(f'{i:3d}: {line[:110]}')
    
    print(f'\n... Total {len(lines)} lines')
else:
    print('Snapshot file not found')
