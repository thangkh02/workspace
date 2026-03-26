# Simple Facebook Group Posts Collection
# Dùng: openclaw browser snapshot + press End để scroll
# Không cần JavaScript, không cần iterate

param(
    [string]$GroupUrl = "https://www.facebook.com/groups/2k5ptit",
    [string]$BrowserProfile = "openclaw",
    [int]$ScrollTimes = 3,
    [int]$PostTarget = 10
)

function Write-Log {
    param([string]$Message)
    Write-Host "$(Get-Date -Format 'HH:mm:ss') | $Message"
}

Write-Log "[START] Facebook Group Posts Collection"
Write-Log "[GROUP] $GroupUrl"
Write-Log "[PROFILE] $BrowserProfile"

# Create output directory
New-Item -ItemType Directory -Force .\data | Out-Null

# ============================================================================
# PHASE 1: Open group & take initial snapshot
# ============================================================================
Write-Log "[PHASE 1] Open group"
openclaw browser --browser-profile $BrowserProfile open "$GroupUrl"

Write-Log "[WAIT] Page load (4s)"
openclaw browser --browser-profile $BrowserProfile wait --time 4000

Write-Log "[SNAP] Taking content snapshot"
$contentSnapshot_1 = openclaw browser --browser-profile $BrowserProfile snapshot --format ai --limit 15000
$contentSnapshot_1 | Set-Content -Encoding UTF8 .\data\group_snapshot_content.txt
Write-Log "[OK] Content snapshot saved"

Write-Log "[SNAP] Taking interactive snapshot"
$uiSnapshot_1 = openclaw browser --browser-profile $BrowserProfile snapshot --interactive --depth 8
$uiSnapshot_1 | Set-Content -Encoding UTF8 .\data\group_snapshot_ui.txt
Write-Log "[OK] UI snapshot saved"

# ============================================================================
# PHASE 2: Parse initial posts
# ============================================================================
Write-Log "[PHASE 2] Parse snapshots"
$parseOutput = python scripts/parse_snapshot_posts.py 2>&1
Write-Log "[PARSE] $parseOutput"

# Load current posts
$postsJson = Get-Content .\data\visible_posts.json -Encoding UTF8 | ConvertFrom-Json
$currentPostCount = $postsJson.count
Write-Log "[STATUS] Current posts: $currentPostCount"

# ============================================================================
# PHASE 3: Scroll & collect more posts
# ============================================================================
$scrollIteration = 1
while ($currentPostCount -lt $PostTarget -and $scrollIteration -le $ScrollTimes) {
    Write-Log "[PHASE 3.$scrollIteration] Scroll iteration $scrollIteration/$ScrollTimes"
    
    # Scroll down using browser press End (go to bottom)
    Write-Log "[SCROLL] Scrolling to bottom..."
    openclaw browser --browser-profile $BrowserProfile press End
    
    # Wait for Facebook to load more posts
    Write-Log "[WAIT] Lazy-load (3s)"
    openclaw browser --browser-profile $BrowserProfile wait --time 3000
    
    # Take new snapshot
    Write-Log "[SNAP] Taking post-scroll snapshot"
    $contentSnapshot = openclaw browser --browser-profile $BrowserProfile snapshot --format ai --limit 15000
    $contentSnapshot | Set-Content -Encoding UTF8 .\data\group_snapshot_content_iter_$scrollIteration.txt
    
    $uiSnapshot = openclaw browser --browser-profile $BrowserProfile snapshot --interactive --depth 8
    $uiSnapshot | Set-Content -Encoding UTF8 .\data\group_snapshot_ui_iter_$scrollIteration.txt
    
    # Copy to main files (overwrite) for parsing
    Copy-Item .\data\group_snapshot_content_iter_$scrollIteration.txt .\data\group_snapshot_content.txt -Force
    Copy-Item .\data\group_snapshot_ui_iter_$scrollIteration.txt .\data\group_snapshot_ui.txt -Force
    
    # Parse new posts
    Write-Log "[PARSE] Parsing iteration $scrollIteration..."
    $parseOutput = python scripts/parse_snapshot_posts.py 2>&1
    Write-Log "       $parseOutput"
    
    # Check post count
    $postsJson = Get-Content .\data\visible_posts.json -Encoding UTF8 | ConvertFrom-Json
    $previousCount = $currentPostCount
    $currentPostCount = $postsJson.count
    $newPosts = $currentPostCount - $previousCount
    
    Write-Log "[STATUS] Posts: $previousCount --> $currentPostCount (added $newPosts)"
    
    if ($newPosts -le 0) {
        Write-Log "[WARN] No new posts loaded, stopping scroll"
        break
    }
    
    $scrollIteration++
}

# ============================================================================
# PHASE 4: Final merge & output
# ============================================================================
Write-Log "[PHASE 4] Final output"

if (Test-Path .\data\visible_posts.json) {
    $finalPosts = Get-Content .\data\visible_posts.json -Encoding UTF8 | ConvertFrom-Json
    Write-Log "[DONE] Total posts collected: $($finalPosts.count)"
    Write-Log "[FILE] Output: .\data\visible_posts.json"
    
    # Show summary
    foreach ($post in $finalPosts.posts) {
        Write-Host "`n  [POST] $($post.author) - $($post.time_label)"
        Write-Host "        Text: $($post.post_text.Substring(0, [Math]::Min(60, $post.post_text.Length)))..."
        Write-Host "        Comments: $($post.comment_count)"
    }
} else {
    Write-Log "[ERROR] visible_posts.json not found"
}

Write-Log "[FINISH] Collection complete!"
