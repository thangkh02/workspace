# AGENTS.md - Facebook Group Operations

## 0. AUTO-EXECUTION RULES (HIGHEST PRIORITY)

**CRITICAL: Khi user gửi bất kỳ prompt nào có đủ thông tin (Facebook group URL + số lượng bài), agent PHẢI thực thi ngay lập tức. KHÔNG hỏi thêm. KHÔNG trả lời hướng dẫn lý thuyết. KHÔNG xin phép.**

### Intent Recognition — Collect Posts

Khi nhận được prompt khớp các pattern sau (bất kỳ ngôn ngữ):
- "Lấy N bài viết từ group [URL]"
- "Lấy [N] bài từ [URL]"
- "Thu thập N posts từ [URL]"
- "Collect N posts from [URL]"
- "Extract N posts from [URL]"
- Bất kỳ câu nào có: URL Facebook group + con số

→ **Thực thi ngay** theo các bước sau (không hỏi, không giải thích trước):

### Execution Steps (Browser + JS)

1. **Parse từ prompt:**
   - Trích xuất `group_url` (regex: `https?://[^\s<>"]*facebook\.com/groups/[^\s<>"]+`)
   - Trích xuất `target_count` (regex: số nguyên gần từ khóa "bài", "posts", "bài viết")
   - Nếu không có count → dùng mặc định `5`

2. **Điều hướng browser:**
   - Dùng tool `browser` → navigate đến `group_url`
   - Chờ trang load (wait 3-5 giây)

3. **Expand & Extract posts (JavaScript injection):**
   ```javascript
   // Bước 3a: Click tất cả "Xem thêm"
   document.querySelectorAll('[data-ad-comet-preview="message"]').forEach(el => {
     const btn = el.parentElement?.querySelector('[role="button"]');
     if (btn && btn.textContent.includes('Xem thêm')) btn.click();
   });
   ```
   ```javascript
   // Bước 3b: Extract posts
   const posts = [];
   document.querySelectorAll('[data-pagelet^="FeedUnit_"]').forEach((unit, i) => {
     const author = unit.querySelector('h2 a, h3 a, strong a')?.textContent?.trim() || '';
     const text = unit.querySelector('[data-ad-comet-preview="message"], [data-testid="post_message"]')?.textContent?.trim() || '';
     const time = unit.querySelector('abbr[data-utime], a[aria-label] abbr, span[id*="jsc"] abbr')?.getAttribute('title') || 
                  unit.querySelector('a[href*="/posts/"] span')?.textContent?.trim() || '';
     const commentEl = unit.querySelectorAll('[aria-label*="bình luận"], [aria-label*="comment"]');
     const comment_count = commentEl[0]?.textContent?.match(/\d+/)?.[0] || '0';
     if (author || text) {
       posts.push({ post_key: `post_${String(posts.length+1).padStart(3,'0')}`, author, time_label: time, post_text: text.slice(0, 500), comment_count: parseInt(comment_count) });
     }
   });
   JSON.stringify(posts.slice(0, TARGET_COUNT));
   ```
   (Thay `TARGET_COUNT` = số lượng từ prompt)

4. **Nếu không đủ posts → scroll:**
   ```javascript
   window.scrollBy(0, 2000);
   ```
   Lặp lại bước 3 sau 2 giây, tối đa 5 lần scroll.

5. **Trả kết quả ngay** theo format:
   ```
   ✅ Đã thu thập [N] bài viết từ [group_url]
   
   | # | Tác giả | Thời gian | Nội dung (tóm tắt) | Bình luận |
   |---|---------|-----------|-------------------|-----------|
   | 1 | ...     | ...       | ...               | ...       |
   ...
   ```

### Rules — KHÔNG được làm

- ❌ KHÔNG hỏi "Bạn có muốn tôi giúp không?"
- ❌ KHÔNG liệt kê "Tôi cần thêm thông tin: tên nhóm, link nhóm, số lượng..."
- ❌ KHÔNG trả lời dạng "Tôi có thể hướng dẫn bạn..."
- ❌ KHÔNG giải thích workflow trước khi thực thi
- ✅ NẾU thiếu URL → hỏi đúng 1 câu: "Bạn muốn lấy bài từ group nào? (dán link vào)"
- ✅ NẾU thiếu số lượng → dùng mặc định 5, không hỏi

---

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
Capture (JS):
  expand_visible_posts.js → extract_visible_posts.js → lookup_post_action_refs.js
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
