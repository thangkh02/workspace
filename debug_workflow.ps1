# debug_workflow.ps1 - Debug từng phase riêng lẻ

param(
    [string]$GroupUrl = "https://www.facebook.com/groups/792610141458395/"
)

Write-Host "=== DEBUG WORKFLOW ===" -ForegroundColor Cyan
Write-Host "Group: $GroupUrl" -ForegroundColor Yellow
Write-Host ""

# Phase 1: Test browser & page load
Write-Host "PHASE 1: Test browser connection" -ForegroundColor Green
Write-Host "Command: openclaw browser evaluate (simple test)" -ForegroundColor Gray

$testJs = @"
(function() {
  return {
    url: window.location.href,
    title: document.title,
    ready: document.readyState,
    posts_found: document.querySelectorAll('article').length
  };
})();
"@

$result1 = openclaw browser evaluate `
    -i openclaw `
    -u $GroupUrl `
    -c $testJs 2>&1

Write-Host "Result:" -ForegroundColor Yellow
Write-Host $result1
Write-Host ""

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR in Phase 1! Exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Browser may not be connected. Check:" -ForegroundColor Yellow
    Write-Host "  1. Browser profile 'openclaw' exists"
    Write-Host "  2. Browser is running"
    Write-Host "  3. Page loaded successfully"
    exit 1
}

# Phase 2: Test expand script
Write-Host "PHASE 2: Test expand_visible_posts.js" -ForegroundColor Green
Write-Host "Script: scripts/expand_visible_posts.js" -ForegroundColor Gray

$result2 = openclaw browser evaluate `
    -i openclaw `
    "./scripts/expand_visible_posts.js" 2>&1

Write-Host "Output:" -ForegroundColor Yellow
Write-Host $result2
Write-Host ""

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR in Phase 2! Exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "expand_visible_posts.js failed" -ForegroundColor Yellow
} else {
    Write-Host "SUCCESS: expand worked" -ForegroundColor Green
}

# Phase 3: Test extract script
Write-Host "PHASE 3: Test extract_visible_posts.js" -ForegroundColor Green
Write-Host "Script: scripts/extract_visible_posts.js" -ForegroundColor Gray

$result3 = openclaw browser evaluate `
    -i openclaw `
    "./scripts/extract_visible_posts.js" 2>&1

Write-Host "Output (first 1000 chars):" -ForegroundColor Yellow
$truncated = if ($result3.Length -gt 1000) { $result3.Substring(0, 1000) + "..." } else { $result3 }
Write-Host $truncated
Write-Host ""

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR in Phase 3! Exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "extract_visible_posts.js failed" -ForegroundColor Yellow
} else {
    Write-Host "SUCCESS: extract worked" -ForegroundColor Green
}

# Phase 4: Test parse (Python)
Write-Host "PHASE 4: Test parse_snapshot_posts.py" -ForegroundColor Green
Write-Host "Script: scripts/parse_snapshot_posts.py" -ForegroundColor Gray

$result4 = python scripts/parse_snapshot_posts.py 2>&1

Write-Host "Output:" -ForegroundColor Yellow
Write-Host $result4
Write-Host ""

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR in Phase 4! Exit code: $LASTEXITCODE" -ForegroundColor Red
} else {
    Write-Host "SUCCESS: parse worked" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "If Phase 1 (browser) fails: Browser not connected" -ForegroundColor Yellow
Write-Host "If Phase 2-3 (JS) fail: Script error in JS" -ForegroundColor Yellow
Write-Host "If Phase 4 (Python) fails: Missing snapshot files" -ForegroundColor Yellow
