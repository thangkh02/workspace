#!/usr/bin/env node
/**
 * fb-collect.js
 *
 * CLI entry point cho bot để thu thập bài viết từ Facebook group.
 * Dùng Playwright trực tiếp (không cần PowerShell hay openclaw browser).
 *
 * Usage:
 *   node scripts/fb-collect.js <group_url> [target_count]
 *   node scripts/fb-collect.js --pipeline <group_url> [target_count]
 *
 * Options:
 *   --pipeline   Sau khi collect, chạy Python pipeline để tạo dry-run report
 *   --headless   Chạy browser không hiển thị (default: false)
 *   --help       Hiển thị hướng dẫn
 *
 * Output:
 *   data/posts_collection.json       Raw posts (always)
 *   data/processed/dry_run_report.txt (if --pipeline)
 *
 * Examples:
 *   node scripts/fb-collect.js "https://www.facebook.com/groups/ttud.2023" 10
 *   node scripts/fb-collect.js --pipeline "https://www.facebook.com/groups/ttud.2023" 15
 */

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

// ── Argument parsing ──────────────────────────────────────────────────────────

const argv = process.argv.slice(2);

if (argv.includes('--help') || argv.length === 0) {
  console.log(`
Usage:
  node scripts/fb-collect.js [--pipeline] [--headless] <group_url> [target_count]

Options:
  --pipeline   Also run Python pipeline (merge → candidates → plan → report)
  --headless   Run browser in headless mode (default: false)
  --help       Show this help

Examples:
  node scripts/fb-collect.js "https://www.facebook.com/groups/ttud.2023" 10
  node scripts/fb-collect.js --pipeline "https://www.facebook.com/groups/ttud.2023" 15
`);
  process.exit(0);
}

const runPipeline = argv.includes('--pipeline');
const headless = argv.includes('--headless');
const positional = argv.filter(a => !a.startsWith('--'));

const groupUrl = positional[0];
const targetCount = parseInt(positional[1], 10) || 10;

if (!groupUrl) {
  console.error('[ERROR] group_url is required.');
  console.error('Usage: node scripts/fb-collect.js <group_url> [target_count]');
  process.exit(1);
}

if (!groupUrl.includes('facebook.com/groups/')) {
  console.error('[ERROR] Invalid Facebook group URL:', groupUrl);
  console.error('URL must contain "facebook.com/groups/"');
  process.exit(1);
}

// ── Constants ─────────────────────────────────────────────────────────────────

const POSTS_PER_SCROLL_ESTIMATE = 4;  // Approximate new posts loaded per scroll
const SAFETY_BUFFER_ROUNDS = 5;       // Extra scroll rounds beyond minimum needed
const MIN_POST_TEXT_LENGTH = 50;      // Minimum characters for a post to be considered valid

const ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT, 'data');
const USER_DATA_DIR = path.join(DATA_DIR, 'pw-profile');
const OUTPUT_FILE = path.join(DATA_DIR, 'posts_collection.json');
const LOGS_DIR = path.join(ROOT, 'logs');

// ── Helpers ───────────────────────────────────────────────────────────────────

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function writeJson(file, data) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf8');
}

function log(msg, level = 'INFO') {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const line = `[${ts}] [${level}] ${msg}`;
  console.log(line);
  ensureDir(LOGS_DIR);
  fs.appendFileSync(path.join(LOGS_DIR, 'fb-collect.log'), line + '\n', 'utf8');
}

function hashText(text) {
  return crypto.createHash('sha1').update(text || '').digest('hex').slice(0, 12);
}

// ── Playwright collect ────────────────────────────────────────────────────────

