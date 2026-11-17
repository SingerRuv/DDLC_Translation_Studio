$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist\windows"
$Work = Join-Path $env:TEMP "ddlc-translation-studio-windows"
$UnrpycLicense = Join-Path $Root "ddlc_studio\vendor\unrpyc\LICENSE"
$LegacyUnrpyc = Join-Path $Root "ddlc_studio\vendor\unrpyc_legacy"

Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $Dist, $Work -Force | Out-Null

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name DDLCTranslationStudio `
    --add-data "$UnrpycLicense;ddlc_studio/vendor/unrpyc" `
    --add-data "$LegacyUnrpyc;ddlc_studio/vendor/unrpyc_legacy" `
    --distpath $Dist --workpath (Join-Path $Work "build") --specpath $Work `
    (Join-Path $Root "app.py")

Get-Item -LiteralPath (Join-Path $Dist "DDLCTranslationStudio.exe") |
    Select-Object FullName, Length, LastWriteTime
