/*
  Azure SQL module
  ────────────────
  Provisions:
    - SQL Server (with admin credentials passed securely at deploy time)
    - SQL Database (Basic tier for dev, Standard S1 for prod)
    - Firewall rule: allow Azure services (App Service → SQL)
    - Firewall rule: allow developer machine IP (optional, for local dev access)

  The admin password is passed as a @secure() param — it is never stored in
  the Bicep template or deployment history in plain text.
*/

param serverName string
param databaseName string
param location string
param adminUser string

@secure()
param adminPassword string

param developerIpAddress string = '0.0.0.0'

@allowed(['dev', 'prod'])
param environment string

// SKU by environment
var dbSku = environment == 'prod'
  ? { name: 'S1', tier: 'Standard', capacity: 20 }
  : { name: 'Basic', tier: 'Basic', capacity: 5 }

// ── SQL Server ────────────────────────────────────────────────────────────────

resource sqlServer 'Microsoft.Sql/servers@2022-11-01-preview' = {
  name: serverName
  location: location
  properties: {
    administratorLogin: adminUser
    administratorLoginPassword: adminPassword
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: '1.2'
  }
}

// ── SQL Database ──────────────────────────────────────────────────────────────

resource sqlDatabase 'Microsoft.Sql/servers/databases@2022-11-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  sku: dbSku
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: environment == 'prod' ? 268435456000 : 2147483648  // 250 GB prod, 2 GB dev
    zoneRedundant: false
  }
}

// ── Firewall: allow Azure services (App Service, etc.) ────────────────────────

resource firewallAzure 'Microsoft.Sql/servers/firewallRules@2022-11-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ── Firewall: allow developer machine ─────────────────────────────────────────
// Set developerIpAddress to your machine's public IP so local dev can connect.
// Leave as '0.0.0.0' to skip (no dev machine rule).

resource firewallDeveloper 'Microsoft.Sql/servers/firewallRules@2022-11-01-preview' = if (developerIpAddress != '0.0.0.0') {
  parent: sqlServer
  name: 'AllowDeveloperMachine'
  properties: {
    startIpAddress: developerIpAddress
    endIpAddress: developerIpAddress
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

@description('SQL Server fully qualified domain name — paste into AZURE_SQL_SERVER')
output serverFqdn string = sqlServer.properties.fullyQualifiedDomainName

output serverName string = sqlServer.name
output databaseName string = sqlDatabase.name

// Connection string is intentionally NOT output here — it contains the password.
// The deploy script builds it from the server FQDN + the password you passed on the command line.
