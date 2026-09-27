#Requires -Version 5.1
<#
.SYNOPSIS
    Builds and starts Cards on the LAN over local-ip.sh HTTPS, then prints the URL to open on phones.
.DESCRIPTION
    For local development and home use. Production deployments use docker-compose.yml alone.
#>
[CmdletBinding()]
param(
    [int]$Port = 443,
    [switch]$Detach
)

$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')

function Test-PrivateIPv4 {
    param([string]$Address)
    $o = $Address.Split('.') | ForEach-Object { [int]$_ }
    return ($o[0] -eq 10) -or
           ($o[0] -eq 192 -and $o[1] -eq 168) -or
           ($o[0] -eq 172 -and $o[1] -ge 16 -and $o[1] -le 31)
}

try {
    docker version --format '{{.Server.Version}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker is not running. Start Docker Desktop and retry.' }

    $lanIp = Get-NetIPConfiguration |
        Where-Object { $null -ne $_.IPv4DefaultGateway } |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        Where-Object { Test-PrivateIPv4 $_ } |
        Select-Object -First 1

    if (-not $lanIp) {
        $found = (Get-NetIPConfiguration |
            Where-Object { $null -ne $_.IPv4DefaultGateway } |
            ForEach-Object { $_.IPv4Address.IPAddress }) -join ', '
        throw @"
No private (RFC1918) address found. Routable addresses seen: $found

This host is not behind NAT, so publishing the port would expose this
unauthenticated service to the internet. Refusing to start.

On an ISP router, check the PC is not plugged into the bridged IPTV
passthrough port; move it to a normal LAN port and retry.
"@
    }

    # The *.local-ip.sh wildcard is not recursive, so only the dashed single label validates.
    $label = $lanIp -replace '\.', '-'
    # Chrome only defaults to https:// when the typed address carries no port.
    $url = if ($Port -eq 443) { "https://$label.local-ip.sh" } else { "https://$label.local-ip.sh:$Port" }
    Write-Host ''
    Write-Host "  Binding to $lanIp only." -ForegroundColor DarkGray
    Write-Host '  Open this on any phone on the network:' -ForegroundColor Green
    Write-Host "  $url" -ForegroundColor Cyan
    Write-Host ''

    $env:CARDS_BIND_IP = $lanIp
    $env:CARDS_PORT = $Port
    $composeArgs = @('compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.local.yml', 'up', '--build')
    if ($Detach) { $composeArgs += '--detach' }
    docker @composeArgs
}
finally {
    Pop-Location
}
