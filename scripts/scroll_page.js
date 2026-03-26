/**
 * scroll_page.js - AGGRESSIVE VERSION
 * 
 * Mục đích: Scroll down Facebook group feed nhiều lần để trigger load more.
 * Facebook dùng Intersection Observer, nên cần scroll to bottom nhiều lần.
 * Chỉ phục vụ đọc dữ liệu (DRY-RUN), KHÔNG được click submit/send/post/comment.
 * 
 * Chạy: openclaw browser evaluate -i <browser_profile> ./scripts/scroll_page.js
 */

(function() {
  const result = {
    initial_scroll_position: window.scrollY,
    scroll_attempts: 0,
    scroll_total_distance: 0,
    final_scroll_position: 0,
    status: 'scrolling',
    loaded_new_content: false,
    errors: []
  };

  try {
    // Get initial position & content count
    result.initial_scroll_position = window.scrollY || window.pageYOffset;
    const initialPostCount = document.querySelectorAll('article').length;
    
    // Aggressive scroll: scroll to bottom multiple times
    // Facebook uses Intersection Observer, so we need to reach bottom
    const scrollDistance = 1500;
    const numScrolls = 3;  // Scroll 3 times to trigger load
    
    for (let i = 0; i < numScrolls; i++) {
      window.scrollBy({
        top: scrollDistance,
        left: 0,
        behavior: 'auto'  // Instant, no animation
      });
      result.scroll_attempts++;
      result.scroll_total_distance += scrollDistance;
    }
    
    // Additional: Scroll to absolute bottom
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    window.scrollTo({
      top: maxScroll,
      behavior: 'auto'
    });
    result.scroll_attempts++;
    
    // Wait for new content to load (longer wait for Intersection Observer)
    const waitPromise = new Promise(resolve => {
      setTimeout(() => {
        const finalPostCount = document.querySelectorAll('article').length;
        result.loaded_new_content = finalPostCount > initialPostCount;
        result.initial_post_count = initialPostCount;
        result.final_post_count = finalPostCount;
        result.new_posts_loaded = finalPostCount - initialPostCount;
        resolve();
      }, 4000);  // Wait 4 seconds for Intersection Observer to trigger
    });
    
    waitPromise.then(() => {
      result.final_scroll_position = window.scrollY || window.pageYOffset;
      result.status = 'success';
    });

  } catch (error) {
    result.status = 'error';
    result.error = error.message;
    result.errors.push(error.message);
  }

  return result;
})();
