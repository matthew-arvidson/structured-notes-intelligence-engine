<#
.SYNOPSIS
    Deploy the Structured Notes Intelligence Engine infrastructure to Azure.

.DESCRIPTION
    Creates the resource group if it does not exist, runs a Bicep what-if preview,
    then deploys on confirmation. Prints all values needed for .env at the end.

.PARAMETER Environment
    Target environment: 'dev' or 'prod'. Default: dev.

.PARAMETER SqlPassword
    SQL Server admin password. Required. Must meet Azure complexity requirements:
    8+ chars, uppercase, lowercase, number, and special character.

.PARAMETER DeveloperIp
    Your machine's public IP for SQL firewall. Defaults to auto-detect.
    Get it from: Invoke-RestMethod https://api.ipify.org

.PARAMETER SkipWhatIf
    Skip the what-if preview and deploy immediately.

.EXAMPLE
    # Preview what will be created (no changes)
    .\infra\deploy.ps1 -Environment dev -SqlPassword "MyP@ssw0rd!"

    # Deploy dev environment
    .\infra\deploy.ps1 -Environment dev -SqlPassword "MyP@ssw0rd!" -SkipWhatIf

    # Deploy prod
    .\infra\deploy.ps1 -Environment prod -SqlPassword "MyP@ssw0rd!" -SkipWhatIf
#>

param(
    [ValidateSet('dev', 'prod')]
    [string]$Environment = 'dev',

    [Parameter(Mandatory = $true)]
    [string]$SqlPassword,

    [string]$DeveloperIp = '',

    [switch]$SkipWhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Config ------------------------------------------------------------------
$ResourceGroup  = "rg-snie-$Environment"
$Location       = "eastus"
$DeploymentName = "snie-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmm')"
$TemplateFile   = Join-Path $PSScriptRoot "main.bicep"
$ParamsFile     = Join-Path $PSScriptRoot "params\$Environment.parameters.json"

# --- Auto-detect developer IP (dev only) -------------------------------------
if ($Environment -eq 'dev' -and $DeveloperIp -eq '') {
    try {
        $DeveloperIp = (Invoke-RestMethod -Uri 'https://api.ipify.org').Trim()
        Write-Host "Auto-detected developer IP: $DeveloperIp" -ForegroundColor Cyan
    }
    catch {
        Write-Host "Could not auto-detect IP - SQL developer firewall rule will be skipped." -ForegroundColor Yellow
        $DeveloperIp = '0.0.0.0'
    }
}

# --- Pre-flight checks -------------------------------------------------------
Write-Host ""
Write-Host "=== Structured Notes Intelligence Engine - Bicep Deploy ===" -ForegroundColor Cyan
Write-Host "Environment  : $Environment"
Write-Host "Resource Grp : $ResourceGroup"
Write-Host "Location     : $Location"
Write-Host "Template     : $TemplateFile"
Write-Host "Params       : $ParamsFile"
Write-Host ""

# Verify az CLI is available
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI not found. Install from https://aka.ms/installazurecliwindows and re-run."
}

# Check login status
$accountJson = az account show 2>$null
if (-not $accountJson) {
    Write-Host "Not logged in to Azure. Running az login..." -ForegroundColor Yellow
    az login | Out-Null
}
$account = az account show | ConvertFrom-Json
Write-Host "Logged in as  : $($account.user.name)" -ForegroundColor Green
Write-Host "Subscription  : $($account.name) ($($account.id))"
Write-Host ""

# --- Create resource group if needed -----------------------------------------
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq 'false') {
    Write-Host "Creating resource group '$ResourceGroup' in '$Location'..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location | Out-Null
    Write-Host "Resource group created." -ForegroundColor Green
}
else {
    Write-Host "Resource group '$ResourceGroup' already exists." -ForegroundColor Green
}
Write-Host ""

# --- Build deployment arguments ----------------------------------------------
$deployArgs = @(
    '--resource-group', $ResourceGroup,
    '--template-file', $TemplateFile,
    '--parameters', "@$ParamsFile",
    '--parameters', "sqlAdminPassword=$SqlPassword"
)

