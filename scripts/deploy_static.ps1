<#
.SYNOPSIS
  Build frontend, inject runtime API URL, and deploy `dist/` to remote server over SSH.

.PARAMETER RemoteHost
  Remote host (IP or domain) where nginx serves the site.
.PARAMETER RemoteUser
  SSH user for remote host.
.PARAMETER RemotePath
  Absolute path on remote host where static files should be uploaded (e.g. /var/www/songlab).
.PARAMETER ApiUrl
  Runtime API URL to inject into `dist/index.html` (e.g. https://api.example.com).
.PARAMETER SshPort
  Optional SSH port (default 22).

.NOTES
  Requires: `npx` (for vite), `node` (for postbuild script), OpenSSH client (scp/ssh) available in PATH.
  The script does not escalate privileges on remote host; remote commands that require sudo will prompt for password.
#>

param(
  [Parameter(Mandatory=$true)] [string] $RemoteHost,
  [Parameter(Mandatory=$true)] [string] $RemoteUser,
  [Parameter(Mandatory=$true)] [string] $RemotePath,
  [Parameter(Mandatory=$true)] [string] $ApiUrl,
  [int] $SshPort = 22
)

Set-StrictMode -Version Latest
Push-Location (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent) \..\

Write-Host "Building frontend (vite)..." -ForegroundColor Cyan
if (Test-Path package.json) {
  # prefer project script if present
  try {
    npx vite build --silent
  } catch {
    Write-Host "vite build failed: $_" -ForegroundColor Red
    Pop-Location; exit 1
  }
} else {
  Write-Host "package.json not found, aborting." -ForegroundColor Red; Pop-Location; exit 1
}

# run postbuild.js if exists
if (Test-Path .\scripts\postbuild.js) {
  Write-Host "Running postbuild.js" -ForegroundColor Cyan
  node .\scripts\postbuild.js
}

# inject runtime API URL into dist/index.html
$distIndex = Join-Path -Path (Get-Location) -ChildPath 'dist\index.html'
if (-not (Test-Path $distIndex)) { Write-Host "dist/index.html not found, build may have failed." -ForegroundColor Red; Pop-Location; exit 1 }

$injection = "<script>window.__SONGLAB_API_URL__ = '$ApiUrl';</script>"
$html = Get-Content -Raw $distIndex -Encoding UTF8
if ($html -notmatch [regex]::Escape($injection)) {
  $html = $html -replace '(?i)(<head[^>]*>)', "$1`n    $injection"
  Set-Content -Path $distIndex -Value $html -Encoding UTF8
  Write-Host "Injected runtime API URL into dist/index.html" -ForegroundColor Green
} else { Write-Host "dist/index.html already contains injection" -ForegroundColor Yellow }

# Upload files via scp (recursively). Use tar+scp/ssh if you prefer atomic deploy.
Write-Host "Uploading dist/ to $RemoteUser@$RemoteHost:$RemotePath (scp)" -ForegroundColor Cyan

$scpCmd = "scp -P $SshPort -r dist/* $RemoteUser@$RemoteHost:`"$RemotePath`""
Write-Host "Running: $scpCmd" -ForegroundColor DarkCyan
$scpResult = & scp -P $SshPort -r (Join-Path (Get-Location) 'dist\*') "$RemoteUser@$RemoteHost:$RemotePath" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "scp failed:" -ForegroundColor Red; Write-Host $scpResult; Pop-Location; exit 1
}

Write-Host "Files uploaded. Reloading nginx on remote host (may require sudo)." -ForegroundColor Cyan
$sshCmd = "ssh -p $SshPort $RemoteUser@$RemoteHost 'sudo systemctl reload nginx || sudo service nginx reload'"
Write-Host "Running: $sshCmd" -ForegroundColor DarkCyan
$sshResult = & ssh -p $SshPort "$RemoteUser@$RemoteHost" "sudo systemctl reload nginx || sudo service nginx reload" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "Remote reload failed. You may need to run reload manually or check sudoers." -ForegroundColor Yellow
  Write-Host $sshResult
} else {
  Write-Host "nginx reloaded successfully." -ForegroundColor Green
}

Pop-Location
Write-Host "Deploy finished." -ForegroundColor Green
