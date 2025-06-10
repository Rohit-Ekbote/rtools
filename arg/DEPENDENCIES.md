# Understanding Resource Dependency Detection

This document explains how the Azure Resource Dependency Graph tool detects and visualizes relationships between Azure resources.

## Types of Dependencies

The tool identifies two categories of dependencies:

1. **Confirmed Dependencies**: Direct connections found in resource properties that explicitly reference other resources.
2. **Potential Dependencies**: Inferred connections based on common architectural patterns and Azure service relationships.

## Dependency Detection Methods

### 1. Resource ID References

The most direct method of dependency detection is finding resource IDs within the properties of another resource. 

```python
# Look for resource IDs in the properties
for potential_dep in resources:
    if potential_dep['id'] != resource_id and potential_dep['id'] in properties_str:
        dependencies[resource_id].add(potential_dep['id'])
```

This approach identifies when a resource explicitly references another resource by its Azure Resource Manager ID.

### 2. Resource-Type Specific Logic

The tool includes specialized logic for common Azure resource types that have well-known dependency patterns:

#### Container Apps

```python
if resource_type == 'microsoft.app/containerapps':
    # Container Apps depend on their environment
    if properties and 'managedEnvironmentId' in properties:
        env_id = properties['managedEnvironmentId']
        dependencies[resource_id].add(env_id)
    
    # Container Apps depend on container registries
    if properties and 'configuration' in properties and 'registries' in properties.get('configuration', {}):
        for registry in properties['configuration']['registries']:
            server = registry.get('server', '')
            # Find the ACR resource by matching the login server
            for potential_acr in resources:
                if potential_acr['type'] == 'microsoft.containerregistry/registries':
                    acr_query = f"Resources | where id == '{potential_acr['id']}' | project properties.loginServer"
                    acr_result = run_az_command(f"az graph query -q \"{acr_query}\" --subscription {subscription_id}")
                    if acr_result.get('data') and acr_result['data'][0].get('properties.loginServer') == server:
                        dependencies[resource_id].add(potential_acr['id'])
```

This identifies:
- Container App Environment connections via the `managedEnvironmentId` property
- Container Registry connections by matching the registry server name with ACR resources

#### Web Apps

```python
elif resource_type == 'microsoft.web/sites':
    # Web Apps often depend on App Service Plans
    if properties and 'serverFarmId' in properties:
        dependencies[resource_id].add(properties['serverFarmId'])
    
    # Check for App Insights connection
    if properties and 'siteConfig' in properties and properties.get('siteConfig') is not None:
        app_settings = properties.get('siteConfig', {}).get('appSettings')
        if app_settings:
            for setting in app_settings:
                if setting.get('name') == 'APPLICATIONINSIGHTS_CONNECTION_STRING' and 'value' in setting:
                    # Extract resource ID from connection string if possible
                    conn_string = setting['value']
                    for potential_insights in resources:
                        if potential_insights['type'] == 'microsoft.insights/components' and potential_insights['name'] in conn_string:
                            dependencies[resource_id].add(potential_insights['id'])
```

This identifies:
- App Service Plan connections via the `serverFarmId` property
- Application Insights connections by analyzing the app settings for connection strings

#### API Management

```python
elif resource_type == 'microsoft.apimanagement/service':
    # APIM often connected to App Insights
    for potential_insights in resources:
        if potential_insights['type'] == 'microsoft.insights/components':
            dependencies[resource_id].add(potential_insights['id'])
```

This creates a default dependency between API Management services and Application Insights resources.

### 3. Common Implicit Dependencies

The tool adds dependencies based on common architectural patterns:

```python
# Add implicit dependency for dashboard -> App Insights
if resource_type == 'microsoft.portal/dashboards':
    for potential_dep in resources:
        if potential_dep['type'] == 'microsoft.insights/components':
            dependencies[resource_id].add(potential_dep['id'])

# Container App Environment -> App Insights
if resource_type == 'microsoft.app/managedenvironments':
    for potential_dep in resources:
        if potential_dep['type'] == 'microsoft.insights/components':
            dependencies[resource_id].add(potential_dep['id'])
```

This adds expected connections between:
- Dashboards and Application Insights
- Container App Environments and Application Insights

### 4. Potential Dependencies Based on Common Patterns

Beyond confirmed dependencies, the tool identifies potential connections based on common architectural patterns:

```python
# Container Apps might use these services
container_apps = [r for r in resources if r['type'] == 'microsoft.app/containerapps']
for ca in container_apps:
    if ca['id'] in id_map:
        ca_node = id_map[ca['id']]
        
        # Potential database connections
        for db in [r for r in resources if r['type'] in ['microsoft.dbforpostgresql/flexibleservers', 'microsoft.documentdb/databaseaccounts']]:
            if db['id'] in id_map:
                potential_deps.append((ca_node, id_map[db['id']]))
        
        # Potential Key Vault connections
        for kv in [r for r in resources if r['type'] == 'microsoft.keyvault/vaults']:
            if kv['id'] in id_map:
                potential_deps.append((ca_node, id_map[kv['id']]))
        
        # Potential Storage connections
        for sa in [r for r in resources if r['type'] == 'microsoft.storage/storageaccounts']:
            if sa['id'] in id_map:
                potential_deps.append((ca_node, id_map[sa['id']]))
        
        # Potential Web PubSub connections
        for wps in [r for r in resources if r['type'] == 'microsoft.signalrservice/webpubsub']:
            if wps['id'] in id_map:
                potential_deps.append((ca_node, id_map[wps['id']]))
        
        # Potential Service Bus connections
        for sb in [r for r in resources if r['type'] == 'microsoft.servicebus/namespaces']:
            if sb['id'] in id_map:
                potential_deps.append((ca_node, id_map[sb['id']]))
```

Similar patterns are applied for:
- Function Apps and their typical backend services
- API Management and its potential backend services
- Logic Apps and their typical connections to API Management

These potential dependencies are represented with dotted lines in the diagram to distinguish them from confirmed dependencies.

## Visualization in the Diagram

In the generated Mermaid diagram:

1. **Solid Arrows (→)**: Represent confirmed dependencies
   ```
   B --> C
   ```

2. **Dotted Arrows (⇢)**: Represent potential dependencies
   ```
   B -.-> N
   ```

## Limitations

The dependency detection has several limitations:

1. **Explicit References Only**: Confirmed dependencies are only detected when a resource explicitly references another resource's ID or well-known properties.

2. **Limited Property Analysis**: The tool only analyzes a subset of properties that commonly contain dependencies.

3. **No Runtime Analysis**: The tool can't detect dependencies formed at runtime or through configuration outside Azure Resource Manager.

4. **Cross-Subscription Boundaries**: Dependencies across subscription boundaries aren't detected.

5. **Manual Configuration**: Dependencies established through manual configuration (like connection strings in application code) aren't detected.

## Extending the Tool

To add support for additional resource types or dependency patterns:

1. Add type-specific logic in the `get_resource_dependencies` function.
2. Add common patterns for potential dependencies in the `generate_mermaid_diagram` function.
3. Update the `type_display_names` dictionary to include human-readable names for new resource types.

## Example Implementation for New Resource Type

```python
# Adding detection for Event Hub dependencies
elif resource_type == 'microsoft.eventhub/namespaces':
    # Check for storage account connections
    if 'captureDescription' in properties and 'destination' in properties['captureDescription']:
        storage_account_resource_id = properties['captureDescription']['destination'].get('storageAccountResourceId')
        if storage_account_resource_id:
            dependencies[resource_id].add(storage_account_resource_id)
```

This would detect when an Event Hub has capture enabled and depends on a storage account. 