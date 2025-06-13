# Azure Resource Dependency Report

**Generated:** 2025-06-13 16:35:12
**Subscription:** 2a0cf760-b...

## 📋 Executive Summary

- **Total Resources:** 33
- **Resource Groups:** 12
- **Confirmed Dependencies:** 9
- **Potential Dependencies:** 15
- **Enhanced Resources:** 8 (with detailed configuration analysis)

## 🏗️ Resource Overview by Type

### ⚡ Logic Apps

- **webhook (workflows)**
  - Location: northcentralus
  - Resource Group: azure-apim-health

### 🌐 Networking

- **NetworkWatcher_canadacentral (networkwatchers)**
  - Location: canadacentral
  - Resource Group: networkwatcherrg

- **NetworkWatcher_eastus (networkwatchers)**
  - Location: eastus
  - Resource Group: networkwatcherrg

### 🌐 Web & App Services

- **app-ojcjiczjudu42-blog (sites)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app
   - Dependencies: 1 confirmed, 2 potential

- **app-ojcjiczjudu42-cms (sites)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app
   - Dependencies: 1 confirmed, 2 potential

- **app-ojcjiczjudu42-stripe (sites)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app
   - Dependencies: 1 confirmed, 2 potential

- **app-web-ojcjiczjudu42 (webpubsub)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app

- **contoso-swa (staticsites)**
  - Location: eastus2
  - Resource Group: sandbox-contoso-rg

- **func-api-ojcjiczjudu42 (sites)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app
   - Dependencies: 1 confirmed, 6 potential

- **plan-ojcjiczjudu42 (serverfarms)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app

- **stapp-web-ojcjiczjudu42 (staticsites)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-network

### 💾 Storage

- **runwhensbxactionstf (storageaccounts)**
  - Location: eastus
  - Resource Group: sandbox

- **sandboxcontosostorage01 (storageaccounts)**
  - Location: eastus
  - Resource Group: sandbox-contoso-rg

- **stojcjiczjudu42 (storageaccounts)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-data

### 📊 Monitoring

- **Application Insights Smart Detection (actiongroups)**
  - Location: global
  - Resource Group: rg-contoso-01-monitoring

- **app-autoscale (autoscalesettings)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app

- **appi-ojcjiczjudu42 (components)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-monitoring
   - Dependencies: 1 confirmed, 0 potential

- **law-sb-health-demo (workspaces)**
  - Location: canadacentral
  - Resource Group: azure-servicebus-health

- **log-ojcjiczjudu42 (workspaces)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-monitoring

- **runwhen-webhooks (actiongroups)**
  - Location: global
  - Resource Group: azure-apim-health

- **sb-deadletter-alert (metricalerts)**
  - Location: global
  - Resource Group: azure-servicebus-health
   - Dependencies: 1 confirmed, 0 potential

### 📦 Container Apps

- **app-api-ojcjiczjudu42 (containerapps)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app
   - Dependencies: 1 confirmed, 0 potential

### 📦 Container Registry

- **crojcjiczjudu42 (registries)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-network

- **runwhensandboxacr (registries)**
  - Location: eastus
  - Resource Group: sandbox

### 📨 Messaging

- **sb-demo-primary (namespaces)**
  - Location: canadacentral
  - Resource Group: azure-servicebus-health

### 🔌 API Management

- **apim-ojcjiczjudu42 (service)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-network
   - Dependencies: 0 confirmed, 1 potential

### 🔐 Security

- **kv-ojcjiczjudu42 (vaults)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-data

### 🔧 Other Services

- **cae-ojcjiczjudu42 (managedenvironments)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-app
   - Dependencies: 0 confirmed, 1 potential

- **dash-ojcjiczjudu42 (dashboards)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-monitoring
   - Dependencies: 1 confirmed, 1 potential

- **evgt-ojcjiczjudu42 (systemtopics)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-data
   - Dependencies: 1 confirmed, 0 potential

### 🗄️ Databases

- **contoso-cosmos (databaseaccounts)**
  - Location: eastus
  - Resource Group: sandbox-contoso-rg

- **cosmos-ojcjiczjudu42 (databaseaccounts)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-data

- **psql-db-ojcjiczjudu42 (flexibleservers)**
  - Location: eastus2
  - Resource Group: rg-contoso-01-data

## 🔗 Dependency Analysis

### 📊 Resources with Most Dependencies

- **func-api-ojcjiczjudu42 (sites)**: 1 confirmed + 6 potential = 7 total
- **app-ojcjiczjudu42-blog (sites)**: 1 confirmed + 2 potential = 3 total
- **app-ojcjiczjudu42-cms (sites)**: 1 confirmed + 2 potential = 3 total
- **app-ojcjiczjudu42-stripe (sites)**: 1 confirmed + 2 potential = 3 total
- **dash-ojcjiczjudu42 (dashboards)**: 1 confirmed + 1 potential = 2 total
- **sb-deadletter-alert (metricalerts)**: 1 confirmed + 0 potential = 1 total
- **app-api-ojcjiczjudu42 (containerapps)**: 1 confirmed + 0 potential = 1 total
- **cae-ojcjiczjudu42 (managedenvironments)**: 0 confirmed + 1 potential = 1 total
- **evgt-ojcjiczjudu42 (systemtopics)**: 1 confirmed + 0 potential = 1 total
- **appi-ojcjiczjudu42 (components)**: 1 confirmed + 0 potential = 1 total

### 🔍 Detailed Dependencies

#### func-api-ojcjiczjudu42 (sites)

**🔴 Confirmed Dependencies:**

