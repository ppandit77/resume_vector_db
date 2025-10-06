Param(
    [string]$DotEnvPath = ".env",
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Load-DotEnv {
    Param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        if ($line.StartsWith('#')) { return }

        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }

        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()

        if ($val.StartsWith('"') -and $val.EndsWith('"')) {
            $val = $val.Substring(1, $val.Length - 2)
        } elseif ($val.StartsWith('\'') -and $val.EndsWith('\'')) {
            $val = $val.Substring(1, $val.Length - 2)
        }

        if (-not [string]::IsNullOrWhiteSpace($key)) {
            $env:$key = $val
        }
    }
}

Write-Host "[MCP] Loading environment from $DotEnvPath if present..."
Load-DotEnv -Path $DotEnvPath

function Get-FirstNonEmpty {
    Param([string[]]$Values)
    foreach ($v in $Values) {
        if ($null -ne $v -and -not [string]::IsNullOrWhiteSpace($v)) { return $v }
    }
    return $null
}

$candidateVars = @(
    'MONGODB_URI',
    'MONGO_URI',
    'MONGO_URL',
    'ATLAS_URI',
    'MONGODB_CONNECTION_STRING',
    'DB_URI'
)

$resolvedValues = @()
foreach ($name in $candidateVars) {
    $resolvedValues += $env:$name
}

$connectionString = Get-FirstNonEmpty -Values $resolvedValues
$usedVarName = $null
if ($connectionString) {
    for ($i = 0; $i -lt $candidateVars.Count; $i++) {
        if ($resolvedValues[$i] -eq $connectionString) {
            $usedVarName = $candidateVars[$i]
            break
        }
    }
}

if ([string]::IsNullOrWhiteSpace($connectionString)) {
    Write-Error "No MongoDB connection string found in env. Tried: $($candidateVars -join ', '). Set one of these in your .env."
    exit 1
}

$readOnly = $true
if ($env:MDB_MCP_READ_ONLY) {
    $parsed = $null
    if ([bool]::TryParse($env:MDB_MCP_READ_ONLY, [ref]$parsed)) {
        $readOnly = $parsed
    } elseif ($env:MDB_MCP_READ_ONLY -eq '0') {
        $readOnly = $false
    }
}

$transport = $env:MDB_MCP_TRANSPORT # e.g. 'http' if you explicitly need HTTP transport

$mask = {
    Param([string]$uri)
    if ([string]::IsNullOrWhiteSpace($uri)) { return $uri }
    # Mask credentials between '//' and '@'
    $start = $uri.IndexOf('//')
    $at = $uri.IndexOf('@')
    if ($start -ge 0 -and $at -gt $start) {
        $prefix = $uri.Substring(0, $start + 2)
        $suffix = $uri.Substring($at)
        return "$prefix***:$***$suffix"
    }
    return $uri
}

$masked = & $mask $connectionString
Write-Host "[MCP] Using env var: $usedVarName"
Write-Host "[MCP] ConnectionString (masked): $masked"
Write-Host "[MCP] readOnly=$readOnly transport=$transport"

if ($CheckOnly) {
    Write-Host "[MCP] Check-only mode: not starting mongodb-mcp-server."
    exit 0
}

$args = @('mongodb-mcp-server', '--connectionString', $connectionString)
if ($readOnly) { $args += '--readOnly' }
if (-not [string]::IsNullOrWhiteSpace($transport)) { $args += @('--transport', $transport) }

Write-Host "[MCP] Starting MongoDB MCP via npx with readOnly=$readOnly transport=$transport"
Write-Host "[MCP] Command: npx -y $($args -join ' ')" 

& npx -y @args

if ($LASTEXITCODE -ne 0) {
    Write-Error "mongodb-mcp-server exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

