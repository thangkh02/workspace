#!/usr/bin/env python3
"""
generate_dry_run_plan.py

Mục đích: Tạo kế hoạch hành động (DRY-RUN) từ danh sách candidate posts.
Input:  data/processed/candidate_posts.json
        data/groups.json
Output: data/processed/dry_run_plan.json

Logic:
- Mỗi candidate → propose action (respond / like / skip)
- Tạo draft_comment gợi ý (ngắn gọn, tự nhiên, liên quan chủ đề)
- Đánh dấu approval_required = true (luôn luôn)
- KHÔNG thực thi bất kỳ action nào
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


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


QUESTION_PATTERNS = [
    'ai biết', 'cho hỏi', 'mọi người ơi', 'giúp mình', 'tư vấn', 'hỏi thăm',
    'có ai', 'làm sao', 'như thế nào', 'bạn nào', 'kinh nghiệm', 'recommend',
    'suggest', 'help', 'question', 'ask', '?'
]


def is_question_post(text: str) -> bool:
    """Detect if post is asking for advice/help."""
    t = (text or '').lower()
    return any(p in t for p in QUESTION_PATTERNS)


def generate_draft_comment(post: Dict[str, Any], group_config: Optional[Dict]) -> str:
    """Generate a short, natural draft comment for the post."""
    text = (post.get('post_text') or '').strip()
    keywords = post.get('matched_keywords', [])

    if not text:
        return ''

    # Very short comment draft — placeholder for agent to customize
    if is_question_post(text):
        if keywords:
            return f"Mình có chút kinh nghiệm về {keywords[0]}, bạn có thể thử xem nhé!"
        return "Mình cũng đang tìm hiểu vấn đề này. Bạn đã thử cách nào chưa?"

    if keywords:
        return f"Chủ đề {keywords[0]} này khá hay! Cảm ơn bạn đã chia sẻ."

    return "Cảm ơn bạn đã chia sẻ thông tin hữu ích!"


def propose_action(post: Dict[str, Any]) -> str:
    """Decide what action to propose for a candidate post."""
    score = post.get('score', 0)
    text = post.get('post_text', '') or ''

    if score >= 0.75 and is_question_post(text):
        return 'respond'
    elif score >= 0.65:
        return 'like'
    else:
        return 'skip'


def generate_plan(
    candidates_file: str = 'data/processed/candidate_posts.json',
    groups_file: str = 'data/groups.json',
    output_file: str = 'data/processed/dry_run_plan.json'
) -> Dict[str, Any]:
    print(f"Loading candidates from {candidates_file} ...", flush=True)

    cand_data = load_json(candidates_file)
    candidates: List[Dict] = []
    if cand_data:
        if isinstance(cand_data, dict):
            candidates = cand_data.get('candidates', [])
        elif isinstance(cand_data, list):
            candidates = cand_data

    groups_raw = load_json(groups_file) or []
    if isinstance(groups_raw, dict):
        groups_raw = groups_raw.get('groups', [])
    group_map = {g.get('name', ''): g for g in groups_raw}

    print(f"Planning for {len(candidates)} candidates ...", flush=True)

    actions = []
    summary = {'respond': 0, 'like': 0, 'skip': 0}

    for cand in candidates:
        action = propose_action(cand)
        group_cfg = group_map.get(cand.get('group_name', ''))

        draft = ''
        if action == 'respond':
            draft = generate_draft_comment(cand, group_cfg)

        # Group-level overrides
        managed = False
        auto_submit = False
        approval_required = True
        if group_cfg:
            managed = bool(group_cfg.get('managed', False))
            auto_submit = bool(group_cfg.get('auto_submit', False))

        entry = {
            'post_key': cand.get('post_key'),
            'author': cand.get('author'),
            'time_label': cand.get('time_label'),
            'post_text_preview': (cand.get('post_text') or '')[:200],
            'score': cand.get('score'),
            'matched_keywords': cand.get('matched_keywords', []),
            'proposed_action': action,
            'draft_comment': draft,
            'refs': cand.get('refs', {}),
            'engagement': cand.get('engagement', {}),
            # Safety flags
            'managed': managed,
            'auto_submit': auto_submit,
            'approval_required': approval_required,  # always True in dry-run
            'approved': False,  # user must flip this
            'dry_run': True
        }
        actions.append(entry)
        summary[action] = summary.get(action, 0) + 1

    plan = {
        'generated_at': datetime.now().isoformat(),
        'dry_run': True,
        'total_actions': len(actions),
        'summary': summary,
        'actions': actions
    }

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"Plan: {summary}", flush=True)
    print(f"Saved to: {output_file}", flush=True)
    return plan


if __name__ == '__main__':
    import sys
    cands = sys.argv[1] if len(sys.argv) > 1 else 'data/processed/candidate_posts.json'
    groups = sys.argv[2] if len(sys.argv) > 2 else 'data/groups.json'
    output = sys.argv[3] if len(sys.argv) > 3 else 'data/processed/dry_run_plan.json'

    r = generate_plan(cands, groups, output)
    sys.exit(0)
