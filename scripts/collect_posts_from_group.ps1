# collect_posts_from_group.ps1
# 
# Mục đích: Collect posts từ Facebook group bằng loop: expand -> extract -> parse -> scroll -> repeat
# Constraint: DRY-RUN ONLY. Không post, không comment, không submit gì.
# 
# Sử dụng: 
#   1. Standalone: powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 -GroupUrl "https://..." -TargetCount 10
#   2. Hoặc gọi từ script khác
#
# Browser API (OpenClaw CLI):
#   - Navigate:  openclaw browser navigate <url> --browser-profile <profile>
#   - Evaluate:  openclaw browser evaluate --fn <jsCode> --browser-profile <profile>
#   - Snapshot:  openclaw browser snapshot --browser-profile <profile>
#   NOTE: Old flags -i/-u are deprecated. Use --browser-profile and navigate separately.

param(
    [Parameter(Mandatory=$false)]
    [string]$GroupUrl = "",  # If empty, sẽ yêu cầu user nhập
    
    [Parameter(Mandatory=$false)]
    [int]$TargetCount = 10,  # Target number of posts to collect
    
    [Parameter(Mandatory=$false)]
    [string]$BrowserProfile = "openclaw",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "data",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxIterations = 20,  # Safety limit to prevent infinite loops
    
    [Parameter(Mandatory=$false)]
    [bool]$DryRun = $true  # Always DRY-RUN per AGENTS.md
)

$ErrorActionPreference = "Continue"  # Don't stop on errors, log them
$StartTime = Get-Date

# ===== Helper Functions =====

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logMsg = "[$timestamp] [$Level] $Message"
    Write-Host $logMsg
    
    # Also log to file
    $logFile = "logs/collect_posts.log"
    New-Item -ItemType Directory -Path "logs" -Force -ErrorAction SilentlyContinue | Out-Null
    Add-Content -Path $logFile -Value $logMsg -ErrorAction SilentlyContinue
}

function Assert-Success {
    param(
        [int]$ExitCode,
        [string]$Context
    )
    if ($ExitCode -ne 0) {
        Write-Log "FAILED at $Context (exit code: $ExitCode)" "ERROR"
        return $false
    }
    return $true
}

function Get-PostCount {
    param([string]$PostsFile)
    
    if (-not (Test-Path $PostsFile)) {
        return 0
    }
    
    try {
        $data = Get-Content -Path $PostsFile -Raw | ConvertFrom-Json
        
        if ($data.posts) {
            return $data.posts.Count
        } elseif ($data -is [array]) {
            return $data.Count
        } else {
            return 0
        }
    } catch {
        Write-Log "Error reading post count from $PostsFile : $_" "WARN"
        return 0
    }
}

function Backup-VisiblePosts {
    param([int]$IterationNum)
    
    $srcFile = "data/visible_posts.json"
    $destFile = "data/visible_posts_iter_$IterationNum.json"
    
    if (Test-Path $srcFile) {
        Copy-Item -Path $srcFile -Destination $destFile -Force -ErrorAction SilentlyContinue
        Write-Log "Backed up posts to: $destFile"
    }
}

function Merge-AllIterationPosts {
    param([int]$TotalIterations)
    
    Write-Log "========== Merging posts from all iterations =========="
    
    $allPosts = @()
    
    # Load posts from each iteration
    for ($i = 1; $i -le $TotalIterations; $i++) {
        $file = "data/visible_posts_iter_$i.json"
        if (Test-Path $file) {
            try {
                $data = Get-Content -Path $file -Raw | ConvertFrom-Json
                $posts = if ($data.posts) { $data.posts } else { $data }
                
                if ($posts -is [array]) {
                    $allPosts += $posts
                    Write-Log "Added $($posts.Count) posts from iteration $i"
                } elseif ($posts) {
                    $allPosts += @($posts)
                    Write-Log "Added 1 post from iteration $i"
                }
            } catch {
                Write-Log "Error loading posts from iteration $i : $_" "WARN"
            }
        }
    }
    
    Write-Log "Total posts before dedup: $($allPosts.Count)"
    
    # Merge using Python script (dedup_posts.py)
    Write-Log "Running dedup_posts.py..."
    
    # Create temporary file with all posts
    $tempFile = "data/temp_all_posts.json"
    $allPostsData = @{
        posts = $allPosts
    }
    $allPostsData | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding UTF8
    
    # Run dedup script
    python scripts/dedup_posts.py $tempFile "data/posts_collection.json" $TargetCount | Out-String | ForEach-Object {
        Write-Log $_
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Warning: dedup_posts.py returned exit code $LASTEXITCODE" "WARN"
    }
    
    # Clean up temp file
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
    
    Write-Log "Final result saved to: data/posts_collection.json"
}

