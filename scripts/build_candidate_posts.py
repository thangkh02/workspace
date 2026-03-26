#!/usr/bin/env python3
"""
build_candidate_posts.py

Mục đích: Lọc merged posts, chỉ giữ những bài đủ tin cậy và đúng chủ đề để đưa vào kế hoạch.
Input:  data/processed/merged_posts.json
        data/groups.json (để lấy topic_keywords và group config)
Output: data/processed/candidate_posts.json

Tiêu chí lọc:
- confidence >= 0.6
- Có ít nhất 2 trong 3: author, time_label, post_text
- skip_reason IS NULL
- (Nếu có topic_keywords) post_text phải chứa ít nhất 1 keyword
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

HIGH_ENGAGEMENT_THRESHOLD = 5   # Min comment count to boost confidence score


def load_json(path: str) -> Optional[Any]:
    f = Path(path)
    if not f.exists():
        return None
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            return json.load(fp)
    except Exception as e:
        print(f"Error loading {path}: {e}", flush=True)
        return None


def matches_keywords(text: str, keywords: List[str]) -> bool:
    """Return True if text contains at least one keyword (case-insensitive)."""
    if not keywords:
        return True  # No filter = accept all
    text_lower = (text or '').lower()
    return any(kw.lower() in text_lower for kw in keywords)


def score_post(post: Dict[str, Any], topic_keywords: List[str]) -> float:
    """Return adjusted score for ranking candidates."""
    base = post.get('confidence', 0.5)

    # Boost if post_text matches keywords
    if topic_keywords and matches_keywords(post.get('post_text', ''), topic_keywords):
        base = min(base + 0.1, 1.0)

    # Boost for engagement
    engagement = post.get('engagement', {})
    if engagement.get('comment_count', 0) > HIGH_ENGAGEMENT_THRESHOLD:
        base = min(base + 0.05, 1.0)

    return round(base, 4)


def build_candidates(
    merged_file: str = 'data/processed/merged_posts.json',
    groups_file: str = 'data/groups.json',
    output_file: str = 'data/processed/candidate_posts.json',
    min_confidence: float = 0.6
) -> Dict[str, Any]:
    print(f"Loading merged posts from {merged_file} ...", flush=True)
    merged_data = load_json(merged_file)

    posts: List[Dict] = []
    if merged_data:
        if isinstance(merged_data, dict):
            posts = merged_data.get('posts', [])
        elif isinstance(merged_data, list):
            posts = merged_data

    # Load group config for keywords
    groups_config = load_json(groups_file) or []
    if isinstance(groups_config, dict):
        groups_config = groups_config.get('groups', [])

    # Collect all topic_keywords across all groups
    all_keywords: List[str] = []
    for g in groups_config:
        kws = g.get('topic_keywords', [])
        if isinstance(kws, list):
            all_keywords.extend(kws)
        # Also check rules
        for rule in g.get('rules', []):
            if rule.get('action') == 'include':
                all_keywords.extend(rule.get('keywords', []))

    print(f"Topic keywords: {all_keywords or '(none - accept all)'}", flush=True)
    print(f"Total merged posts: {len(posts)}", flush=True)

    candidates = []
    skipped = {'low_confidence': 0, 'missing_fields': 0, 'skip_reason': 0, 'keyword_mismatch': 0}

    for post in posts:
        # Skip if explicitly flagged
        if post.get('skip_reason'):
            skipped['skip_reason'] += 1
            continue

        # Confidence threshold
        confidence = post.get('confidence', 0)
        if confidence < min_confidence:
            skipped['low_confidence'] += 1
            continue

        # Require at least 2 of 3 core fields
        has_author = bool(post.get('author'))
        has_time = bool(post.get('time_label'))
        has_text = bool(post.get('post_text'))
        field_count = sum([has_author, has_time, has_text])
        if field_count < 2:
            skipped['missing_fields'] += 1
            continue

        # Keyword filter (only if keywords are configured)
        if all_keywords and not matches_keywords(post.get('post_text', ''), all_keywords):
            skipped['keyword_mismatch'] += 1
            continue

        # Build candidate entry
        candidate = {
            'post_key': post.get('post_key'),
            'author': post.get('author'),
            'time_label': post.get('time_label'),
            'post_text': post.get('post_text'),
            'confidence': post.get('confidence'),
            'score': score_post(post, all_keywords),
            'engagement': post.get('engagement', {}),
            'refs': post.get('refs', {}),
            'flags': post.get('flags', {}),
            'matched_keywords': [kw for kw in all_keywords if kw.lower() in (post.get('post_text') or '').lower()],
            'candidate_at': datetime.now().isoformat()
        }
        candidates.append(candidate)

    # Sort by score descending
    candidates.sort(key=lambda c: c['score'], reverse=True)

    result = {
        'total_input': len(posts),
        'total_candidates': len(candidates),
        'skipped': skipped,
        'built_at': datetime.now().isoformat(),
        'candidates': candidates
    }

    # Save
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Candidates: {len(candidates)} (from {len(posts)} merged posts)", flush=True)
    print(f"Skipped: {skipped}", flush=True)
    print(f"Saved to: {output_file}", flush=True)

    return result


if __name__ == '__main__':
    import sys
    merged = sys.argv[1] if len(sys.argv) > 1 else 'data/processed/merged_posts.json'
    groups = sys.argv[2] if len(sys.argv) > 2 else 'data/groups.json'
    output = sys.argv[3] if len(sys.argv) > 3 else 'data/processed/candidate_posts.json'

    r = build_candidates(merged, groups, output)
    sys.exit(0 if r['total_candidates'] >= 0 else 1)
