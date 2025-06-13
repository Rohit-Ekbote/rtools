#!/usr/bin/env python3
"""
Azure Resource Dependency Graph Generator

This script generates a visual dependency graph of Azure resources in a subscription
using the Azure Resource Graph service. It can output either a Mermaid diagram or
an interactive HTML page with D3.js visualization.
"""

import argparse
import json
import subprocess
import sys
import os
from typing import Dict, List, Set, Tuple, Optional

# Import the visualization modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


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

def run_az_command_list(command: List[str], subscription_id: str = None) -> dict:
    """
    Run an Azure CLI command from a list and return the JSON output.
    
    Args:
        command: The Azure CLI command as a list
        subscription_id: Optional subscription ID
        
    Returns:
        The parsed JSON output of the command
    """
    try:
        if subscription_id:
            command.extend(['--subscription', subscription_id])
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {}
        
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(command)}: {e.stderr}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return {}

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

def get_network_information(resource: Dict[str, any], subscription_id: str) -> Dict[str, any]:
    """Get network information for addressable resources"""
    resource_type = resource.get('type', '').lower()
    resource_group = resource.get('resourceGroup', '')
    name = resource.get('name', '')
    network_info = {}
    
    try:
        # Virtual Machines
        if 'microsoft.compute/virtualmachines' in resource_type:
            vm_details = run_az_command_list([
                'az', 'vm', 'show',
                '--resource-group', resource_group,
                '--name', name,
                '--show-details'
            ], subscription_id)
            if vm_details:
                network_info.update({
                    'privateIps': vm_details.get('privateIps', []),
                    'publicIps': vm_details.get('publicIps', []),
                    'fqdns': vm_details.get('fqdns', [])
                })
        
        # Public IP Addresses
        elif 'microsoft.network/publicipaddresses' in resource_type:
            pip_details = run_az_command_list([
                'az', 'network', 'public-ip', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if pip_details:
                network_info.update({
                    'ipAddress': pip_details.get('ipAddress'),
                    'fqdn': pip_details.get('dnsSettings', {}).get('fqdn'),
                    'allocationMethod': pip_details.get('publicIPAllocationMethod')
                })
        
        # Load Balancers
        elif 'microsoft.network/loadbalancers' in resource_type:
            lb_details = run_az_command_list([
                'az', 'network', 'lb', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if lb_details:
                frontend_ips = []
                for frontend in lb_details.get('frontendIPConfigurations', []):
                    if frontend.get('publicIPAddress'):
                        frontend_ips.append(frontend['publicIPAddress'].get('id', '').split('/')[-1])
                network_info['frontendIPs'] = frontend_ips
        
        # App Services
        elif 'microsoft.web/sites' in resource_type:
            app_details = run_az_command_list([
                'az', 'webapp', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if app_details:
                network_info.update({
                    'defaultHostName': app_details.get('defaultHostName'),
                    'hostNames': app_details.get('hostNames', []),
                    'outboundIpAddresses': app_details.get('outboundIpAddresses', '').split(',') if app_details.get('outboundIpAddresses') else []
                })
        
        # Storage Accounts
        elif 'microsoft.storage/storageaccounts' in resource_type:
            storage_details = run_az_command_list([
                'az', 'storage', 'account', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if storage_details:
                primary_endpoints = storage_details.get('primaryEndpoints', {})
                network_info['endpoints'] = primary_endpoints
        
    except Exception as e:
        print(f"Error getting network info for {name}: {str(e)}")
        
    return network_info

def get_environment_variables(resource: Dict[str, any], subscription_id: str) -> Dict[str, any]:
    """Get environment variables for supported resources"""
    resource_type = resource.get('type', '').lower()
    resource_group = resource.get('resourceGroup', '')
    name = resource.get('name', '')
    env_vars = {}
    
    try:
        # App Service / Web Apps
        if 'microsoft.web/sites' in resource_type:
            app_settings = run_az_command_list([
                'az', 'webapp', 'config', 'appsettings', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if isinstance(app_settings, list):
                env_vars['appSettings'] = {setting['name']: setting['value'] for setting in app_settings}
            
            # Get connection strings
            conn_strings = run_az_command_list([
                'az', 'webapp', 'config', 'connection-string', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if isinstance(conn_strings, list):
                env_vars['connectionStrings'] = {cs['name']: cs['value'] for cs in conn_strings}
        
        # Function Apps
        elif 'microsoft.web/sites' in resource_type and resource.get('kind', '').lower() == 'functionapp':
            func_settings = run_az_command_list([
                'az', 'functionapp', 'config', 'appsettings', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if isinstance(func_settings, list):
                env_vars['functionAppSettings'] = {setting['name']: setting['value'] for setting in func_settings}
        
        # Container Instances
        elif 'microsoft.containerinstance/containergroups' in resource_type:
            container_details = run_az_command_list([
                'az', 'container', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if container_details:
                containers = container_details.get('containers', [])
                for i, container in enumerate(containers):
                    if container.get('environmentVariables'):
                        env_vars[f'container_{i}_env'] = {
                            env['name']: env.get('value', env.get('secureValue', 'SECURE_VALUE'))
                            for env in container['environmentVariables']
                        }
                        
    except Exception as e:
        print(f"Error getting environment variables for {name}: {str(e)}")
        
    return env_vars

def get_resource_specific_config(resource: Dict[str, any], subscription_id: str) -> Dict[str, any]:
    """Get resource-specific configuration details"""
    resource_type = resource.get('type', '').lower()
    resource_group = resource.get('resourceGroup', '')
    name = resource.get('name', '')
    config = {}
    
    try:
        # Virtual Machines - Get VM size, OS info, etc.
        if 'microsoft.compute/virtualmachines' in resource_type:
            vm_details = run_az_command_list([
                'az', 'vm', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if vm_details:
                config.update({
                    'vmSize': vm_details.get('hardwareProfile', {}).get('vmSize'),
                    'osType': vm_details.get('storageProfile', {}).get('osDisk', {}).get('osType'),
                    'imageReference': vm_details.get('storageProfile', {}).get('imageReference'),
                    'adminUsername': vm_details.get('osProfile', {}).get('adminUsername')
                })
        
        # Storage Accounts - Get SKU, access tier, etc.
        elif 'microsoft.storage/storageaccounts' in resource_type:
            storage_details = run_az_command_list([
                'az', 'storage', 'account', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if storage_details:
                config.update({
                    'sku': storage_details.get('sku'),
                    'accessTier': storage_details.get('accessTier'),
                    'encryption': storage_details.get('encryption'),
                    'networkRuleSet': storage_details.get('networkRuleSet')
                })
        
        # SQL Databases
        elif 'microsoft.sql/servers/databases' in resource_type:
            # Extract server name from resource ID
            server_name = resource.get('id', '').split('/')[8] if len(resource.get('id', '').split('/')) > 8 else ''
            if server_name:
                db_details = run_az_command_list([
                    'az', 'sql', 'db', 'show',
                    '--resource-group', resource_group,
                    '--server', server_name,
                    '--name', name
                ], subscription_id)
                if db_details:
                    config.update({
                        'edition': db_details.get('edition'),
                        'serviceLevelObjective': db_details.get('serviceLevelObjective'),
                        'maxSizeBytes': db_details.get('maxSizeBytes'),
                        'collation': db_details.get('collation')
                    })
        
        # Key Vaults
        elif 'microsoft.keyvault/vaults' in resource_type:
            kv_details = run_az_command_list([
                'az', 'keyvault', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if kv_details:
                config.update({
                    'sku': kv_details.get('properties', {}).get('sku'),
                    'accessPolicies': kv_details.get('properties', {}).get('accessPolicies'),
                    'enabledForDeployment': kv_details.get('properties', {}).get('enabledForDeployment'),
                    'enabledForTemplateDeployment': kv_details.get('properties', {}).get('enabledForTemplateDeployment')
                })
                
    except Exception as e:
        print(f"Error getting specific config for {name}: {str(e)}")
        
    return config

def list_resources_basic(subscription_id: str) -> List[dict]:
    """
    List all resources in the subscription with basic information.
    
    Args:
        subscription_id: The Azure subscription ID
        
    Returns:
        A list of basic resource objects
    """
    query = f"Resources | where subscriptionId == '{subscription_id}' | project id, name, type, resourceGroup, kind, location, tags, properties"
    result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
    return result.get('data', [])

def list_resources(subscription_id: str, basic_mode: bool = False) -> List[dict]:
    """
    List all resources in the subscription with enhanced details.
    
    Args:
        subscription_id: The Azure subscription ID
        basic_mode: If True, only gather basic resource information
        
    Returns:
        A list of resource objects with detailed information
    """
    if basic_mode:
        print("Using basic mode - gathering resource information without detailed enhancement...")
        return list_resources_basic(subscription_id)
    
    print("Using enhanced mode - gathering detailed resource information...")
    print("Fetching basic resource information...")
    query = f"Resources | where subscriptionId == '{subscription_id}' | project id, name, type, resourceGroup, kind, location, tags"
    result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
    basic_resources = result.get('data', [])
    
    enhanced_resources = []
    total_resources = len(basic_resources)
    
    print(f"Enhancing resource details for {total_resources} resources...")
    for i, resource in enumerate(basic_resources, 1):
        print(f"Processing resource {i}/{total_resources}: {resource.get('name', 'Unknown')}")
        
        try:
            # Get enhanced resource details
            enhanced_resource = resource.copy()
            
            # Add network information
            network_info = get_network_information(resource, subscription_id)
            if network_info:
                enhanced_resource['networkInfo'] = network_info
                
            # Add environment variables
            env_vars = get_environment_variables(resource, subscription_id)
            if env_vars:
                enhanced_resource['environmentVariables'] = env_vars
                
            # Add resource-specific configurations
            specific_config = get_resource_specific_config(resource, subscription_id)
            if specific_config:
                enhanced_resource['specificConfiguration'] = specific_config
            
            # Get properties from Resource Graph for dependency analysis
            resource_id = resource['id']
            properties_query = f"Resources | where id == '{resource_id}' | project properties"
            properties_result = run_az_command(f"az graph query -q \"{properties_query}\" --subscription {subscription_id}")
            if properties_result.get('data'):
                enhanced_resource['properties'] = properties_result['data'][0].get('properties', {})
            
            enhanced_resources.append(enhanced_resource)
            
        except Exception as e:
            print(f"Warning: Error enhancing resource {resource.get('name', 'Unknown')}: {str(e)}")
            # Add basic resource info if enhancement fails
            enhanced_resources.append(resource)
    
    print(f"Enhanced {len(enhanced_resources)} resources with detailed information")
    return enhanced_resources

def get_resource_dependencies(subscription_id: str, resources: List[dict]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Identify dependencies between resources using enhanced resource information.
    
    Args:
        subscription_id: The Azure subscription ID
        resources: List of enhanced resources to analyze
        
    Returns:
        A tuple containing (confirmed_dependencies, potential_dependencies) dictionaries mapping resource IDs to sets of dependent resource IDs
    """
    confirmed_dependencies = {}
    potential_dependencies = {}
    
    # Initialize empty dependency sets for all resources
    for resource in resources:
        confirmed_dependencies[resource['id']] = set()
        potential_dependencies[resource['id']] = set()
    
    print("Analyzing resource dependencies with enhanced information...")
    
    # Check for different types of dependencies
    for resource in resources:
        resource_id = resource['id']
        resource_type = resource['type']
        
        # Use enhanced properties if available, otherwise use basic properties
        properties = resource.get('properties', {})
        properties_str = json.dumps(properties)
        
        # Enhanced dependency detection using environment variables
        env_vars = resource.get('environmentVariables', {})
        
        # Enhanced dependency detection using network information
        network_info = resource.get('networkInfo', {})
        
        # Enhanced dependency detection using specific configurations
        specific_config = resource.get('specificConfiguration', {})
        
        # Look for resource IDs in properties, environment variables, and configurations
        all_resource_data = json.dumps({
            'properties': properties,
            'environmentVariables': env_vars,
            'specificConfiguration': specific_config,
            'networkInfo': network_info
        })
        
        for potential_dep in resources:
            if potential_dep['id'] != resource_id and potential_dep['id'] in all_resource_data:
                confirmed_dependencies[resource_id].add(potential_dep['id'])
        
        # Enhanced dependency detection using environment variables (potential dependencies)
        if env_vars:
            # App Settings dependencies
            app_settings = env_vars.get('appSettings', {})
            for setting_name, setting_value in app_settings.items():
                if isinstance(setting_value, str):
                    # Look for resource names in connection strings, URLs, and other settings
                    for potential_dep in resources:
                        dep_name = potential_dep.get('name', '')
                        if dep_name and len(dep_name) > 3:  # Avoid matching very short names
                            # Direct name match
                            if dep_name in setting_value:
                                potential_dependencies[resource_id].add(potential_dep['id'])
                            # For URLs, also check if the resource name appears as a subdomain or hostname
                            elif dep_name.replace('-', '') in setting_value.replace('-', ''):
                                potential_dependencies[resource_id].add(potential_dep['id'])
            
            # Connection strings dependencies
            conn_strings = env_vars.get('connectionStrings', {})
            for conn_name, conn_value in conn_strings.items():
                if isinstance(conn_value, str):
                    # Look for server names or resource names in connection strings
                    for potential_dep in resources:
                        dep_name = potential_dep.get('name', '')
                        if dep_name and len(dep_name) > 3:  # Avoid matching very short names
                            # Direct name match
                            if dep_name in conn_value:
                                potential_dependencies[resource_id].add(potential_dep['id'])
                            # For URLs and connection strings, also check without hyphens
                            elif dep_name.replace('-', '') in conn_value.replace('-', ''):
                                potential_dependencies[resource_id].add(potential_dep['id'])
        
        # Enhanced dependency detection using network information (potential dependencies)
        if network_info:
            # Look for dependencies based on hostnames, endpoints, etc.
            for key, value in network_info.items():
                if isinstance(value, (str, list)):
                    value_str = json.dumps(value) if isinstance(value, list) else value
                    for potential_dep in resources:
                        dep_name = potential_dep.get('name', '')
                        if dep_name and dep_name in value_str:
                            potential_dependencies[resource_id].add(potential_dep['id'])
        
        # Type-specific dependency detection (confirmed dependencies from properties)
        if resource_type == 'microsoft.app/containerapps':
            # Container Apps depend on their environment and registry
            if properties and 'managedEnvironmentId' in properties:
                env_id = properties['managedEnvironmentId']
                confirmed_dependencies[resource_id].add(env_id)
            
            # Container Apps secret references and registry dependencies
            if properties and 'configuration' in properties:
                config = properties['configuration']
                
                # Registry dependencies
                if 'registries' in config:
                    for registry in config['registries']:
                        server = registry.get('server', '')
                        # Find the ACR resource by matching the login server
                        for potential_acr in resources:
                            if potential_acr['type'] == 'microsoft.containerregistry/registries':
                                acr_query = f"Resources | where id == '{potential_acr['id']}' | project properties.loginServer"
                                acr_result = run_az_command(f"az graph query -q \"{acr_query}\" --subscription {subscription_id}")
                                if acr_result.get('data') and acr_result['data'][0].get('properties.loginServer') == server:
                                    confirmed_dependencies[resource_id].add(potential_acr['id'])
                
                # Secret references that might point to Key Vault or other services
                if 'secrets' in config:
                    for secret in config['secrets']:
                        secret_name = secret.get('name', '')
                        # Common patterns for secret names that indicate dependencies
                        if 'keyvault' in secret_name.lower() or 'kv' in secret_name.lower():
                            for potential_kv in resources:
                                if potential_kv['type'] == 'microsoft.keyvault/vaults':
                                    potential_dependencies[resource_id].add(potential_kv['id'])
                        elif 'storage' in secret_name.lower():
                            for potential_storage in resources:
                                if potential_storage['type'] == 'microsoft.storage/storageaccounts':
                                    potential_dependencies[resource_id].add(potential_storage['id'])
                        elif 'database' in secret_name.lower() or 'db' in secret_name.lower():
                            for potential_db in resources:
                                if potential_db['type'] in ['microsoft.sql/servers', 'microsoft.documentdb/databaseaccounts', 'microsoft.dbforpostgresql/flexibleservers']:
                                    potential_dependencies[resource_id].add(potential_db['id'])
            
            # Environment variable secret references
            if properties and 'template' in properties and 'containers' in properties['template']:
                for container in properties['template']['containers']:
                    if 'env' in container:
                        for env_var in container['env']:
                            if 'secretRef' in env_var:
                                secret_ref = env_var['secretRef']
                                # Analyze secret reference patterns
                                if 'appinsights' in secret_ref.lower():
                                    for potential_insights in resources:
                                        if potential_insights['type'] == 'microsoft.insights/components':
                                            potential_dependencies[resource_id].add(potential_insights['id'])
                                elif 'webpubsub' in secret_ref.lower() or 'signalr' in secret_ref.lower():
                                    for potential_signalr in resources:
                                        if potential_signalr['type'] in ['microsoft.signalrservice/signalr', 'microsoft.signalrservice/webpubsub']:
                                            potential_dependencies[resource_id].add(potential_signalr['id'])
        
        elif resource_type == 'microsoft.web/sites':
            # Web Apps often depend on App Service Plans (confirmed dependency)
            if properties and 'serverFarmId' in properties:
                confirmed_dependencies[resource_id].add(properties['serverFarmId'])
            
            # Enhanced App Insights detection using environment variables (potential dependencies)
            if env_vars:
                app_settings = env_vars.get('appSettings', {})
                # Look for Application Insights connection strings
                for setting_name, setting_value in app_settings.items():
                    if isinstance(setting_value, str) and 'APPLICATIONINSIGHTS' in setting_name.upper():
                        for potential_insights in resources:
                            if potential_insights['type'] == 'microsoft.insights/components':
                                if potential_insights['name'] in setting_value:
                                    potential_dependencies[resource_id].add(potential_insights['id'])
                
                # Look for database connection strings
                conn_strings = env_vars.get('connectionStrings', {})
                for conn_name, conn_value in conn_strings.items():
                    if isinstance(conn_value, str):
                        # SQL Database dependencies
                        if 'database.windows.net' in conn_value or 'sql.azuresynapse.net' in conn_value:
                            for potential_sql in resources:
                                if potential_sql['type'] in ['microsoft.sql/servers', 'microsoft.sql/servers/databases']:
                                    if potential_sql['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_sql['id'])
                        
                        # Storage Account dependencies
                        if 'blob.core.windows.net' in conn_value or 'table.core.windows.net' in conn_value or 'queue.core.windows.net' in conn_value or 'file.core.windows.net' in conn_value:
                            for potential_storage in resources:
                                if potential_storage['type'] == 'microsoft.storage/storageaccounts':
                                    if potential_storage['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_storage['id'])
                        
                        # Cosmos DB dependencies (MongoDB, SQL API, etc.)
                        if 'cosmos.azure.com' in conn_value or 'documents.azure.com' in conn_value:
                            for potential_cosmos in resources:
                                if potential_cosmos['type'] == 'microsoft.documentdb/databaseaccounts':
                                    if potential_cosmos['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_cosmos['id'])
                        
                        # PostgreSQL dependencies
                        if 'postgres.database.azure.com' in conn_value:
                            for potential_pg in resources:
                                if potential_pg['type'] in ['microsoft.dbforpostgresql/servers', 'microsoft.dbforpostgresql/flexibleservers']:
                                    if potential_pg['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_pg['id'])
                        
                        # MySQL dependencies
                        if 'mysql.database.azure.com' in conn_value:
                            for potential_mysql in resources:
                                if potential_mysql['type'] in ['microsoft.dbformysql/servers', 'microsoft.dbformysql/flexibleservers']:
                                    if potential_mysql['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_mysql['id'])
                        
                        # Service Bus dependencies
                        if 'servicebus.windows.net' in conn_value:
                            for potential_sb in resources:
                                if potential_sb['type'] == 'microsoft.servicebus/namespaces':
                                    if potential_sb['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_sb['id'])
                        
                        # Event Hub dependencies
                        if 'servicebus.windows.net' in conn_value and 'EntityPath=' in conn_value:
                            for potential_eh in resources:
                                if potential_eh['type'] == 'microsoft.eventhub/namespaces':
                                    if potential_eh['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_eh['id'])
                        
                        # Redis Cache dependencies
                        if 'redis.cache.windows.net' in conn_value:
                            for potential_redis in resources:
                                if potential_redis['type'] == 'microsoft.cache/redis':
                                    if potential_redis['name'] in conn_value:
                                        potential_dependencies[resource_id].add(potential_redis['id'])
            
            # Enhanced detection for Key Vault secret references
            if env_vars:
                app_settings = env_vars.get('appSettings', {})
                for setting_name, setting_value in app_settings.items():
                    if isinstance(setting_value, str):
                        # Key Vault secret references (format: @Microsoft.KeyVault(SecretUri=...))
                        if '@Microsoft.KeyVault' in setting_value or 'vault.azure.net' in setting_value:
                            for potential_kv in resources:
                                if potential_kv['type'] == 'microsoft.keyvault/vaults':
                                    if potential_kv['name'] in setting_value:
                                        potential_dependencies[resource_id].add(potential_kv['id'])
                        
                        # Service Bus connection strings in app settings
                        if 'servicebus.windows.net' in setting_value:
                            for potential_sb in resources:
                                if potential_sb['type'] == 'microsoft.servicebus/namespaces':
                                    if potential_sb['name'] in setting_value:
                                        potential_dependencies[resource_id].add(potential_sb['id'])
                        
                        # SignalR/Web PubSub connection strings
                        if 'webpubsub.azure.com' in setting_value or 'service.signalr.net' in setting_value:
                            for potential_signalr in resources:
                                if potential_signalr['type'] in ['microsoft.signalrservice/signalr', 'microsoft.signalrservice/webpubsub']:
                                    if potential_signalr['name'] in setting_value:
                                        potential_dependencies[resource_id].add(potential_signalr['id'])
            
            # Check for App Insights connection in properties (confirmed dependency)
            if properties and 'siteConfig' in properties and properties.get('siteConfig') is not None:
                app_settings = properties.get('siteConfig', {}).get('appSettings')
                if app_settings:
                    for setting in app_settings:
                        if setting.get('name') == 'APPLICATIONINSIGHTS_CONNECTION_STRING' and 'value' in setting:
                            conn_string = setting['value']
                            for potential_insights in resources:
                                if potential_insights['type'] == 'microsoft.insights/components' and potential_insights['name'] in conn_string:
                                    confirmed_dependencies[resource_id].add(potential_insights['id'])
        
        elif resource_type == 'microsoft.insights/components':
            # Application Insights may depend on storage accounts for logs (potential dependency)
            if specific_config:
                for potential_storage in resources:
                    if potential_storage['type'] == 'microsoft.storage/storageaccounts':
                        # Check if storage account is referenced in App Insights config
                        if potential_storage['name'] in json.dumps(specific_config):
                            potential_dependencies[resource_id].add(potential_storage['id'])
        
        elif resource_type == 'microsoft.apimanagement/service':
            # APIM often connected to App Insights (potential dependency)
            for potential_insights in resources:
                if potential_insights['type'] == 'microsoft.insights/components':
                    potential_dependencies[resource_id].add(potential_insights['id'])
            
            # Enhanced APIM dependency detection using configuration (potential dependencies)
            if specific_config:
                # Look for backend services, named values, etc.
                config_str = json.dumps(specific_config)
                for potential_dep in resources:
                    if potential_dep['type'] in ['microsoft.web/sites', 'microsoft.storage/storageaccounts', 'microsoft.keyvault/vaults']:
                        if potential_dep['name'] in config_str:
                            potential_dependencies[resource_id].add(potential_dep['id'])
        
        elif resource_type == 'microsoft.keyvault/vaults':
            # Key Vault may be referenced by other services
            # This is typically a reverse dependency, but we can detect some patterns
            if specific_config:
                access_policies = specific_config.get('accessPolicies', [])
                for policy in access_policies:
                    if isinstance(policy, dict) and 'objectId' in policy:
                        # Could potentially match this to service principals of other resources
                        pass
        
        elif resource_type == 'microsoft.compute/virtualmachines':
            # VMs depend on various resources (potential dependencies from config)
            if specific_config:
                # Check for dependencies on storage accounts (for diagnostics, disks)
                config_str = json.dumps(specific_config)
                for potential_storage in resources:
                    if potential_storage['type'] == 'microsoft.storage/storageaccounts':
                        if potential_storage['name'] in config_str:
                            potential_dependencies[resource_id].add(potential_storage['id'])
            
            # VMs depend on their network interfaces (confirmed dependency)
            if properties and 'networkProfile' in properties:
                network_interfaces = properties.get('networkProfile', {}).get('networkInterfaces', [])
                for nic in network_interfaces:
                    if isinstance(nic, dict) and 'id' in nic:
                        confirmed_dependencies[resource_id].add(nic['id'])
        
        elif resource_type == 'microsoft.storage/storageaccounts':
            # Storage accounts may have network restrictions pointing to VNets (confirmed dependency)
            if specific_config and 'networkRuleSet' in specific_config:
                network_rules = specific_config.get('networkRuleSet', {})
                if 'virtualNetworkRules' in network_rules:
                    for vnet_rule in network_rules['virtualNetworkRules']:
                        if isinstance(vnet_rule, dict) and 'id' in vnet_rule:
                            # This points to a subnet, we need to find the parent VNet
                            subnet_id = vnet_rule['id']
                            for potential_vnet in resources:
                                if potential_vnet['type'] == 'microsoft.network/virtualnetworks':
                                    if potential_vnet['id'] in subnet_id:
                                        confirmed_dependencies[resource_id].add(potential_vnet['id'])
    
    # Add common implicit dependencies based on resource types (potential dependencies)
    for resource in resources:
        resource_id = resource['id']
        resource_type = resource['type']
        
        # Add implicit dependency for dashboard -> App Insights
        if resource_type == 'microsoft.portal/dashboards':
            for potential_dep in resources:
                if potential_dep['type'] == 'microsoft.insights/components':
                    potential_dependencies[resource_id].add(potential_dep['id'])
        
        # Container App Environment -> App Insights
        if resource_type == 'microsoft.app/managedenvironments':
            for potential_dep in resources:
                if potential_dep['type'] == 'microsoft.insights/components':
                    potential_dependencies[resource_id].add(potential_dep['id'])
    
    return confirmed_dependencies, potential_dependencies

def get_resource_data(subscription_id: str = None, basic_mode: bool = False) -> Tuple[str, List[dict], List[dict], Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Collect all Azure resource data needed for visualization.
    
    Args:
        subscription_id: The Azure subscription ID (if None, uses current subscription)
        basic_mode: If True, only gather basic resource information
        
    Returns:
        A tuple containing (subscription_id, resources, resource_groups, confirmed_dependencies, potential_dependencies)
    """
    # Check prerequisites
    if not check_az_cli_installed():
        print("Error: Azure CLI not found. Please install it first: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)
    
    if not check_az_cli_logged_in():
        print("Error: Not logged in to Azure. Please run 'az login' first.")
        sys.exit(1)
    
    # Get subscription ID
    if not subscription_id:
        subscription_id = get_subscription_id()
        
    truncated_sub_id = truncate_subscription_id(subscription_id)
    print(f"Using subscription: {truncated_sub_id}")
    
    # Get resources and resource groups
    print("Fetching resource groups...")
    resource_groups = list_resource_groups(subscription_id)
    print(f"Found {len(resource_groups)} resource groups")
    
    # Get resources (basic or enhanced mode)
    resources = list_resources(subscription_id, basic_mode)
    print(f"Found {len(resources)} resources {'(basic mode)' if basic_mode else '(enhanced mode)'}")
    
    # Analyze dependencies using enhanced resource data
    confirmed_dependencies, potential_dependencies = get_resource_dependencies(subscription_id, resources)
    
    # Print summary of enhanced data collected
    enhanced_count = sum(1 for r in resources if any(key in r for key in ['networkInfo', 'environmentVariables', 'specificConfiguration']))
    print(f"Enhanced {enhanced_count}/{len(resources)} resources with detailed information")
    
    # Print dependency summary
    total_confirmed_deps = sum(len(deps) for deps in confirmed_dependencies.values())
    total_potential_deps = sum(len(deps) for deps in potential_dependencies.values())
    print(f"Discovered {total_confirmed_deps} confirmed dependencies and {total_potential_deps} potential dependencies")
    
    return subscription_id, resources, resource_groups, confirmed_dependencies, potential_dependencies

def main():
    parser = argparse.ArgumentParser(description='Generate Azure resource dependency graph with enhanced resource discovery')
    parser.add_argument('--subscription', '-s', type=str, help='Azure subscription ID (if not provided, uses current subscription)')
    parser.add_argument('--no-potential-deps', action='store_true', help='Exclude potential dependencies from the diagram')
    parser.add_argument('--output', '-o', type=str, default='azure_resource_graph', help='Output file path prefix')
    parser.add_argument('--no-data', action='store_true', help='Use existing data file instead of fetching from Azure')
    parser.add_argument('--no-html', action='store_true', help='Skip HTML visualization generation')
    parser.add_argument('--no-md', action='store_true', help='Skip Markdown visualization generation')
    parser.add_argument('--basic-mode', action='store_true', help='Use basic resource discovery without enhanced details (faster but less comprehensive)')
    args = parser.parse_args()

    # Determine whether to collect data or use existing file
    data_file = f"{args.output}.json"
    
    if not args.no_data:
        # Query Azure for resource data
        subscription_id, resources, resource_groups, confirmed_dependencies, potential_dependencies = get_resource_data(args.subscription, args.basic_mode)
        
        # Save data to file
        deps_serializable = {k: list(v) for k, v in confirmed_dependencies.items()}
        total_confirmed_deps = sum(len(deps) for deps in confirmed_dependencies.values())
        total_potential_deps = sum(len(deps) for deps in potential_dependencies.values())
        data = {
            'subscription_id': subscription_id,
            'resources': resources,
            'resource_groups': resource_groups,
            'confirmed_dependencies': deps_serializable,
            'potential_dependencies': {k: list(v) for k, v in potential_dependencies.items()},
            'metadata': {
                'enhanced_mode': not args.basic_mode,
                'total_resources': len(resources),
                'total_confirmed_dependencies': total_confirmed_deps,
                'total_potential_dependencies': total_potential_deps,
                'enhanced_resources': sum(1 for r in resources if any(key in r for key in ['networkInfo', 'environmentVariables', 'specificConfiguration'])) if not args.basic_mode else 0
            }
        }
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Resource data saved to {data_file}")
        if not args.basic_mode:
            print(f"Enhanced data includes network info, environment variables, and detailed configurations")
    else:
        try:
            print(f"Loading resource data from {data_file}...")
            with open(data_file, 'r') as f:
                data = json.load(f)
                subscription_id = data['subscription_id']
                resources = data['resources']
                resource_groups = data['resource_groups']
                confirmed_dependencies = {k: set(v) for k, v in data['confirmed_dependencies'].items()}
                potential_dependencies = {k: set(v) for k, v in data['potential_dependencies'].items()}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading data file: {e}")
            print("Falling back to querying Azure...")
            subscription_id, resources, resource_groups, confirmed_dependencies, potential_dependencies = get_resource_data(args.subscription, args.basic_mode)

    include_potential_deps = not args.no_potential_deps

    # Generate HTML output if requested
    if not args.no_html:
        from arg_html import generate_html_diagram
        html_file = f"{args.output}.html"
        print("Generating interactive HTML diagram...")
        generate_html_diagram(
            subscription_id, 
            resources, 
            resource_groups, 
            confirmed_dependencies,
            potential_dependencies,
            include_potential_deps,
            html_file
        )
        print(f"HTML diagram saved to {html_file}")

    # Generate Markdown output if requested
    if not args.no_md:
        from arg_mermaid import generate_mermaid_diagram
        md_file = f"{args.output}.md"
        print("Generating mermaid diagram...")
        mermaid_diagram = generate_mermaid_diagram(
            subscription_id, 
            resources, 
            resource_groups, 
            confirmed_dependencies,
            potential_dependencies,
            include_potential_deps
        )
        
        # Save to file
        with open(md_file, 'w') as f:
            f.write("# Azure Resources Dependency Graph\n\n")
            f.write("This diagram shows the resources in your Azure subscription and their dependencies.\n\n")
            f.write("- Resources are displayed with their proper Azure display names and resource names\n")
            f.write("- Resource types and kinds are included for better identification\n")
            f.write("- Solid lines represent confirmed dependencies\n")
            if include_potential_deps:
                f.write("- Dotted lines represent potential dependencies based on common patterns\n")
            f.write("\n```mermaid\n")
            f.write(mermaid_diagram)
            f.write("\n```\n")
        
        print(f"Markdown diagram saved to {md_file}")
    
    # Print final summary
    mode_msg = "basic mode (faster, less comprehensive)" if args.basic_mode else "enhanced mode (comprehensive resource analysis)"
    print(f"\n✅ Resource graph generation completed using {mode_msg}")
    
    if include_potential_deps:
        print("Included both confirmed and potential dependencies.")
    else:
        print("Included only confirmed dependencies. Potential dependencies were excluded.")
    
    if not args.basic_mode:
        print("Enhanced features included:")
        print("  - Network information (IPs, hostnames, endpoints)")
        print("  - Environment variables and configuration settings")
        print("  - Resource-specific detailed configurations")
        print("  - Advanced dependency detection using configuration data")
    else:
        print("To get more detailed resource information and better dependency detection, run without --basic-mode")

if __name__ == "__main__":
    main() 