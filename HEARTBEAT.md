# HEARTBEAT.md - Periodic Tasks for OpenClaw

## Enable Periodic Monitoring

Uncomment and configure tasks below to enable automated collection.

## Example: Collect posts every 4 hours

```yaml
tasks:
  - name: "Collect TTUD Group Posts"
    enabled: false              # Set to true to activate
    schedule: "0 */4 * * *"    # Every 4 hours (cron format)
    command: "python extract_posts.py"
    args:
      - "https://www.facebook.com/groups/ttud.2023"
      - "10"                     # Number of posts to collect
    output: "data/posts_collection.json"
    report_template: "data/processed/dry_run_report.txt"
```

## Example: Multiple Groups

```yaml
tasks:
  - name: "Collect Group 1"
    enabled: false
    schedule: "0 0 * * *"      # Every day at midnight
    command: "python extract_posts.py"
    args: ["https://www.facebook.com/groups/group1", "15"]

  - name: "Collect Group 2"
    enabled: false
    schedule: "0 6 * * *"      # Every day at 6 AM
    command: "python extract_posts.py"
    args: ["https://www.facebook.com/groups/group2", "10"]

  - name: "Generate Daily Report"
    enabled: false
    schedule: "0 22 * * *"     # Every day at 10 PM
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

## How to Enable

1. Edit this file
2. Set `enabled: true` for the task
3. Save
4. OpenClaw will activate on next heartbeat check
5. View logs: `cat logs/heartbeat.log`

## Notes

- ⚠️ **DRY-RUN MODE**: All tasks run in read-only mode
- ✅ Results saved to `data/` folder (gitignored)
- ✅ Actions logged to `data/ledger.json`
- ✅ Reports generated to `data/processed/`
- ⏱️ Timeouts: Default 5 minutes per task
