# Extending the Azure Resource Dependency Graph Tool

This guide provides examples and instructions for extending the tool to support additional Azure resource types and dependency scenarios.

## Adding Support for New Resource Types

### Step 1: Update the Resource Type Display Names

Add the new resource type to the `type_display_names` dictionary in the `generate_mermaid_diagram` function:

```python
type_display_names = {
    # Existing entries...
    'microsoft.eventhub/namespaces': 'Event Hub',
    'microsoft.cache/redis': 'Redis Cache',
    'microsoft.network/privateendpoints': 'Private Endpoint',
    # Add your new resource type here
}
```

### Step 2: Add Type-Specific Dependency Logic

Add a new condition in the `get_resource_dependencies` function:

```python
# Add Event Hub specific dependency detection
elif resource_type == 'microsoft.eventhub/namespaces':
    # Check for storage account connections (capture feature)
    if properties and 'captureDescription' in properties and 'destination' in properties.get('captureDescription', {}):
        storage_account_resource_id = properties['captureDescription']['destination'].get('storageAccountResourceId')
        if storage_account_resource_id:
            dependencies[resource_id].add(storage_account_resource_id)
    
    # Check for disaster recovery pairing
    if properties and 'disasterRecoveryConfig' in properties:
        partner_namespace = properties['disasterRecoveryConfig'].get('partnerNamespace')
        if partner_namespace:
            dependencies[resource_id].add(partner_namespace)
```

### Step 3: Add Potential Dependencies

Update the potential dependencies section in `generate_mermaid_diagram`:

```python
# Event Hubs might connect to these services
event_hubs = [r for r in resources if r['type'] == 'microsoft.eventhub/namespaces']
for eh in event_hubs:
    if eh['id'] in id_map:
        eh_node = id_map[eh['id']]
        
        # Potential Logic App connections
        for la in [r for r in resources if r['type'] == 'microsoft.logic/workflows']:
            if la['id'] in id_map:
                potential_deps.append((la_node, id_map[eh['id']]))
        
        # Potential Function App connections
        for fa in function_apps:
            if fa['id'] in id_map:
                potential_deps.append((id_map[fa['id']], eh_node))
```

## Examples for Common Azure Services

### Azure Virtual Network and Subnets

```python
elif resource_type == 'microsoft.network/virtualnetworks':
    # Find resources that use this VNet
    for resource in resources:
        if resource['id'] != resource_id:
            # Check for subnet references in network profiles
            vnet_query = f"Resources | where id == '{resource['id']}' | project properties.networkProfile"
            vnet_result = run_az_command(f"az graph query -q \"{vnet_query}\" --subscription {subscription_id}")
            if vnet_result.get('data'):
                network_profile = vnet_result['data'][0].get('properties.networkProfile', {})
                if network_profile and 'virtualNetwork' in str(network_profile) and resource_id in str(network_profile):
                    dependencies[resource['id']].add(resource_id)
```

### Private Endpoints

```python
elif resource_type == 'microsoft.network/privateendpoints':
    # Private Endpoints connect to a target resource
    if properties and 'privateLinkServiceConnections' in properties:
        connections = properties['privateLinkServiceConnections']
        for connection in connections:
            if 'properties' in connection and 'privateLinkServiceId' in connection['properties']:
                target_resource_id = connection['properties']['privateLinkServiceId']
                dependencies[resource_id].add(target_resource_id)
    
    # Private Endpoints depend on a subnet
    if properties and 'subnet' in properties and 'id' in properties['subnet']:
        subnet_id = properties['subnet']['id']
        dependencies[resource_id].add(subnet_id)
```

### Azure Kubernetes Service

