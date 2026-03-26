---
name: collect_posts
description: Thu thập bài viết từ Facebook group bằng browser. Tự động thực thi khi user cung cấp link group và số lượng. KHÔNG hỏi thêm nếu đã đủ thông tin.
triggers:
  - "lấy * bài * từ group"
  - "collect * posts from"
  - "thu thập * bài"
  - "extract * posts"
---

# Skill: collect_posts — Thu thập bài viết Facebook Group

## Mục tiêu

Khi user cung cấp **link Facebook group** và **số lượng bài viết**, skill này **tự động thực thi** và trả về danh sách bài viết với: author, time_label, post_text, comment_count.

## Input

| Tham số | Nguồn | Mặc định |
|---------|-------|----------|
| `group_url` | Parse từ prompt (regex facebook.com/groups/...) | BẮT BUỘC |
| `target_count` | Số nguyên trong prompt | 5 |

## Execution Flow

### Bước 1: Parse prompt

```
group_url = regex_match(r'https?://[^\s]*facebook\.com/groups/[^\s<>"]+', prompt)
target_count = first_integer_near(["bài", "posts", "bài viết", "articles"], prompt) or 5
```

### Bước 2: Navigate browser

```
browser.navigate(group_url)
browser.wait(3000)  # chờ load
```

### Bước 3: Expand tất cả "Xem thêm"

Inject JavaScript:
```javascript
const expandBtns = document.querySelectorAll('[role="button"]');
expandBtns.forEach(btn => {
  if (btn.textContent.trim() === 'Xem thêm' || btn.textContent.trim() === 'See more') {
    btn.click();
  }
});
```

### Bước 4: Extract posts

Inject JavaScript (thay `{{TARGET_COUNT}}` bằng target_count):
```javascript
const posts = [];
const units = document.querySelectorAll('[data-pagelet^="FeedUnit_"], [role="article"]');
units.forEach((unit, i) => {
  if (posts.length >= {{TARGET_COUNT}}) return;
  const author = (
    unit.querySelector('h2 a')?.textContent ||
    unit.querySelector('h3 a')?.textContent ||
    unit.querySelector('strong a')?.textContent ||
    unit.querySelector('a[href*="profile"] span')?.textContent ||
    ''
  ).trim();
  const textEl = (
    unit.querySelector('[data-ad-comet-preview="message"]') ||
    unit.querySelector('[data-testid="post_message"]') ||
    unit.querySelector('div[dir="auto"]')
  );
  const text = textEl?.textContent?.trim().slice(0, 500) || '';
  const time = (
    unit.querySelector('abbr[data-utime]')?.getAttribute('title') ||
    unit.querySelector('a[href*="/posts/"] span')?.textContent ||
    unit.querySelector('a[href*="?story_fbid"] span')?.textContent ||
    ''
  ).trim();
  const commentMatch = [...unit.querySelectorAll('span')].find(s => /\d+\s*(bình luận|comment)/i.test(s.textContent));
  const comment_count = parseInt(commentMatch?.textContent?.match(/\d+/)?.[0] || '0');
  if (author || text) {
    posts.push({
      post_key: `post_${String(posts.length + 1).padStart(3, '0')}`,
      author,
      time_label: time,
      post_text: text,
      comment_count
    });
  }
});
JSON.stringify(posts);
```

### Bước 5: Nếu thiếu posts → scroll và retry

```
if (collected < target_count):
  for i in range(5):
    browser.execute("window.scrollBy(0, 2000)")
    browser.wait(2000)
    # Lặp lại bước 4
    if collected >= target_count: break
```

### Bước 6: Hiển thị kết quả

Format output:
```
✅ Đã thu thập {collected}/{target_count} bài viết từ {group_url}

| # | Tác giả | Thời gian | Nội dung (tóm tắt) | Bình luận |
|---|---------|-----------|-------------------|-----------|
| 1 | {author} | {time_label} | {post_text[:100]}... | {comment_count} |
...

📁 Đã lưu vào data/posts_collection.json
```

## Error Handling

| Lỗi | Xử lý |
|-----|-------|
| Chưa đăng nhập Facebook | Thông báo: "Cần đăng nhập Facebook trong browser trước" |
| Group private / không tồn tại | Thông báo: "Không thể truy cập group này" |
| 0 bài tìm được sau 5 scroll | Thông báo: "Không tìm thấy bài viết. Group có thể yêu cầu đăng nhập hoặc join trước." |
| URL không hợp lệ | Hỏi: "Link group không hợp lệ. Bạn có thể dán đúng link Facebook group không?" |

## QUAN TRỌNG

- **KHÔNG giải thích workflow trước khi chạy**
- **KHÔNG hỏi lại nếu đã có đủ URL + count (hoặc dùng default)**
- **KHÔNG trả lời "tôi có thể hướng dẫn bạn"**
- Chỉ hỏi khi **thiếu group URL** — đúng 1 câu ngắn
- Kết quả phải có ít nhất: author HOẶC post_text để được tính là hợp lệ