# ===== Main Workflow =====

Write-Log "========== Starting Posts Collection Workflow =========="
Write-Log "Configuration:"
Write-Log "  GroupUrl: $GroupUrl"
Write-Log "  TargetCount: $TargetCount"
Write-Log "  BrowserProfile: $BrowserProfile"
Write-Log "  MaxIterations: $MaxIterations"
Write-Log "  DryRun: $DryRun"

# Validate GroupUrl
if ([string]::IsNullOrWhiteSpace($GroupUrl)) {
    Write-Log "GroupUrl is required. Please provide -GroupUrl parameter or configure in groups.json" "ERROR"
    exit 1
}

# Check if it's a valid Facebook group URL
if (-not ($GroupUrl -match "facebook\.com/groups/")) {
    Write-Log "Invalid Facebook group URL: $GroupUrl" "ERROR"
    exit 1
}

Write-Log "Target URL: $GroupUrl"

# Create output directories
New-Item -ItemType Directory -Path $OutputDir -Force -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Path "$OutputDir/raw" -Force -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Path "logs" -Force -ErrorAction SilentlyContinue | Out-Null

# ===== Main Loop =====
$iteration = 0
$totalPostsCollected = 0

# Navigate browser to the group URL before the loop
Write-Log "Navigating browser to: $GroupUrl"
openclaw browser navigate $GroupUrl --browser-profile $BrowserProfile 2>&1 | ForEach-Object { Write-Log $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Log "Warning: browser navigate returned non-zero exit code, continuing..." "WARN"
}
Start-Sleep -Seconds 3  # Wait for page to load

