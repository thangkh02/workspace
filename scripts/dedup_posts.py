#!/usr/bin/env python3
"""
dedup_posts.py

Mục đích: Merge posts từ multiple iterations, deduplicate, return top N posts.
Input: data/visible_posts.json (accumulated from all iterations)
Output: data/posts_collection.json (final result, deduplicated, top N)

Logic:
1. Load all posts from visible_posts.json
2. Deduplicate by (author, time_label) - same author + time = same post
3. Sort by collection order (preserve chronological)
4. Return top N posts
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

def clean_for_comparison(text: str) -> str:
    """Normalize text for comparison."""
    text = text or ""
    text = text.lower().strip()
    text = " ".join(text.split())  # normalize whitespace
    return text

def post_signature(post: Dict[str, Any]) -> Tuple[str, str]:
    """Create unique signature for post (author, time)."""
    author = clean_for_comparison(post.get('author', ''))
    time_label = clean_for_comparison(post.get('time_label', ''))
    return (author, time_label)

def dedup_posts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate posts by (author, time_label), keeping first occurrence."""
    seen = set()
    unique_posts = []
    
    for post in posts:
        sig = post_signature(post)
        # Skip if both author and time are empty
        if not sig[0] and not sig[1]:
            continue
        # Skip if already seen
        if sig in seen:
            continue
        seen.add(sig)
        unique_posts.append(post)
    
    return unique_posts

def load_visible_posts(path: str) -> List[Dict[str, Any]]:
    """Load posts from visible_posts.json."""
    file = Path(path)
    if not file.exists():
        print(f"File not found: {path}", flush=True)
        return []
    
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract posts array
        if isinstance(data, dict) and 'posts' in data:
            posts = data['posts']
        elif isinstance(data, list):
            posts = data
        else:
            print(f"Unexpected format in {path}", flush=True)
            return []
        
        if not isinstance(posts, list):
            return []
        
        return posts
    except Exception as e:
        print(f"Error loading {path}: {e}", flush=True)
        return []

def collect_posts_results(
    input_file: str = "data/visible_posts.json",
    output_file: str = "data/posts_collection.json",
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Main orchestrator: load, dedup, return top N posts.
    """
    result = {
        'timestamp': datetime.now().isoformat(),
        'input_file': input_file,
        'output_file': output_file,
        'target_count': top_n,
        'total_loaded': 0,
        'after_dedup': 0,
        'final_count': 0,
        'posts': [],
        'status': 'success',
        'error': None
    }
    
    try:
        # Load posts
        posts = load_visible_posts(input_file)
        result['total_loaded'] = len(posts)
        print(f"Loaded {len(posts)} posts from {input_file}", flush=True)
        
        if not posts:
            result['status'] = 'warning'
            result['error'] = 'No posts loaded'
            return result
        
        # Deduplicate
        unique_posts = dedup_posts(posts)
        result['after_dedup'] = len(unique_posts)
        print(f"After dedup: {len(unique_posts)} unique posts", flush=True)
        
        # Take top N
        final_posts = unique_posts[:top_n]
        result['final_count'] = len(final_posts)
        result['posts'] = final_posts
        
        print(f"Final result: {len(final_posts)} posts (target: {top_n})", flush=True)
        
        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output_data = {
            'metadata': {
                'timestamp': result['timestamp'],
                'total_loaded': result['total_loaded'],
                'after_dedup': result['after_dedup'],
                'final_count': result['final_count'],
                'target_count': top_n,
                'status': result['status']
            },
            'posts': final_posts
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved result to: {output_file}", flush=True)
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        print(f"Error: {e}", flush=True)
    
    return result

if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "data/visible_posts.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "data/posts_collection.json"
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    result = collect_posts_results(input_file, output_file, top_n)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    
    sys.exit(0 if result['status'] == 'success' else 1)
