# Facebook Operations Guide - Quick Start

## TL;DR - Use on OpenClaw

**Scenario 1: Manual extraction**
```
User: "Extract posts from https://www.facebook.com/groups/ttud.2023, get 15 posts"
Agent: Runs pipeline automatically → Returns JSON with posts
```

**Scenario 2: Periodic monitoring**
Configure in `HEARTBEAT.md`:
```yaml
tasks:
  - name: "fb_collect_ttud"
    schedule: "every 4 hours"
    link: "https://www.facebook.com/groups/ttud.2023"
    target: 10 posts
```

## Step-by-Step Setup

### 1. Configure Group (First Time)

Edit `data/groups.json`:
```json
{
  "groups": [
    {
      "id": "ttud.2023",
      "url": "https://www.facebook.com/groups/ttud.2023",
      "name": "TTUD 2023 Group",
      "managed": false,
      "auto_submit": false,
      "topic_keywords": ["python", "java", "web"],
      "rules": [
        {
          "type": "filter",
          "keywords": ["hỏi", "tư vấn", "?"],
          "action": "include"
        }
      ]
    }
  ]
}
```

### 2. Test Manual Extraction

**Using Python wrapper:**
```powershell
cd c:\Users\pntha\.openclaw\workspace
python extract_posts.py "https://www.facebook.com/groups/ttud.2023" 10
```

**Using PowerShell directly:**
```powershell
powershell -ExecutionPolicy Bypass `
  -File scripts/collect_posts_from_group.ps1 `
  -GroupUrl "https://www.facebook.com/groups/ttud.2023" `
  -TargetCount 10
```

### 3. Check Results

```powershell
# View collected posts
cat data/posts_collection.json | ConvertFrom-Json | ConvertTo-Json

# View action log
cat data/ledger.json | ConvertFrom-Json | ConvertTo-Json

# Run analysis pipeline
python scripts/merge_posts_and_refs.py
python scripts/build_candidate_posts.py
python scripts/generate_dry_run_plan.py
```

### 4. Setup Periodic Collection (Optional)

Edit `HEARTBEAT.md`:
```markdown
# Periodic Tasks

## Task: Collect from TTUD Group

- Schedule: Every 4 hours
- Group: ttud.2023
- Target: 10 posts
- Filter: questions + advice requests
- Action: Extract & generate report
```

Then openclaw will run:
```powershell
# Every 4 hours
python extract_posts.py "https://www.facebook.com/groups/ttud.2023" 10
python scripts/render_dry_run_report.py
```

## Output Files

After extraction:

| File | Content |
|------|---------|
| `data/posts_collection.json` | Raw posts extracted |
| `data/ledger.json` | Action log |
| `data/processed/merged_posts.json` | Merged with refs |
| `data/processed/candidate_posts.json` | Filtered candidates |
| `data/processed/dry_run_report.txt` | Human-readable report |
| `data/processed/dry_run_report.json` | Structured report |

## DRY-RUN Mode (Always On)

✅ **Allowed:**
- Extract posts (read-only)
- Analyze content
- Generate reports
- Store to JSON

❌ **NOT Allowed:**
- Post/comment on Facebook
- React to posts
- Share posts
- Any write operations

## Approval Workflow (For Future)

When `managed=true`:
1. ✅ Extract & generate report
2. ✅ User reviews `dry_run_report.txt`
3. ✅ User approves specific actions
4. ✅ Agent executes approved actions only
5. ✅ Log to `ledger.json`

## Common Commands on OpenClaw

```
# Extract posts
"Extract 15 posts from https://www.facebook.com/groups/ttud.2023"

# Generate report
"Show analysis report for ttud.2023"

# Check activity
"Show last 5 actions from ledger"

# List groups
"What groups are configured?"

# Filter posts
"Find questions in last collection with confidence > 0.8"
```

## Troubleshooting

**Browser won't start**
```powershell
# Check playwright installation
npx playwright install

# Verify browser paths
npx playwright install-deps
```

**Posts not extracting**
```powershell
# Check logs
cat logs/collect_posts.log

# Verify Facebook access
# Open group manually in browser
# Check if Facebook structure changed
```

**timeout errors**
```powershell
# Increase timeout in script
# Edit scripts/collect_posts_from_group.ps1
# Change $MaxIterations or timeouts
```

## Architecture

```
OpenClaw Workspace
├── .instructions.md          ← Custom capabilities
├── extract_posts.py          ← Main entry point
├── HEARTBEAT.md              ← Periodic tasks
├── AGENTS.md                 ← Agent rules
├── data/
│   ├── groups.json           ← Configuration
│   ├── ledger.json           ← Action log
│   ├── posts_collection.json ← Results
│   └── processed/            ← Analyzed data
└── scripts/
    ├── collect_posts_from_group.ps1  ← PowerShell pipeline
    ├── merge_posts_and_refs.py       ← Merge step
    ├── build_candidate_posts.py      ← Filter step
    └── render_dry_run_report.py      ← Report step
```

---

**Ready to use on OpenClaw now!** ✅  
Just give OpenClaw a Facebook link, and it will extract posts automatically.