while ($iteration -lt $MaxIterations) {
    $iteration += 1
    Write-Log ""
    Write-Log "========== ITERATION $iteration =========="
    
    # Phase 1: Expand visible posts
    Write-Log "[Phase 1/5] Expanding visible posts..."
    $expandJs = Get-Content -Path "./scripts/expand_visible_posts.js" -Raw
    $expandOutput = openclaw browser evaluate --fn $expandJs --browser-profile $BrowserProfile 2>&1
    
    if (-not (Assert-Success $LASTEXITCODE "expand_visible_posts.js")) {
        Write-Log "Warning: expand_visible_posts failed, continuing..." "WARN"
        Write-Log "Output: $expandOutput" "WARN"
    } else {
        Write-Log "Expand complete"
    }
    
    Start-Sleep -Seconds 1  # Let DOM stabilize
    
    # Phase 2: Extract visible posts from DOM
    Write-Log "[Phase 2/5] Extracting posts from DOM..."
    $extractJs = Get-Content -Path "./scripts/extract_visible_posts.js" -Raw
    $extractOutput = openclaw browser evaluate --fn $extractJs --browser-profile $BrowserProfile 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        try {
            $extractResult = $extractOutput | ConvertFrom-Json
            $extractedCount = $extractResult.total
            Write-Log "Extracted $extractedCount posts from DOM"
        } catch {
            Write-Log "Failed to parse extract output" "WARN"
            Write-Log "Output: $extractOutput" "WARN"
        }
    } else {
        Write-Log "Warning: extract_visible_posts failed (exit code $LASTEXITCODE), continuing..." "WARN"
    }
    
    Start-Sleep -Seconds 1
    
    # Phase 3: Lookup action references
    Write-Log "[Phase 3/5] Looking up action references..."
    $refsJs = Get-Content -Path "./scripts/lookup_post_action_refs.js" -Raw
    $refsOutput = openclaw browser evaluate --fn $refsJs --browser-profile $BrowserProfile 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        try {
            $refsResult = $refsOutput | ConvertFrom-Json
            Write-Log "Found refs for posts"
        } catch {
            Write-Log "Failed to parse refs output" "WARN"
            Write-Log "Output: $refsOutput" "WARN"
        }
    } else {
        Write-Log "Warning: lookup_post_action_refs failed (exit code $LASTEXITCODE), continuing..." "WARN"
    }
    
    Start-Sleep -Seconds 1
    
    # Phase 4: Parse snapshots using Python
    Write-Log "[Phase 4/5] Parsing snapshots..."
    python scripts/parse_snapshot_posts.py 2>&1 | ForEach-Object {
        Write-Log $_
    }
    
    if (-not (Assert-Success $LASTEXITCODE "parse_snapshot_posts.py")) {
        Write-Log "Warning: parse_snapshot_posts failed, continuing..." "WARN"
    }
    
    # Phase 5: Merge posts and refs
    Write-Log "[Phase 5/5] Merging posts with action refs..."
    python scripts/merge_posts_and_refs.py 2>&1 | ForEach-Object {
        Write-Log $_
    }
    
    if (-not (Assert-Success $LASTEXITCODE "merge_posts_and_refs.py")) {
        Write-Log "Warning: merge_posts_and_refs failed, continuing..." "WARN"
    }
    
    # Check post count
    $postsFile = "data/visible_posts.json"
    $currentCount = Get-PostCount -PostsFile $postsFile
    $totalPostsCollected = $currentCount
    
    Write-Log "Posts collected in this iteration: $currentCount"
    Write-Log "Total posts so far: $totalPostsCollected / $TargetCount"
    
    # Backup this iteration's posts
    Backup-VisiblePosts -IterationNum $iteration
    
    # Check if we have enough posts
    if ($totalPostsCollected -ge $TargetCount) {
        Write-Log "Reached target count! Stopping collection."
        break
    }
    
    # If not enough posts, scroll and continue
    if ($iteration -lt $MaxIterations) {
        Write-Log "Need more posts. Scrolling down (aggressive: 3 attempts + wait 4s)..."
        $scrollJs = Get-Content -Path "./scripts/scroll_page.js" -Raw
        $scrollOutput = openclaw browser evaluate --fn $scrollJs --browser-profile $BrowserProfile 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            try {
                $scrollResult = $scrollOutput | ConvertFrom-Json
                
                if ($scrollResult.status -eq "success" -or $scrollResult.status -eq "scrolled") {
                    Write-Log "Scroll complete:"
                    Write-Log "  - Scroll distance: $($scrollResult.scroll_total_distance)px"
                    Write-Log "  - Posts before scroll: $($scrollResult.initial_post_count)"
                    Write-Log "  - Posts after scroll: $($scrollResult.final_post_count)"
                    Write-Log "  - New posts loaded: $($scrollResult.new_posts_loaded)"
                    Start-Sleep -Seconds 1
                } else {
                    Write-Log "Scroll status: $($scrollResult.status)" "WARN"
                    if ($scrollResult.error) {
                        Write-Log "Scroll error: $($scrollResult.error)" "WARN"
                    }
                    Start-Sleep -Seconds 2
                }
            } catch {
                Write-Log "Failed to parse scroll output" "WARN"
                Write-Log "Output: $scrollOutput" "WARN"
                Start-Sleep -Seconds 2
            }
        } else {
            Write-Log "Scroll command failed (exit code $LASTEXITCODE)" "WARN"
            Start-Sleep -Seconds 2
        }
    }
}

Write-Log ""
Write-Log "========== Collection Complete =========="
Write-Log "Total iterations: $iteration"
Write-Log "Total posts collected: $totalPostsCollected"

# Final merge of all iterations (always merge to deduplicate)
Write-Log ""
Merge-AllIterationPosts -TotalIterations $iteration

# Summary
Write-Log ""
Write-Log "========== Summary =========="
Write-Log "Status: Success"
Write-Log "Target count: $TargetCount"
Write-Log "Actual collected: $totalPostsCollected"
Write-Log "Iterations: $iteration / $MaxIterations"
Write-Log "Output files:"
Write-Log "  - data/visible_posts.json (latest iteration)"
Write-Log "  - data/posts_collection.json (final merged & deduped)"

if ($iteration -ge $MaxIterations) {
    Write-Log "Note: Reached max iterations limit without collecting enough posts" "WARN"
}

$EndTime = Get-Date
$Duration = $EndTime - $StartTime
Write-Log "Total duration: $($Duration.TotalSeconds) seconds"

exit 0
