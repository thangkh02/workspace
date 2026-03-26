/**
 * expand_visible_posts.js
 * 
 * Mục đích: Expand các nút "Xem thêm" trên feed để hiển thị toàn bộ nội dung bài viết.
 * Chỉ phục vụ đọc dữ liệu (DRY-RUN), KHÔNG được click submit/send/post/comment.
 * 
 * Chạy: openclaw browser evaluate -i <browser_profile> ./scripts/expand_visible_posts.js
 */

(function() {
  const result = {
    clicked_count: 0,
    errors: [],
    actions: []
  };

  try {
    // Tìm tất cả nút "Xem thêm" / "See more" trên page
    // Heuristic: text node chứa "Xem thêm" hoặc "See more"
    const buttons = Array.from(document.querySelectorAll('button, div[role="button"], span[role="button"]'));
    
    // Filter buttons có text chứa "Xem thêm" hoặc "See more"
    const expandButtons = buttons.filter(btn => {
      const text = (btn.textContent || '').trim();
      return /xem thêm|see more/i.test(text);
    });

    console.log(`Found ${expandButtons.length} expand buttons`);

    // Click từng button theo thứ tự, với delay để DOM update
    let clickedCount = 0;
    for (let i = 0; i < expandButtons.length; i++) {
      try {
        const btn = expandButtons[i];
        const text = (btn.textContent || '').trim();
        
        // Check button visible trước khi click
        if (!btn.offsetParent) {
          result.actions.push({
            index: i,
            text: text,
            status: 'skip',
            reason: 'button_not_visible'
          });
          continue;
        }

        // Scroll vào view
        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Wait ngắn để scroll hoàn tất
        const delay = new Promise(resolve => setTimeout(resolve, 200));
        
        // Click button
        btn.click();
        clickedCount++;
        
        result.actions.push({
          index: i,
          text: text,
          status: 'clicked',
          position: {
            top: btn.offsetTop,
            left: btn.offsetLeft
          }
        });

      } catch (e) {
        result.errors.push({
          index: i,
          error: e.message,
          context: 'click_expand_button'
        });
      }
    }

    result.clicked_count = clickedCount;
    
    // Wait thêm time để tất cả DOM updates
    if (clickedCount > 0) {
      const delay = new Promise(resolve => setTimeout(resolve, Math.min(clickedCount * 300, 1500)));
    }

  } catch (e) {
    result.errors.push({
      error: e.message,
      context: 'main_execution'
    });
  }

  return result;
})();
