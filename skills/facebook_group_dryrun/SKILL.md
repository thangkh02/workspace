---
name: facebook_group_dryrun
description: Chạy toàn bộ pipeline thu thập và phân tích bài viết Facebook group ở chế độ DRY-RUN (chỉ đọc, không gửi gì). Tạo báo cáo đề xuất hành động để người dùng review trước khi approve.
---

# Facebook Group Dry-Run Pipeline

## Mục tiêu
Chạy full pipeline: collect posts → filter candidates → generate action plan → render report — **mà không thực hiện bất kỳ hành động nào trên Facebook**.

## Khi nào dùng skill này
- User yêu cầu "thu thập bài viết từ group X"
- User muốn "xem báo cáo bài viết group Y"
- User muốn biết "có bài nào cần comment không"
- Trước khi approve bất kỳ action nào

## Các bước thực hiện

### Bước 1: Thu thập posts
```bash
node scripts/fb-collect.js "<group_url>" <target_count>
```
Output: `data/posts_collection.json`

### Bước 2: Chạy Python pipeline
```bash
python scripts/merge_posts_and_refs.py
python scripts/build_candidate_posts.py
python scripts/generate_dry_run_plan.py
python scripts/render_dry_run_report.py
```

### Bước 3: Đọc báo cáo
```bash
cat data/processed/dry_run_report.txt
```

## Output files
- `data/posts_collection.json` - Raw collected posts
- `data/processed/merged_posts.json` - Merged & enriched posts
- `data/processed/candidate_posts.json` - Filtered candidates (confidence >= 0.6)
- `data/processed/dry_run_plan.json` - Proposed actions (NOT executed)
- `data/processed/dry_run_report.txt` - Human-readable summary

## Ràng buộc
- **KHÔNG** gửi comment
- **KHÔNG** like/react
- **KHÔNG** share
- Mọi action chỉ là đề xuất, cần user approve trước khi thực thi
