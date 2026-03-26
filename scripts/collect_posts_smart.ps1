#!/usr/bin/env pwsh
# Smart Facebook Group Posts Collection
# - Use browser press End to scroll
# - Accumulate posts from all iterations
# - Dedup by (author, time_label)
# - Stop when target reached OR no new posts

param(
    [string]$GroupUrl = "https://www.facebook.com/groups/2k5ptit",
    [string]$BrowserProfile = "openclaw",
    [int]$ScrollTimes = 10,
    [int]$PostTarget = 10,
    [int]$MaxNoNewPostsIterations = 2
)

# ============================================================================
# CONSOLE ENCODING SETUP - CRITICAL for Vietnamese text!
# ============================================================================
# Must set BEFORE any OpenClaw commands so output is already UTF-8
chcp 65001 | Out-Null
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Log {
    param([string]$Message)
    Write-Host "$(Get-Date -Format 'HH:mm:ss') | $Message"
}

function Write-Summary {
    param(
        [int]$Current,
        [int]$Target,
        [string]$Reason = ""
    )
    
    $percentage = [Math]::Min(100, [Math]::Round(($Current / $Target) * 100))
    $bar = "[" + ("=" * [Math]::Floor($percentage / 5)).PadRight(20, " ") + "] $percentage%"
    
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "COLLECTION STATUS: $Current / $Target posts $bar"
    if ($Reason) { Write-Host "  Reason: $Reason" }
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n"
}

Write-Log "[START] Facebook Group Posts Collection"
Write-Log "[GROUP] $GroupUrl"
Write-Log "[TARGET] $PostTarget posts"
Write-Log "[MAX_SCROLL] $ScrollTimes iterations"

# Create output directory
New-Item -ItemType Directory -Force .\data | Out-Null

# ============================================================================
# PHASE 1: Open group & take initial snapshot
# ============================================================================
Write-Log "[PHASE 1] Open group"
openclaw browser --browser-profile $BrowserProfile open "$GroupUrl"

Write-Log "[WAIT] Page load (4s)"
openclaw browser --browser-profile $BrowserProfile wait --time 4000

Write-Log "[SNAP] Taking initial snapshot"
$contentSnapshot = openclaw browser --browser-profile $BrowserProfile snapshot --format ai --limit 15000
# Convert to string array and write with proper encoding
[System.IO.File]::WriteAllText("$(Get-Location)/data/group_snapshot_content.txt", ($contentSnapshot -join "`n"), [System.Text.Encoding]::UTF8)

$uiSnapshot = openclaw browser --browser-profile $BrowserProfile snapshot --interactive --depth 8
[System.IO.File]::WriteAllText("$(Get-Location)/data/group_snapshot_ui.txt", ($uiSnapshot -join "`n"), [System.Text.Encoding]::UTF8)

# ============================================================================
# PHASE 2: Parse initial posts
# ============================================================================
Write-Log "[PHASE 2] Parse iteration 0"
$parseOutput = python scripts/parse_snapshot_posts.py 2>&1
Write-Log "[PARSE] $parseOutput"

# Load & accumulate posts
$allPosts = @()
if (Test-Path .\data\visible_posts.json) {
    $postsJson = Get-Content .\data\visible_posts.json -Encoding UTF8 | ConvertFrom-Json
    $allPosts = @($postsJson.posts)
}
Write-Summary -Current $allPosts.Count -Target $PostTarget -Reason "Initial load"

# ============================================================================
# PHASE 3: Scroll & collect more posts
# ============================================================================
$scrollIteration = 1
$noNewPostsCount = 0

while ($allPosts.Count -lt $PostTarget -and $scrollIteration -le $ScrollTimes) {
    Write-Log "[SCROLL $scrollIteration/$ScrollTimes] Pressing End..."
    openclaw browser --browser-profile $BrowserProfile press End
    
    Write-Log "[WAIT] Lazy-load (3s)"
    openclaw browser --browser-profile $BrowserProfile wait --time 3000
    
    Write-Log "[SNAP] Taking post-scroll snapshot"
    $contentSnapshot = openclaw browser --browser-profile $BrowserProfile snapshot --format ai --limit 15000
    [System.IO.File]::WriteAllText("$(Get-Location)/data/group_snapshot_content.txt", ($contentSnapshot -join "`n"), [System.Text.Encoding]::UTF8)
    
    $uiSnapshot = openclaw browser --browser-profile $BrowserProfile snapshot --interactive --depth 8
    [System.IO.File]::WriteAllText("$(Get-Location)/data/group_snapshot_ui.txt", ($uiSnapshot -join "`n"), [System.Text.Encoding]::UTF8)
    
    Write-Log "[PARSE] Parsing iteration $scrollIteration..."
    $parseOutput = python scripts/parse_snapshot_posts.py 2>&1
    Write-Log "[PARSE] $parseOutput"
    
    if (Test-Path .\data\visible_posts.json) {
        $postsJson = Get-Content .\data\visible_posts.json -Encoding UTF8 | ConvertFrom-Json
        $iterationPosts = @($postsJson.posts)
        
        $beforeCount = $allPosts.Count
        
        # Merge posts (add new ones from this iteration)
        foreach ($post in $iterationPosts) {
            $exists = $allPosts | Where-Object {
                $_.author -eq $post.author -and $_.time_label -eq $post.time_label
            }
            
            if (-not $exists) {
                $allPosts += $post
            }
        }
        
        $afterCount = $allPosts.Count
        $newPosts = $afterCount - $beforeCount
        
        Write-Log "[MERGE] +$newPosts posts (total: $afterCount)"
        
        if ($newPosts -le 0) {
            $noNewPostsCount++
            Write-Summary -Current $afterCount -Target $PostTarget -Reason "No new posts ($noNewPostsCount/$MaxNoNewPostsIterations)"
            
            if ($noNewPostsCount -ge $MaxNoNewPostsIterations) {
                Write-Log "[STOP] No new posts for $MaxNoNewPostsIterations iterations"
                break
            }
        } else {
            $noNewPostsCount = 0
            Write-Summary -Current $afterCount -Target $PostTarget -Reason "Scrolling (iteration $scrollIteration)"
            
            if ($afterCount -ge $PostTarget) {
                Write-Log "[SUCCESS] Reached target!"
                break
            }
        }
    }
    
    $scrollIteration++
}

# ============================================================================
# PHASE 4: Save final merged posts
# ============================================================================
Write-Log "[PHASE 4] Saving final posts"

$finalOutput = @{
    ok = $true
    count = $allPosts.Count
    posts = $allPosts
    collected_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    target = $PostTarget
    actual = $allPosts.Count
    completion_rate = [Math]::Min(100, [Math]::Round(($allPosts.Count / $PostTarget) * 100))
}

$finalOutput | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 .\data\visible_posts.json

Write-Summary -Current $allPosts.Count -Target $PostTarget -Reason "Collection complete"

# Show summary
Write-Host "COLLECTION SUMMARY:" -ForegroundColor Cyan
$postIndex = 1
foreach ($post in $allPosts) {
    $autho = if ($post.is_anonymous) { "Anon" } else { $post.author.Substring(0, [Math]::Min(20, $post.author.Length)) }
    $text = $post.post_text.Substring(0, [Math]::Min(45, $post.post_text.Length))
    Write-Host "$($postIndex.ToString('D2')). $($autho.PadRight(20)) | $($post.time_label.PadRight(8)) | $text..."
    $postIndex++
}

Write-Log "[FINISH] Collection saved to ./data/visible_posts.json"
