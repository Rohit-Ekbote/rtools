# Azure Resources Dependency Graph

This diagram shows the resources in your Azure subscription and their dependencies.

- Resources are displayed with their proper Azure display names and resource names
- Resource types and kinds are included for better identification
- Solid lines represent confirmed dependencies
- Dotted lines represent potential dependencies based on common patterns

```mermaid
graph TD;
    A[Subscription<br/>2a0cf760-b...]

    %% Resource Groups
    A --> B["azure-ado-triage"]
    A --> C["azure-apim-health"]
    A --> D["azure-rg-triage"]
    A --> E["azure-servicebus-health"]
    A --> F["NetworkWatcherRG"]
    A --> G["rg-contoso-01-app"]
    A --> H["rg-contoso-01-data"]
    A --> I["rg-contoso-01-monitoring"]
    A --> J["rg-contoso-01-network"]
    A --> K["runwhen-base-org"]
    A --> L["sandbox"]
    A --> M["sandbox-contoso-rg"]

    %% Containerapps Resources
    G --> B["<b>Container App</b><br/>app-api-ojcjiczjudu42"]

    %% Managedenvironments Resources
    G --> C["<b>Container App Environment</b><br/>cae-ojcjiczjudu42"]

    %% Sites Resources
    G --> D["<b>Linux Web App</b><br/>app-ojcjiczjudu42-blog"]
    G --> E["<b>Linux Web App</b><br/>app-ojcjiczjudu42-cms"]
    G --> F["<b>Linux Web App</b><br/>app-ojcjiczjudu42-stripe"]
    G --> G["<b>Function App</b><br/>func-api-ojcjiczjudu42"]

    %% Serverfarms Resources
    G --> H["<b>App Service Plan</b><br/>plan-ojcjiczjudu42<br/><i>(linux)</i>"]

    %% Staticsites Resources
    J --> I["<b>Static Site</b><br/>stapp-web-ojcjiczjudu42"]
    M --> J["<b>Static Site</b><br/>contoso-swa"]

    %% Registries Resources
    J --> K["<b>Container Registry</b><br/>crojcjiczjudu42"]
    L --> L["<b>Container Registry</b><br/>runwhensandboxacr"]

    %% Vaults Resources
    H --> M["<b>Key Vault</b><br/>kv-ojcjiczjudu42"]

    %% Flexibleservers Resources
    H --> N["<b>PostgreSQL</b><br/>psql-db-ojcjiczjudu42"]

    %% Databaseaccounts Resources
    H --> O["<b>Cosmos DB (MongoDB)</b><br/>cosmos-ojcjiczjudu42<br/><i>(MongoDB)</i>"]
    M --> P["<b>Cosmos DB</b><br/>contoso-cosmos<br/><i>(GlobalDocumentDB)</i>"]

    %% Storageaccounts Resources
    H --> Q["<b>Storage Account v2</b><br/>stojcjiczjudu42<br/><i>(StorageV2)</i>"]
    M --> R["<b>Storage Account v2</b><br/>sandboxcontosostorage01<br/><i>(StorageV2)</i>"]
    L --> S["<b>Storage Account v2</b><br/>runwhensbxactionstf<br/><i>(StorageV2)</i>"]

    %% Namespaces Resources
    E --> T["<b>Service Bus</b><br/>sb-demo-primary"]

    %% Webpubsub Resources
    G --> U["<b>Web PubSub</b><br/>app-web-ojcjiczjudu42<br/><i>(WebPubSub)</i>"]

    %% Components Resources
    I --> V["<b>App Insights</b><br/>appi-ojcjiczjudu42<br/><i>(web)</i>"]

    %% Actiongroups Resources
    C --> W["<b>Action Group</b><br/>runwhen-webhooks"]
    I --> X["<b>Action Group</b><br/>Application Insights Smart Detection"]

    %% Metricalerts Resources
    E --> Y["<b>Metric Alert</b><br/>sb-deadletter-alert"]

    %% Workspaces Resources
    E --> Z["<b>Log Analytics</b><br/>law-sb-health-demo"]
    I --> node_1["<b>Log Analytics</b><br/>log-ojcjiczjudu42"]

    %% Service Resources
    J --> node_2["<b>API Management</b><br/>apim-ojcjiczjudu42"]

    %% Networkwatchers Resources

    %% Dashboards Resources
    I --> node_5["<b>Dashboard</b><br/>dash-ojcjiczjudu42"]

    %% Workflows Resources
    C --> node_6["<b>Logic App</b><br/>webhook"]

    %% Systemtopics Resources
    H --> node_7["<b>Event Grid</b><br/>evgt-ojcjiczjudu42"]

    %% Autoscalesettings Resources
    G --> node_8["<b>Autoscalesettings</b><br/>app-autoscale"]

    %% Confirmed Dependencies
    Y --> T
    B --> C
    node_7 --> Q
    V --> node_1
    node_5 --> V

    %% Potential Dependencies
    C -.-> V
    D -.-> D
    D -.-> M
    E -.-> E
    E -.-> M
    F -.-> M
    F -.-> F
    G -.-> O
    G -.-> G
    G -.-> F
    G -.-> Q
    G -.-> M
    G -.-> N
    node_5 -.-> V
    node_2 -.-> V

```
