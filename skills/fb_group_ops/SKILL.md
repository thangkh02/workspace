---
name: fb_group_ops
description: Thu thập bài viết từ Facebook group và quản lý tương tác. Khi user yêu cầu lấy bài viết, tự động chạy workflow collect và trả kết quả. Nếu thiếu thông tin chỉ hỏi ngắn gọn, không giải thích lý thuyết.
---

# Facebook Group Ops

## Hành động 1: Thu thập bài viết (COLLECT POSTS)

**Kích hoạt khi:** User yêu cầu lấy/thu thập/collect bài viết từ group Facebook.

**Quy trình tự động:**
1. Parse group URL và số lượng từ message của user
2. Chạy lệnh:
   ```
   powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 -GroupUrl "<URL>" -TargetCount <N>
   ```
3. Đọc kết quả từ `data/posts_collection.json`
4. Trả về thông tin: author, post_text, comment_count, time cho mỗi bài

**Nếu thiếu thông tin:**
- Thiếu URL và số lượng: "Vui lòng gửi link group Facebook và số lượng bài cần lấy"
- Chỉ thiếu URL: "Vui lòng gửi link group Facebook"
- Chỉ thiếu số lượng: Dùng mặc định 10 bài

**Tuyệt đối KHÔNG:**
- Không giải thích lý thuyết về fb_group_ops
- Không nói "tôi không có quyền truy cập"
- Không liệt kê hướng dẫn dài dòng
- Không hỏi lại nếu đã đủ thông tin

**Format kết quả trả về:**
```
✅ Đã thu thập <N> bài từ group <tên-hoặc-url>

Bài 1: <author> (<time>)
<post_text rút gọn 200 ký tự>
💬 <comment_count> bình luận

Bài 2: ...
```

## Hành động 2: Quản lý draft comments

**Kích hoạt khi:** User yêu cầu tạo comment/nhận xét cho các bài ứng viên.

**Quy trình:**
- Đọc file `data/candidates.json`
- Tìm tối đa 3 bài phù hợp nhất theo topic_keywords
- Tạo draft comment ngắn gọn, tự nhiên, liên quan
- Ghi kết quả vào `data/drafts.json`

**Quy tắc:**
- Nếu post không liên quan đến topic_keywords thì bỏ qua
- Không tạo comment spam
- Không lặp lại comment giữa nhiều bài
- Nếu `approval_required=true` thì KHÔNG được tự publish
- Chỉ publish nếu: `approved=true` hoặc (`managed=true` và `auto_submit=true`)

**Output JSON fields:**
- key, group_name, permalink, matched, score, reason
- draft_comment, managed, approval_required, auto_submit, approved

**Score:** 0.0-1.0, chỉ giữ >= 0.75

**Giọng văn:** ngắn gọn, tự nhiên, không quá sale, không khẳng định điều không chắc