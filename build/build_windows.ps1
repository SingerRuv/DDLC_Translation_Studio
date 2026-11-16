$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist\windows"
$Work = Join-Path $env:TEMP "ddlc-translation-studio-windows"

Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $Dist, $Work -Force | Out-Null

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name DDLCTranslationStudio `
    --distpath $Dist --workpath (Join-Path $Work "build") --specpath $Work `
    (Join-Path $Root "app.py")

Get-Item -LiteralPath (Join-Path $Dist "DDLCTranslationStudio.exe") |
    Select-Object FullName, Length, LastWriteTime
