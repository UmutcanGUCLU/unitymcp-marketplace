# PUSH-TO-GITHUB.ps1
# unitymcp-marketplace repo'sunu GitHub'a otomatik push eder.
#
# KULLANIM (PowerShell):
#   1. Bu script'in oldugu klasore cd yap
#   2. .\PUSH-TO-GITHUB.ps1
#   3. Ilk seferde GitHub username + Personal Access Token sorulur, kaydedilir
#
# GEREKSINIMLER:
#   - Git kurulu (git-scm.com)
#   - GitHub hesabin + Personal Access Token (github.com/settings/tokens)
#     Token olustururken "repo" scope'unu sec

param(
    [string]$RepoName = "unitymcp-marketplace",
    [string]$Description = "Full-stack Unity 6 (URP) Claude Code plugin + self-extending knowledge base (BM25 + vector hybrid search)",
    [switch]$Private,
    [switch]$Force = $false
)

# Native git komutlari stderr'e yazinca PowerShell fatal saymasin
$ErrorActionPreference = "Continue"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "[ERR] $msg" -ForegroundColor Red }

# Native git komutlarinda stderr'i fatal saymamak icin yardimci
function Test-HasCommits {
    & git rev-parse --verify HEAD 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}
function Get-RemoteUrl {
    $out = & git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0) { return $out }
    return $null
}

# Bu script repo kokunde mi kontrol et
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (-not (Test-Path ".\.claude-plugin\marketplace.json")) {
    Write-Err "marketplace.json bulunamadi. Bu script'i unitymcp-repo klasorunun icinde calistir."
    exit 1
}

# Git var mi
try {
    git --version | Out-Null
} catch {
    Write-Err "Git kurulu degil. https://git-scm.com adresinden indir."
    exit 1
}

# Credential dosyasi
$credPath = Join-Path $env:USERPROFILE ".unitymcp-github-creds"

if ((Test-Path $credPath) -and -not $Force) {
    Write-Step "Mevcut credentials kullaniliyor: $credPath"
    $cred = Get-Content $credPath | ConvertFrom-Json
    $username = $cred.username
    $token = $cred.token
} else {
    Write-Step "GitHub kimlik bilgileri (ilk seferlik)"
    Write-Host "Personal Access Token olustur: https://github.com/settings/tokens"
    Write-Host "  -> 'Generate new token (classic)' -> 'repo' scope -> Generate"
    Write-Host ""
    $username = Read-Host "GitHub username"
    $tokenSecure = Read-Host "Personal Access Token" -AsSecureString
    $token = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($tokenSecure)
    )

    $cred = @{ username = $username; token = $token } | ConvertTo-Json
    $cred | Set-Content $credPath
    # NOT: USERPROFILE klasoru zaten ACL ile sadece kullaniciya acik
    Write-OK "Credentials kaydedildi: $credPath"
}

