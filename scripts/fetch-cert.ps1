#Requires -Version 5.1
<#
.SYNOPSIS
    Downloads the public *.local-ip.sh TLS certificate pair into certs/.
.DESCRIPTION
    local-ip.sh publishes a Let's Encrypt wildcard certificate AND its private key so that
    LAN devices get a publicly trusted HTTPS origin with nothing to install client-side.
    The key is public, so this provides secure-context eligibility, not confidentiality.
    The certificate expires like any Let's Encrypt cert: re-run this every couple of months.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$certDir = Join-Path $PSScriptRoot '..\certs'
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

foreach ($name in @('server.pem', 'server.key')) {
    $target = Join-Path $certDir $name
    Write-Host "Downloading $name..."
    Invoke-WebRequest -Uri "https://local-ip.sh/$name" -OutFile $target -UseBasicParsing
}

Write-Host "Certificate written to $((Resolve-Path $certDir).Path)" -ForegroundColor Green

$lanIp = Get-NetIPConfiguration |
Where-Object { $null -ne $_.IPv4DefaultGateway } |
ForEach-Object { $_.IPv4Address.IPAddress } |
Select-Object -First 1

if (-not $lanIp) {
    Write-Warning 'Could not determine the LAN IP. Find it with ipconfig and dash-substitute it manually.'
    return
}

# The wildcard is not recursive, so only the dashed single-label form validates.
$label = $lanIp -replace '\.', '-'
Write-Host ''
Write-Host "LAN IP:   $lanIp"
Write-Host "Hostname: $label.local-ip.sh"
Write-Host "Open on the phone: https://$label.local-ip.sh:8443" -ForegroundColor Cyan
