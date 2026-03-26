# HEARTBEAT.md - Periodic Tasks for OpenClaw

## Active Tasks

### Collect TTUD Group Posts (every 4 hours)

```yaml
tasks:
  - name: "Collect TTUD Group Posts"
    enabled: true
    schedule: "0 */4 * * *"
    skill: "skills/fb_group_ops.js"
    args:
      groupUrl: "https://www.facebook.com/groups/ttud.2023"
      targetCount: 10
    output: "data/posts_collection.json"
    report_template: "data/processed/dry_run_report.txt"
    notify: telegram
```

## Add More Groups

Copy the block above and set `enabled: true`:

```yaml
tasks:
  - name: "Collect Group 1"
    enabled: false
    schedule: "0 0 * * *"
    skill: "skills/fb_group_ops.js"
    args:
      groupUrl: "https://www.facebook.com/groups/GROUP_ID"
      targetCount: 15

  - name: "Collect Group 2"
    enabled: false
    schedule: "0 6 * * *"
    skill: "skills/fb_group_ops.js"
    args:
      groupUrl: "https://www.facebook.com/groups/GROUP2_ID"
      targetCount: 10

  - name: "Generate Daily Report"
    enabled: false
    schedule: "0 22 * * *"
    depends_on: ["Collect Group 1", "Collect Group 2"]
    command: "python scripts/render_dry_run_report.py"
```

## Available Cron Schedules

| Pattern | Meaning |
|---------|---------|
| `0 * * * *` | Every hour |
| `0 */4 * * *` | Every 4 hours |
| `0 0 * * *` | Every day at midnight |
| `0 6 * * *` | Every day at 6 AM |
| `0 9-17 * * MON-FRI` | Every hour, 9 AM-5 PM weekdays |

## How to Enable / Disable

1. Edit this file — set `enabled: true` or `enabled: false`
2. Save
3. OpenClaw activates on next heartbeat check
4. View logs: `cat logs/heartbeat.log`

## Notes

- ⚠️ **DRY-RUN MODE**: All tasks run in read-only mode
- ✅ Results saved to `data/` folder (gitignored)
- ✅ Actions logged to `data/ledger.json`
- ✅ Reports generated to `data/processed/`
- ✅ Telegram notifications sent when `notify: telegram` is set
- ⏱️ Timeouts: Default 10 minutes per task
