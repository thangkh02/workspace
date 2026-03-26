# Quick Start Guide - Facebook Group Posts Collection

## TL;DR - Lệnh nhanh

```powershell
# Điều kiện: Đã cấu hình browser, có group URL
cd c:\Users\pntha\.openclaw\workspace

# Chạy để lấy 10 bài viết từ group
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/123456789" `
    -TargetCount 10
```

## Kết quả

Tool sẽ:
1. ✅ **Tự động mở browser** → điều hướng tới group
2. ✅ **Expand các "Xem thêm"** để show full posts
3. ✅ **Extract tất cả dữ liệu** (author, time, text, comment count)
4. ✅ **Scroll feed** để tìm posts mới
5. ✅ **Lặp lại** cho đến khi có đủ 10 posts
6. ✅ **Lưu kết quả** vào `data/posts_collection.json`

**Output JSON** chứa:
```json
{
  "metadata": { /* info về collection */ },
  "posts": [
    {
      "post_key": "post_001",
      "author": "Tên người dùng",
      "time_label": "22 giờ",
      "post_text": "Nội dung bài viết...",
      "comment_count": 33,
      /* ... more fields ... */
    },
    /* ... 9 more posts ... */
  ]
}
```

## Các Lựa Chọn Khác

### Lấy 15 bài viết
```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/123456789" `
    -TargetCount 15
```

### Tăng giới hạn iteration (nếu group có ít posts)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/123456789" `
    -TargetCount 10 `
    -MaxIterations 50
```

### Custom output directory
```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/123456789" `
    -TargetCount 10 `
    -OutputDir "data/my_group"
```

## Dòng Chảy Chi Tiết

```
Lặp (max 20 lần):
  ├─ 1️⃣ Expand "Xem thêm" buttons
  ├─ 2️⃣ Extract posts từ DOM (author, time, text)
  ├─ 3️⃣ Lookup action button refs (like, comment, share)
  ├─ 4️⃣ Parse các snapshot files
  ├─ 5️⃣ Merge dữ liệu
  ├─ ✓ Kiểm tra: đã có 10 posts?
  ├─ 🎯 YES → Kết thúc
  └─ ❌ NO → Scroll down → Quay lại bước 1

Sau cùng:
  ├─ Merge posts từ tất cả iterations
  ├─ Remove duplicates (cùng author + time)
  ├─ Lấy top 10
  └─ Lưu vào data/posts_collection.json
```

## Files được tạo

### Tập tin Output
- `data/posts_collection.json` ← **The main result** (merged + deduped)
- `data/visible_posts.json` ← Latest iteration raw data
- `logs/collect_posts.log` ← Full execution log

### Tập tin Backup (từng iteration)
- `data/visible_posts_iter_1.json`
- `data/visible_posts_iter_2.json`
- ... (N iterations)

## Xem Kết Quả

### Nhanh chóng - PowerShell
```powershell
# Xem số posts
(Get-Content data/posts_collection.json | ConvertFrom-Json).posts.Count

# Xem tên tác giả của posts
(Get-Content data/posts_collection.json | ConvertFrom-Json).posts | Select-Object author
```

### Chi tiết - Mở JSON
```powershell
# Mở file với VS Code
code data/posts_collection.json
```

### Script - Python
```python
import json
with open('data/posts_collection.json') as f:
    data = json.load(f)
    print(f"Collected {len(data['posts'])} posts")
    for post in data['posts']:
        print(f"  • {post['author']}: {post['post_text'][:50]}...")
```

## Lỗi Thường Gặp & Cách Khắc Phục

### "GroupUrl is required"
```powershell
# ❌ Sai: Không có URL
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1

# ✅ Đúng: Phải có -GroupUrl
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 -GroupUrl "..."
```

### "Invalid Facebook group URL"
```powershell
# ❌ Sai:
-GroupUrl "https://facebook.com/myngroup"      # Thiếu /groups/
-GroupUrl "https://www.facebook.com/MY_GROUP" # Không có /groups/

# ✅ Đúng:
-GroupUrl "https://www.facebook.com/groups/123456789"
```

### Quá ít posts được collect
- Tăng `MaxIterations` (default 20, thử 50):
  ```powershell
  -MaxIterations 50
  ```
- Group có thể ít posts hoặc bài viết bị hạn chế quyền xem

### Browser không mở
- Check browser profile tồn tại: `openclaw`
- Thử đặt tường minh: `-BrowserProfile "openclaw"`

## Tính Năng & Ưu Điểm

✅ **Tự động hoàn toàn**
- Không cần click manual
- Loop tự động cho đến 10 posts
- Scroll tự động

✅ **Dữ liệu sạch & Đáng tin**
- Exact author + time captured từ DOM
- Removal duplicates
- Confidence scoring

✅ **An toàn (DRY-RUN)**
- Chỉ đọc dữ liệu
- KHÔNG post/comment/share
- KHÔNG submit forms
- Compliant với AGENTS.md constraints

✅ **Logging & Transparency**
- Full log tất cả operations
- Backup từng iteration
- Metadata trong output

## Limitation

⚠️ **Hiện tại:**
- Posts bị ẩn danh hoặc restricted không được capture
- Nếu group có <10 posts và MaxIterations = 20, sẽ collect tất cả
- Ads/promoted posts có thể bị skip (heuristic filtering)

## Tiếp Theo

1. Collect posts → `data/posts_collection.json`
2. Parse JSON → Load vào DB/Excel/etc
3. Phân tích trending topics, authors, engagement
4. Report/visualize

---

**Status**: Ready to use
**Last Updated**: 2026-03-25
