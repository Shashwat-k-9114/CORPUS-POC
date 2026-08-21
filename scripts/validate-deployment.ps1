[CmdletBinding()]
param([string]$ApiUrl = "http://127.0.0.1:8000")

$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod "$ApiUrl/health"
$ready = Invoke-RestMethod "$ApiUrl/ready"
Write-Output (@{ health = $health.status; ready = $ready.status } | ConvertTo-Json -Compress)
