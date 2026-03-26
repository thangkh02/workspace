const fs = require("fs");
const path = require("path");
const readline = require("readline");
const crypto = require("crypto");
const { chromium } = require("playwright");

const ROOT = path.join(process.env.USERPROFILE, ".openclaw", "workspace");
const DATA_DIR = path.join(ROOT, "data");
const GROUPS_FILE = path.join(DATA_DIR, "groups.json");
const LEDGER_FILE = path.join(DATA_DIR, "ledger.json");
const OUT_FILE = path.join(DATA_DIR, "candidates.json");
const USER_DATA_DIR = path.join(DATA_DIR, "pw-profile");

function readJson(file, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJson(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
}

function hashText(text) {
  return crypto.createHash("sha1").update(text || "").digest("hex");
}

function askEnter(promptText) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    rl.question(promptText, () => {
      rl.close();
      resolve();
    });
  });
}

async function ensureLoggedIn(page) {
  await page.goto("https://www.facebook.com/", {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForTimeout(3000);

  const needsLogin = await page.locator('input[type="password"]').first().isVisible().catch(() => false);
  if (needsLogin) {
    console.log("\n[!] Playwright profile này chưa login Facebook.");
    console.log("[!] Browser sẽ mở ra. Hãy đăng nhập bằng tay.");
    await askEnter("[?] Login xong quay lại PowerShell và nhấn Enter...");
    await page.waitForTimeout(2000);
  }
}

async function scrollFeed(page, rounds = 4) {
  for (let i = 0; i < rounds; i++) {
    await page.mouse.wheel(0, 2600);
    await page.waitForTimeout(2200);
  }
}

async function collectPosts(page, group) {
  await page.goto(group.url, {
    waitUntil: "domcontentloaded",
    timeout: 60000
  });
  await page.waitForTimeout(5000);
  await scrollFeed(page, 4);

  const posts = await page.evaluate(() => {
    const articles = Array.from(document.querySelectorAll('div[role="article"]'));
    const out = [];

    for (const article of articles) {
      const text = (article.innerText || "").trim();
      if (!text || text.length < 100) continue;

      const links = Array.from(article.querySelectorAll("a"))
        .map(a => a.href)
        .filter(Boolean);

      const permalink =
        links.find(h =>
          h.includes("/posts/") ||
          h.includes("permalink") ||
          h.includes("/groups/") ||
          h.includes("/reel/")
        ) || null;

      out.push({
        text,
        permalink
      });
    }

    return out.slice(0, 8);
  });

  return posts;
}

(async () => {
  const groups = readJson(GROUPS_FILE, []);
  const ledger = readJson(LEDGER_FILE, {
    seen_keys: [],
    drafted_keys: [],
    published_keys: []
  });

  if (!Array.isArray(groups) || groups.length === 0) {
    throw new Error("groups.json rỗng hoặc sai format");
  }

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    viewport: { width: 1400, height: 900 }
  });

  const page = context.pages()[0] || await context.newPage();
  await ensureLoggedIn(page);

  const all = [];

  for (const group of groups) {
    console.log(`\n[>] Scanning ${group.name}`);
    try {
      const posts = await collectPosts(page, group);

      for (const p of posts) {
        const keyBase = p.permalink || p.text.slice(0, 500);
        const key = hashText(keyBase);

        if (ledger.seen_keys.includes(key)) {
          continue;
        }

        ledger.seen_keys.push(key);

        all.push({
          key,
          group_name: group.name,
          group_url: group.url,
          topic_keywords: group.topic_keywords || [],
          managed: !!group.managed,
          approval_required: !!group.approval_required,
          auto_submit: !!group.auto_submit,
          permalink: p.permalink,
          text: p.text,
          scraped_at: new Date().toISOString()
        });
      }

      console.log(`[+] New candidates: ${all.length}`);
    } catch (err) {
      console.error(`[x] Failed ${group.name}: ${String(err)}`);
    }
  }

  writeJson(OUT_FILE, all);
  writeJson(LEDGER_FILE, ledger);

  console.log(`\n[OK] Saved ${all.length} candidates to ${OUT_FILE}`);
  await context.close();
})();