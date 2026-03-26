# example_collect_posts.ps1
# 
# Example script to collect posts from Facebook group
# Just change GROUP_URL and run!

# ===== CONFIG =====
# CHANGE THE LINE BELOW WITH YOUR GROUP URL
$GROUP_URL = "https://www.facebook.com/groups/792610141458395/"

# (Optional) Other options
$TARGET_COUNT = 10         # Number of posts to collect (default 10)
$BROWSER_PROFILE = "openclaw"  # Browser profile (default openclaw)
$MAX_ITERATIONS = 20       # Max loop iterations (default 20)

# ===== VALIDATION =====
if ($GROUP_URL -eq "https://www.facebook.com/groups/YOUR_GROUP_ID_HERE") {
    Write-Host "[ERROR] Please change GROUP_URL!" -ForegroundColor Red
    Write-Host "   Example: https://www.facebook.com/groups/123456789" -ForegroundColor Yellow
    exit 1
}

if (-not ($GROUP_URL -match "facebook\.com/groups/")) {
    Write-Host "[ERROR] Invalid URL! Must be Facebook group URL" -ForegroundColor Red
    Write-Host "   Format: https://www.facebook.com/groups/YOUR_ID" -ForegroundColor Yellow
    exit 1
}

# ===== RUN WORKFLOW =====
Write-Host ""
Write-Host "[OK] Configuration:" -ForegroundColor Green
Write-Host "   Group URL: $GROUP_URL"
Write-Host "   Target: $TARGET_COUNT posts"
Write-Host "   Browser: $BROWSER_PROFILE"
Write-Host "   Max iterations: $MAX_ITERATIONS"
Write-Host ""

# Navigate to workspace
$WorkspacePath = "c:\Users\pntha\.openclaw\workspace"
if (-not (Test-Path $WorkspacePath)) {
    Write-Host "[ERROR] Workspace not found at $WorkspacePath" -ForegroundColor Red
    exit 1
}

Set-Location $WorkspacePath
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

# Run the main collector
Write-Host ""
Write-Host "[INFO] Starting collection..." -ForegroundColor Cyan
Write-Host ""

powershell -ExecutionPolicy Bypass -File scripts/collect_posts_from_group.ps1 `
    -GroupUrl $GROUP_URL `
    -TargetCount $TARGET_COUNT `
    -BrowserProfile $BROWSER_PROFILE `
    -MaxIterations $MAX_ITERATIONS

$ExitCode = $LASTEXITCODE

# ===== SUMMARY =====
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($ExitCode -eq 0) {
    Write-Host "[SUCCESS] Collection completed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Results saved to:" -ForegroundColor Green
    Write-Host "   data/posts_collection.json (final merged & deduped)" -ForegroundColor Yellow
    Write-Host "   data/visible_posts.json (latest iteration)" -ForegroundColor Yellow
    Write-Host "   logs/collect_posts.log (full log)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "   1. Check results: type data/posts_collection.json" -ForegroundColor Yellow
    Write-Host "   2. Parse JSON for further analysis" -ForegroundColor Yellow
    Write-Host "   3. Export to CSV/Excel if needed" -ForegroundColor Yellow
} else {
    Write-Host "[ERROR] Collection failed with exit code: $ExitCode" -ForegroundColor Red
    Write-Host "Check logs: logs/collect_posts.log" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

exit $ExitCode
