# Scroll Debugging Guide

## Hiện Tại: Aggressive Scroll Strategy

### Cách Hoạt Động (scroll_page.js)

```javascript
// 1. Count posts trước scroll
initialPostCount = document.querySelectorAll('article').length

// 2. Scroll 3 lần (1500px mỗi lần) để trigger load
for (i = 0 to 3) {
  window.scrollBy({ top: 1500, behavior: 'auto' })
}

// 3. Scroll to absolute bottom
window.scrollTo({ top: maxScroll, behavior: 'auto' })

// 4. Wait 4 giây cho Intersection Observer
setTimeout(() => {
  finalPostCount = document.querySelectorAll('article').length
  newPostsLoaded = finalPostCount - initialPostCount
}, 4000)
```

### Output Mới

```json
{
  "status": "success",
  "scroll_attempts": 4,
  "scroll_total_distance": 4500,
  "initial_post_count": 6,
  "final_post_count": 10,
  "new_posts_loaded": 4,
  "loaded_new_content": true
}
```

## Log Output Chi Tiết

Trong collect script, sẽ log:
```
Scroll complete:
  - Scroll distance: 4500px
  - Posts before scroll: 6
  - Posts after scroll: 10
  - New posts loaded: 4
```

## Troubleshooting

### Nếu `new_posts_loaded = 0`
- Group chỉ có 6 posts visible
- Hoặc scroll không trigger Facebook infinite scroll
- Hoặc posts require user interaction (click, hover)

### Nếu `new_posts_loaded > 0`
- Scroll hoạt động!
- Feed load thêm posts sau scroll
- Collection sẽ get more posts ở lần tiếp theo

## Test Cách Scroll

Chạy để xem scroll report:

```powershell
# Run 1-2 iterations để thấy scroll effect
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/792610141458395/" `
    -TargetCount 10 `
    -MaxIterations 2
```

Check log:
```powershell
code logs/collect_posts.log
```

Tìm dòng:
```
[INFO] Scroll complete:
[INFO]   - New posts loaded: X
```

- **X = 0**: Scroll fail, need different approach
- **X > 0**: Scroll OK! Should get more posts

## Nếu Vẫn Không Ổn

Alternative approaches:

1. **Wait lâu hơn** (4s → 6s)
2. **Scroll từng element** thay vì 1 lần
3. **Trigger scroll events** thay vì chỉ scrollBy
4. **Hover elements** để lazy-load content

Báo cho tôi kết quả sau khi chạy!
