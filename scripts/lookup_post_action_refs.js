/**
 * lookup_post_action_refs.js
 *
 * Mục đích: Tìm các button refs (comment, like, share) cho từng post article.
 * Chạy trong browser context qua: openclaw browser evaluate -i <profile> ./scripts/lookup_post_action_refs.js
 *
 * Output JSON:
 * {
 *   total: N,
 *   posts_with_all_refs: M,
 *   posts_with_missing_refs: K,
 *   posts: [{ post_key, comment_ref, like_ref, react_ref, share_ref, has_all_refs }]
 * }
 */

(function () {
  const results = [];
  const articles = Array.from(document.querySelectorAll('article, [role="article"]'));

  const ACTION_PATTERNS = {
    comment: /bình luận|comment/i,
    like: /thích|like/i,
    react: /cảm xúc|react|biểu cảm/i,
    share: /chia sẻ|share/i
  };

  function findButtonRef(article, pattern) {
    const buttons = Array.from(article.querySelectorAll('div[role="button"], button, a[role="button"]'));
    for (const btn of buttons) {
      const label = (btn.getAttribute('aria-label') || btn.textContent || '').trim();
      if (pattern.test(label)) {
        // Return a stable ref: aria-label or text
        return btn.getAttribute('aria-label') || label.slice(0, 50) || null;
      }
    }
    return null;
  }

  articles.forEach(function (article, idx) {
    const postKey = 'post_' + String(idx + 1).padStart(3, '0');
    const commentRef = findButtonRef(article, ACTION_PATTERNS.comment);
    const likeRef = findButtonRef(article, ACTION_PATTERNS.like);
    const reactRef = findButtonRef(article, ACTION_PATTERNS.react);
    const shareRef = findButtonRef(article, ACTION_PATTERNS.share);

    const hasAllRefs = !!(commentRef && likeRef);

    results.push({
      post_key: postKey,
      comment_ref: commentRef,
      like_ref: likeRef,
      react_ref: reactRef,
      share_ref: shareRef,
      has_all_refs: hasAllRefs
    });
  });

  var withAll = results.filter(function (p) { return p.has_all_refs; }).length;

  return {
    total: results.length,
    posts_with_all_refs: withAll,
    posts_with_missing_refs: results.length - withAll,
    posts: results,
    captured_at: new Date().toISOString()
  };
})();
