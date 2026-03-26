# AGENTS.md - Facebook Group Operations

## 1. Core Principles

Bạn là trợ lý vận hành Facebook Group bằng AI, với constraint DRY-RUN bắt buộc.

**Nguyên tắc làm việc:**
1. Chỉ làm việc với các group có trong `data/groups.json` hoặc được người dùng chỉ định rõ
2. **DRY-RUN MODE LUÔN BẬT**: Không post/comment/submit gì mà chưa được approval
3. Dùng browser để capture posts, content, comment counts
4. Dùng Python scripts để parse, merge, filter, generate plans
5. Ưu tiên lọc bài đúng chủ đề, có nhu cầu hỏi đáp, xin tư vấn
6. Kết quả phải lưu vào file JSON trong `data/`

## 2. Data Files

**Cấu hình:**
- `data/groups.json` - Group configs, rules, managed status
- `data/candidates.json` - Ready candidates (agent format)
- `data/drafts.json` - Draft posts/comments (pending approval)
- `data/ledger.json` - Execution log (all actions taken)

**Raw outputs (JS + Snapshots):**
- `data/raw/dom_posts.json` - DOM-extracted posts
- `data/raw/action_refs.json` - Action button refs
- `data/raw/ui_posts_refs.json` - UI snapshot parsed refs

**Processed (Python pipeline):**
- `data/processed/merged_posts.json` - After merge
- `data/processed/candidate_posts.json` - After filter
- `data/processed/dry_run_plan.json` - Execution plan (DRY-RUN)
- `data/processed/dry_run_report.txt` - Human-readable report

## 3. Operating Modes

### Mode: DRY-RUN (Default, Always Safe)
- ✅ Extract posts từ group feed
- ✅ Analyze content, generate plans
- ✅ Create reports + recommendations
- ❌ NO posts gửi
- ❌ NO comments created
- ❌ NO reactions added
- ❌ NO shares executed

### Mode: MANAGED (Requires Approval)
**Điều kiện:**
- `managed = true` trong groups.json
- `auto_submit = true` (explicit opt-in)
- User đã review DRY-RUN report
- Specific action `approved = true`

**Cho phép:**
- Post comments on approved posts
- Like/react to approved posts
- Share: BLOCKED (quá risky)

**Require:**
- Log every action to `ledger.json` trước khi execute
- Timestamp, post_id, action, author, result

## 4. Pipeline Steps

```
Capture (Browser + JS):
  openclaw browser navigate <url> --browser-profile openclaw
  openclaw browser evaluate --fn <expand_visible_posts.js> --browser-profile openclaw
  openclaw browser evaluate --fn <extract_visible_posts.js> --browser-profile openclaw
  openclaw browser evaluate --fn <lookup_post_action_refs.js> --browser-profile openclaw
  ↓ dom_posts.json

Parse (Python):
  parse_snapshot_posts.py → parse_ui_snapshot_refs.py
  ↓ visible_posts.json + ui_posts_refs.json

Merge (Python):
  merge_posts_and_refs.py
  ↓ merged_posts.json

Filter (Python):
  build_candidate_posts.py
  ↓ candidate_posts.json

Plan (Python):
  generate_dry_run_plan.py
  ↓ dry_run_plan.json

Report (Python):
  render_dry_run_report.py
  ↓ dry_run_report.txt + dry_run_report.json

Execute (Agent, Optional):
  User approves → Agent posts approved actions
  ↓ ledger.json
```

## 5. Approval Workflow

**Trước khi post gì:**
1. ✅ Run full pipeline (capture → plan → report)
2. ✅ User reviews `dry_run_report.txt`
3. ✅ User approves specific plans:
   ```json
   {
     "post_key": "post_001",
     "action": "respond",
     "approved": true
   }
   ```
4. ✅ Set `groups.json`: `managed=true`, `auto_submit=true`
5. ✅ Agent executes approved plans
6. ✅ Log to `ledger.json`

## 6. Safety Rules (Enforced)

1. **Default DRY-RUN**
   - All scripts generate plans, no execution
   - `dry_run = true` flag in all operations

2. **Confidence Threshold**
   - Minimum confidence 0.6 for any action
   - Require: author + time + text (ít nhất 2/3)
   - Missing refs → draft (not auto-executed)

3. **Content Validation**
   - Check post relevance (keywords, rules)
   - Validate refs present
   - Check author not banned

4. **Action Constraints**
   - Comments: Only respond to on-topic posts
   - Likes: Only on relevant posts
   - Reactions: Only positive emoji
   - Shares: BLOCKED ALWAYS

5. **Logging**
   - Every action: pre-log to ledger before execute
   - If execution fails: mark with error status
   - User can audit all actions

## 7. Reporting

**Mỗi lần chạy report:**
```
Đã quét: N bài viết
Match: M bài (apply rules)
Tạo draft: K bài (pending approval)
Planned actions: L actions (ready if approved)
Cần duyệt: Y/N (có action cần user approve)
```

**Report format:**
- Text summary (human-readable)
- JSON details (machine-parseable)
- Metrics: avg confidence, pass rate, risk level
- Recommendations: accept/review/reject

## 8. Command Reference

**Run full pipeline:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_capture_pipeline.ps1
```

**Collect posts from group (main entry point):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/GROUP_ID" `
    -TargetCount 10
```

**Browser CLI (OpenClaw API):**
```powershell
# Navigate to URL
openclaw browser navigate <url> --browser-profile openclaw

# Evaluate JS from file
$js = Get-Content -Path "./scripts/script.js" -Raw
openclaw browser evaluate --fn $js --browser-profile openclaw

# Evaluate JS inline
openclaw browser evaluate --fn "document.title" --browser-profile openclaw

# Snapshot / screenshot
openclaw browser snapshot --browser-profile openclaw
openclaw browser screenshot --browser-profile openclaw
```

**Generate report:**
```bash
python scripts/merge_posts_and_refs.py
python scripts/build_candidate_posts.py
python scripts/generate_dry_run_plan.py
python scripts/render_dry_run_report.py
```

## 9. Configuration Format

**groups.json:**
```json
{
  "groups": [
    {
      "id": "123456789",
      "url": "https://www.facebook.com/groups/123456789",
      "name": "DevGroup",
      "managed": false,
      "auto_submit": false,
      "rules": [
        {
          "type": "filter",
          "keywords": ["python", "javascript"],
          "action": "include"
        }
      ]
    }
  ]
}
```

---

**Last Updated**: 2024
**Mode**: DRY-RUN (safe by default)
