# Facebook Group Posts Collection Workflow

## Overview

Workflow tự động để collect posts từ Facebook group cho đến khi đủ số lượng posts (mặc định 10).

**Constraint**: DRY-RUN ONLY - chỉ đọc dữ liệu, không post/comment/submit.

## How to Use

### Quick Start

```powershell
# Collect 10 posts from a Facebook group
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/YOUR_GROUP_ID" `
    -TargetCount 10 `
    -BrowserProfile "openclaw"
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `GroupUrl` | string | (required) | Facebook group URL |
| `TargetCount` | int | 10 | Target number of posts to collect |
| `BrowserProfile` | string | "openclaw" | Browser profile name |
| `OutputDir` | string | "data" | Output directory for JSON files |
| `MaxIterations` | int | 20 | Max loop iterations (safety limit) |
| `DryRun` | bool | true | Always true per AGENTS.md |

### Examples

#### Collect 15 posts
```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/123456789" `
    -TargetCount 15
```

#### Control max iterations
```powershell
powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl "https://www.facebook.com/groups/123456789" `
    -TargetCount 10 `
    -MaxIterations 30
```

## Workflow Logic

### Main Loop (per iteration)

```
1. Expand visible posts
   ↓ Click "Xem thêm" buttons to show full content
   
2. Extract posts from DOM
   ↓ Parse author, time, post_text from page
   
3. Lookup action references
   ↓ Find comment/like/share button element references
   
4. Parse snapshots
   ↓ Use parse_snapshot_posts.py on UI/content snapshots
   
5. Merge posts & action refs
   ↓ Combine DOM data with snapshot refs
   
6. Check post count
   ├─ If posts >= TargetCount → STOP
   └─ Else → Scroll + repeat
```

### Post-collection (Multiple iterations)

```
1. Backup each iteration's posts
   
2. Merge all iteration posts
   ├─ Load posts from all iteration_* backup files
   └─ Combine into single dataset
   
3. Deduplicate
   ├─ Group by (author + time_label)
   └─ Keep first occurrence
   
4. Take top N posts
   
5. Save final result to data/posts_collection.json
```

## Output Files

### During Collection

```
data/
├── visible_posts.json                 # Latest iteration's posts
├── visible_posts_iter_1.json         # Backup from iteration 1
├── visible_posts_iter_2.json         # Backup from iteration 2
├── visible_posts_iter_N.json         # Backup from iteration N
└── ...
```

### Final Result

```
data/
└── posts_collection.json             # Final merged & deduped posts
```

### Log Files

```
logs/
└── collect_posts.log                 # Full execution log
```

## Output Format

### data/posts_collection.json

```json
{
  "metadata": {
    "timestamp": "2026-03-25T10:30:00.123456",
    "total_loaded": 45,
    "after_dedup": 35,
    "final_count": 10,
    "target_count": 10,
    "status": "success"
  },
  "posts": [
    {
      "post_key": "post_001",
      "author": "Tùng Lâm",
      "time_label": "22 giờ",
      "post_text": "bác nào biết chỗ đánh chìa khoá...",
      "comment_count": 33,
      "like_ref": "e58",
      "react_ref": "e59",
      "comment_ref": "e60",
      "share_ref": "e61",
      ...
    },
    ...
  ]
}
```

## Internal Scripts

### scroll_page.js
- Purpose: Scroll down Facebook feed
- Usage: Called internally by PowerShell orchestrator
- Scrolls 800px down, waits 2s for content load

### dedup_posts.py
- Purpose: Merge, deduplicate, and select top N posts
- Usage: Called internally during final merging
- Input: Combined posts from all iterations
- Output: Final JSON with metadata

### collect_posts_from_group.ps1
- Purpose: Main orchestrator - loop, manage iterations, call all sub-scripts
- Usage: Entry point for user
- Manages: navigation, iteration backups, merging logic

## Workflow Scripts (Existing)

These scripts are part of the data extraction pipeline:

- `expand_visible_posts.js` - Click "Xem thêm" buttons
- `extract_visible_posts.js` - Extract posts from DOM
- `lookup_post_action_refs.js` - Find button element references
- `parse_snapshot_posts.py` - Parse UI/content snapshots to JSON
- `merge_posts_and_refs.py` - Merge DOM + snapshot data

## Troubleshooting

### No posts collected
- Check if GroupUrl is correct
- Check if browser profile exists
- Review `logs/collect_posts.log` for errors

### Too few posts after max iterations
- Increase `MaxIterations` parameter
- Group may have limited posts
- Check post visibility (some may be restricted)

### Dedup reduced posts too much
- Posts with same author+time are considered duplicates
- This is normal for rapid-fire posts
- Adjust dedup logic in `dedup_posts.py` if needed

## Safety & DRY-RUN Compliance

✅ **Safe operations**:
- Reading posts
- Capturing snapshots
- Parsing data
- Generating JSON output

❌ **Blocked operations** (per AGENTS.md):
- Posting new content
- Adding comments
- Reacting to posts
- Sharing posts
- Submitting forms

All operations are read-only and logged.

## Next Steps

1. Use output JSON for analysis/reporting
2. Store results in database
3. Integrate with other tools
4. Monitor collection success rate

## References

- [AGENTS.md](../AGENTS.md) - Core operational constraints
- [BOOTSTRAP.md](../BOOTSTRAP.md) - System setup
- [Facebook Group Structure](https://developers.facebook.com/docs/graph-api/reference/group)

---

**Last Updated**: 2026-03-25
**Status**: Production Ready
