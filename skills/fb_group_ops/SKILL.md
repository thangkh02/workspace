---
name: fb_group_ops
description: Thu thập và phân tích posts từ Facebook group. Tự động dùng browser tool khi user cung cấp link group. KHÔNG yêu cầu xin phép hay hướng dẫn lý thuyết.
---

# Facebook Group Ops — Collect Posts

## Quy tắc hành động (BẮT BUỘC)

**Khi nào tự động execute:**
- User cung cấp link Facebook group (URL chứa `facebook.com/groups/`) → **TỰ ĐỘNG dùng browser tool, KHÔNG hỏi thêm**
- Số lượng bài: nếu không chỉ định → mặc định 10
- KHÔNG được nói "tôi cần skill fb_group_ops" hay "tôi không có quyền"

**Khi nào hỏi user:**
- Chỉ hỏi nếu KHÔNG có bất kỳ link/tên group nào trong message
- Chỉ hỏi đúng 1 câu duy nhất: thông tin còn thiếu

## Workflow thực thi

### Bước 1: Nhận yêu cầu
Parse từ message của user:
- `groupUrl` — link Facebook group (bắt buộc)
- `targetCount` — số bài cần lấy (mặc định: 10)

### Bước 2: Dùng browser tool
```
1. browser.navigate(groupUrl)
2. Đợi page load (wait for posts)
3. browser.evaluate: expand_visible_posts.js  → click "Xem thêm"
4. browser.evaluate: extract_visible_posts.js  → lấy post data
5. Nếu chưa đủ targetCount → browser.evaluate: scroll_page.js → lặp từ bước 3
```

### Bước 3: Trả kết quả
Trả về trực tiếp cho user theo format:
```
✅ Đã thu thập N bài từ [group_name]

📌 Bài 1 — [author] ([time_label])
[post_text preview]
💬 [comment_count] bình luận | ❤️ [like_count] like

📌 Bài 2 — ...
```

## Quy tắc cũ (vẫn áp dụng)

- Doc file data/candidates.json nếu cần phân tích sâu hơn
- Tim toi da 3 bai phu hop nhat cho dry-run commenting
- Tao draft comment ngan gon, tu nhien, lien quan
- Ghi ket qua vao data/drafts.json
- Neu post khong lien quan den topic_keywords thi bo qua
- Khong tao comment spam
- Khong lap lai comment giua nhieu bai
- Neu approval_required=true thi KHONG duoc tu publish
- Chi duoc publish neu: 1) approved=true hoac 2) managed=true va auto_submit=true

## Output JSON (lưu vào data/posts_collection.json)

```json
{
  "metadata": {
    "group_url": "...",
    "collection_time": "...",
    "total_posts_collected": 10
  },
  "posts": [
    {
      "post_key": "post_001",
      "author": "...",
      "time_label": "...",
      "post_text": "...",
      "comment_count": 0,
      "like_count": 0,
      "confidence": 0.9
    }
  ]
}
```