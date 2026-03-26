#!/usr/bin/env python3
"""Fix encoding issues in snapshot files"""
from pathlib import Path

def fix_snapshot_encoding():
    ui_path = Path("data/group_snapshot_ui.txt")
    content_path = Path("data/group_snapshot_content.txt")
    
    for fpath in [ui_path, content_path]:
        if not fpath.exists():
            print(f"⏭️  {fpath.name}: Not found")
            continue
            
        print(f"🔍 {fpath.name}...")
        
        try:
            # Read as bytes first
            raw_bytes = fpath.read_bytes()
            
            # Try UTF-8
            try:
                data = raw_bytes.decode('utf-8')
                if 'Γöé' in data or 'ß╗' in data:
                    raise ValueError("Has corrupted chars in UTF-8")
                print(f"  ✅ Already valid UTF-8")
                continue
            except (UnicodeDecodeError, ValueError):
                pass
            
            # Try other encodings
            for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    data = raw_bytes.decode(encoding)
                    if 'Γöé' not in data and 'ß╗' not in data:
                        print(f"  🔄 Found encoding: {encoding}, converting to UTF-8...")
                        fpath.write_text(data, encoding='utf-8')
                        print(f"  ✅ Fixed!")
                        break
                except UnicodeDecodeError:
                    continue
            else:
                print(f"  ❌ Could not determine correct encoding")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == '__main__':
    fix_snapshot_encoding()
