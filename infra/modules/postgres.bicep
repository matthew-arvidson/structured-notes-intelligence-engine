/*
  Azure Database for PostgreSQL Flexible Server module
  -----------------------------------------------------
  Provisions:
    - PostgreSQL Flexible Server (Burstable B1ms for dev, GeneralPurpose D2s for prod)
    - Database
    - Firewall rule: allow Azure services (App Service -> Postgres)
    - Firewall rule: allow developer machine IP (for local dev access)

  Why PostgreSQL over Azure SQL:
    - No regional provisioning restrictions on standard subscriptions
    - Matches local dev environment (no ODBC driver required)
    - Lower cost at dev tier (B1ms ~$12/mo vs SQL Basic ~$5/mo but no region issues)
    - SQLAlchemy uses psycopg2 — simpler connection string
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
var serverSku = environment == 'prod'
  ? { name: 'Standard_D2s_v3', tier: 'GeneralPurpose' }
  : { name: 'Standard_B1ms',   tier: 'Burstable' }

var storageSizeGB = environment == 'prod' ? 128 : 32
var backupDays    = environment == 'prod' ? 14  : 7

// ── PostgreSQL Flexible Server ────────────────────────────────────────────────

resource pgServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: serverName
  location: location
  sku: serverSku
  properties: {
    administratorLogin: adminUser
    administratorLoginPassword: adminPassword
    version: '16'
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: backupDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// ── Database ──────────────────────────────────────────────────────────────────

resource pgDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2022-12-01' = {
  parent: pgServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ── Firewall: allow Azure services (App Service, etc.) ────────────────────────

resource firewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2022-12-01' = {
  parent: pgServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ── Firewall: allow developer machine ─────────────────────────────────────────

resource firewallDeveloper 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2022-12-01' = if (developerIpAddress != '0.0.0.0') {
  parent: pgServer
  name: 'AllowDeveloperMachine'
  properties: {
    startIpAddress: developerIpAddress
    endIpAddress: developerIpAddress
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

@description('PostgreSQL server FQDN — paste into AZURE_PG_HOST in .env')
output serverFqdn string = pgServer.properties.fullyQualifiedDomainName

output serverName string = pgServer.name
output databaseName string = pgDatabase.name
