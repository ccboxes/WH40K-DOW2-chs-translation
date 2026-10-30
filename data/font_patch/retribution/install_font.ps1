$ErrorActionPreference = 'Stop'

$gameDir = $PSScriptRoot
$modulePath = Join-Path $gameDir 'DOW2.module'
$sgaPath = Join-Path $gameDir 'GameAssets\Archives\zz_font.sga'

if (-not (Test-Path -LiteralPath $modulePath)) {
    throw "DOW2.module not found next to this script: $modulePath"
}
if (-not (Test-Path -LiteralPath $sgaPath)) {
    throw "zz_font.sga not found: $sgaPath"
}

$text = [System.IO.File]::ReadAllText($modulePath)
if ($text -match '(?im)^\s*archive\.\d+\s*=\s*GameAssets\\Archives\\zz_font\.sga\s*$') {
    Write-Host 'Font patch is already registered in DOW2.module.'
    exit 0
}

$m = [regex]::Match($text, '(?ms)^\[data:common\][ \t]*\r?\n(.*?)(?=^\[|\z)')
if (-not $m.Success) {
    throw 'Could not find the [data:common] section in DOW2.module.'
}

$maxIndex = 0
foreach ($line in ($m.Groups[1].Value -split "\r?\n")) {
    if ($line -match '^\s*archive\.(\d+)\s*=') {
        $index = [int]$Matches[1]
        if ($index -gt $maxIndex) {
            $maxIndex = $index
        }
    }
}

$nextIndex = $maxIndex + 1
$newLine = "archive.$nextIndex = GameAssets\Archives\zz_font.sga"
$newlineChars = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
$section = $m.Groups[1].Value.TrimEnd([char[]]"`r`n")
$newSection = $section + $newlineChars + $newLine + $newlineChars

$newText = $text.Substring(0, $m.Groups[1].Index) + $newSection +
    $text.Substring($m.Groups[1].Index + $m.Groups[1].Length)

$backupPath = "$modulePath.bak"
if (-not (Test-Path -LiteralPath $backupPath)) {
    Copy-Item -LiteralPath $modulePath -Destination $backupPath
}

$moduleItem = Get-Item -LiteralPath $modulePath
if ($moduleItem.IsReadOnly) {
    $moduleItem.IsReadOnly = $false
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($modulePath, $newText, $utf8NoBom)

Write-Host "Registered $newLine"
Write-Host 'Done. Start Dawn of War II - Retribution and check the Chinese text.'