```python
elif resource_type == 'microsoft.containerservice/managedclusters':
    # AKS clusters often depend on these resources
    
    # Log Analytics Workspace for monitoring
    if properties and 'addonProfiles' in properties and 'omsagent' in properties['addonProfiles']:
        omsagent = properties['addonProfiles']['omsagent']
        if 'config' in omsagent and 'logAnalyticsWorkspaceResourceID' in omsagent['config']:
            workspace_id = omsagent['config']['logAnalyticsWorkspaceResourceID']
            dependencies[resource_id].add(workspace_id)
    
    # ACR integration
    if properties and 'identityProfile' in properties:
        for profile_name, profile in properties['identityProfile'].items():
            if profile_name == 'kubeletidentity' and 'resourceId' in profile:
                kubelet_identity_id = profile['resourceId']
                # This identity may have ACR pull permissions
                for acr in [r for r in resources if r['type'] == 'microsoft.containerregistry/registries']:
                    # This is a potential dependency, could be detected through role assignments
                    # For now we'll add it as a direct dependency
                    dependencies[resource_id].add(acr['id'])
```

### Logic Apps

```python
elif resource_type == 'microsoft.logic/workflows':
    # Look for API connections in the workflow definition
    if properties and 'definition' in properties and 'connections' in properties['definition']:
        connections = properties['definition']['connections']
        for connection_name, connection in connections.items():
            # API Management connection
            if 'connectionId' in connection and '/connections/apimanagement' in connection['connectionId']:
                for apim in [r for r in resources if r['type'] == 'microsoft.apimanagement/service']:
                    # This is a simplified approach; in reality would need to parse the connection ID
                    dependencies[resource_id].add(apim['id'])
            
            # Service Bus connection
            if 'connectionId' in connection and '/connections/servicebus' in connection['connectionId']:
                for sb in [r for r in resources if r['type'] == 'microsoft.servicebus/namespaces']:
                    dependencies[resource_id].add(sb['id'])
```

## Advanced Dependency Detection

### Role-Based Access Control (RBAC) Dependencies

To detect dependencies based on role assignments:

```python
# Check for role assignments that indicate dependencies
for resource in resources:
    resource_id = resource['id']
    
    # Get role assignments for this resource
    role_query = f"Resources | where type == 'microsoft.authorization/roleassignments' | where properties.scope == '{resource_id}' | project properties"
    role_result = run_az_command(f"az graph query -q \"{role_query}\" --subscription {subscription_id}")
    
    if role_result.get('data'):
        for assignment in role_result['data']:
            principal_id = assignment.get('properties', {}).get('principalId')
            if principal_id:
                # Find the resource that uses this identity
                for potential_dependent in resources:
                    if 'identity' in potential_dependent and 'principalId' in potential_dependent['identity'] and potential_dependent['identity']['principalId'] == principal_id:
                        # The resource with this identity depends on the resource with the role assignment
                        dependencies[potential_dependent['id']].add(resource_id)
```

### Private Link Service Dependencies

```python
elif resource_type == 'microsoft.network/privatelinkservices':
    # Private Link Services are connected to a load balancer frontend
    if properties and 'loadBalancerFrontendIpConfigurations' in properties:
        for frontend in properties['loadBalancerFrontendIpConfigurations']:
            if 'id' in frontend:
                lb_frontend_id = frontend['id']
                # Extract the load balancer ID from the frontend ID
                lb_id_parts = lb_frontend_id.split('/frontendIPConfigurations/')
                if len(lb_id_parts) > 0:
                    lb_id = lb_id_parts[0]
                    dependencies[resource_id].add(lb_id)
```

## Testing Extensions

When adding new dependency detection logic, you should test it with resources that match the expected patterns:

1. Create a test subscription with the resources you want to detect
2. Run the tool against that subscription
3. Verify that the expected dependencies appear in the diagram

## Contributing Back

If you develop extensions for additional resource types, consider contributing them back to the project by:

1. Forking the repository
2. Adding your extension code
3. Testing it thoroughly
4. Submitting a pull request with a clear description of the new capability

This helps the community benefit from improved dependency detection for a wider range of Azure services. 