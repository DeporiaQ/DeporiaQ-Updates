param(
    [Parameter(Mandatory=$true)][string]$AppPath,
    [Parameter(Mandatory=$true)][string]$Version,
    [int]$SetupProcessId = 0
)
$ErrorActionPreference = 'Stop'
$logDir = Join-Path $env:LOCALAPPDATA 'DeporiaQ\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'relaunch.log'
function Write-LaunchLog([string]$Message) {
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format o) $Message" -Encoding UTF8
}
try {
    if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt 2000000) {
        Move-Item -LiteralPath $log -Destination "$log.previous" -Force
    }
    Write-LaunchLog "Waiting for Setup PID=$SetupProcessId; expected version=$Version"
    # The helper is outside the frozen updater and waits until Setup releases files.
    if ($SetupProcessId -gt 0) {
        $setupDeadline = (Get-Date).AddSeconds(180)
        while (Get-Process -Id $SetupProcessId -ErrorAction SilentlyContinue) {
            if ((Get-Date) -gt $setupDeadline) { throw 'Installer did not exit within 180 seconds.' }
            Start-Sleep -Milliseconds 400
        }
    }
    if (-not (Test-Path -LiteralPath $AppPath -PathType Leaf)) { throw 'Installed application was not found.' }
    Get-ChildItem Env: | Where-Object { $_.Name -like '_PYI*' -or $_.Name -eq '_MEIPASS2' } | ForEach-Object {
        [Environment]::SetEnvironmentVariable($_.Name,$null,'Process')
    }
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    # Never retry a live process: a slow startup must not create duplicate windows.
    for ($attempt=1; $attempt -le 2; $attempt++) {
        $token = [Guid]::NewGuid().ToString('N')
        $receipt = Join-Path $logDir "ready-$token.json"
        Write-LaunchLog "Starting attempt=$attempt token=$token"
        $process = Start-Process -FilePath $AppPath -WorkingDirectory (Split-Path -Parent $AppPath) -ArgumentList @('--after-update',$token) -PassThru
        $deadline = (Get-Date).AddSeconds(120)
        while ((Get-Date) -lt $deadline) {
            if (Test-Path -LiteralPath $receipt) {
                $ready = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
                if ($ready.version -ne $Version) { throw "Wrong running version: $($ready.version)" }
                Write-LaunchLog "READY version=$($ready.version) pid=$($ready.pid) attempt=$attempt"
                Remove-Item -LiteralPath $receipt -Force
                exit 0
            }
            $process.Refresh()
            if ($process.HasExited) { break }
            Start-Sleep -Milliseconds 400
        }
        $process.Refresh()
        if (-not $process.HasExited) { throw 'Application is running but did not confirm its window. No duplicate was started.' }
        Write-LaunchLog "Application exited before readiness; code=$($process.ExitCode)"
        Start-Sleep -Seconds 2
    }
    throw 'Application exited before opening its window on both attempts.'
} catch {
    Write-LaunchLog "ERROR $($_.Exception.Message)"
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show("DeporiaQ güncellendi fakat pencerenin açıldığı doğrulanamadı. Masaüstü kısayolunu deneyin. Destek için $logDir klasöründeki relaunch.log ve startup.log dosyalarını deporiaq@gmail.com adresine iletebilirsiniz.", 'DeporiaQ - Açılış kontrolü') | Out-Null
    exit 1
}
