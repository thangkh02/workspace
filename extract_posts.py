#!/usr/bin/env python3
"""
Facebook Group Posts Extractor
Direct Python wrapper to trigger PowerShell pipeline from openclaw
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def extract_fb_posts(link: str, target_count: int = 10, browser_profile: str = "openclaw") -> dict:
    """
    Main function: Extract posts from Facebook link
    
    Args:
        link: Facebook URL (group, page, or profile)
        target_count: Number of posts to collect
        browser_profile: Browser profile to use
    
    Returns:
        dict with results
    """
    
    workspace_dir = Path(__file__).parent
    
    # Validate input
    if not link or "facebook.com" not in link:
        return {
            "success": False,
            "error": "Invalid Facebook URL",
            "url": link
        }
    
    print(f"📱 Extracting posts from: {link}")
    print(f"🎯 Target: {target_count} posts")
    
    # PowerShell command to run
    ps_script = workspace_dir / "scripts" / "collect_posts_from_group.ps1"
    
    cmd = [
        "powershell",
        "-ExecutionPolicy", "Bypass",
        "-File", str(ps_script),
        "-GroupUrl", link,
        "-TargetCount", str(target_count),
        "-BrowserProfile", browser_profile,
        "-OutputDir", "data"
    ]
    
    try:
        # Run PowerShell script
        result = subprocess.run(
            cmd,
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        
        # Check result
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"PowerShell execution failed: {result.stderr}",
                "stdout": result.stdout,
                "url": link
            }
        
        # Try to read result
        posts_file = workspace_dir / "data" / "posts_collection.json"
        
        if posts_file.exists():
            with open(posts_file, 'r', encoding='utf-8') as f:
                posts_data = json.load(f)
            
            return {
                "success": True,
                "posts_collected": len(posts_data.get("posts", [])),
                "data": posts_data,
                "url": link,
                "saved_to": str(posts_file),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Output file not generated",
                "url": link,
                "expected_path": str(posts_file)
            }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Collection timeout (5+ minutes)",
            "url": link
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "url": link
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_posts.py <FACEBOOK_URL> [TARGET_COUNT]")
        print("Example: python extract_posts.py https://www.facebook.com/groups/ttud.2023 15")
        sys.exit(1)
    
    fb_link = sys.argv[1]
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    result = extract_fb_posts(fb_link, target)
    
    print("\n" + "="*60)
    print("📊 RESULT:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    sys.exit(0 if result["success"] else 1)
