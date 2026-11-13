# Chạy toàn bộ kiểm thử QA: kiểm tra phía host (docker compose config, import ZIP dashboard) rồi kiểm thử trình duyệt
# (scripts/qa_check.py trong service screenshots). Kết quả: evidence/qa_test_cases.md, evidence/qa_results.json.
#   powershell -ExecutionPolicy Bypass -File scripts\qa_run.ps1
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

docker compose config -q 2>$null
$cfg1 = $LASTEXITCODE
docker compose --profile tools --profile screenshots config -q 2>$null
$cfg2 = $LASTEXITCODE
$services = @(docker compose --profile tools --profile screenshots config --services 2>$null)

# Import ZIP (overwrite) trước kiểm thử trình duyệt: các ca dashboard chạy trên bản vừa import.
$out = (docker compose run --rm tools python superset/import_dashboard.py 2>&1 | ForEach-Object { "$_" }) -join "`n"
$impExit = $LASTEXITCODE
$impLine = ($out -split "`n" | Where-Object { $_ -match '^\d{3} ' } | Select-Object -First 1)

$host_checks = [ordered]@{
    compose_config = [ordered]@{ exit = $cfg1; exit_all_profiles = $cfg2 }
    services = $services
    import = [ordered]@{ exit = $impExit; output = "$impLine" }
}
$json = $host_checks | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText((Join-Path (Get-Location) "evidence\qa_host_checks.json"), $json, (New-Object Text.UTF8Encoding $false))
Write-Host "docker compose config: $cfg1 / $cfg2; services: $($services -join ', '); import: exit=$impExit $impLine"

docker compose run --rm screenshots python scripts/qa_check.py
