using '../main.bicep'

// sqlAdminPassword is intentionally omitted here — it is passed at deploy time via:
//   .\infra\deploy.ps1 -SqlPassword "YourPassword"
// Never store passwords in .bicepparam files — they get committed to source control.
// The BCP258 warning from the Bicep extension is expected and harmless.

// --- Dev environment parameters ---
// Cheap SKUs — destroy and recreate freely.
// SQL: Basic (5 DTU, 2 GB) | App Service: B1 (1 core, 1.75 GB RAM)

param environment = 'dev'
param location = 'eastus'
param projectName = 'snie'
param chatModelName = 'gpt-4o'
param embeddingModelName = 'text-embedding-3-small'
param sqlAdminUser = 'sniadmin'

// developerIpAddress: set to your machine's public IP so you can connect to SQL locally.
// Get it from: https://whatismyip.com  or run: Invoke-RestMethod https://api.ipify.org
// Leave as '0.0.0.0' to skip the developer firewall rule.
param developerIpAddress = '173.92.140.182'

// sqlAdminPassword is NOT set here — pass it on the command line:
//   --parameters sqlAdminPassword="YourSecurePassword123!"
// Requirements: 8+ chars, uppercase, lowercase, number, special char
