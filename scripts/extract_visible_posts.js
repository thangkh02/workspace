/**
 * extract_visible_posts.js
 * 
 * Mục đích: Extract danh sách visible posts từ DOM sau khi expand.
 * Ưu tiên lấy: author, time, post_text, attachment_titles, text_truncated status.
 * Dùng heuristic để tránh nhầm: "Gửi", "Quản trị viên", docs.google.com links.
 * 
 * Chạy: openclaw browser evaluate -i <browser_profile> ./scripts/extract_visible_posts.js
 */

(function() {
  const posts = [];
  const errors = [];

  try {
    // Heuristic: Tìm post containers
    // Facebook groups thường có structure: article hoặc role="article"
    // Hoặc nested divs với pattern author -> time -> content -> reactions
    
    // Cách 1: Tìm articles
    const articles = Array.from(document.querySelectorAll('article, [role="article"]'));
    console.log(`Found ${articles.length} articles`);

    let postIdx = 0;

    for (const article of articles) {
      try {
       postIdx++;
        const post = {
          post_key: `post_${String(postIdx).padStart(3, '0')}`,
          author: '',
          time_label: '',
          post_text: '',
          attachment_titles: [],
          text_truncated: false,
          expand_button_count: 0,
          dom_confidence: 0.5,
          extracted_at: new Date().toISOString(),
          skip_reason: null
        };

        // Extract author
        // Heuristic: first link / strong / text that looks like name
        // Avoid: "Quản trị viên", "Gửi", "Bình luận", "Chia sẻ"
        const nameElem = article.querySelector('[href*="/user/"], [href*="/profile.php"], strong, b');
        if (nameElem) {
          const authorText = (nameElem.textContent || '').trim();
          
          // Filter noise
          if (!/gửi|quản trị|bình luận|chia sẻ|thích|cảm xúc|see more|xem thêm/i.test(authorText) 
              && authorText.length > 2 
              && authorText.length < 80) {
            post.author = authorText;
            post.dom_confidence = Math.max(post.dom_confidence, 0.9);
          }
        }

        // Extract time
        // Heuristic: text matching patterns like "X giờ", "X Tháng Y, Z", "5 days ago"
        const timePatterns = /(\d+\s*(?:giờ|phút|ngày|tuần|tháng|năm)|vừa xong|hôm qua|yesterday|\d+\s+tháng\s+\d+,?\s*\d*|just now|\d+\s+(?:hours?|days?|weeks?|months?))/i;
        const textNodes = Array.from(article.querySelectorAll('*')).map(el => el.textContent);
        for (const text of textNodes) {
          const match = timePatterns.exec(text);
          if (match) {
            post.time_label = match[1].trim();
            break;
          }
        }

        // Extract post text
        // Heuristic: largest text block trong article, không phải button/link/label
        const textElements = Array.from(article.querySelectorAll('div, p, span'))
          .filter(el => {
            const text = el.textContent.trim();
            // Avoid noise: short, labels, button text, URLs
            if (text.length < 20) return false;
            if (/^(giờ|phút|ngày|tháng|năm|gửi|quản trị|bình luận|chia sẻ|thích)$/i.test(text)) return false;
            if (/^https?:\/\/|^\/groups\/|^\/user\//.test(text)) return false;
            if (text.startsWith('button') || text.startsWith('Nút')) return false;
            
            // Avoid nested text (prefer outermost)
            const parent = el.parentElement;
            if (parent && parent.querySelector('div, p, span') !== el) return false;
            
            return true;
          })
          .sort((a, b) => b.textContent.length - a.textContent.length)
          .slice(0, 3); // Top 3 longest texts

        if (textElements.length > 0) {
          // Combine top texts
          const postTextParts = textElements.map(el => el.textContent.trim());
          post.post_text = postTextParts.join(' ');
          post.dom_confidence = Math.max(post.dom_confidence, 0.85);
        }

        // Check if text truncated
        // Heuristic: text ended with "..." hoặc có button "Xem thêm"
        post.text_truncated = post.post_text.endsWith('...') 
          || article.querySelector('button:has-text("Xem thêm")') !== null;

        // Extract attachment titles
        // Heuristic: text từ links đến Google Docs, Google Drive, external sources
        const attachmentLinks = Array.from(article.querySelectorAll('a[href*="docs.google.com"], a[href*="drive.google.com"], a[href*="dropbox"]'));
        post.attachment_titles = attachmentLinks.map(link => (link.textContent || '').trim()).filter(t => t && t.length > 0);

        // Validate: cần ít nhất author hoặc time hoặc post_text
        if (!post.author && !post.time_label && !post.post_text) {
          post.skip_reason = 'insufficient_content';
          post.dom_confidence = 0.1;
        }

        // Skip if author là những noise keywords
        if (post.author && /^(gửi|quản trị|thành viên ẩn danh|viết bình luận)$/i.test(post.author)) {
          post.skip_reason = 'likely_noise_author';
          post.dom_confidence = 0.2;
        }

        posts.push(post);

      } catch (e) {
        errors.push({
          postIdx: postIdx,
          error: e.message,
          context: 'post_extraction'
        });
      }
    }

  } catch (e) {
    errors.push({
      error: e.message,
      context: 'main_execution'
    });
  }

  return {
    posts: posts,
    total: posts.length,
    errors: errors,
    extracted_at: new Date().toISOString()
  };
})();