if ($DeveloperIp -ne '0.0.0.0') {
    $deployArgs += '--parameters', "developerIpAddress=$DeveloperIp"
}

# --- What-if preview ---------------------------------------------------------
if (-not $SkipWhatIf) {
    Write-Host "Running what-if preview (no changes made yet)..." -ForegroundColor Cyan
    az deployment group what-if @deployArgs
    Write-Host ""
    Write-Host "Review the changes above."
    $confirm = Read-Host "Proceed with deployment? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "Deployment cancelled." -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# --- Deploy ------------------------------------------------------------------
Write-Host "Deploying... (this takes 5-10 minutes)" -ForegroundColor Cyan
$resultJson = az deployment group create `
    @deployArgs `
    --name $DeploymentName `
    --output json

if ($LASTEXITCODE -ne 0) {
    throw "Deployment failed. Check the Azure portal Activity Log for details."
}

$result  = $resultJson | ConvertFrom-Json
$outputs = $result.properties.outputs

Write-Host ""
Write-Host "Deployment succeeded!" -ForegroundColor Green

# --- Fetch the OpenAI API key (not returned in Bicep outputs for security) ---
$openaiAccountName = az resource list `
    --resource-group $ResourceGroup `
    --resource-type "Microsoft.CognitiveServices/accounts" `
    --query "[0].name" `
    --output tsv

$openaiKey = az cognitiveservices account keys list `
    --name $openaiAccountName `
    --resource-group $ResourceGroup `
    --query "key1" `
    --output tsv

# --- Extract outputs ---------------------------------------------------------
$openaiEndpoint      = $outputs.openaiEndpoint.value
$chatDeployment      = $outputs.chatDeploymentName.value
$embeddingDeployment = $outputs.embeddingDeploymentName.value
$sqlServerFqdn       = $outputs.sqlServerFqdn.value
$sqlDatabase         = $outputs.sqlDatabaseName.value
$sqlUser             = $outputs.sqlAdminUser.value
$backendUrl          = $outputs.backendUrl.value
$frontendUrl         = $outputs.frontendUrl.value
$keyVaultUri         = $outputs.keyVaultUri.value

# --- Print .env values -------------------------------------------------------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " Copy the block below into your .env file" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "AZURE_OPENAI_API_KEY=$openaiKey"
Write-Host "AZURE_OPENAI_ENDPOINT=$openaiEndpoint"
Write-Host "AZURE_OPENAI_API_VERSION=2024-02-01"
Write-Host "AZURE_OPENAI_CHAT_DEPLOYMENT=$chatDeployment"
Write-Host "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$embeddingDeployment"
Write-Host ""
Write-Host "AZURE_PG_HOST=$sqlServerFqdn"
Write-Host "AZURE_PG_DATABASE=$sqlDatabase"
Write-Host "AZURE_PG_USER=${sqlUser}"
Write-Host "AZURE_PG_PASSWORD=<paste the -SqlPassword value you used above>"
Write-Host "AZURE_PG_PORT=5432"
Write-Host ""
Write-Host "CHROMA_PATH=./chroma_db"
Write-Host "CHROMA_COLLECTION=term_sheets"
Write-Host ""
Write-Host "ALLOWED_ORIGINS=$frontendUrl"
Write-Host "API_PORT=3001"
Write-Host "LOG_LEVEL=INFO"
Write-Host ""
Write-Host "# Key Vault URI - use for secret references in prod"
Write-Host "# KEY_VAULT_URI=$keyVaultUri"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend URL  : $backendUrl" -ForegroundColor Green
Write-Host "Frontend URL : $frontendUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Paste the block above into your .env file"
Write-Host "  2. pip install -r requirements.txt"
Write-Host "  3. pytest backend/tests/test_flag_risks.py -v"
Write-Host "  4. uvicorn backend.main:app --reload --port 3001"
