Set-Location C:/SZL/edge-debug/estate-cards
git init 2>&1 | Out-Null
git branch -M main
git add -A 2>&1 | Out-Null
git -c user.name="stephenlutar2-hash" -c user.email="stephenlutar2-hash@users.noreply.github.com" commit -m "estate-cards weaver v0.1.0: receipt-honest card system (charts, audit, cards, paced HF roller, Kimi-reviewed design)" 2>&1 | Select-Object -First 3
$exists = gh repo view szl-holdings/estate-cards --json name 2>$null
if (-not $exists) {
  gh repo create szl-holdings/estate-cards --public --description "Receipt-honest showcase card system for the SZL estate: HF + GitHub repos, deterministic SVG graphs, KANCHAY design" 2>&1 | Select-Object -First 2
}
git remote remove origin 2>$null
git remote add origin https://github.com/szl-holdings/estate-cards.git
git push -u origin main 2>&1 | Select-Object -First 5
Write-Output "PUSH_DONE"
 exit