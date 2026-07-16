/*
  App Service module
  ──────────────────
  Provisions:
    - App Service Plan (Linux, B1 dev / B2 prod)
    - Backend App Service  (FastAPI, Python 3.11)
    - Frontend App Service (Next.js, Node 20)

  Both apps get system-assigned managed identities so they can authenticate
  to Key Vault without storing credentials anywhere.

  App settings wire up all env vars the application expects from config.py.
  In prod, swap plain-text values for Key Vault references:
    @Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/<name>/)
*/

param planName string
param backendAppName string
param frontendAppName string
param location string

@allowed(['dev', 'prod'])
param environment string

// Azure OpenAI config
param openaiEndpoint string
param openaiChatDeployment string
param openaiEmbeddingDeployment string

// PostgreSQL config — credentials fetched from Key Vault at runtime, not embedded here
param sqlServerFqdn string
param sqlAdminUser string
param sqlDatabaseName string

param keyVaultName string

// SKU by environment
var planSku = environment == 'prod'
  ? { name: 'B2', tier: 'Basic', size: 'B2', family: 'B', capacity: 1 }
  : { name: 'B1', tier: 'Basic', size: 'B1', family: 'B', capacity: 1 }

// ── App Service Plan ──────────────────────────────────────────────────────────

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: planSku
  properties: {
    reserved: true    // required for Linux
  }
}

// ── Backend App Service (FastAPI / Python) ────────────────────────────────────

resource backendApp 'Microsoft.Web/sites@2023-01-01' = {
  name: backendAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: environment == 'prod'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        // OpenAI — key is set manually after deploy via Key Vault or az CLI
        // Run: az keyvault secret set --vault-name <kv> --name AZURE-OPENAI-API-KEY --value <key>
        // Then update this setting to: @Microsoft.KeyVault(SecretUri=https://<kv>.vault.azure.net/secrets/AZURE-OPENAI-API-KEY/)
        { name: 'AZURE_OPENAI_API_KEY',              value: 'SET-FROM-KEYVAULT-AFTER-DEPLOY' }
        { name: 'AZURE_OPENAI_ENDPOINT',             value: openaiEndpoint }
        { name: 'AZURE_OPENAI_API_VERSION',          value: '2024-02-01' }
        { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT',      value: openaiChatDeployment }
        { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: openaiEmbeddingDeployment }
        // SQL — password set manually after deploy via Key Vault
        { name: 'AZURE_SQL_SERVER',                  value: sqlServerFqdn }
        { name: 'AZURE_SQL_DATABASE',                value: sqlDatabaseName }
        { name: 'AZURE_SQL_USER',                    value: sqlAdminUser }
        { name: 'AZURE_SQL_PASSWORD',                value: 'SET-FROM-KEYVAULT-AFTER-DEPLOY' }
        { name: 'CHROMA_PATH',                       value: '/home/site/chroma_db' }
        { name: 'CHROMA_COLLECTION',                 value: 'term_sheets' }
        { name: 'ALLOWED_ORIGINS',                   value: 'https://${frontendAppName}.azurewebsites.net' }
        { name: 'LOG_LEVEL',                         value: environment == 'prod' ? 'WARNING' : 'INFO' }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT',    value: 'true' }
        { name: 'WEBSITE_RUN_FROM_PACKAGE',          value: '0' }
      ]
      appCommandLine: 'uvicorn backend.main:app --host 0.0.0.0 --port 8000'
    }
  }
}

// ── Frontend App Service (Next.js / Node) ─────────────────────────────────────

resource frontendApp 'Microsoft.Web/sites@2023-01-01' = {
  name: frontendAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'NODE|20-lts'
      alwaysOn: environment == 'prod'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'NEXT_PUBLIC_API_URL',            value: 'https://${backendAppName}.azurewebsites.net' }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
        { name: 'WEBSITE_RUN_FROM_PACKAGE',       value: '0' }
      ]
    }
  }
}

// ── Key Vault RBAC: grant both apps "Key Vault Secrets User" ─────────────────
// Role definition ID for "Key Vault Secrets User" (read secrets)
var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource kvRoleBackend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultName, backendApp.name, kvSecretsUserRoleId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource kvRoleFrontend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultName, frontendApp.name, kvSecretsUserRoleId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: frontendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

output backendUrl string = 'https://${backendApp.properties.defaultHostName}'
output frontendUrl string = 'https://${frontendApp.properties.defaultHostName}'
output backendPrincipalId string = backendApp.identity.principalId
output frontendPrincipalId string = frontendApp.identity.principalId
