# Run several swarm configurations in parallel. Each line: name|args. Output goes to logs\<name>-<line>.log.
param([string]$Spec)
$env:Path = [Environment]::GetEnvironmentVariable('Path','User') + ';' + [Environment]::GetEnvironmentVariable('Path','Machine')
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force logs | Out-Null
$lines = @(Get-Content $Spec | Where-Object { $_.Trim() -and -not $_.StartsWith('#') })
$tag = [IO.Path]::GetFileNameWithoutExtension($Spec)
$procs = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $name, $rest = $lines[$i].Split('|', 2)
    $argList = "run python run.py --name $name $rest"
    $procs += Start-Process -FilePath uv -ArgumentList $argList -NoNewWindow -PassThru `
        -RedirectStandardOutput "logs\$name-$tag-$i.log" -RedirectStandardError "logs\$name-$tag-$i.err"
}
$procs | Wait-Process
for ($i = 0; $i -lt $lines.Count; $i++) {
    $name = $lines[$i].Split('|', 2)[0]
    Get-Content "logs\$name-$tag-$i.log"
    Get-Content "logs\$name-$tag-$i.err" -ErrorAction SilentlyContinue | Select-String -Pattern 'Error|Traceback' | Select-Object -Last 3
}