**🟠 Potential Dependencies:**
- cosmos-ojcjiczjudu42 (databaseaccounts)
- func-api-ojcjiczjudu42 (sites)
- app-ojcjiczjudu42-stripe (sites)
- stojcjiczjudu42 (storageaccounts)
- kv-ojcjiczjudu42 (vaults)
- psql-db-ojcjiczjudu42 (flexibleservers)

#### app-ojcjiczjudu42-blog (sites)

**🔴 Confirmed Dependencies:**

**🟠 Potential Dependencies:**
- app-ojcjiczjudu42-blog (sites)
- kv-ojcjiczjudu42 (vaults)

#### app-ojcjiczjudu42-cms (sites)

**🔴 Confirmed Dependencies:**

**🟠 Potential Dependencies:**
- app-ojcjiczjudu42-cms (sites)
- kv-ojcjiczjudu42 (vaults)

#### app-ojcjiczjudu42-stripe (sites)

**🔴 Confirmed Dependencies:**

**🟠 Potential Dependencies:**
- kv-ojcjiczjudu42 (vaults)
- app-ojcjiczjudu42-stripe (sites)

#### dash-ojcjiczjudu42 (dashboards)

**🔴 Confirmed Dependencies:**
- appi-ojcjiczjudu42 (components)

**🟠 Potential Dependencies:**
- appi-ojcjiczjudu42 (components)

#### sb-deadletter-alert (metricalerts)

**🔴 Confirmed Dependencies:**
- sb-demo-primary (namespaces)

#### app-api-ojcjiczjudu42 (containerapps)

**🔴 Confirmed Dependencies:**
- cae-ojcjiczjudu42 (managedenvironments)

#### cae-ojcjiczjudu42 (managedenvironments)

**🟠 Potential Dependencies:**
- appi-ojcjiczjudu42 (components)

#### evgt-ojcjiczjudu42 (systemtopics)

**🔴 Confirmed Dependencies:**
- stojcjiczjudu42 (storageaccounts)

#### appi-ojcjiczjudu42 (components)

**🔴 Confirmed Dependencies:**
- log-ojcjiczjudu42 (workspaces)

#### apim-ojcjiczjudu42 (service)

**🟠 Potential Dependencies:**
- appi-ojcjiczjudu42 (components)

## 📁 Resource Groups Analysis

### azure-apim-health

**Resources:** 2

**Resource Types:**
- actiongroups: 1
- workflows: 1

### azure-servicebus-health

**Resources:** 3

**Dependencies:**
- Internal (within RG): 1
- External (cross-RG): 0

**Resource Types:**
- metricalerts: 1
- namespaces: 1
- workspaces: 1

### networkwatcherrg

**Resources:** 2

**Resource Types:**
- networkwatchers: 2

### rg-contoso-01-app

**Resources:** 9

**Dependencies:**
- Internal (within RG): 6
- External (cross-RG): 8

**Resource Types:**
- autoscalesettings: 1
- containerapps: 1
- managedenvironments: 1
- serverfarms: 1
- sites: 4
- webpubsub: 1

### rg-contoso-01-data

**Resources:** 5

**Dependencies:**
- Internal (within RG): 1
- External (cross-RG): 0

**Resource Types:**
- databaseaccounts: 1
- flexibleservers: 1
- storageaccounts: 1
- systemtopics: 1
- vaults: 1

### rg-contoso-01-monitoring

**Resources:** 4

**Dependencies:**
- Internal (within RG): 3
- External (cross-RG): 0

**Resource Types:**
- actiongroups: 1
- components: 1
- dashboards: 1
- workspaces: 1

### rg-contoso-01-network

**Resources:** 3

**Dependencies:**
- Internal (within RG): 0
- External (cross-RG): 1

**Resource Types:**
- registries: 1
- service: 1
- staticsites: 1

### sandbox

**Resources:** 2

**Resource Types:**
- registries: 1
- storageaccounts: 1

### sandbox-contoso-rg

**Resources:** 3

**Resource Types:**
- databaseaccounts: 1
- staticsites: 1
- storageaccounts: 1

## 🚀 Enhanced Analysis Features

This report was generated using enhanced resource discovery, which includes:

- **🔍 Environment Variables Analysis**: Detection of connection strings and configuration
- **🌐 Network Information**: IP addresses, hostnames, and endpoints
- **🔐 Secret References**: Key Vault references and secret patterns
- **⚙️ Resource-Specific Configurations**: Detailed service configurations
- **🔗 Advanced Dependency Detection**: URL parsing and pattern matching

### 🔗 Connection Strings Detected

- **app-ojcjiczjudu42-blog**: APPLICATIONINSIGHTS_CONNECTION_STRING
- **app-ojcjiczjudu42-cms**: APPLICATIONINSIGHTS_CONNECTION_STRING
- **app-ojcjiczjudu42-stripe**: APPLICATIONINSIGHTS_CONNECTION_STRING
- **func-api-ojcjiczjudu42**: AZURE_COSMOS_CONNECTION_STRING_KV
- **func-api-ojcjiczjudu42**: AzureWebJobsStorage

## 💡 Recommendations

- **🔍 Review Potential Dependencies**: Many potential dependencies detected - review for accuracy
- **🏝️ Isolated Resources**: Many resources appear to have no dependencies - verify if this is intentional
- **📊 Regular Reviews**: Periodically review dependencies to ensure architecture alignment
- **🔐 Security**: Ensure connection strings and secrets are properly secured in Key Vault

---

*This report was generated automatically from Azure Resource Graph data with enhanced dependency detection.*