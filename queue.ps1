# Run spec lines (name|args, one run each) from a queue file, at most -Max at a time, in order.
# Logs to logs\queue-<name>-<i>.log. Re-running a line replays its cached model calls with no new cost.
param([string]$Spec, [int]$Max = 8)
$env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
$env:PYTHONIOENCODING = 'utf-8'
$env:UV_CACHE_DIR = 'D:\ml-cache\uv'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force logs | Out-Null
$lines = @(Get-Content $Spec | Where-Object { $_.Trim() -and -not $_.StartsWith('#') })
$running = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $name, $rest = $lines[$i].Split('|', 2)
    while (@($running | Where-Object { -not $_.HasExited }).Count -ge $Max) { Start-Sleep -Seconds 5 }
    $p = Start-Process -FilePath uv -ArgumentList "run python run.py --name $name $rest" -NoNewWindow -PassThru `
        -RedirectStandardOutput "logs\queue-$name-$i.log" -RedirectStandardError "logs\queue-$name-$i.err"
    $running += $p
    "{0} started [{1}/{2}] {3} {4}" -f (Get-Date -Format HH:mm), ($i + 1), $lines.Count, $name, $rest
}
$running | Wait-Process
"{0} queue finished" -f (Get-Date -Format HH:mm)
