#!/usr/bin/env python3
"""
Azure Resource Dependency Graph Generator

This script generates a visual dependency graph of Azure resources in a subscription
using the Azure Resource Graph service.
"""

import argparse
import json
import subprocess
import sys
from typing import Dict, List, Set, Tuple, Optional

def truncate_subscription_id(subscription_id: str) -> str:
    """
    Truncate subscription ID to first 10 characters plus ellipsis.
    
    Args:
        subscription_id: The full Azure subscription ID
        
    Returns:
        Truncated subscription ID
    """
    return subscription_id[:10] + "..."

def run_az_command(command: str) -> dict:
    """
    Run an Azure CLI command and return the JSON output.
    
    Args:
        command: The Azure CLI command to run
        
    Returns:
        The parsed JSON output of the command
    """
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr.decode()}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error parsing JSON output from command: {command}")
        sys.exit(1)

def check_az_cli_installed() -> bool:
    """Check if Azure CLI is installed."""
    try:
        subprocess.run(["az", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_az_cli_logged_in() -> bool:
    """Check if the user is logged in to Azure CLI."""
    try:
        subprocess.run(["az", "account", "show"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_subscription_id() -> str:
    """Get the current Azure subscription ID."""
    result = run_az_command("az account show --query id -o json")
    return result.strip('"')

def list_resource_groups(subscription_id: str) -> List[dict]:
    """
    List all resource groups in the subscription.
    
    Args:
        subscription_id: The Azure subscription ID
        
    Returns:
        A list of resource group objects
    """
    query = f"ResourceContainers | where type == 'microsoft.resources/subscriptions/resourcegroups' | where subscriptionId == '{subscription_id}' | project name, id"
    result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
    return result.get('data', [])

def list_resources(subscription_id: str) -> List[dict]:
    """
    List all resources in the subscription.
    
    Args:
        subscription_id: The Azure subscription ID
        
    Returns:
        A list of resource objects
    """
    query = f"Resources | where subscriptionId == '{subscription_id}' | project id, name, type, resourceGroup, kind"
    result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
    return result.get('data', [])

def get_resource_dependencies(subscription_id: str, resources: List[dict]) -> Dict[str, Set[str]]:
    """
    Identify dependencies between resources.
    
    Args:
        subscription_id: The Azure subscription ID
        resources: List of resources to analyze
        
    Returns:
        A dictionary mapping resource IDs to sets of dependent resource IDs
    """
    dependencies = {}
    
    # Initialize empty dependency sets for all resources
    for resource in resources:
        dependencies[resource['id']] = set()
    
    # Check for different types of dependencies
    for resource in resources:
        resource_id = resource['id']
        resource_type = resource['type']
        
        # Query for properties that might contain dependencies
        query = f"Resources | where id == '{resource_id}' | project properties"
        result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
        
        if not result.get('data'):
            continue
            
        properties = result['data'][0].get('properties', {})
        properties_str = json.dumps(properties)
        
        # Look for resource IDs in the properties
        for potential_dep in resources:
            if potential_dep['id'] != resource_id and potential_dep['id'] in properties_str:
                dependencies[resource_id].add(potential_dep['id'])
        
        # Type-specific dependency detection
        if resource_type == 'microsoft.app/containerapps':
            # Container Apps depend on their environment and registry
            if properties and 'managedEnvironmentId' in properties:
                env_id = properties['managedEnvironmentId']
                dependencies[resource_id].add(env_id)
            
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
        
        elif resource_type == 'microsoft.insights/components':
            # Nothing specific here, but could add logic for specific insights dependencies
            pass
        
        elif resource_type == 'microsoft.apimanagement/service':
            # APIM often connected to App Insights
            for potential_insights in resources:
                if potential_insights['type'] == 'microsoft.insights/components':
                    dependencies[resource_id].add(potential_insights['id'])
    
    # Add common implicit dependencies based on resource types
    for resource in resources:
        resource_id = resource['id']
        resource_type = resource['type']
        
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
    
    return dependencies

def generate_mermaid_diagram(subscription_id: str, resources: List[dict], resource_groups: List[dict], 
                             dependencies: Dict[str, Set[str]], include_potential_deps: bool = True) -> str:
    """
    Generate a Mermaid.js diagram of the resource dependencies.
    
    Args:
        subscription_id: The Azure subscription ID
        resources: List of resources
        resource_groups: List of resource groups
        dependencies: Dictionary of resource dependencies
        include_potential_deps: Whether to include potential dependencies in the diagram
        
    Returns:
        A string containing the Mermaid.js diagram
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
        'microsoft.documentdb/databaseaccounts': 'Cosmos DB',
        'microsoft.storage/storageaccounts': 'Storage Account',
        'microsoft.servicebus/namespaces': 'Service Bus',
        'microsoft.signalrservice/webpubsub': 'Web PubSub',
        'microsoft.insights/components': 'App Insights',
        'microsoft.insights/actiongroups': 'Action Group',
        'microsoft.insights/metricalerts': 'Metric Alert',
        'microsoft.operationalinsights/workspaces': 'Log Analytics',
        'microsoft.apimanagement/service': 'API Management',
        'microsoft.network/networkwatchers': 'Network Watcher',
        'microsoft.portal/dashboards': 'Dashboard',
        'microsoft.logic/workflows': 'Logic App',
        'microsoft.eventgrid/systemtopics': 'Event Grid'
    }
    
    # Function to get display name based on resource kind
    def get_display_name(resource_type: str, resource: dict) -> str:
        display_name = type_display_names.get(resource_type, resource_type.split('/')[-1].capitalize())
        
        # Special handling for web apps vs function apps
        if resource_type == 'microsoft.web/sites' and resource.get('kind'):
            if 'functionapp' in resource.get('kind', ''):
                return 'Function App'
        
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
            
            # Add node for resource
            mermaid += f"    {rg_node_id} --> {node_id}[\"{display_name}<br/>{resource['name']}\"]\n"
    
    # Add confirmed dependencies
    mermaid += "\n    %% Confirmed Dependencies\n"
    added_deps = set()
    
    for resource_id, deps in dependencies.items():
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
        
        # Add implicit dependencies based on common Azure patterns
        potential_deps = []
        
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
        
        # Function Apps might use these services
        function_apps = [r for r in resources if r['type'] == 'microsoft.web/sites' and r.get('kind') and 'functionapp' in r.get('kind', '')]
        for fa in function_apps:
            if fa['id'] in id_map:
                fa_node = id_map[fa['id']]
                
                # Potential database connections
                for db in [r for r in resources if r['type'] in ['microsoft.dbforpostgresql/flexibleservers', 'microsoft.documentdb/databaseaccounts']]:
                    if db['id'] in id_map:
                        potential_deps.append((fa_node, id_map[db['id']]))
                
                # Potential Storage connections
                for sa in [r for r in resources if r['type'] == 'microsoft.storage/storageaccounts']:
                    if sa['id'] in id_map:
                        potential_deps.append((fa_node, id_map[sa['id']]))
                
                # Potential Web PubSub connections
                for wps in [r for r in resources if r['type'] == 'microsoft.signalrservice/webpubsub']:
                    if wps['id'] in id_map:
                        potential_deps.append((fa_node, id_map[wps['id']]))
                
                # Potential Service Bus connections
                for sb in [r for r in resources if r['type'] == 'microsoft.servicebus/namespaces']:
                    if sb['id'] in id_map:
                        potential_deps.append((fa_node, id_map[sb['id']]))
        
        # API Management might connect to backends
        apim_services = [r for r in resources if r['type'] == 'microsoft.apimanagement/service']
        for apim in apim_services:
            if apim['id'] in id_map:
                apim_node = id_map[apim['id']]
                
                # Potential backend connections
                for backend in [r for r in resources if r['type'] in ['microsoft.app/containerapps', 'microsoft.web/sites']]:
                    if backend['id'] in id_map:
                        potential_deps.append((apim_node, id_map[backend['id']]))
        
        # Logic Apps might connect to API Management
        logic_apps = [r for r in resources if r['type'] == 'microsoft.logic/workflows']
        for la in logic_apps:
            if la['id'] in id_map:
                la_node = id_map[la['id']]
                
                for apim in apim_services:
                    if apim['id'] in id_map:
                        potential_deps.append((la_node, id_map[apim['id']]))
        
        # Add potential dependencies to diagram with dotted lines
        added_potential_deps = set()
        for source, target in potential_deps:
            dep_key = f"{source}-{target}"
            if dep_key not in added_deps and dep_key not in added_potential_deps:
                mermaid += f"    {source} -.-> {target}\n"
                added_potential_deps.add(dep_key)
    
    return mermaid

def main():
    parser = argparse.ArgumentParser(description='Generate Azure resource dependency graph')
    parser.add_argument('--subscription', '-s', type=str, help='Azure subscription ID (if not provided, uses current subscription)')
    parser.add_argument('--output', '-o', type=str, default='azure_resources_diagram.md', help='Output Markdown file path')
    parser.add_argument('--no-potential-deps', action='store_true', help='Exclude potential dependencies from the diagram')
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_az_cli_installed():
        print("Error: Azure CLI not found. Please install it first: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)
    
    if not check_az_cli_logged_in():
        print("Error: Not logged in to Azure. Please run 'az login' first.")
        sys.exit(1)
    
    # Get subscription ID
    subscription_id = args.subscription if args.subscription else get_subscription_id()
    truncated_sub_id = truncate_subscription_id(subscription_id)
    print(f"Using subscription: {truncated_sub_id}")
    
    # Get resources and resource groups
    print("Fetching resource groups...")
    resource_groups = list_resource_groups(subscription_id)
    print(f"Found {len(resource_groups)} resource groups")
    
    print("Fetching resources...")
    resources = list_resources(subscription_id)
    print(f"Found {len(resources)} resources")
    
    print("Analyzing resource dependencies...")
    dependencies = get_resource_dependencies(subscription_id, resources)
    
    print("Generating diagram...")
    include_potential_deps = not args.no_potential_deps
    mermaid_diagram = generate_mermaid_diagram(
        subscription_id, 
        resources, 
        resource_groups, 
        dependencies,
        include_potential_deps
    )
    
    # Save to file
    with open(args.output, 'w') as f:
        f.write("# Azure Resources Dependency Graph\n\n")
        f.write("This diagram shows the resources in your Azure subscription and their dependencies.\n\n")
        f.write("- Solid lines represent confirmed dependencies\n")
        if include_potential_deps:
            f.write("- Dotted lines represent potential dependencies based on common patterns\n")
        f.write("\n```mermaid\n")
        f.write(mermaid_diagram)
        f.write("\n```\n")
    
    print(f"Diagram saved to {args.output}")
    if include_potential_deps:
        print("Included both confirmed and potential dependencies.")
    else:
        print("Included only confirmed dependencies. Potential dependencies were excluded.")

if __name__ == "__main__":
    main() 