param(
    [int]$Port = 5174,
    [switch]$UseVite
)

# Simple static file server for frontend_temp using Python's http.server
# Usage: .\run_dev_server.ps1 -Port 5174

$cwd = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $cwd

$frontendPath = Join-Path $cwd '..\frontend_temp' | Resolve-Path
function Test-PortFree($p) {
    $out = netstat -ano | findstr ":$p "
    return -not [string]::IsNullOrEmpty($out) -and $false
}

# Try requested port, otherwise find free port in range
Write-Output "Attempting to serve $frontendPath"
$chosen = $null
try {
    $list = netstat -ano | Select-String ":$Port\b"
    if ($list) {
        Write-Output "Port $Port appears in use. Searching for free port..."
    } else {
        $chosen = $Port
    }
} catch {
    $chosen = $Port
}

if (-not $chosen) {
    for ($p = $Port; $p -lt $Port + 50; $p++) {
        $r = netstat -ano | Select-String ":$p\b"
        if (-not $r) { $chosen = $p; break }
    }
}

if (-not $chosen) { Write-Output "No free port found in range $Port..$($Port+49). Aborting."; exit 1 }

Write-Output "Serving on chosen port: $chosen"

# If a built dist exists, serve it (demo mode)
$distPath = Join-Path $cwd 'dist'
if (Test-Path $distPath) {
    Write-Output "Found dist/ directory; serving built demo from $distPath"
    if ($UseVite) {
        Write-Output "Starting Vite preview bound to 127.0.0.1:$chosen"
        $viteArgs = @('vite','preview','--host','127.0.0.1','--port',"$chosen")
        $proc = Start-Process -FilePath 'npx' -ArgumentList $viteArgs -PassThru
    } else {
        $args = @('-m','http.server', "$chosen", '--directory', "$distPath")
        Write-Output "Starting python http.server for dist with Args: $args"
        $proc = Start-Process -FilePath 'python' -ArgumentList $args -PassThru
    }
} else {
    if ($UseVite) {
        Write-Output "Attempting to start Vite dev server bound to 127.0.0.1:$chosen"
        $viteArgs = @('vite','--host','127.0.0.1','--port',"$chosen")
        $proc = Start-Process -FilePath 'npx' -ArgumentList $viteArgs -PassThru
    } else {
        # Start python http.server in background on chosen port
        $args = @('-m','http.server', "$chosen", '--directory', "$frontendPath")
        Write-Output "Starting dev server with Start-Process. Args: $args"
        $proc = Start-Process -FilePath 'python' -ArgumentList $args -PassThru
    }
}
Start-Sleep -Seconds 1
if ($proc -and -not $proc.HasExited) {
    Write-Output "Dev server started (PID: $($proc.Id)) on port $chosen"
    Write-Output "To stop: Stop-Process -Id $($proc.Id)"
} else {
    Write-Output "Failed to start dev server. Check python availability and port conflicts."
}
