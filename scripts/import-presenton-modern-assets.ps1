param(
    [Parameter(Mandatory = $true)]
    [string]$PresentonRoot
)

$ErrorActionPreference = "Stop"
$expectedRevision = "523b9cb47889e1fc124bb0dab77015b344a46f76"
$resolvedSource = (Resolve-Path -LiteralPath $PresentonRoot).Path
$revision = git -C $resolvedSource rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $revision.Trim() -ne $expectedRevision) {
    throw "Presenton checkout must be pinned to $expectedRevision."
}

$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$fontDirectory = Join-Path $workspaceRoot "apps\web\public\fonts"
$licenseDirectory = Join-Path $workspaceRoot "LICENSES"
$templateDirectory = Join-Path $workspaceRoot "apps\api\app\generation\templates"
New-Item -ItemType Directory -Force -Path $fontDirectory, $licenseDirectory, $templateDirectory | Out-Null

$sourceFontDirectory = Join-Path $resolvedSource "templates\executive\static"
Copy-Item -LiteralPath (Join-Path $sourceFontDirectory "Montserrat Regular.ttf") -Destination (Join-Path $fontDirectory "montserrat-regular.ttf") -Force
Copy-Item -LiteralPath (Join-Path $sourceFontDirectory "Montserrat Bold.ttf") -Destination (Join-Path $fontDirectory "montserrat-bold.ttf") -Force
Copy-Item -LiteralPath (Join-Path $resolvedSource "templates\modern\template.json") -Destination (Join-Path $templateDirectory "modern.json") -Force

Invoke-WebRequest -Uri "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/OFL.txt" -OutFile (Join-Path $licenseDirectory "Montserrat-OFL-1.1.txt")

Write-Output "Imported Presenton Modern template and font assets from $expectedRevision."
