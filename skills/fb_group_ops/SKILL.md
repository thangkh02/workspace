---
name: fb_group_ops
description: Tự động thu thập bài viết từ Facebook group ở chế độ DRY-RUN (chỉ đọc) khi nhận link group từ user.
---

# Facebook Group Ops

## Mục tiêu chính

**fb_group_ops là tool dùng để tự động thu thập và phân tích bài viết từ Facebook group.**

Cụ thể:
- Nhận link Facebook group từ user
- Mở browser, điều hướng đến group
- Thu thập bài viết: tác giả, thời gian, nội dung, số comment/like
- Lọc bài phù hợp theo topic_keywords (nếu có)
- Tạo báo cáo có cấu trúc (JSON + text)
- Ghi kết quả vào data/

## Khi nào kích hoạt

Kích hoạt **ngay lập tức** khi user cung cấp:
- Link Facebook group (bắt buộc)
- Số lượng bài cần lấy (tùy chọn, mặc định: 10)

**KHÔNG** hỏi thêm thông tin nếu đã có link. **KHÔNG** trả lời hướng dẫn lý thuyết.

## Hành động tự động

1. Parse URL và số lượng từ message của user
2. Mở browser → điều hướng đến Facebook group
3. Thu thập bài viết (scroll, expand, extract)
4. Xử lý dữ liệu qua pipeline Python
5. Trả về kết quả có cấu trúc: author, time, text, comment_count

## Quy tắc an toàn (DRY-RUN)

- Chỉ đọc (READ ONLY) — không đăng, không comment, không react
- approval_required=true → KHÔNG tự publish
- Chỉ publish khi: approved=true HOẶC (managed=true VÀ auto_submit=true)
- Mọi hành động đều ghi log vào data/ledger.json

## Output

```json
{
  "metadata": {
    "group_url": "...",
    "total_posts_collected": 10,
    "collection_time": "..."
  },
  "posts": [
    {
      "post_key": "post_001",
      "author": "Tên người dùng",
      "time_label": "22 giờ",
      "post_text": "Nội dung bài viết...",
      "comment_count": 33,
      "confidence": 0.95
    }
  ]
}
```

## Score & Filter

- Score: 0.0 → 1.0 (>= 0.75 mới giữ lại)
- Bỏ qua post không liên quan đến topic_keywords
- Không tạo comment spam, không lặp lại comment

## Giọng văn (khi tạo draft comment)

- Ngắn gọn, tự nhiên
- Không quá sales
- Không khẳng định điều không biết chắc