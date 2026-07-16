using '../main.bicep'

// sqlAdminPassword is intentionally omitted here — it is passed at deploy time via:
//   .\infra\deploy.ps1 -Environment prod -SqlPassword "YourPassword"
// Never store passwords in .bicepparam files — they get committed to source control.
// The BCP258 warning from the Bicep extension is expected and harmless.

// --- Prod environment parameters ---
// Better SKUs — keep running, treat as persistent.
// SQL: Standard S1 (20 DTU, 250 GB) | App Service: B2 (2 cores, 3.5 GB RAM)

param environment = 'prod'
param location = 'eastus'
param projectName = 'snie'
param chatModelName = 'gpt-4o'
param embeddingModelName = 'text-embedding-3-small'
param sqlAdminUser = 'sniadmin'

// In prod, no developer IP rule — access goes through App Service only.
param developerIpAddress = '0.0.0.0'

// sqlAdminPassword is NOT set here — pass it on the command line:
//   --parameters sqlAdminPassword="YourSecurePassword123!"
// In prod, also set this in Key Vault after deploy:
//   az keyvault secret set --vault-name <kv-name> --name AZURE-SQL-PASSWORD --value "YourSecurePassword123!"