async function collectPosts(groupUrl, targetCount, headless) {
  let playwright;
  try {
    playwright = require('playwright');
  } catch (e) {
    log('Playwright not found. Run: npm install', 'ERROR');
    throw new Error('Playwright not installed. Run: npm install');
  }

  const { chromium } = playwright;

  log(`Opening browser (headless=${headless}) ...`);
  log(`Target: ${groupUrl} — collecting up to ${targetCount} posts`);

  ensureDir(USER_DATA_DIR);

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless,
    viewport: { width: 1400, height: 900 },
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });

  const page = context.pages()[0] || await context.newPage();

  try {
    // Navigate to group
    log(`Navigating to ${groupUrl} ...`);
    await page.goto(groupUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(4000);

    const allPosts = [];
    const seenHashes = new Set();
    let scrollRounds = 0;
    const maxScrollRounds = Math.ceil(targetCount / POSTS_PER_SCROLL_ESTIMATE) + SAFETY_BUFFER_ROUNDS; // safety limit

    while (allPosts.length < targetCount && scrollRounds < maxScrollRounds) {
      scrollRounds++;

      // Click "Xem thêm" / "See more" buttons
      try {
        const seeMoreButtons = await page.locator('div[role="button"]:has-text("Xem thêm"), div[role="button"]:has-text("See more")').all();
        for (const btn of seeMoreButtons) {
          await btn.click({ timeout: 2000 }).catch(() => {});
          await page.waitForTimeout(300);
        }
      } catch (_) {}

      // Extract posts from DOM
      const extracted = await page.evaluate((minTextLength) => {
        const articles = Array.from(document.querySelectorAll('div[role="article"], article'));
        const posts = [];

        for (const article of articles) {
          const text = (article.innerText || '').trim();
          if (!text || text.length < minTextLength) continue;

          // Author: look for profile links or strong elements
          let author = '';
          const nameEl = article.querySelector('a[href*="/user/"], a[href*="/profile.php"], strong, b');
          if (nameEl) {
            const t = (nameEl.textContent || '').trim();
            if (t.length > 1 && t.length < 80 && !/^(Gửi|Bình luận|Chia sẻ|Thích)$/i.test(t)) {
              author = t;
            }
          }

          // Time label
          let timeLabel = '';
          const timePatterns = /(\d+\s*(?:giờ|phút|ngày|tuần|tháng|năm)|vừa xong|hôm qua|yesterday|\d+\s+(?:hours?|days?|weeks?|months?)\s+ago)/i;
          const allText = article.innerText || '';
          const timeMatch = timePatterns.exec(allText);
          if (timeMatch) timeLabel = timeMatch[1].trim();

          // Permalink
          const links = Array.from(article.querySelectorAll('a')).map(a => a.href).filter(Boolean);
          const permalink = links.find(h => /\/(posts|permalink|reel|groups)\//i.test(h)) || null;

          // Post text: the longest text block
          const textBlocks = Array.from(article.querySelectorAll('div[data-ad-comet-preview], div[dir="auto"], p'))
            .map(el => (el.textContent || '').trim())
            .filter(t => t.length > 30)
            .sort((a, b) => b.length - a.length);

          const postText = textBlocks[0] || text.slice(0, 1000);

          // Engagement counts
          const countPatterns = /(\d+)\s*(?:bình luận|comment|nhận xét)/i;
          const likePatterns = /(\d+)\s*(?:người|lượt thích|likes?)/i;
          const commentMatch = countPatterns.exec(allText);
          const likeMatch = likePatterns.exec(allText);

          posts.push({
            author,
            time_label: timeLabel,
            post_text: postText,
            permalink,
            comment_count: commentMatch ? parseInt(commentMatch[1], 10) : 0,
            like_count: likeMatch ? parseInt(likeMatch[1], 10) : 0,
            extracted_at: new Date().toISOString()
          });
        }

        return posts;
      }, MIN_POST_TEXT_LENGTH);

      // Deduplicate and add to collection
      let newInRound = 0;
      for (const post of extracted) {
        const sig = hashText((post.author || '') + '|' + (post.time_label || '') + '|' + (post.post_text || '').slice(0, 100));
        if (!seenHashes.has(sig)) {
          seenHashes.add(sig);
          post.post_key = `post_${String(allPosts.length + 1).padStart(3, '0')}`;
          allPosts.push(post);
          newInRound++;
        }
      }

      log(`Round ${scrollRounds}: extracted ${extracted.length} posts, ${newInRound} new (total: ${allPosts.length}/${targetCount})`);

      if (allPosts.length >= targetCount) break;
      if (newInRound === 0 && scrollRounds > 3) {
        log('No new posts in last round, stopping.', 'WARN');
        break;
      }

      // Scroll down to load more
      await page.mouse.wheel(0, 3000);
      await page.waitForTimeout(2500);
    }

    const result = allPosts.slice(0, targetCount);
    log(`Collection complete: ${result.length} posts`);
    return result;

  } finally {
    await context.close();
  }
}

// ── Python pipeline ───────────────────────────────────────────────────────────

function runPythonPipeline() {
  const steps = [
    'python scripts/merge_posts_and_refs.py',
    'python scripts/build_candidate_posts.py',
    'python scripts/generate_dry_run_plan.py',
    'python scripts/render_dry_run_report.py'
  ];

  log('Running Python pipeline ...');
  for (const cmd of steps) {
    log(`  → ${cmd}`);
    try {
      const out = execSync(cmd, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
      if (out.trim()) log(out.trim().split('\n').map(l => '    ' + l).join('\n'));
    } catch (e) {
      log(`Warning: "${cmd}" failed: ${e.message}`, 'WARN');
      // Continue — don't abort on individual step failure
    }
  }
  log('Python pipeline complete.');
}

// ── Main ──────────────────────────────────────────────────────────────────────

(async () => {
  log('=== fb-collect.js starting ===');
  log(`Group URL:    ${groupUrl}`);
  log(`Target count: ${targetCount}`);
  log(`Pipeline:     ${runPipeline}`);
  log(`Headless:     ${headless}`);

  ensureDir(DATA_DIR);

  let posts = [];
  let status = 'success';
  let error = null;

  try {
    posts = await collectPosts(groupUrl, targetCount, headless);
  } catch (e) {
    log(`Collection failed: ${e.message}`, 'ERROR');
    status = 'error';
    error = e.message;
  }

  const output = {
    metadata: {
      collected_at: new Date().toISOString(),
      group_url: groupUrl,
      target_count: targetCount,
      actual_count: posts.length,
      status,
      error
    },
    posts
  };

  writeJson(OUTPUT_FILE, output);
  log(`Saved ${posts.length} posts to: ${OUTPUT_FILE}`);

  if (runPipeline && status === 'success') {
    runPythonPipeline();
  }

  // Print summary JSON to stdout for bot to parse
  const summary = {
    status,
    group_url: groupUrl,
    posts_collected: posts.length,
    output_file: OUTPUT_FILE,
    pipeline_run: runPipeline && status === 'success',
    report_file: runPipeline ? path.join(ROOT, 'data/processed/dry_run_report.txt') : null,
    error
  };

  console.log('\n' + JSON.stringify(summary, null, 2));

  log('=== fb-collect.js done ===');
  process.exit(status === 'error' ? 1 : 0);
})();
