/*
  Azure OpenAI module
  ───────────────────
  Provisions:
    - Azure OpenAI account (S0, the only available SKU)
    - Chat model deployment  (gpt-4.1 / Standard)
    - Embedding deployment   (text-embedding-3-small)

  Capacity is in thousands of tokens per minute (TPM).
  Dev: lower capacity to control costs.
  Prod: higher capacity for throughput.

  gpt-4.1 (2025-04-14) is deployable via classic CognitiveServices resource.
  Retirement: October 2027. Upgrade path: switch to gpt-5.x via Foundry later.
*/

param name string
param location string
param chatDeploymentName string
param embeddingDeploymentName string

@allowed(['dev', 'prod'])
param environment string

// TPM capacity by environment
var chatCapacity = environment == 'prod' ? 80 : 30
var embeddingCapacity = environment == 'prod' ? 120 : 60

// ── Azure OpenAI Account ───────────────────────────────────────────────────────

resource openAIAccount 'Microsoft.CognitiveServices/accounts@2026-03-15-preview' = {
  name: name
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// ── Chat Model Deployment (gpt-5.4 GlobalStandard) ───────────────────────────

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-03-15-preview' = {
  parent: openAIAccount
  name: chatDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: chatCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.4'
      version: '2026-03-05'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

// ── Embedding Deployment (text-embedding-3-small) ─────────────────────────────

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-03-15-preview' = {
  parent: openAIAccount
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: embeddingCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
  dependsOn: [chatDeployment]   // deploy sequentially to avoid capacity conflicts
}

// ── Outputs ───────────────────────────────────────────────────────────────────

@description('Azure OpenAI endpoint — paste into AZURE_OPENAI_ENDPOINT')
output endpoint string = openAIAccount.properties.endpoint

// API key is intentionally NOT output here — fetch it post-deploy via:
//   az cognitiveservices account keys list --name <account> --resource-group <rg> --query key1 -o tsv

output accountName string = openAIAccount.name
output accountId string = openAIAccount.id
