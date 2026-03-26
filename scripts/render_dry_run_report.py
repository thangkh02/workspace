#!/usr/bin/env python3
"""
render_dry_run_report.py

Mục đích: Render báo cáo DRY-RUN thành dạng human-readable và machine-readable.
Input:  data/processed/dry_run_plan.json
Output: data/processed/dry_run_report.txt  (human-readable)
        data/processed/dry_run_report.json (machine-readable with metrics)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

MEDIUM_RISK_THRESHOLD = 5   # respond actions count above which risk is 'medium'
HIGH_RISK_THRESHOLD = 10    # respond actions count above which risk is 'high'


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


def render_text_report(plan: Dict[str, Any]) -> str:
    """Render a human-readable text report from the dry-run plan."""
    lines = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summary = plan.get('summary', {})
    actions = plan.get('actions', [])
    total = plan.get('total_actions', 0)

    lines.append("=" * 60)
    lines.append("       📋 DRY-RUN REPORT — Facebook Group Ops")
    lines.append("=" * 60)
    lines.append(f"Thời điểm: {now}")
    lines.append(f"Chế độ:    DRY-RUN (chỉ xem, không thực thi)")
    lines.append("")
    lines.append("── TỔNG QUAN ─────────────────────────────────────────")
    lines.append(f"  Bài viết đã quét:    {total}")
    lines.append(f"  Đề xuất respond:     {summary.get('respond', 0)}")
    lines.append(f"  Đề xuất like:        {summary.get('like', 0)}")
    lines.append(f"  Bỏ qua (skip):       {summary.get('skip', 0)}")
    lines.append(f"  Cần duyệt:           {'CÓ' if total > 0 else 'KHÔNG'}")
    lines.append("")

    respond_actions = [a for a in actions if a.get('proposed_action') == 'respond']
    like_actions = [a for a in actions if a.get('proposed_action') == 'like']

    if respond_actions:
        lines.append("── BÀI CẦN TRẢ LỜI (respond) ────────────────────────")
        for i, a in enumerate(respond_actions, 1):
            lines.append(f"\n  [{i}] {a.get('post_key', '?')} — {a.get('author', '(unknown)')}")
            lines.append(f"      Thời gian: {a.get('time_label', '?')}")
            preview = (a.get('post_text_preview') or '').replace('\n', ' ')[:120]
            lines.append(f"      Nội dung:  {preview}...")
            lines.append(f"      Score:     {a.get('score', 0):.2f}")
            if a.get('matched_keywords'):
                lines.append(f"      Keywords:  {', '.join(a['matched_keywords'])}")
            if a.get('draft_comment'):
                lines.append(f"      Draft:     {a['draft_comment']}")
            engagement = a.get('engagement', {})
            lines.append(f"      Engagement: 💬{engagement.get('comment_count', 0)} 👍{engagement.get('like_count', 0)}")
            lines.append(f"      Approval:  {'✅ Đã approve' if a.get('approved') else '⏳ Chờ duyệt'}")
        lines.append("")

    if like_actions:
        lines.append("── BÀI ĐỀ XUẤT LIKE ─────────────────────────────────")
        for i, a in enumerate(like_actions, 1):
            preview = (a.get('post_text_preview') or '').replace('\n', ' ')[:80]
            lines.append(f"  [{i}] {a.get('post_key', '?')} | {a.get('author', '?')} | score={a.get('score', 0):.2f}")
            lines.append(f"       {preview}...")
        lines.append("")

    lines.append("── HƯỚNG DẪN DUYỆT ───────────────────────────────────")
    lines.append("  1. Xem file: data/processed/dry_run_plan.json")
    lines.append('  2. Đặt "approved": true cho action muốn thực thi')
    lines.append('  3. Đặt groups.json: "managed": true, "auto_submit": true')
    lines.append("  4. Bot sẽ thực thi các action đã được approve")
    lines.append("")
    lines.append("⚠️  NHẮC NHỞ: Chưa có action nào được thực thi!")
    lines.append("=" * 60)

    return "\n".join(lines)


def calculate_metrics(actions: List[Dict]) -> Dict[str, Any]:
    """Calculate report metrics."""
    if not actions:
        return {'avg_confidence': 0, 'pass_rate': 0, 'risk_level': 'low'}

    scores = [a.get('score', 0) for a in actions]
    avg_score = sum(scores) / len(scores)

    respond_count = sum(1 for a in actions if a.get('proposed_action') == 'respond')
    pass_rate = respond_count / len(actions) if actions else 0

    risk = 'low'
    if respond_count > MEDIUM_RISK_THRESHOLD:
        risk = 'medium'
    if respond_count > HIGH_RISK_THRESHOLD:
        risk = 'high'

    return {
        'avg_score': round(avg_score, 4),
        'pass_rate': round(pass_rate, 4),
        'risk_level': risk,
        'total_with_refs': sum(1 for a in actions if a.get('refs', {}).get('comment_ref')),
        'pending_approval': sum(1 for a in actions if not a.get('approved') and a.get('proposed_action') != 'skip')
    }


def render_report(
    plan_file: str = 'data/processed/dry_run_plan.json',
    txt_output: str = 'data/processed/dry_run_report.txt',
    json_output: str = 'data/processed/dry_run_report.json'
) -> Dict[str, Any]:
    print(f"Loading plan from {plan_file} ...", flush=True)
    plan = load_json(plan_file)

    if not plan:
        print("No plan found. Run generate_dry_run_plan.py first.", flush=True)
        plan = {
            'dry_run': True,
            'total_actions': 0,
            'summary': {},
            'actions': [],
            'generated_at': datetime.now().isoformat()
        }

    actions = plan.get('actions', [])
    metrics = calculate_metrics(actions)

    # Text report
    text = render_text_report(plan)
    out_txt = Path(txt_output)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Text report saved to: {txt_output}", flush=True)

    # JSON report
    report_json = {
        'rendered_at': datetime.now().isoformat(),
        'dry_run': True,
        'metrics': metrics,
        'summary': plan.get('summary', {}),
        'total_actions': plan.get('total_actions', 0),
        'needs_approval': metrics['pending_approval'] > 0,
        'actions_preview': [
            {
                'post_key': a.get('post_key'),
                'author': a.get('author'),
                'action': a.get('proposed_action'),
                'score': a.get('score'),
                'approved': a.get('approved', False)
            }
            for a in actions
        ]
    }

    out_json = Path(json_output)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)
    print(f"JSON report saved to: {json_output}", flush=True)

    # Also print text to stdout
    print("\n" + text, flush=True)

    return report_json


if __name__ == '__main__':
    import sys
    plan = sys.argv[1] if len(sys.argv) > 1 else 'data/processed/dry_run_plan.json'
    txt = sys.argv[2] if len(sys.argv) > 2 else 'data/processed/dry_run_report.txt'
    js = sys.argv[3] if len(sys.argv) > 3 else 'data/processed/dry_run_report.json'

    r = render_report(plan, txt, js)
    sys.exit(0)
