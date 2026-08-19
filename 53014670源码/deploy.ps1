# Scenic Guide AI - Docker Compose deploy (Windows PowerShell)

param(
    [switch]$Reindex,
    [switch]$Reset,
    [switch]$Down,
    [switch]$Logs,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$DocsDir = Join-Path $Root "backend\data\scenic_docs"
$EnvFile = Join-Path $Root "backend\.env"

function Write-Step([string]$msg) {
    Write-Host ("==> " + $msg) -ForegroundColor Cyan
}

function Write-WarnMsg([string]$msg) {
    Write-Host ("!!> " + $msg) -ForegroundColor Yellow
}

function Stop-Deploy([string]$msg) {
    Write-Host ("ERR> " + $msg) -ForegroundColor Red
    exit 1
}

function Get-DemoFolderName {
    $codes = @(31034,33539,26223,21306,20844,24320,36164,26009,21253)
    $chars = foreach ($code in $codes) { [char]$code }
    return (-join $chars)
}

function Get-DemoSourceDir {
    $folderName = Get-DemoFolderName
    $preferred = Join-Path $Root $folderName
    if (Test-Path $preferred) {
        $official = Get-ChildItem $preferred -Recurse -Include "*.docx", "*.xlsx", "*.pdf", "*.txt", "*.md" -File -ErrorAction SilentlyContinue
        if ($official -and $official.Count -gt 0) {
            return $preferred
        }
    }
    return $null
}

if ($Help) {
    Write-Host "Usage: .\deploy.ps1 [-Reindex] [-Reset] [-Down] [-Logs] [-Help]"
    exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-Deploy "Docker not found. Install Docker Desktop first."
}

docker compose version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Stop-Deploy "docker compose not found. Start Docker Desktop and retry."
}

if ($Down) {
    Write-Step "Stopping services..."
    docker compose down
    Write-Step "Stopped. Volumes are kept."
    exit 0
}

if ($Logs) {
    docker compose logs -f
    exit 0
}

Write-Step "Checking backend .env ..."
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root "backend\.env.example") $EnvFile
    Write-WarnMsg "Created backend .env from .env.example."
}

Write-Step "Syncing official demo package to backend data ..."
New-Item -ItemType Directory -Force -Path $DocsDir | Out-Null

$DemoDir = Get-DemoSourceDir
if (-not $DemoDir) {
    Write-WarnMsg "No official package folder found at project root."
    $docsFirst = Get-ChildItem $DocsDir -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $docsFirst) {
        Write-Step "Using existing files in backend data."
    }
    else {
        Stop-Deploy "No official documents found. Please put documents into backend\data\scenic_docs or the official package folder."
    }
}
else {
    $env:OFFICIAL_PACKAGE_DIR = $DemoDir
    Copy-Item -Path (Join-Path $DemoDir "*") -Destination $DocsDir -Recurse -Force
    $fileCount = (Get-ChildItem $DocsDir -Recurse -File).Count
    Write-Step ("Synced " + $fileCount + " files from official package.")
}

if ($Reindex -or $Reset) {
    $env:FORCE_REINDEX = "true"
}
else {
    $env:FORCE_REINDEX = "false"
}

if ($Reset) {
    $env:RESET_INDEX = "true"
}
else {
    $env:RESET_INDEX = "false"
}

Write-Step "Building and starting containers. First run may take 5-20 min..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Stop-Deploy "docker compose up failed."
}

Write-Step "Waiting for backend health check..."
$maxAttempts = 60
$attempt = 0
$healthy = $false
while ($attempt -lt $maxAttempts) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>$null | Out-Null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference

    if ($exitCode -eq 0) {
        $healthy = $true
        break
    }
    $attempt++
    Start-Sleep -Seconds 5
}

if (-not $healthy) {
    Write-WarnMsg "Backend still starting. Check: docker compose logs backend"
}

if ($env:HTTP_PORT) {
    $httpPort = $env:HTTP_PORT
}
else {
    $httpPort = "80"
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "Deploy finished!" -ForegroundColor Green
Write-Host ("  Web client : http://localhost:" + $httpPort + "/") -ForegroundColor Green
Write-Host ("  Admin      : http://localhost:" + $httpPort + "/admin/") -ForegroundColor Green
Write-Host ("  API docs   : http://localhost:" + $httpPort + "/docs") -ForegroundColor Green
Write-Host ("  Health     : http://localhost:" + $httpPort + "/health") -ForegroundColor Green
Write-Host ""
Write-Host "  docker compose logs -f" -ForegroundColor Green
Write-Host "  .\deploy.ps1 -Reindex" -ForegroundColor Green
Write-Host "  .\deploy.ps1 -Down" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
