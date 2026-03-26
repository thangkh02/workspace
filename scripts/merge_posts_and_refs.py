#!/usr/bin/env python3
"""
merge_posts_and_refs.py

Mục đích: Combine DOM-extracted posts với snapshot-extracted refs.
Input: 
  - data/raw/dom_posts.json (từ extract_visible_posts.js)
  - data/raw/ui_posts_refs.json (từ parse_ui_snapshot_refs.py)
  - data/visible_posts.json (từ parse_snapshot_posts.py - old parser)

Output: data/processed/merged_posts.json
  - Merged posts với confidence scores
  - Combine author từ DOM + refs từ UI
  - Mark posts với missing/conflicting data

Logic:
1. Match posts by index (post_001 = post_001)
2. Prefer DOM data for content (author, text, time)
3. Use snapshot refs for action buttons
4. Calculate merged confidence score
5. Flag conflicts cho review
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

def load_json(path: str) -> Optional[Dict[str, Any] | List]:
    """Load JSON file safely."""
    file = Path(path)
    if not file.exists():
        return None
    
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}", flush=True)
        return None


def match_posts_by_index(dom_posts: List[Dict], snapshot_posts: List[Dict]) -> List[Tuple[Optional[Dict], Optional[Dict]]]:
    """
    Match DOM posts với snapshot posts by index.
    Return: List of (dom_post, snapshot_post) tuples
    """
    # Create index maps
    dom_map = {post.get('post_key'): post for post in dom_posts if post.get('post_key')}
    snapshot_map = {f'post_{idx:03d}': post for idx, post in enumerate(snapshot_posts, 1)}
    
    # All unique post keys
    all_keys = set(dom_map.keys()) | set(snapshot_map.keys())
    
    # Match tuples: (dom_post, snapshot_post)
    matches = []
    for key in sorted(all_keys):
        dom = dom_map.get(key)
        snapshot = snapshot_map.get(key)
        matches.append((dom, snapshot))
    
    return matches


def merge_post(dom_post: Optional[Dict], snapshot_post: Optional[Dict], index: int) -> Dict[str, Any]:
    """
    Merge a DOM post with snapshot post data.
    
    Preference: DOM > Snapshot for content, Snapshot for refs
    """
    merged = {
        'post_key': f'post_{index:03d}',
        'source': {
            'has_dom': dom_post is not None,
            'has_snapshot': snapshot_post is not None,
            'dom_confidence': dom_post.get('dom_confidence', 0) if dom_post else 0,
            'snapshot_confidence': snapshot_post.get('confidence', 0) if snapshot_post else 0
        }
    }
    
    # Author: prefer DOM, fallback to snapshot
    if dom_post and dom_post.get('author'):
        merged['author'] = dom_post['author']
        merged['author_source'] = 'dom'
    elif snapshot_post and snapshot_post.get('author'):
        merged['author'] = snapshot_post['author']
        merged['author_source'] = 'snapshot'
    else:
        merged['author'] = None
        merged['author_source'] = 'none'
    
    # Time: prefer DOM, fallback to snapshot
    if dom_post and dom_post.get('time_label'):
        merged['time_label'] = dom_post['time_label']
        merged['time_source'] = 'dom'
    elif snapshot_post and snapshot_post.get('time_label'):
        merged['time_label'] = snapshot_post['time_label']
        merged['time_source'] = 'snapshot'
    else:
        merged['time_label'] = None
        merged['time_source'] = 'none'
    
    # Post text: prefer DOM (more reliable), fallback to snapshot
    if dom_post and dom_post.get('post_text'):
        merged['post_text'] = dom_post['post_text']
        merged['text_source'] = 'dom'
        merged['text_truncated'] = dom_post.get('text_truncated', False)
    elif snapshot_post and snapshot_post.get('post_text'):
        merged['post_text'] = snapshot_post['post_text']
        merged['text_source'] = 'snapshot'
        merged['text_truncated'] = snapshot_post.get('text_truncated', False)
    else:
        merged['post_text'] = None
        merged['text_source'] = 'none'
        merged['text_truncated'] = False
    
    # Attachments: combine from both sources
    merged['attachments'] = {
        'titles': list(set(
            (dom_post.get('attachment_titles') or [] if dom_post else []) + 
            (snapshot_post.get('attachment_titles') or [] if snapshot_post else [])
        )),
        'count': len(set(
            (dom_post.get('attachment_titles') or [] if dom_post else []) + 
            (snapshot_post.get('attachment_titles') or [] if snapshot_post else [])
        ))
    }
    
    # Action refs: prefer snapshot (more structured), fallback to DOM
    if snapshot_post:
        merged['refs'] = {
            'comment_ref': snapshot_post.get('comment_ref'),
            'like_ref': snapshot_post.get('like_ref'),
            'react_ref': snapshot_post.get('react_ref'),
            'share_ref': snapshot_post.get('share_ref'),
            'source': 'snapshot'
        }
    elif dom_post:
        merged['refs'] = {
            'comment_ref': None,
            'like_ref': None,
            'react_ref': None,
            'share_ref': None,
            'source': 'dom'
        }
    else:
        merged['refs'] = {
            'comment_ref': None,
            'like_ref': None,
            'react_ref': None,
            'share_ref': None,
            'source': 'none'
        }
    
    # Comment/like counts: from snapshot
    if snapshot_post:
        merged['engagement'] = {
            'comment_count': snapshot_post.get('comment_count', 0) or 0,
            'like_count': snapshot_post.get('like_count', 0) or 0,
            'reaction_count': snapshot_post.get('reaction_count', 0) or 0,
            'share_count': snapshot_post.get('share_count', 0) or 0
        }
    else:
        merged['engagement'] = {
            'comment_count': 0,
            'like_count': 0,
            'reaction_count': 0,
            'share_count': 0
        }
    
    # Calculate merged confidence score
    confidence_scores = []
    if dom_post and dom_post.get('dom_confidence'):
        confidence_scores.append(dom_post.get('dom_confidence', 0.5))
    if snapshot_post and snapshot_post.get('confidence'):
        confidence_scores.append(snapshot_post.get('confidence', 0.5))
    
    base_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
    
    # Boost confidence if post has all required fields
    has_required = merged['author'] and merged['time_label'] and merged['post_text']
    has_refs = merged['refs'].get('comment_ref') or merged['refs'].get('like_ref')
    
    if has_required and has_refs:
        merged['confidence'] = max(base_confidence, 0.75)  # Boost to at least 0.75
    elif has_required or has_refs:
        merged['confidence'] = max(base_confidence, 0.65)  # Boost to at least 0.65
    else:
        merged['confidence'] = base_confidence
    
    # Skip reason: inherited from either source
    if dom_post and dom_post.get('skip_reason'):
        merged['skip_reason'] = dom_post['skip_reason']
        merged['skip_source'] = 'dom'
    elif snapshot_post and snapshot_post.get('skip_reason'):
        merged['skip_reason'] = snapshot_post['skip_reason']
        merged['skip_source'] = 'snapshot'
    else:
        merged['skip_reason'] = None
        merged['skip_source'] = None
    
    # Flags
    merged['flags'] = {
        'missing_author': not merged['author'],
        'missing_time': not merged['time_label'],
        'missing_text': not merged['post_text'],
        'missing_refs': not all([
            merged['refs'].get('comment_ref'),
            merged['refs'].get('like_ref'),
            merged['refs'].get('share_ref')
        ]),
        'conflicting_author': (
            dom_post and snapshot_post and 
            dom_post.get('author') and snapshot_post.get('author') and
            dom_post.get('author') != snapshot_post.get('author')
        ),
        'low_confidence': merged['confidence'] < 0.6
    }
    
    return merged


def main():
    """Main merge pipeline."""
    print(f"Starting merge at {datetime.now().isoformat()}", flush=True)
    
    # Load inputs - priority: DOM first, fallback to snapshot
    dom_posts = load_json('data/raw/dom_posts.json')
    dom_posts = dom_posts.get('posts', []) if isinstance(dom_posts, dict) else (dom_posts or [])
    
    # Try visible_posts.json (from parse_snapshot_posts.py)
    snapshot_posts = load_json('data/visible_posts.json')
    if snapshot_posts:
        snapshot_posts = snapshot_posts if isinstance(snapshot_posts, list) else snapshot_posts.get('posts', [])
    else:
        snapshot_posts = []
    
    print(f"Loaded: {len(dom_posts)} DOM posts, {len(snapshot_posts)} snapshot posts", flush=True)
    
    # Match and merge
    matches = match_posts_by_index(dom_posts, snapshot_posts)
    merged_posts = []
    
    for idx, (dom_post, snapshot_post) in enumerate(matches, 1):
        merged = merge_post(dom_post, snapshot_post, idx)
        merged_posts.append(merged)
    
    # Output
    result = {
        'total': len(merged_posts),
        'merged_at': datetime.now().isoformat(),
        'posts': merged_posts,
        'summary': {
            'all_fields_present': sum(1 for p in merged_posts if not any(p['flags'].values())),
            'missing_author': sum(1 for p in merged_posts if p['flags']['missing_author']),
            'missing_time': sum(1 for p in merged_posts if p['flags']['missing_time']),
            'missing_text': sum(1 for p in merged_posts if p['flags']['missing_text']),
            'missing_refs': sum(1 for p in merged_posts if p['flags']['missing_refs']),
            'low_confidence': sum(1 for p in merged_posts if p['flags']['low_confidence'])
        }
    }
    
    # Save
    output_file = Path('data/processed/merged_posts.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(json.dumps(result['summary'], indent=2), flush=True)
    print(f"Saved to: {output_file}", flush=True)


if __name__ == '__main__':
    main()
