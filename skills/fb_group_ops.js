/**
 * fb_group_ops.js
 *
 * Skill để bot (Telegram hoặc agent) trigger workflow collect posts từ Facebook group.
 *
 * Flow:
 *   1. parseGroupUrl(userMessage)  → group URL
 *   2. collectPosts(groupUrl, targetCount) → chạy PowerShell script
 *   3. formatReport(result)        → Telegram-ready message
 *
 * Usage (bot side):
 *   const skill = require('./skills/fb_group_ops');
 *   const url = skill.parseGroupUrl(userMessage);
 *   const result = await skill.collectPosts(url, 10);
 *   const report = skill.formatReport(result);
 *   // send report via Telegram
 *
 * Constraint: DRY-RUN only. No post/comment/submit without explicit approval.
 */

'use strict';

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ─── Constants ────────────────────────────────────────────────────────────────

const WORKSPACE_ROOT = path.resolve(__dirname, '..');
const OUTPUT_FILE = path.join(WORKSPACE_ROOT, 'data', 'posts_collection.json');
const SCRIPT_PATH = path.join(WORKSPACE_ROOT, 'scripts', 'collect_posts_from_group.ps1');
const TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes

// Known group slug → URL mapping (expand as needed)
const GROUP_ALIASES = {
  'ttud.2023': 'https://www.facebook.com/groups/ttud.2023',
  'ttud': 'https://www.facebook.com/groups/ttud.2023',
};

// ─── URL Parser ───────────────────────────────────────────────────────────────

/**
 * Extract a Facebook group URL from a free-form user message.
 *
 * Handles:
 *  - Full URLs:  "https://www.facebook.com/groups/ttud.2023"
 *  - Group IDs:  "groups/123456789" or "group 123456"
 *  - Known slugs: "ttud.2023", "ttud"
 *  - Natural lang: "lấy posts từ group ttud.2023"
 *
 * @param {string} message
 * @returns {string|null} Full Facebook group URL, or null if not found.
 */
function parseGroupUrl(message) {
  if (!message || typeof message !== 'string') return null;

  const text = message.trim();

  // 1. Full URL already present
  const urlMatch = text.match(/https?:\/\/(?:www\.)?facebook\.com\/groups\/[\w.]+/i);
  if (urlMatch) return urlMatch[0].replace(/\/$/, '');

  // 2. "groups/<id>" shorthand
  const groupsPathMatch = text.match(/groups?\/?[/\s]+([\w.]+)/i);
  if (groupsPathMatch) {
    const slug = groupsPathMatch[1];
    if (GROUP_ALIASES[slug.toLowerCase()]) return GROUP_ALIASES[slug.toLowerCase()];
    return `https://www.facebook.com/groups/${slug}`;
  }

  // 3. Known alias anywhere in the message
  for (const [alias, url] of Object.entries(GROUP_ALIASES)) {
    if (text.toLowerCase().includes(alias)) return url;
  }

  // 4. Any word that looks like a group slug (alphanumeric + dots, 5+ chars)
  const slugMatch = text.match(/\b([a-zA-Z0-9]{3,}\.[\w.]+|\d{10,})\b/);
  if (slugMatch) {
    const candidate = slugMatch[1];
    if (GROUP_ALIASES[candidate.toLowerCase()]) return GROUP_ALIASES[candidate.toLowerCase()];
    return `https://www.facebook.com/groups/${candidate}`;
  }

  return null;
}

// ─── Workflow Runner ───────────────────────────────────────────────────────────

/**
 * Run the PowerShell collect workflow and return parsed results.
 *
 * @param {string} groupUrl  Full Facebook group URL.
 * @param {number} [targetCount=10]  Number of posts to collect.
 * @returns {{ posts: Array, meta: object }}
 * @throws {Error} on script failure or unreadable output.
 */
