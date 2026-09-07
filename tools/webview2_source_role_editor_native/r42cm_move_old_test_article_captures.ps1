param(
  [Parameter(Mandatory=$true)][string]$Root,
  [Parameter(Mandatory=$true)][string]$Backup
)
$ErrorActionPreference = 'Stop'
$base = Join-Path $Root 'profile_media_live_captures'
if (!(Test-Path -LiteralPath $base)) { return }
$destRoot = Join-Path $Backup 'old_test_article_captures'
New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
$patterns = @(
  'archive.ph_6mr3C',
  'archive.ph\6mr3C',
  'archive.ph/6mr3C',
  'people-shout-seagull-eater',
  'metro.co.uk_2026_07_17_people-shout-seagull-eater',
  'web.archive.org_web_20260717224516'
)
$exclude = @('r42cm_hard_clean_archive_material_test_backups','r42cl_clean_archive_material_test_backups')
$moved = 0
$dirs = Get-ChildItem -LiteralPath $base -Directory -Recurse -ErrorAction SilentlyContinue | Sort-Object { $_.FullName.Length } -Descending
foreach ($d in $dirs) {
  $full = $d.FullName
  if ($exclude | Where-Object { $full -like "*$_*" }) { continue }
  $match = $false
  foreach ($p in $patterns) {
    if ($full -like "*$p*") { $match=$true; break }
  }
  if (!$match) { continue }
  if (!(Test-Path -LiteralPath $d.FullName)) { continue }
  $rel = $d.FullName.Substring($base.Length).TrimStart('\')
  $safe = ($rel -replace '[:\\/]+','__')
  $target = Join-Path $destRoot $safe
  try {
    Move-Item -LiteralPath $d.FullName -Destination $target -Force
    Write-Host "MOVED_OLD_CAPTURE: $rel"
    $moved++
  } catch {
    Write-Host "WARN_COULD_NOT_MOVE_OLD_CAPTURE: $rel :: $($_.Exception.Message)"
  }
}
Write-Host "OLD_TEST_CAPTURE_DIRS_MOVED: $moved"
