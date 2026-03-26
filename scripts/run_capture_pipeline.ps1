# run_capture_pipeline.ps1
# 
# Mục đích: Orchestrate toàn bộ capture -> parse -> merge -> filter -> report pipeline
# Constraint: DRY-RUN ONLY. Không post, không comment, không submit gì.
# 
# Usage: powershell -ExecutionPolicy Bypass -File scripts/run_capture_pipeline.ps1 [-GroupUrl "..."] [-DryRun $true]

param(
    [string]$GroupUrl = "https://www.facebook.com/groups/123456789",  # Config từ groups.json
    [string]$BrowserProfile = "openclaw",
    [bool]$DryRun = $true,
    [string]$OutputDir = "data/processed",
    [string]$RawDir = "data/raw"
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

# Logging helper
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logMsg = "[$timestamp] [$Level] $Message"
    Write-Host $logMsg
    Add-Content -Path "logs/pipeline.log" -Value $logMsg -ErrorAction SilentlyContinue
}

function Assert-Success {
    param([int]$ExitCode, [string]$Context)
    if ($ExitCode -ne 0) {
        Write-Log "FAILED at $Context (exit code: $ExitCode)" "ERROR"
        exit $ExitCode
    }
}

# ===== PHASE 1: Expand visible posts (click "Xem thêm") =====
Write-Log "========== PHASE 1: Expand visible posts =========="
Write-Log "Opening browser and clicking 'Xem thêm' buttons..."

$expandResult = openclaw browser evaluate `
    -i $BrowserProfile `
    -u $GroupUrl `
    "./scripts/expand_visible_posts.js"

Assert-Success $LASTEXITCODE "expand_visible_posts.js"

Write-Log "Expanded posts: Check browser console output"

# Wait for DOM to stabilize
Start-Sleep -Seconds 2

# ===== PHASE 2: Extract visible posts (DOM content) =====
Write-Log "========== PHASE 2: Extract visible posts from DOM =========="
Write-Log "Extracting post content, author, time from page DOM..."

$extractResult = openclaw browser evaluate `
    -i $BrowserProfile `
    "./scripts/extract_visible_posts.js" | ConvertFrom-Json

Assert-Success $LASTEXITCODE "extract_visible_posts.js"

$extractedCount = $extractResult.total
Write-Log "Extracted $extractedCount posts from DOM"
if ($extractResult.errors.Count -gt 0) {
    Write-Log "Extraction errors: $($extractResult.errors | ConvertTo-Json)" "WARN"
}

# Save DOM extraction output
$extractFile = "$RawDir/dom_posts.json"
$extractResult | ConvertTo-Json -Depth 10 | Out-File -FilePath $extractFile -Encoding UTF8
Write-Log "Saved DOM posts to: $extractFile"

# ===== PHASE 3: Lookup action references =====
Write-Log "========== PHASE 3: Lookup action references =========="
Write-Log "Finding comment/like/share button references..."

$refsResult = openclaw browser evaluate `
    -i $BrowserProfile `
    "./scripts/lookup_post_action_refs.js" | ConvertFrom-Json

Assert-Success $LASTEXITCODE "lookup_post_action_refs.js"

Write-Log "Posts with all refs: $($refsResult.posts_with_all_refs) / $($refsResult.total)"
if ($refsResult.posts_with_missing_refs -gt 0) {
    Write-Log "Posts with missing refs: $($refsResult.posts_with_missing_refs)" "WARN"
}

# Save refs output
$refsFile = "$RawDir/action_refs.json"
$refsResult | ConvertTo-Json -Depth 10 | Out-File -FilePath $refsFile -Encoding UTF8
Write-Log "Saved action refs to: $refsFile"

# ===== PHASE 4: Parse UI snapshot (existing parse_snapshot_posts.py) =====
Write-Log "========== PHASE 4: Parse UI/Content snapshots =========="
Write-Log "Running Python parser on snapshots..."

python scripts/parse_snapshot_posts.py
Assert-Success $LASTEXITCODE "parse_snapshot_posts.py"

# Load snapshot parser output (data/visible_posts.json)
if (Test-Path "data/visible_posts.json") {
    $snapshotPosts = Get-Content "data/visible_posts.json" | ConvertFrom-Json
    $snapshotCount = $snapshotPosts.Count
    Write-Log "Parsed $snapshotCount posts from snapshots"
} else {
    Write-Log "No snapshot output found" "WARN"
    $snapshotPosts = @()
    $snapshotCount = 0
}

# ===== PHASE 5: Merge DOM & Snapshot data =====
Write-Log "========== PHASE 5: Merge DOM and Snapshot data =========="
Write-Log "Merging $extractedCount DOM posts + $snapshotCount snapshot posts..."

# Create merge input JSON
$mergeInput = @{
    dom_posts = $extractResult.posts
    snapshot_posts = $snapshotPosts
    timestamp = (Get-Date -AsUTC).ToString("o")
} | ConvertTo-Json -Depth 10

$mergeInput | Out-File -FilePath "$RawDir/merge_input.json" -Encoding UTF8

# Run merge script (will create parse_merge_posts.py next)
python scripts/merge_posts_and_refs.py
Assert-Success $LASTEXITCODE "merge_posts_and_refs.py"

# ===== PHASE 6: Build candidate posts =====
Write-Log "========== PHASE 6: Build candidate posts =========="
Write-Log "Filtering and preparing candidates..."

python scripts/build_candidate_posts.py
Assert-Success $LASTEXITCODE "build_candidate_posts.py"

# ===== PHASE 7: Generate DRY-RUN report =====
Write-Log "========== PHASE 7: Generate dry-run report =========="
Write-Log "Creating execution plan report..."

python scripts/generate_dry_run_plan.py
python scripts/render_dry_run_report.py
Assert-Success $LASTEXITCODE "report generation"
# ===== SUMMARY =====
Write-Log "========== PIPELINE SUMMARY =========="
Write-Log "DRY-RUN: $DryRun (no posts/comments sent)"
Write-Log "Duration: $((Get-Date) - $StartTime)"
Write-Log "DOM Posts Extracted: $extractedCount"
Write-Log "Snapshot Posts Parsed: $snapshotCount"
Write-Log "Raw outputs saved to: $RawDir/"
Write-Log "Awaiting next pipeline phases..."
Write-Log "========== PIPELINE COMPLETE =========="