# Repo zaten var mi
Write-Step ("GitHub repo kontrol: {0}/{1}" -f $username, $RepoName)
$headers = @{
    "Authorization" = "Bearer $token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$checkUrl = "https://api.github.com/repos/{0}/{1}" -f $username, $RepoName
$repoExists = $false
$repoUrl = ""

try {
    $existing = Invoke-RestMethod -Uri $checkUrl -Headers $headers -Method Get -ErrorAction Stop
    $repoExists = $true
    $repoUrl = $existing.clone_url
    Write-OK ("Repo zaten var: {0}" -f $existing.html_url)
} catch {
    $statusCode = 0
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    if ($statusCode -eq 404) {
        Write-Step "Yeni repo olusturuluyor..."
        $createUrl = "https://api.github.com/user/repos"
        $body = @{
            name = $RepoName
            description = $Description
            private = [bool]$Private
            auto_init = $false
            has_issues = $true
            has_wiki = $false
        } | ConvertTo-Json

        try {
            $newRepo = Invoke-RestMethod -Uri $createUrl -Headers $headers -Method Post -Body $body -ContentType "application/json"
            Write-OK ("Repo olusturuldu: {0}" -f $newRepo.html_url)
            $repoUrl = $newRepo.clone_url
            $repoExists = $true
        } catch {
            Write-Err ("Repo olusturulamadi: {0}" -f $_.Exception.Message)
            Write-Host "Olasi sebep: token izinleri yetersiz (repo scope gerekli) veya token yanlis"
            exit 1
        }
    } else {
        Write-Err ("GitHub API hatasi (status={0}): {1}" -f $statusCode, $_.Exception.Message)
        Write-Host "Token gecersiz veya expired olabilir. -Force ile yeni token gir."
        exit 1
    }
}

# Git init / mevcut repo
if (-not (Test-Path ".git")) {
    Write-Step "Git repo baslatiliyor..."
    git init | Out-Null
    git branch -M main
    Write-OK "Git init"
} else {
    Write-Step "Mevcut git repo kullaniliyor"
}

# .gitignore kontrol
if (-not (Test-Path ".gitignore")) {
    Write-Err ".gitignore yok"
    Write-Host "Devam etmek istediginize emin misiniz? (y/N): " -NoNewline
    $confirm = Read-Host
    if ($confirm -ne "y") { exit 1 }
}

# git config kontrol
$gitUserName = & git config user.name 2>$null
$gitUserEmail = & git config user.email 2>$null
if (-not $gitUserName) {
    git config user.name $username
    Write-OK ("git config user.name = {0}" -f $username)
}
if (-not $gitUserEmail) {
    $defaultEmail = "{0}@users.noreply.github.com" -f $username
    $email = Read-Host ("git config user.email [{0}]" -f $defaultEmail)
    if (-not $email) { $email = $defaultEmail }
    git config user.email $email
    Write-OK ("git config user.email = {0}" -f $email)
}

# Add + commit
Write-Step "Dosyalar staging'e ekleniyor..."
git add .
$staged = (git diff --cached --name-only | Measure-Object).Count
Write-OK ("{0} dosya staged" -f $staged)

if ($staged -gt 0) {
    if (-not (Test-HasCommits)) {
        $commitMsg = "feat: initial release v0.2.0 - full-stack Unity 6 plugin + knowledge layer"
    } else {
        $commitMsg = Read-Host "Commit mesaji [feat: update]"
        if (-not $commitMsg) { $commitMsg = "feat: update" }
    }
    & git commit -m $commitMsg 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Commit basarisiz oldu"
        exit 1
    }
    Write-OK ("Commit: {0}" -f $commitMsg)
} else {
    Write-Host "Commit edilecek yeni dosya yok"
    if (-not (Test-HasCommits)) {
        Write-Err "Repo bos, hic commit yok. Iptal."
        exit 1
    }
}

# Remote ayarla (token gomulu URL ile push, sonra temizle)
$cleanRepoUrl = "https://github.com/{0}/{1}.git" -f $username, $RepoName
$authRepoUrl = "https://{0}:{1}@github.com/{2}/{3}.git" -f $username, $token, $username, $RepoName

$existingRemote = Get-RemoteUrl
if (-not $existingRemote) {
    & git remote add origin $authRepoUrl 2>&1 | Out-Null
    Write-OK "Remote 'origin' eklendi"
} else {
    & git remote set-url origin $authRepoUrl 2>&1 | Out-Null
}

# Push
Write-Step "GitHub'a push ediliyor..."
$pushOk = $false
try {
    git push -u origin main 2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -eq 0) {
        $pushOk = $true
        Write-OK "Push basarili"
    }
} catch {
    Write-Err ("Push hatasi: {0}" -f $_.Exception.Message)
}

# Token'i URL'den temizle
git remote set-url origin $cleanRepoUrl

if (-not $pushOk) {
    Write-Err "Push basarisiz oldu. Yukaridaki cikti'ya bak."
    exit 1
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "  Tamamlandi!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

$webUrl = "https://github.com/{0}/{1}" -f $username, $RepoName
$marketplaceCmd = "/plugin marketplace add github:{0}/{1}" -f $username, $RepoName

Write-Host ("  Repo URL: {0}" -f $webUrl)
Write-Host ("  Clone URL: {0}.git" -f $webUrl)
Write-Host ""
Write-Host "Baska bir PC'den cekmek icin:"
Write-Host ("  git clone {0}.git" -f $webUrl) -ForegroundColor Yellow
Write-Host ""
Write-Host "Claude Code'a marketplace eklemek icin:"
Write-Host ("  {0}" -f $marketplaceCmd) -ForegroundColor Yellow
Write-Host ""
