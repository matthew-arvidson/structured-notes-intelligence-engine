/*
  Structured Notes Intelligence Engine — Azure Infrastructure
  ============================================================
  Top-level deployment. Orchestrates all modules and outputs the
  values needed to populate .env.

  Deploy (dev):
    az group create --name rg-snie-dev --location eastus
    az deployment group create \
      --resource-group rg-snie-dev \
      --template-file infra/main.bicep \
      --parameters infra/params/dev.bicepparam \
      --parameters sqlAdminPassword="YourSecurePassword123!"

  Deploy (prod):
    az group create --name rg-snie-prod --location eastus
    az deployment group create \
      --resource-group rg-snie-prod \
      --template-file infra/main.bicep \
      --parameters infra/params/prod.bicepparam \
      --parameters sqlAdminPassword="YourSecurePassword123!"

  After deploy, copy outputs into .env:
    az deployment group show \
      --resource-group rg-snie-dev \
      --name main \
      --query properties.outputs
*/

@description('Environment name — used to select SKUs and name resources.')
@allowed(['dev', 'prod'])
param environment string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Short name used in all resource names. Keep to 8 chars max.')
@maxLength(8)
param projectName string = 'snie'

@description('Azure OpenAI chat model deployment name.')
param chatModelName string = 'gpt-5.4'

@description('Azure OpenAI embedding model deployment name.')
param embeddingModelName string = 'text-embedding-3-small'

@description('PostgreSQL administrator username.')
param sqlAdminUser string = 'sniadmin'

@description('PostgreSQL administrator password. Pass via --parameters at deploy time — never hardcode.')
@secure()
param sqlAdminPassword string

@description('Your local IP address for SQL firewall (allows dev machine access). Get it from https://whatismyip.com')
param developerIpAddress string = '0.0.0.0'

@description('Deploy App Service resources. Set to false for local-only dev (avoids VM quota requirement).')
param deployAppService bool = false

// ── Name tokens ───────────────────────────────────────────────────────────────
// uniqueString produces a deterministic 13-char hash from the resource group id.
// This ensures globally unique names without manual coordination.
var suffix = uniqueString(resourceGroup().id)
var shortSuffix = take(suffix, 6)

var names = {
  openai: 'oai-${projectName}-${environment}-${shortSuffix}'
  pgServer: 'pg-${projectName}-${environment}-${shortSuffix}'
  pgDatabase: 'pgdb-${projectName}-${environment}'
  appServicePlan: 'asp-${projectName}-${environment}'
  backendApp: 'app-${projectName}-api-${environment}-${shortSuffix}'
  frontendApp: 'app-${projectName}-web-${environment}-${shortSuffix}'
  keyVault: 'kv-${projectName}-${environment}-${shortSuffix}'
}

// ── Modules ───────────────────────────────────────────────────────────────────

module openai 'modules/openai.bicep' = {
  name: 'openai-deploy'
  params: {
    name: names.openai
    location: location
    chatDeploymentName: chatModelName
    embeddingDeploymentName: embeddingModelName
    environment: environment
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres-deploy'
  params: {
    serverName: names.pgServer
    databaseName: names.pgDatabase
    location: location
    adminUser: sqlAdminUser
    adminPassword: sqlAdminPassword
    developerIpAddress: developerIpAddress
    environment: environment
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-deploy'
  params: {
    name: names.keyVault
    location: location
    environment: environment
  }
}

module appService 'modules/app-service.bicep' = if (deployAppService) {
  name: 'appservice-deploy'
  params: {
    planName: names.appServicePlan
    backendAppName: names.backendApp
    frontendAppName: names.frontendApp
    location: location
    environment: environment
    openaiEndpoint: openai.outputs.endpoint
    openaiChatDeployment: chatModelName
    openaiEmbeddingDeployment: embeddingModelName
    sqlServerFqdn: postgres.outputs.serverFqdn
    sqlAdminUser: sqlAdminUser
    sqlDatabaseName: names.pgDatabase
    keyVaultName: names.keyVault
  }
}

// ── Outputs — copy these into .env ────────────────────────────────────────────

@description('Paste into AZURE_OPENAI_ENDPOINT in .env')
output openaiEndpoint string = openai.outputs.endpoint

@description('Paste into AZURE_OPENAI_CHAT_DEPLOYMENT in .env')
output chatDeploymentName string = chatModelName

@description('Paste into AZURE_OPENAI_EMBEDDING_DEPLOYMENT in .env')
output embeddingDeploymentName string = embeddingModelName

@description('Backend App Service URL (empty if deployAppService is false)')
output backendUrl string = deployAppService ? appService.outputs.backendUrl : 'localhost:3001 (run locally)'

@description('Frontend App Service URL (empty if deployAppService is false)')
output frontendUrl string = deployAppService ? appService.outputs.frontendUrl : 'localhost:3000 (run locally)'

@description('PostgreSQL server FQDN — use in AZURE_PG_HOST in .env')
output sqlServerFqdn string = postgres.outputs.serverFqdn

@description('PostgreSQL database name — use in AZURE_PG_DATABASE in .env')
output sqlDatabaseName string = names.pgDatabase

@description('Key Vault URI — use for secret references in prod')
output keyVaultUri string = keyVault.outputs.uri

@description('SQL admin username — use in AZURE_SQL_USER in .env')
output sqlAdminUser string = sqlAdminUser
