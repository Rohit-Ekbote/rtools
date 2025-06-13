#!/usr/bin/env python3
"""
Azure Resource Dependency Graph Generator - Mermaid Diagram Module

This module contains functions for generating Mermaid.js diagrams of Azure resources.
"""

from typing import Dict, List, Set

def truncate_subscription_id(subscription_id: str) -> str:
    """
    Truncate subscription ID to first 10 characters plus ellipsis.
    
    Args:
        subscription_id: The full Azure subscription ID
        
    Returns:
        Truncated subscription ID
    """
    return subscription_id[:10] + "..."

def generate_mermaid_diagram(subscription_id: str, resources: List[dict], resource_groups: List[dict], 
                            confirmed_dependencies: Dict[str, Set[str]], potential_dependencies: Dict[str, Set[str]], 
                            include_potential_deps: bool = True) -> str:
    """
    Generate a Mermaid diagram showing Azure resource dependencies.
    
    Args:
        subscription_id: The Azure subscription ID
        resources: List of resource objects
        resource_groups: List of resource group objects  
        confirmed_dependencies: Dictionary mapping resource IDs to sets of confirmed dependent resource IDs
        potential_dependencies: Dictionary mapping resource IDs to sets of potential dependent resource IDs
        include_potential_deps: Whether to include potential dependencies in the diagram
        
    Returns:
        A string containing the Mermaid diagram markup
    """
    # Create ID mapping for diagram nodes
    id_map = {}
    node_counter = 0
    
    # Truncate subscription ID to first 10 characters
    truncated_sub_id = truncate_subscription_id(subscription_id)
    
    # Start with subscription
    mermaid = "graph TD;\n"
    sub_node = f"A[Subscription<br/>{truncated_sub_id}]"
    mermaid += f"    {sub_node}\n\n"
    
    # Add resource groups
    mermaid += "    %% Resource Groups\n"
    for i, rg in enumerate(resource_groups):
        node_id = chr(66 + i)  # Start with B
        id_map[rg['id']] = node_id
        mermaid += f"    A --> {node_id}[\"{rg['name']}\"]\n"
    
    # Group resources by type for better organization
    resource_by_type = {}
    for resource in resources:
        resource_type = resource['type']
        if resource_type not in resource_by_type:
            resource_by_type[resource_type] = []
        resource_by_type[resource_type].append(resource)
    
    # Define a order for common resource types
    type_order = [
        'microsoft.app/containerapps',
        'microsoft.app/managedenvironments',
        'microsoft.web/sites',
        'microsoft.web/serverfarms',
        'microsoft.web/staticsites',
        'microsoft.containerregistry/registries',
        'microsoft.keyvault/vaults',
        'microsoft.dbforpostgresql/flexibleservers',
        'microsoft.documentdb/databaseaccounts',
        'microsoft.storage/storageaccounts',
        'microsoft.servicebus/namespaces',
        'microsoft.signalrservice/webpubsub',
        'microsoft.insights/components',
        'microsoft.insights/actiongroups',
        'microsoft.insights/metricalerts',
        'microsoft.operationalinsights/workspaces',
        'microsoft.apimanagement/service',
        'microsoft.network/networkwatchers',
        'microsoft.portal/dashboards',
        'microsoft.logic/workflows',
        'microsoft.eventgrid/systemtopics'
    ]
    
    # Sort the types based on the defined order
    ordered_types = []
    # Add types in the defined order if they exist
    for t in type_order:
        if t in resource_by_type:
            ordered_types.append(t)
    # Add any remaining types not in the defined order
    for t in resource_by_type:
        if t not in ordered_types:
            ordered_types.append(t)
    
    # Get human-readable type names
    type_display_names = {
        'microsoft.app/containerapps': 'Container App',
        'microsoft.app/managedenvironments': 'Container App Environment',
        'microsoft.web/sites': 'Web App',
        'microsoft.web/serverfarms': 'App Service Plan',
        'microsoft.web/staticsites': 'Static Site',
        'microsoft.containerregistry/registries': 'Container Registry',
        'microsoft.keyvault/vaults': 'Key Vault',
        'microsoft.dbforpostgresql/flexibleservers': 'PostgreSQL',
        'microsoft.sql/servers': 'SQL Server',
        'microsoft.sql/servers/databases': 'SQL Database',
        'microsoft.documentdb/databaseaccounts': 'Cosmos DB',
        'microsoft.storage/storageaccounts': 'Storage Account',
        'microsoft.servicebus/namespaces': 'Service Bus',
        'microsoft.signalrservice/webpubsub': 'Web PubSub',
        'microsoft.signalrservice/signalr': 'SignalR Service',
        'microsoft.insights/components': 'App Insights',
        'microsoft.insights/actiongroups': 'Action Group',
        'microsoft.insights/metricalerts': 'Metric Alert',
        'microsoft.operationalinsights/workspaces': 'Log Analytics',
        'microsoft.apimanagement/service': 'API Management',
        'microsoft.network/networkwatchers': 'Network Watcher',
        'microsoft.network/virtualnetworks': 'Virtual Network',
        'microsoft.network/networksecuritygroups': 'Network Security Group',
        'microsoft.network/publicipaddresses': 'Public IP',
        'microsoft.network/applicationgateways': 'Application Gateway',
        'microsoft.network/loadbalancers': 'Load Balancer',
        'microsoft.network/frontdoors': 'Front Door',
        'microsoft.cdn/profiles': 'CDN Profile',
        'microsoft.cdn/profiles/endpoints': 'CDN Endpoint',
        'microsoft.portal/dashboards': 'Dashboard',
        'microsoft.logic/workflows': 'Logic App',
        'microsoft.eventgrid/systemtopics': 'Event Grid',
        'microsoft.eventgrid/topics': 'Event Grid Topic',
        'microsoft.eventhub/namespaces': 'Event Hub',
        'microsoft.cache/redis': 'Redis Cache',
        'microsoft.cognitiveservices/accounts': 'Cognitive Service',
        'microsoft.machinelearningservices/workspaces': 'ML Workspace',
        'microsoft.compute/virtualmachines': 'Virtual Machine',
        'microsoft.compute/virtualmachinescalesets': 'VM Scale Set',
        'microsoft.containerservice/managedclusters': 'AKS Cluster',
        'microsoft.datafactory/factories': 'Data Factory',
        'microsoft.synapse/workspaces': 'Synapse Workspace',
        'microsoft.batch/batchaccounts': 'Batch Account',
        'microsoft.search/searchservices': 'Search Service',
        'microsoft.dbformysql/flexibleservers': 'MySQL Server',
        'microsoft.dbformariadb/servers': 'MariaDB Server',
        'microsoft.devices/iothubs': 'IoT Hub',
        'microsoft.notificationhubs/namespaces': 'Notification Hub'
    }
    
    # Function to get display name based on resource kind
    def get_display_name(resource_type: str, resource: dict) -> str:
        display_name = type_display_names.get(resource_type, resource_type.split('/')[-1].capitalize())
        
        # Special handling based on resource kind
        if resource_type == 'microsoft.web/sites' and resource.get('kind'):
            kind = resource.get('kind', '').lower()
            if 'functionapp' in kind:
                return 'Function App'
            elif 'api' in kind:
                return 'API App'
            elif 'container' in kind:
                return 'Container Web App'
            elif 'linux' in kind:
                return 'Linux Web App'
        
        # Special handling for storage accounts based on kind
        elif resource_type == 'microsoft.storage/storageaccounts' and resource.get('kind'):
            kind = resource.get('kind', '').lower()
            if kind == 'blobstorage':
                return 'Blob Storage'
            elif kind == 'filestorage':
                return 'File Storage'
            elif kind == 'blockblobstorage':
                return 'Block Blob Storage'
            elif 'storagev2' in kind:
                return 'Storage Account v2'
        
        # Special handling for Cosmos DB based on kind
        elif resource_type == 'microsoft.documentdb/databaseaccounts' and resource.get('kind'):
            kind = resource.get('kind', '').lower()
            if kind == 'mongodb':
                return 'Cosmos DB (MongoDB)'
            elif kind == 'cassandra':
                return 'Cosmos DB (Cassandra)'
            elif kind == 'gremlin':
                return 'Cosmos DB (Gremlin)'
            elif kind == 'table':
                return 'Cosmos DB (Table)'
            
        return display_name
    
    # Add resources by type
    for resource_type in ordered_types:
        resources_of_type = resource_by_type[resource_type]
        type_name = resource_type.split('/')[-1].capitalize()
        
        mermaid += f"\n    %% {type_name} Resources\n"
        
        for resource in resources_of_type:
            node_counter += 1
            # Use letters for first 26 nodes, then switch to node_1, node_2, etc.
            if node_counter < 26:
                node_id = chr(65 + node_counter)
            else:
                node_id = f"node_{node_counter - 25}"
                
            id_map[resource['id']] = node_id
            
            # Get resource display name
            display_name = get_display_name(resource_type, resource)
            
            # Find resource group
            rg_node_id = None
            for rg in resource_groups:
                if rg['name'] == resource['resourceGroup']:
                    rg_node_id = id_map[rg['id']]
                    break
            
            # If resource group not found, skip
            if not rg_node_id:
                continue
            
            # Add node for resource with more detailed display name formatting
            # Include additional information like resource type and kind if available
            resource_info = f"<b>{display_name}</b><br/>{resource['name']}"
            
            # Add resource kind if available and different from resource type
            if resource.get('kind') and not resource_type == 'microsoft.web/sites':
                resource_info += f"<br/><i>({resource['kind']})</i>"
                
            mermaid += f"    {rg_node_id} --> {node_id}[\"{resource_info}\"]\n"
    
    # Add confirmed dependencies
    mermaid += "\n    %% Confirmed Dependencies\n"
    added_deps = set()
    
    for resource_id, deps in confirmed_dependencies.items():
        if resource_id in id_map:
            source_node = id_map[resource_id]
            for dep_id in deps:
                if dep_id in id_map:
                    target_node = id_map[dep_id]
                    dep_key = f"{source_node}-{target_node}"
                    if dep_key not in added_deps:
                        mermaid += f"    {source_node} --> {target_node}\n"
                        added_deps.add(dep_key)
    
    # Add potential dependencies if requested
    if include_potential_deps:
        mermaid += "\n    %% Potential Dependencies\n"
        for resource_id, deps in potential_dependencies.items():
            if resource_id in id_map:
                source_node = id_map[resource_id]
                for dep_id in deps:
                    if dep_id in id_map:
                        target_node = id_map[dep_id]
                        dep_key = (source_node, target_node)
                        
                        # Skip if we've already added this dependency (confirmed takes priority)
                        if dep_key not in added_deps:
                            mermaid += f"    {source_node} -.-> {target_node}\n"
                            added_deps.add(dep_key)
    
    return mermaid 