function collectPosts(groupUrl, targetCount = 10) {
  if (!groupUrl || !groupUrl.includes('facebook.com/groups/')) {
    throw new Error(`Invalid Facebook group URL: "${groupUrl}"`);
  }
  if (typeof targetCount !== 'number' || targetCount < 1 || targetCount > 100) {
    throw new Error(`targetCount must be between 1 and 100, got: ${targetCount}`);
  }

  // Ensure output directory exists
  const dataDir = path.join(WORKSPACE_ROOT, 'data');
  if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

  const cmd = [
    'powershell',
    '-ExecutionPolicy', 'Bypass',
    '-File', `"${SCRIPT_PATH}"`,
    '-GroupUrl', `"${groupUrl}"`,
    '-TargetCount', String(targetCount),
  ].join(' ');

  try {
    execSync(cmd, {
      cwd: WORKSPACE_ROOT,
      stdio: 'inherit',
      timeout: TIMEOUT_MS,
    });
  } catch (err) {
    throw new Error(`PowerShell script failed: ${err.message}`);
  }

  // Read result file
  if (!fs.existsSync(OUTPUT_FILE)) {
    throw new Error(`Output file not found after script run: ${OUTPUT_FILE}`);
  }

  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf-8'));
  } catch (parseErr) {
    throw new Error(`Failed to parse output JSON: ${parseErr.message}`);
  }

  // Normalise: support both array and { posts: [...] } shapes
  const posts = Array.isArray(raw) ? raw : (raw.posts || raw.results || []);
  const meta = Array.isArray(raw) ? {} : (raw.meta || raw.summary || {});

  return { posts, meta };
}

// ─── Report Formatter ─────────────────────────────────────────────────────────

/** Return the first truthy value among a post's field variants. */
function getField(post, ...keys) {
  for (const key of keys) {
    if (post[key] != null && post[key] !== '') return post[key];
  }
  return '';
}

/**
 * Format the collected posts into a Telegram-ready text report.
 *
 * @param {{ posts: Array, meta: object }} result
 * @param {number} [maxPosts=5]  Maximum posts to include in the report.
 * @returns {string}
 */
function formatReport({ posts, meta }, maxPosts = 5) {
  if (!posts || posts.length === 0) {
    return '⚠️ Không tìm thấy bài viết nào. Hãy kiểm tra lại group URL hoặc thử lại sau.';
  }

  const total = posts.length;
  const shown = posts.slice(0, maxPosts);

  const lines = [
    `✅ *Kết quả collect posts*`,
    `📊 Thu được: *${total}* bài viết`,
    '',
  ];

  if (meta.group_name) lines.push(`📌 Group: *${meta.group_name}*`);
  if (meta.collected_at) lines.push(`🕒 Thời gian: ${meta.collected_at}`);
  if (meta.group_name || meta.collected_at) lines.push('');

  shown.forEach((post, idx) => {
    const author = getField(post, 'author', 'name') || 'Ẩn danh';
    const time = getField(post, 'time', 'timestamp', 'date');
    const rawText = getField(post, 'text', 'content', 'message').replace(/\n+/g, ' ');
    const text = rawText.length > 200 ? `${rawText.slice(0, 200)}…` : rawText;
    const comments = post.comment_count != null ? `💬 ${post.comment_count}` : '';
    const likes = post.like_count != null ? `👍 ${post.like_count}` : '';

    const meta_parts = [time, comments, likes].filter(Boolean).join(' · ');

    lines.push(`*${idx + 1}. ${author}*`);
    if (meta_parts) lines.push(`_${meta_parts}_`);
    if (text) lines.push(text);
    lines.push('');
  });

  if (total > maxPosts) {
    lines.push(`_… và ${total - maxPosts} bài viết khác (xem data/posts_collection.json)_`);
  }

  lines.push('');
  lines.push('🔒 _Chế độ DRY-RUN: Không có hành động nào được thực hiện._');

  return lines.join('\n');
}

// ─── Public API ───────────────────────────────────────────────────────────────

module.exports = { parseGroupUrl, collectPosts, formatReport };
