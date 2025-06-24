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
import time
from typing import Dict, List, Set, Tuple, Optional, Any, Callable, TypeVar
from functools import wraps

# Import the visualization modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Global list to collect non-fatal errors and warnings
_failed_operations_log: List[str] = []

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

def log_failure(message: str):
    """Logs a failure message that allows the script to continue."""
    global _failed_operations_log
    _failed_operations_log.append(message)
    print(f"Warning: {message}", file=sys.stderr)

def truncate_subscription_id(subscription_id: str) -> str:
    """
    Truncate subscription ID to first 10 characters plus ellipsis.
    
    Args:
        subscription_id: The full Azure subscription ID
        
    Returns:
        Truncated subscription ID
    """
    return subscription_id[:10] + "..."

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0) -> Callable[[F], F]:
    """
    A decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of times to retry the function.
        initial_delay: Initial delay in seconds before the first retry.
        backoff_factor: Factor by which the delay increases for each retry.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except subprocess.CalledProcessError as e:
                    # Check for throttling or other retryable errors
                    stderr_output = e.stderr if e.stderr else "{e}"
                    if "RateLimiting" in stderr_output or "TooManyRequests" in stderr_output or "Throttled" in stderr_output:
                        log_failure(f"Attempt {i+1}/{max_retries+1}: Command failed due to throttling. Retrying in {delay:.2f}s. Command: {args[0] if args else 'N/A'}")
                        if i < max_retries:
                            time.sleep(delay)
                            delay *= backoff_factor
                        else:
                            log_failure(f"Max retries reached for command: {args[0] if args else 'N/A'}. Giving up.")
                            raise # Re-raise the last exception if max retries reached
                    else:
                        log_failure(f"Non retryable error encountered, Error: {e}")
                        raise
                except Exception as e:
                    log_failure(f"Attempt {i+1}/{max_retries+1}: An unexpected error occurred. Retrying in {delay:.2f}s. Error: {e}")
                    if i < max_retries:
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        log_failure(f"Max retries reached for unexpected error. Giving up.")
                        raise
            return None # Should not be reached
        return wrapper
    return decorator

@retry_with_backoff()
#def run_az_command(command: str) -> Optional[Any]:
def _run_az_command(command: str) -> Optional[Any]:
    """
    Run an Azure CLI command and return its output (JSON parsed or raw string).
    
    Args:
        command: The Azure CLI command to run
        
    Returns:
        The parsed JSON output (dict/list), raw string output, or None if an error occurs.
    """
    print(f"Executing command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If not valid JSON, return the raw string output
                return result.stdout.strip()
        return None # Command ran successfully but returned no output
    except subprocess.CalledProcessError as e:
        # This will be caught by the decorator's exception handling
        log_failure(f"Error executing command {' '.join(command)}: {e.stderr}")
        raise
    except Exception as e: # Catch any other unexpected errors
        # This will be caught by the decorator's exception handling
        raise

#def run_az_command_all_pages(command: str) -> list[dict]:
def run_az_command(command: str) -> list[dict]:
    all_results = []
    skip_token = None
    original_command = command

    while True:
        command = f"{original_command} --first 1000"
        if skip_token:
            command += f" --skip-token \"{skip_token}\""

        try:
            response = _run_az_command(command)  # Retry handled here
        except Exception as e:
            print(f"Failed to fetch page with skipToken={skip_token}: {e}")
            break

        if not response:
            break

        all_results.extend(response.get("data", []))
        skip_token = response.get("skipToken")
        if not skip_token:
            break

    return {'data': all_results}

@retry_with_backoff()
def run_az_command_list(command: List[str], subscription_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run an Azure CLI command from a list and return the JSON output.
    
    Args:
        command: The Azure CLI command as a list
        subscription_id: Optional subscription ID
        
    Returns:
        The parsed JSON output of the command
    """
    print(f"Executing command: {' '.join(command)}")
    full_command = list(command) # Create a copy to avoid modifying the original list
    
    try:
        if subscription_id:
            full_command.extend(['--subscription', subscription_id])
        
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            return json.loads(result.stdout)
        return {}
        
    except subprocess.CalledProcessError as e:
        # This will be caught by the decorator's exception handling
        log_failure(f"Error executing command {' '.join(full_command)}: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        log_failure(f"Error parsing JSON response from command {' '.join(full_command)}: {e}")
        return {}
    except Exception as e:
        # This will be caught by the decorator's exception handling
        raise


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

def get_subscription_id() -> Optional[str]:
    """Get the current Azure subscription ID."""
    try:
        result = run_az_command("az account show --query id -o json")
        if result is None:
            log_failure("Failed to retrieve subscription ID.")
            return None
        if isinstance(result, str):
            return result.strip('"')
        elif isinstance(result, dict) and 'id' in result:
            return result['id']
        log_failure(f"Unexpected format for subscription ID: {result}")
        return None
    except Exception as e:
        log_failure(f"Error in get_subscription_id: {e}")
        return None

def list_resource_groups(subscription_id: str, resource_group_ids_to_include: List[str] = []) -> List[Dict[str, Any]]:
    """
    List all resource groups in the subscription.
    
    Args:
        subscription_id: The Azure subscription ID
        resource_group_ids_to_include: List of resourceGroupIDs to include in the data
    Returns:
        A list of resource group objects
    """
    query = f"ResourceContainers | where type == 'microsoft.resources/subscriptions/resourcegroups' | where subscriptionId == '{subscription_id}' | project name, id"
    if resource_group_ids_to_include:
        or_id_has = "' or id has '"
        query += f' | where id has \'{or_id_has.join(resource_group_ids_to_include)}\''
    print(f"Resource Group Query: {query}")
    try:
        result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
        if result is None:
            log_failure(f"Failed to retrieve resource groups for subscription {subscription_id}.")
            return []
        if isinstance(result, dict):
            return result.get('data', [])
        log_failure(f"Unexpected format for resource groups: {result}")
        return []
    except Exception as e:
        log_failure(f"Error in list_resource_groups for subscription {subscription_id}: {e}")
        return []

def get_network_information(resource: Dict[str, Any], subscription_id: str, detailed_resource_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get network information for addressable resources"""
    resource_type = resource.get('type', '').lower()
    resource_group = resource.get('resourceGroup', '')
    name = resource.get('name', '')
    network_info = {}
    
    if not resource_group or not name:
        log_failure(f"Skipping network info for resource {name} due to missing resourceGroup or name.")
        return network_info

    try:
        # Virtual Machines
        if 'microsoft.compute/virtualmachines' == resource_type:
            if detailed_resource_data:
                vm_details = detailed_resource_data
            else:
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
        
        # Virtual Machine Scale Sets
        elif 'microsoft.compute/virtualmachinescalesets' == resource_type:
            if detailed_resource_data:
                vmss_details = detailed_resource_data
            else:
                vmss_details = run_az_command_list([
                    'az', 'vmss', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ], subscription_id)
            
            if vmss_details:
                # Get basic VMSS network configuration
                network_profile = vmss_details.get('virtualMachineProfile', {}).get('networkProfile', {})
                network_interface_configs = network_profile.get('networkInterfaceConfigurations', [])
                
                public_ips = []
                load_balancers = []
                
                for nic_config in network_interface_configs:
                    if isinstance(nic_config, dict):
                        ip_configs = nic_config.get('ipConfigurations', [])
                        for ip_config in ip_configs:
                            if isinstance(ip_config, dict):
                                # Check for public IP configurations
                                public_ip_config = ip_config.get('publicIPAddressConfiguration')
                                if public_ip_config:
                                    public_ips.append(public_ip_config.get('name', 'Unknown'))
                                
                                # Check for load balancer backend pools
                                lb_backend_pools = ip_config.get('loadBalancerBackendAddressPools', [])
                                for pool in lb_backend_pools:
                                    if isinstance(pool, dict) and 'id' in pool:
                                        # Extract load balancer name from the ID
                                        lb_id_parts = pool['id'].split('/')
                                        if len(lb_id_parts) >= 9:
                                            load_balancers.append(lb_id_parts[8])
                
                network_info.update({
                    'publicIPConfigurations': public_ips,
                    'associatedLoadBalancers': load_balancers,
                    'instanceCount': vmss_details.get('sku', {}).get('capacity', 0)
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
                frontend_configs = lb_details.get('frontendIPConfigurations', [])
                if isinstance(frontend_configs, list):
                    for frontend in frontend_configs:
                        public_ip_address = frontend.get('publicIPAddress')
                        if public_ip_address and isinstance(public_ip_address, dict):
                            frontend_ips.append(public_ip_address.get('id', '').split('/')[-1])
                else:
                    log_failure(f"Unexpected format for 'frontendIPConfigurations' in LB {name}. Expected list, got {type(frontend_configs)}.")
                network_info['frontendIPs'] = frontend_ips
        
        # App Services (but NOT Function Apps)
        elif 'microsoft.web/sites' in resource_type and 'functionapp' not in resource.get('kind', '').lower():
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
        
        # Function Apps - Use comprehensive networking data
        elif 'microsoft.web/sites' in resource_type and 'functionapp' in resource.get('kind', '').lower():
            if detailed_resource_data and 'functionAppConfig' in detailed_resource_data:
                # Use pre-fetched comprehensive Function App data
                func_config = detailed_resource_data['functionAppConfig']
                
                # Basic network info from metadata
                metadata = func_config.get('metadata', {})
                if metadata:
                    network_info.update({
                        'defaultHostName': metadata.get('defaultHostName'),
                        'hostNames': metadata.get('hostNames', []),
                        'outboundIpAddresses': metadata.get('outboundIpAddresses', '').split(',') if metadata.get('outboundIpAddresses') else [],
                        'possibleOutboundIpAddresses': metadata.get('possibleOutboundIpAddresses', '').split(',') if metadata.get('possibleOutboundIpAddresses') else []
                    })
                
                # VNET Integration
                vnet_integration = func_config.get('vnetIntegration', [])
                if vnet_integration and isinstance(vnet_integration, list):
                    vnet_info = []
                    for vnet in vnet_integration:
                        if isinstance(vnet, dict):
                            vnet_info.append({
                                'vnetResourceId': vnet.get('vnetResourceId'),
                                'subnetResourceId': vnet.get('subnetResourceId'),
                                'name': vnet.get('name')
                            })
                    network_info['vnetIntegration'] = vnet_info
                
                # Private Endpoints
                private_endpoints = func_config.get('privateEndpoints', [])
                if private_endpoints and isinstance(private_endpoints, list):
                    pe_info = []
                    for pe in private_endpoints:
                        if isinstance(pe, dict):
                            pe_info.append({
                                'name': pe.get('name'),
                                'id': pe.get('id'),
                                'connectionState': pe.get('properties', {}).get('connectionState'),
                                'privateEndpoint': pe.get('properties', {}).get('privateEndpoint')
                            })
                    network_info['privateEndpoints'] = pe_info
                
                # Hybrid Connections
                hybrid_connections = func_config.get('hybridConnections', [])
                if hybrid_connections and isinstance(hybrid_connections, list):
                    hc_info = []
                    for hc in hybrid_connections:
                        if isinstance(hc, dict):
                            hc_info.append({
                                'name': hc.get('name'),
                                'resourceGroup': hc.get('resourceGroup'),
                                'hostname': hc.get('hostname'),
                                'port': hc.get('port')
                            })
                    network_info['hybridConnections'] = hc_info
            else:
                # Fallback to basic Function App details
                app_details = run_az_command_list([
                    'az', 'functionapp', 'show',
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
        log_failure(f"Error getting network info for {name} ({resource_type}): {str(e)}")
        
    return network_info

def get_function_app_full_config(resource_group: str, name: str, subscription_id: str) -> Dict[str, Any]:
    """Get comprehensive Function App configuration data similar to function_app_info.sh"""
    full_config = {}
    
    try:
        # Function App metadata
        metadata = run_az_command_list([
            'az', 'functionapp', 'show',
            '--resource-group', resource_group,
            '--name', name
        ], subscription_id)
        if metadata:
            full_config['metadata'] = metadata
        
        # App Settings (Environment Variables)
        app_settings = run_az_command_list([
            'az', 'functionapp', 'config', 'appsettings', 'list',
            '--resource-group', resource_group,
            '--name', name
        ], subscription_id)
        if app_settings:
            full_config['appSettings'] = app_settings
        
        # Runtime Configuration
        config = run_az_command_list([
            'az', 'functionapp', 'config', 'show',
            '--resource-group', resource_group,
            '--name', name
        ], subscription_id)
        if config:
            full_config['config'] = config
        
        # Authentication Settings
        try:
            auth = run_az_command_list([
                'az', 'webapp', 'auth', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if auth:
                full_config['auth'] = auth
        except Exception as e:
            log_failure(f"Error getting auth settings for Function App {name}: {str(e)}")
        
        # VNET Integration
        try:
            vnet_integration = run_az_command_list([
                'az', 'functionapp', 'vnet-integration', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if vnet_integration:
                full_config['vnetIntegration'] = vnet_integration
        except Exception as e:
            log_failure(f"Error getting VNET integration for Function App {name}: {str(e)}")
        
        # Private Endpoint Connections
        try:
            private_endpoints = run_az_command_list([
                'az', 'network', 'private-endpoint-connection', 'list',
                '--resource-group', resource_group,
                '--name', name,
                '--type', 'Microsoft.Web/sites'
            ], subscription_id)
            if private_endpoints:
                full_config['privateEndpoints'] = private_endpoints
        except Exception as e:
            log_failure(f"Error getting private endpoints for Function App {name}: {str(e)}")
        
        # Hybrid Connections
        try:
            hybrid_connections = run_az_command_list([
                'az', 'functionapp', 'hybrid-connection', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if hybrid_connections:
                full_config['hybridConnections'] = hybrid_connections
        except Exception as e:
            log_failure(f"Error getting hybrid connections for Function App {name}: {str(e)}")
            
    except Exception as e:
        log_failure(f"Error getting full config for Function App {name}: {str(e)}")
    
    return full_config

def get_environment_variables(resource: Dict[str, Any], subscription_id: str, detailed_resource_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get environment variables for supported resources"""
    resource_type = resource.get('type', '').lower()
    resource_group = resource.get('resourceGroup', '')
    name = resource.get('name', '')
    env_vars = {}

    if not resource_group or not name:
        log_failure(f"Skipping environment variables for resource {name} due to missing resourceGroup or name.")
        return env_vars
    
    try:
        # App Service / Web Apps (but NOT Function Apps)
        if 'microsoft.web/sites' in resource_type and 'functionapp' in resource.get('kind', '').lower():
            app_settings = run_az_command_list([
                'az', 'webapp', 'config', 'appsettings', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if isinstance(app_settings, list):
                env_vars['appSettings'] = {setting.get('name'): setting.get('value') for setting in app_settings if isinstance(setting, dict) and setting.get('name')}
            
            # Get connection strings
            conn_strings = run_az_command_list([
                'az', 'webapp', 'config', 'connection-string', 'list',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if isinstance(conn_strings, list):
                env_vars['connectionStrings'] = {cs.get('name'): cs.get('value') for cs in conn_strings if isinstance(cs, dict) and cs.get('name')}
        
        # Function Apps - Use comprehensive configuration
        elif 'microsoft.web/sites' in resource_type and 'functionapp' in resource.get('kind', '').lower():
            if detailed_resource_data and 'functionAppConfig' in detailed_resource_data:
                # Use pre-fetched comprehensive Function App data
                func_config = detailed_resource_data['functionAppConfig']
                
                # App Settings
                app_settings = func_config.get('appSettings', [])
                if isinstance(app_settings, list):
                    env_vars['functionAppSettings'] = {setting.get('name'): setting.get('value') for setting in app_settings if isinstance(setting, dict) and setting.get('name')}
                
                # Runtime Configuration
                runtime_config = func_config.get('config', {})
                if runtime_config:
                    env_vars['runtimeConfig'] = runtime_config
                
                # Authentication Settings
                auth_config = func_config.get('auth', {})
                if auth_config:
                    env_vars['authConfig'] = auth_config
            else:
                # Fallback to basic Function App settings
                func_settings = run_az_command_list([
                    'az', 'functionapp', 'config', 'appsettings', 'list',
                    '--resource-group', resource_group,
                    '--name', name
                ], subscription_id)
                if isinstance(func_settings, list):
                    env_vars['functionAppSettings'] = {setting.get('name'): setting.get('value') for setting in func_settings if isinstance(setting, dict) and setting.get('name')}
        
        # Virtual Machines (can have custom script extensions, cloud-init, and custom data with environment variables)
        elif 'microsoft.compute/virtualmachines' == resource_type:
            if detailed_resource_data:
                vm_details = detailed_resource_data
            else:
                vm_details = run_az_command_list([
                    'az', 'vm', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ], subscription_id)
            
            if vm_details:
                # Extract custom data (base64 encoded user data)
                os_profile = vm_details.get('osProfile', {})
                custom_data = os_profile.get('customData')
                if custom_data:
                    env_vars['customData'] = custom_data
                
                # Extract cloud-init data for Linux VMs
                linux_config = os_profile.get('linuxConfiguration', {})
                if linux_config:
                    env_vars['linuxConfiguration'] = linux_config
                
                # Extract Windows configuration
                windows_config = os_profile.get('windowsConfiguration', {})
                if windows_config:
                    env_vars['windowsConfiguration'] = windows_config
            
            # Get VM extensions which may contain environment variables
            try:
                vm_extensions = run_az_command_list([
                    'az', 'vm', 'extension', 'list',
                    '--resource-group', resource_group,
                    '--vm-name', name
                ], subscription_id)
                
                if isinstance(vm_extensions, list):
                    for ext in vm_extensions:
                        if isinstance(ext, dict):
                            ext_name = ext.get('name', 'unknown')
                            ext_type = ext.get('typeHandlerVersion', ext.get('type', 'unknown'))
                            
                            # Custom Script Extension for Windows
                            if 'CustomScriptExtension' in ext.get('type', ''):
                                settings = ext.get('settings', {})
                                if isinstance(settings, dict):
                                    if settings.get('commandToExecute'):
                                        env_vars[f'extension_{ext_name}_command'] = settings['commandToExecute']
                                    if settings.get('fileUris'):
                                        env_vars[f'extension_{ext_name}_fileUris'] = settings['fileUris']
                            
                            # Custom Script Extension for Linux
                            elif 'CustomScript' in ext.get('type', '') and 'Linux' in ext.get('type', ''):
                                settings = ext.get('settings', {})
                                if isinstance(settings, dict):
                                    if settings.get('commandToExecute'):
                                        env_vars[f'extension_{ext_name}_command'] = settings['commandToExecute']
                                    if settings.get('script'):
                                        env_vars[f'extension_{ext_name}_script'] = settings['script']
                                    if settings.get('fileUris'):
                                        env_vars[f'extension_{ext_name}_fileUris'] = settings['fileUris']
                            
                            # Docker Extension
                            elif 'DockerExtension' in ext.get('type', ''):
                                settings = ext.get('settings', {})
                                if isinstance(settings, dict):
                                    env_vars[f'extension_{ext_name}_docker'] = settings
                            
                            # Other extensions that might have configuration
                            else:
                                settings = ext.get('settings', {})
                                protected_settings = ext.get('protectedSettings', {})
                                if settings or protected_settings:
                                    ext_config = {}
                                    if settings:
                                        ext_config['settings'] = settings
                                    if protected_settings:
                                        ext_config['protectedSettings'] = 'PROTECTED_DATA'  # Don't expose sensitive data
                                    env_vars[f'extension_{ext_name}_{ext_type}'] = ext_config
                else:
                    log_failure(f"Unexpected format for VM extensions in {name}. Expected list, got {type(vm_extensions)}.")
            except Exception as e:
                log_failure(f"Error getting VM extensions for {name}: {str(e)}")
        
        # Virtual Machine Scale Sets (can have custom script extensions with environment variables)
        elif 'microsoft.compute/virtualmachinescalesets' == resource_type:
            if detailed_resource_data:
                vmss_details = detailed_resource_data
            else:
                vmss_details = run_az_command_list([
                    'az', 'vmss', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ], subscription_id)
            
            if vmss_details:
                vm_profile = vmss_details.get('virtualMachineProfile', {})
                extension_profile = vm_profile.get('extensionProfile', {})
                extensions = extension_profile.get('extensions', [])
                
                if isinstance(extensions, list):
                    for ext in extensions:
                        if isinstance(ext, dict):
                            ext_settings = ext.get('settings', {})
                            if isinstance(ext_settings, dict) and ext_settings.get('commandToExecute'):
                                # Extract environment variables from custom script extensions
                                command = ext_settings['commandToExecute']
                                env_vars[f'extension_{ext.get("name", "unknown")}_command'] = command
                else:
                    log_failure(f"Unexpected format for 'extensions' in VMSS {name}. Expected list, got {type(extensions)}.")
        
        # Container Instances
        elif 'microsoft.containerinstance/containergroups' in resource_type:
            container_details = run_az_command_list([
                'az', 'container', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if container_details:
                containers = container_details.get('containers', [])
                if isinstance(containers, list):
                    for i, container in enumerate(containers):
                        if isinstance(container, dict) and container.get('environmentVariables'):
                            env_vars[f'container_{i}_env'] = {
                                env.get('name'): env.get('value', env.get('secureValue', 'SECURE_VALUE'))
                                for env in container['environmentVariables'] if isinstance(env, dict) and env.get('name')
                            }
                else:
                    log_failure(f"Unexpected format for 'containers' in Container Group {name}. Expected list, got {type(containers)}.")
                        
    except Exception as e:
        log_failure(f"Error getting environment variables for {name} ({resource_type}): {str(e)}")
        
    return env_vars

def get_resource_specific_config(resource: Dict[str, Any], subscription_id: str, detailed_resource_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get resource-specific configuration details"""
    resource_type = resource.get('type', '').lower()
    resource_group = resource.get('resourceGroup', '')
    name = resource.get('name', '')
    config = {}

    if not resource_group or not name:
        log_failure(f"Skipping specific config for resource {name} due to missing resourceGroup or name.")
        return config
    
    try:
        # Virtual Machines
        if 'microsoft.compute/virtualmachines' == resource_type:
            if detailed_resource_data:
                vm_details = detailed_resource_data
            else:
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
        
        # Virtual Machine Scale Sets
        elif 'microsoft.compute/virtualmachinescalesets' == resource_type:
            if detailed_resource_data:
                vmss_details = detailed_resource_data
            else:
                vmss_details = run_az_command_list([
                    'az', 'vmss', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ], subscription_id)
            
            if vmss_details:
                vm_profile = vmss_details.get('virtualMachineProfile', {})
                config.update({
                    'vmSize': vm_profile.get('hardwareProfile', {}).get('vmSize'),
                    'osType': vm_profile.get('storageProfile', {}).get('osDisk', {}).get('osType'),
                    'imageReference': vm_profile.get('storageProfile', {}).get('imageReference'),
                    'adminUsername': vm_profile.get('osProfile', {}).get('adminUsername'),
                    'capacity': vmss_details.get('sku', {}).get('capacity'),
                    'upgradePolicy': vmss_details.get('upgradePolicy'),
                    'provisioningState': vmss_details.get('provisioningState'),
                    'overprovision': vmss_details.get('overprovision'),
                    'singlePlacementGroup': vmss_details.get('singlePlacementGroup')
                })
        
        # Storage Accounts
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
            resource_id_parts = resource.get('id', '').split('/')
            server_name = ''
            if len(resource_id_parts) > 8:
                server_name = resource_id_parts[8]
            
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
            else:
                log_failure(f"Could not extract server name from resource ID for SQL Database {name}.")
        
        # Key Vaults
        elif 'microsoft.keyvault/vaults' in resource_type:
            kv_details = run_az_command_list([
                'az', 'keyvault', 'show',
                '--resource-group', resource_group,
                '--name', name
            ], subscription_id)
            if kv_details:
                properties_dict = kv_details.get('properties', {})
                access_policies = properties_dict.get('accessPolicies', [])
                if not isinstance(access_policies, list):
                    log_failure(f"Unexpected format for 'accessPolicies' in Key Vault {name}. Expected list, got {type(access_policies)}.")
                    access_policies = []
                config.update({
                    'sku': properties_dict.get('sku'),
                    'accessPolicies': access_policies,
                    'enabledForDeployment': properties_dict.get('enabledForDeployment'),
                    'enabledForTemplateDeployment': properties_dict.get('enabledForTemplateDeployment')
                })
        
        # Function Apps - Use comprehensive configuration data
        elif 'microsoft.web/sites' in resource_type and 'functionapp' in resource.get('kind', '').lower():
            if detailed_resource_data and 'functionAppConfig' in detailed_resource_data:
                # Use pre-fetched comprehensive Function App data
                func_config = detailed_resource_data['functionAppConfig']
                
                # Runtime and hosting configuration
                runtime_config = func_config.get('config', {})
                metadata = func_config.get('metadata', {})
                
                if metadata:
                    config.update({
                        'state': metadata.get('state'),
                        'hostingEnvironmentProfile': metadata.get('hostingEnvironmentProfile'),
                        'serverFarmId': metadata.get('serverFarmId'),
                        'reserved': metadata.get('reserved'),  # Linux vs Windows
                        'isXenon': metadata.get('isXenon'),
                        'hyperV': metadata.get('hyperV'),
                        'siteConfig': metadata.get('siteConfig', {}),
                        'scmSiteAlsoStopped': metadata.get('scmSiteAlsoStopped'),
                        'clientAffinityEnabled': metadata.get('clientAffinityEnabled'),
                        'clientCertEnabled': metadata.get('clientCertEnabled'),
                        'httpsOnly': metadata.get('httpsOnly'),
                        'redundancyMode': metadata.get('redundancyMode'),
                        'storageAccountRequired': metadata.get('storageAccountRequired')
                    })
                
                if runtime_config:
                    config.update({
                        'runtimeConfig': {
                            'numberOfWorkers': runtime_config.get('numberOfWorkers'),
                            'defaultDocuments': runtime_config.get('defaultDocuments'),
                            'netFrameworkVersion': runtime_config.get('netFrameworkVersion'),
                            'phpVersion': runtime_config.get('phpVersion'),
                            'pythonVersion': runtime_config.get('pythonVersion'),
                            'nodeVersion': runtime_config.get('nodeVersion'),
                            'powerShellVersion': runtime_config.get('powerShellVersion'),
                            'linuxFxVersion': runtime_config.get('linuxFxVersion'),
                            'windowsFxVersion': runtime_config.get('windowsFxVersion'),
                            'requestTracingEnabled': runtime_config.get('requestTracingEnabled'),
                            'remoteDebuggingEnabled': runtime_config.get('remoteDebuggingEnabled'),
                            'httpLoggingEnabled': runtime_config.get('httpLoggingEnabled'),
                            'logsDirectorySizeLimit': runtime_config.get('logsDirectorySizeLimit'),
                            'detailedErrorLoggingEnabled': runtime_config.get('detailedErrorLoggingEnabled'),
                            'publishingUsername': runtime_config.get('publishingUsername'),
                            'appSettings': runtime_config.get('appSettings'),
                            'connectionStrings': runtime_config.get('connectionStrings'),
                            'machineKey': runtime_config.get('machineKey'),
                            'handlerMappings': runtime_config.get('handlerMappings'),
                            'documentRoot': runtime_config.get('documentRoot'),
                            'scmType': runtime_config.get('scmType'),
                            'use32BitWorkerProcess': runtime_config.get('use32BitWorkerProcess'),
                            'webSocketsEnabled': runtime_config.get('webSocketsEnabled'),
                            'alwaysOn': runtime_config.get('alwaysOn'),
                            'javaVersion': runtime_config.get('javaVersion'),
                            'javaContainer': runtime_config.get('javaContainer'),
                            'javaContainerVersion': runtime_config.get('javaContainerVersion'),
                            'managedPipelineMode': runtime_config.get('managedPipelineMode'),
                            'virtualApplications': runtime_config.get('virtualApplications'),
                            'loadBalancing': runtime_config.get('loadBalancing'),
                            'experiments': runtime_config.get('experiments'),
                            'limits': runtime_config.get('limits'),
                            'autoHealEnabled': runtime_config.get('autoHealEnabled'),
                            'autoHealRules': runtime_config.get('autoHealRules'),
                            'tracingOptions': runtime_config.get('tracingOptions'),
                            'vnetName': runtime_config.get('vnetName'),
                            'cors': runtime_config.get('cors'),
                            'push': runtime_config.get('push'),
                            'apiDefinition': runtime_config.get('apiDefinition'),
                            'autoSwapSlotName': runtime_config.get('autoSwapSlotName'),
                            'localMySqlEnabled': runtime_config.get('localMySqlEnabled'),
                            'managedServiceIdentityId': runtime_config.get('managedServiceIdentityId'),
                            'xManagedServiceIdentityId': runtime_config.get('xManagedServiceIdentityId'),
                            'ipSecurityRestrictions': runtime_config.get('ipSecurityRestrictions'),
                            'scmIpSecurityRestrictions': runtime_config.get('scmIpSecurityRestrictions'),
                            'scmIpSecurityRestrictionsUseMain': runtime_config.get('scmIpSecurityRestrictionsUseMain'),
                            'http20Enabled': runtime_config.get('http20Enabled'),
                            'minTlsVersion': runtime_config.get('minTlsVersion'),
                            'ftpsState': runtime_config.get('ftpsState'),
                            'preWarmedInstanceCount': runtime_config.get('preWarmedInstanceCount'),
                            'functionAppScaleLimit': runtime_config.get('functionAppScaleLimit'),
                            'healthCheckPath': runtime_config.get('healthCheckPath'),
                            'functionsRuntimeScaleMonitoringEnabled': runtime_config.get('functionsRuntimeScaleMonitoringEnabled')
                        }
                    })
                
                # Authentication configuration
                auth_config = func_config.get('auth', {})
                if auth_config:
                    config['authenticationConfig'] = {
                        'enabled': auth_config.get('enabled'),
                        'unauthenticatedClientAction': auth_config.get('unauthenticatedClientAction'),
                        'tokenStoreEnabled': auth_config.get('tokenStoreEnabled'),
                        'allowedExternalRedirectUrls': auth_config.get('allowedExternalRedirectUrls'),
                        'defaultProvider': auth_config.get('defaultProvider'),
                        'clientId': auth_config.get('clientId'),
                        'issuer': auth_config.get('issuer'),
                        'allowedAudiences': auth_config.get('allowedAudiences'),
                        'additionalLoginParams': auth_config.get('additionalLoginParams'),
                        'googleClientId': auth_config.get('googleClientId'),
                        'facebookAppId': auth_config.get('facebookAppId'),
                        'twitterConsumerKey': auth_config.get('twitterConsumerKey'),
                        'microsoftAccountClientId': auth_config.get('microsoftAccountClientId')
                    }
            else:
                # Fallback to basic Function App configuration
                func_details = run_az_command_list([
                    'az', 'functionapp', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ], subscription_id)
                if func_details:
                    config.update({
                        'state': func_details.get('state'),
                        'serverFarmId': func_details.get('serverFarmId'),
                        'reserved': func_details.get('reserved'),
                        'httpsOnly': func_details.get('httpsOnly')
                    })
                
    except Exception as e:
        log_failure(f"Error getting specific config for {name} ({resource_type}): {str(e)}")
        
    return config

def list_resources_basic(subscription_id: str, resource_group_ids_to_include: List[str] = [], resource_types_to_include: List[str] = []) -> List[Dict[str, Any]]:
    """
    List all resources in the subscription with basic information.
    
    Args:
        subscription_id: The Azure subscription ID
        resource_group_ids_to_include: List of resource group IDs to include in the data
        resource_types_to_include: List of resource types to include in the data (with Microsoft. prefix added if needed)
    Returns:
        A list of basic resource objects
    """
    query = f"Resources | where subscriptionId == '{subscription_id}' | project id, name, type, resourceGroup, kind, location, tags, properties"
    if resource_group_ids_to_include:
        or_id_has = "' or resourceGroup has '"
        query += f' | where resourceGroup has \'{or_id_has.join(resource_group_ids_to_include)}\''
    
    if resource_types_to_include:
        or_id_has = "' or type has '"
        query += f' | where type has \'{or_id_has.join(resource_types_to_include)}\''
        
    #if resource_types_to_include:
    #    # Add Microsoft. prefix if not already present and create type filter
    #    normalized_types = []
    #    for resource_type in resource_types_to_include:
    #        if not resource_type.lower().startswith('microsoft.'):
    #            normalized_types.append(f'microsoft.{resource_type.lower()}')
    #        else:
    #            normalized_types.append(resource_type.lower())
    #    type_conditions = "' or type =~ '".join(normalized_types)
    #    query += f" | where type =~ '{type_conditions}'"
    
    print(f"Resource Query: {query}")
    try:
        result = run_az_command(f"az graph query -q \"{query}\" --subscription {subscription_id}")
        if result is None:
            log_failure(f"Failed to retrieve basic resources for subscription {subscription_id}.")
            return []
        if isinstance(result, dict):
            data = result.get('data', [])
            resources = []
            for resource in data:
                resource_type = resource.get('type', '')
                resource_name = resource.get('name', '')
                if resource_type in [
                    "Microsoft.Insights/metricalerts", 
                    "microsoft.eventgrid/systemtopics", 
                    "microsoft.portal/dashboards",
                    "microsoft.insights/actiongroups",
                    "microsoft.alertsmanagement/smartdetectoralertrules",
                    ]:
                    print(f"Skipping resource {resource_type}/{resource_name}")
                    continue
                resources.append(resource)
            return resources
        log_failure(f"Unexpected format for basic resources: {result}")
        return []
    except Exception as e:
        log_failure(f"Error in list_resources_basic for subscription {subscription_id}: {e}")
        return []

def list_resources(subscription_id: str, enhanced_mode: bool = False, resource_group_ids_to_include: List[str] = [], resource_types_to_include: List[str] = []) -> List[Dict[str, Any]]:
    """
    List all resources in the subscription with enhanced details.
    
    Args:
        subscription_id: The Azure subscription ID
        enhanced_mode: If True, only gather basic resource information
        resource_group_ids_to_include: List of resource group IDs to include in the data
        resource_types_to_include: List of resource types to include in the data
    Returns:
        A list of resource objects with detailed information
    """
    basic_resources = list_resources_basic(subscription_id, resource_group_ids_to_include, resource_types_to_include)
    if not enhanced_mode:
        print("Using basic mode - gathering resource information without detailed enhancement...")
        return basic_resources
    
    print("Using enhanced mode - gathering detailed resource information...")

    enhanced_resources = []
    total_resources = len(basic_resources)
    
    print(f"Enhancing resource details for {total_resources} resources...")
    for i, resource in enumerate(basic_resources, 1):
        resource_name = resource.get('name', 'Unknown')
        resource_id = resource.get('id')
        resource_type = resource.get('type')


        print(f"Processing resource {i}/{total_resources}: {resource_name}")
        
        if not resource_id:
            log_failure(f"Resource {resource_name} missing 'id', skipping detailed enhancement.")
            enhanced_resources.append(resource)
            continue
        if not resource_type:
            log_failure(f"Resource {resource_name} ({resource_id}) missing 'type', skipping detailed enhancement.")
            enhanced_resources.append(resource)
            continue

        try:
            # Get enhanced resource details
            enhanced_resource = resource.copy()
            
            # Fetch detailed resource data once for VM/VMSS/Function Apps to avoid duplicate API calls
            detailed_resource_data = None
            if resource_type in ['microsoft.compute/virtualmachines', 'microsoft.compute/virtualmachinescalesets'] or (resource_type == 'microsoft.web/sites' and 'functionapp' in resource.get('kind', '').lower()):
                resource_group = resource.get('resourceGroup', '')
                resource_name = resource.get('name', '')
                
                if resource_group and resource_name:
                    try:
                        if resource_type == 'microsoft.compute/virtualmachines':
                            detailed_resource_data = run_az_command_list([
                                'az', 'vm', 'show',
                                '--resource-group', resource_group,
                                '--name', resource_name,
                                '--show-details'
                            ], subscription_id)
                        elif resource_type == 'microsoft.compute/virtualmachinescalesets':
                            detailed_resource_data = run_az_command_list([
                                'az', 'vmss', 'show',
                                '--resource-group', resource_group,
                                '--name', resource_name
                            ], subscription_id)
                        elif resource_type == 'microsoft.web/sites' and 'functionapp' in resource.get('kind', '').lower():
                            # Get comprehensive Function App configuration
                            function_app_config = get_function_app_full_config(resource_group, resource_name, subscription_id)
                            detailed_resource_data = {'functionAppConfig': function_app_config}
                    except Exception as e:
                        log_failure(f"Error fetching detailed data for {resource_name} ({resource_type}): {str(e)}")
            
            # Add network information
            network_info = get_network_information(resource, subscription_id, detailed_resource_data)
            if network_info:
                enhanced_resource['networkInfo'] = network_info
                
            # Add environment variables
            env_vars = get_environment_variables(resource, subscription_id, detailed_resource_data)
            if env_vars:
                enhanced_resource['environmentVariables'] = env_vars
                
            # Add resource-specific configurations
            specific_config = get_resource_specific_config(resource, subscription_id, detailed_resource_data)
            if specific_config:
                enhanced_resource['specificConfiguration'] = specific_config
            
            # Get properties from Resource Graph for dependency analysis
            properties_query = f"Resources | where id == '{resource_id}' | project properties"
            try:
                properties_result = run_az_command(f"az graph query -q \"{properties_query}\" --subscription {subscription_id}")
                
                if properties_result is not None and isinstance(properties_result, dict) and properties_result.get('data'):
                    if properties_result['data'] and isinstance(properties_result['data'][0], dict):
                        enhanced_resource['properties'] = properties_result['data'][0].get('properties', {})
                    else:
                        log_failure(f"Properties query for {resource_id} returned unexpected data format: {properties_result}")
                elif properties_result is not None:
                    log_failure(f"Properties query for {resource_id} returned no data or unexpected type: {properties_result}")
                else:
                    log_failure(f"Failed to retrieve properties for {resource_id}.")
            except Exception as e:
                log_failure(f"Error retrieving properties for {resource_id}: {e}")
            
            enhanced_resources.append(enhanced_resource)
            
        except Exception as e:
            log_failure(f"Error enhancing resource {resource_name} ({resource_id}): {str(e)}")
            # Add basic resource info if enhancement fails
            enhanced_resources.append(resource)
    
    print(f"Enhanced {len(enhanced_resources)} resources with detailed information")
    return enhanced_resources

def get_resource_dependencies(subscription_id: str, resources: List[Dict[str, Any]]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Identify dependencies between resources using enhanced resource information.
    
    Args:
        subscription_id: The Azure subscription ID
        resources: List of enhanced resources to analyze
        
    Returns:
        A tuple containing (confirmed_dependencies, potential_dependencies) dictionaries mapping resource IDs to sets of dependent resource IDs
    """
    confirmed_dependencies: Dict[str, Set[str]] = {}
    potential_dependencies: Dict[str, Set[str]] = {}
    
    # Initialize empty dependency sets for all resources
    for resource in resources:
        resource_id = resource.get('id')
        if resource_id:
            confirmed_dependencies[resource_id] = set()
            potential_dependencies[resource_id] = set()
        else:
            log_failure(f"Resource missing 'id', cannot initialize for dependency tracking: {resource.get('name', 'Unknown')}")
    
    print("Analyzing resource dependencies with enhanced information...")
    
    # Check for different types of dependencies
    for resource in resources:
        resource_id = resource.get('id')
        resource_type = resource.get('type')
        
        if not resource_id:
            log_failure(f"Resource missing 'id', skipping dependency analysis for {resource.get('name', 'Unknown')}.")
            continue
        if not resource_type:
            log_failure(f"Resource {resource_id} missing 'type', skipping dependency analysis.")
            continue
        
        # Use enhanced properties if available, otherwise use basic properties
        properties = resource.get('properties', {})
        
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
            potential_dep_id = potential_dep.get('id')
            if potential_dep_id and potential_dep_id != resource_id and potential_dep_id in all_resource_data:
                confirmed_dependencies[resource_id].add(potential_dep_id)
        
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
            managed_environment_id = properties.get('managedEnvironmentId')
            if managed_environment_id:
                confirmed_dependencies[resource_id].add(managed_environment_id)
            
            # Container Apps secret references and registry dependencies
            config = properties.get('configuration')
            if isinstance(config, dict):
                # Registry dependencies
                registries = config.get('registries', [])
                if not isinstance(registries, list):
                    log_failure(f"Unexpected format for 'registries' in resource {resource_id}. Expected list, got {type(registries)}. Skipping registry dependencies.")
                    registries = [] # Ensure it's an empty list to prevent TypeError
                for registry in registries:
                    if isinstance(registry, dict):
                        server = registry.get('server', '')
                        # Find the ACR resource by matching the login server
                        for potential_acr in resources:
                            potential_acr_type = potential_acr.get('type')
                            if potential_acr_type == 'microsoft.containerregistry/registries':
                                try:
                                    acr_query = f"Resources | where id == '{potential_acr.get('id')}' | project properties.loginServer"
                                    acr_result = run_az_command(f"az graph query -q \"{acr_query}\" --subscription {subscription_id}")
                                    if acr_result is not None and isinstance(acr_result, dict) and acr_result.get('data'):
                                        if acr_result['data'] and isinstance(acr_result['data'][0], dict):
                                            if acr_result['data'][0].get('properties.loginServer') == server:
                                                confirmed_dependencies[resource_id].add(potential_acr['id'])
                                        else:
                                            log_failure(f"ACR query for {potential_acr.get('id')} returned unexpected data format: {acr_result}")
                                    elif acr_result is not None:
                                        log_failure(f"ACR query for {potential_acr.get('id')} returned no data or unexpected type: {acr_result}")
                                    else:
                                        log_failure(f"Failed to retrieve ACR login server for {potential_acr.get('id')}.")
                                except Exception as e:
                                    log_failure(f"Error retrieving ACR login server for {potential_acr.get('id')}: {e}")
                
                # Secret references that might point to Key Vault or other services
                secrets = config.get('secrets', [])
                if not isinstance(secrets, list):
                    log_failure(f"Unexpected format for 'secrets' in resource {resource_id}. Expected list, got {type(secrets)}. Skipping secret dependencies.")
                    secrets = []
                for secret in secrets:
                    if isinstance(secret, dict):
                        secret_name = secret.get('name', '')
                        # Common patterns for secret names that indicate dependencies
                        if 'keyvault' in secret_name.lower() or 'kv' in secret_name.lower():
                            for potential_kv in resources:
                                if potential_kv.get('type') == 'microsoft.keyvault/vaults':
                                    potential_dependencies[resource_id].add(potential_kv['id'])
                        elif 'storage' in secret_name.lower():
                            for potential_storage in resources:
                                if potential_storage.get('type') == 'microsoft.storage/storageaccounts':
                                    potential_dependencies[resource_id].add(potential_storage['id'])
                        elif 'database' in secret_name.lower() or 'db' in secret_name.lower():
                            for potential_db in resources:
                                potential_db_type = potential_db.get('type')
                                if potential_db_type in ['microsoft.sql/servers', 'microsoft.documentdb/databaseaccounts', 'microsoft.dbforpostgresql/flexibleservers']:
                                    potential_dependencies[resource_id].add(potential_db['id'])
            
            # Environment variable secret references
            template = properties.get('template')
            if isinstance(template, dict):
                containers = template.get('containers', [])
                if not isinstance(containers, list):
                    log_failure(f"Unexpected format for 'containers' in resource {resource_id} template. Expected list, got {type(containers)}. Skipping container env dependencies.")
                    containers = []
                for container in containers:
                    if isinstance(container, dict) and 'env' in container:
                        env_list = container.get('env', [])
                        if not isinstance(env_list, list):
                            log_failure(f"Unexpected format for 'env' in container of resource {resource_id}. Expected list, got {type(env_list)}. Skipping env var dependencies.")
                            env_list = []
                        for env_var in env_list:
                            if isinstance(env_var, dict) and 'secretRef' in env_var:
                                secret_ref = env_var['secretRef']
                                # Analyze secret reference patterns
                                if 'appinsights' in secret_ref.lower():
                                    for potential_insights in resources:
                                        if potential_insights.get('type') == 'microsoft.insights/components':
                                            potential_dependencies[resource_id].add(potential_insights['id'])
                                elif 'webpubsub' in secret_ref.lower() or 'signalr' in secret_ref.lower():
                                    for potential_signalr in resources:
                                        potential_signalr_type = potential_signalr.get('type')
                                        if potential_signalr_type in ['microsoft.signalrservice/signalr', 'microsoft.signalrservice/webpubsub']:
                                            potential_dependencies[resource_id].add(potential_signalr['id'])
        
        elif resource_type == 'microsoft.web/sites':
            # Separate handling for Web Apps vs Function Apps
            is_function_app = 'functionapp' in resource.get('kind', '').lower()
            
            if is_function_app:
                # Function App specific dependency detection
                # Function Apps often depend on App Service Plans (confirmed dependency)
                server_farm_id = properties.get('serverFarmId')
                if server_farm_id:
                    confirmed_dependencies[resource_id].add(server_farm_id)
                
                # Enhanced Function App dependency detection using comprehensive configuration
                if env_vars and 'functionAppSettings' in env_vars:
                    func_settings = env_vars.get('functionAppSettings', {})
                    
                    # Storage Account dependencies (AzureWebJobsStorage is required for Function Apps)
                    storage_conn_settings = [
                        'AzureWebJobsStorage', 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING',
                        'AzureWebJobsDashboard', 'FUNCTIONS_EXTENSION_VERSION'
                    ]
                    for setting_name, setting_value in func_settings.items():
                        if isinstance(setting_value, str):
                            # Function App storage dependencies (confirmed)
                            if setting_name in storage_conn_settings and ('blob.core.windows.net' in setting_value or 'file.core.windows.net' in setting_value):
                                for potential_storage in resources:
                                    if potential_storage.get('type') == 'microsoft.storage/storageaccounts':
                                        if potential_storage.get('name') and potential_storage['name'] in setting_value:
                                            confirmed_dependencies[resource_id].add(potential_storage['id'])
                            
                            # Application Insights dependencies (confirmed)
                            if 'APPLICATIONINSIGHTS' in setting_name.upper():
                                for potential_insights in resources:
                                    if potential_insights.get('type') == 'microsoft.insights/components':
                                        if potential_insights.get('name') and potential_insights['name'] in setting_value:
                                            confirmed_dependencies[resource_id].add(potential_insights['id'])
                            
                            # Key Vault references (confirmed)
                            if '@Microsoft.KeyVault' in setting_value or 'vault.azure.net' in setting_value:
                                for potential_kv in resources:
                                    if potential_kv.get('type') == 'microsoft.keyvault/vaults':
                                        if potential_kv.get('name') and potential_kv['name'] in setting_value:
                                            confirmed_dependencies[resource_id].add(potential_kv['id'])
                            
                            # Service Bus dependencies (potential)
                            if 'servicebus.windows.net' in setting_value:
                                for potential_sb in resources:
                                    if potential_sb.get('type') == 'microsoft.servicebus/namespaces':
                                        if potential_sb.get('name') and potential_sb['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_sb['id'])
                            
                            # Event Hub dependencies (potential)
                            if 'servicebus.windows.net' in setting_value and 'EntityPath=' in setting_value:
                                for potential_eh in resources:
                                    if potential_eh.get('type') == 'microsoft.eventhub/namespaces':
                                        if potential_eh.get('name') and potential_eh['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_eh['id'])
                            
                            # Cosmos DB dependencies (potential)
                            if 'cosmos.azure.com' in setting_value or 'documents.azure.com' in setting_value:
                                for potential_cosmos in resources:
                                    if potential_cosmos.get('type') == 'microsoft.documentdb/databaseaccounts':
                                        if potential_cosmos.get('name') and potential_cosmos['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_cosmos['id'])
                            
                            # SQL Database dependencies (potential)
                            if 'database.windows.net' in setting_value or 'sql.azuresynapse.net' in setting_value:
                                for potential_sql in resources:
                                    potential_sql_type = potential_sql.get('type')
                                    if potential_sql_type in ['microsoft.sql/servers', 'microsoft.sql/servers/databases']:
                                        if potential_sql.get('name') and potential_sql['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_sql['id'])
                            
                            # Redis Cache dependencies (potential)
                            if 'redis.cache.windows.net' in setting_value:
                                for potential_redis in resources:
                                    if potential_redis.get('type') == 'microsoft.cache/redis':
                                        if potential_redis.get('name') and potential_redis['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_redis['id'])
                
                # VNET Integration dependencies (confirmed)
                if network_info and 'vnetIntegration' in network_info:
                    vnet_integrations = network_info.get('vnetIntegration', [])
                    for vnet_integration in vnet_integrations:
                        if isinstance(vnet_integration, dict):
                            vnet_resource_id = vnet_integration.get('vnetResourceId')
                            subnet_resource_id = vnet_integration.get('subnetResourceId')
                            
                            if vnet_resource_id:
                                confirmed_dependencies[resource_id].add(vnet_resource_id)
                            if subnet_resource_id:
                                # Find the parent VNet from the subnet ID
                                for potential_vnet in resources:
                                    if potential_vnet.get('type') == 'microsoft.network/virtualnetworks':
                                        if potential_vnet.get('id') and potential_vnet['id'] in subnet_resource_id:
                                            confirmed_dependencies[resource_id].add(potential_vnet['id'])
                
                # Private Endpoint dependencies (confirmed)
                if network_info and 'privateEndpoints' in network_info:
                    private_endpoints = network_info.get('privateEndpoints', [])
                    for pe in private_endpoints:
                        if isinstance(pe, dict):
                            pe_info = pe.get('privateEndpoint')
                            if pe_info and isinstance(pe_info, dict) and 'id' in pe_info:
                                confirmed_dependencies[resource_id].add(pe_info['id'])
            
            else:
                # Regular Web App dependency detection
                # Web Apps often depend on App Service Plans (confirmed dependency)
                server_farm_id = properties.get('serverFarmId')
                if server_farm_id:
                    confirmed_dependencies[resource_id].add(server_farm_id)
                
                # Enhanced App Insights detection using environment variables (potential dependencies)
                if env_vars:
                    app_settings = env_vars.get('appSettings', {})
                    # Look for Application Insights connection strings
                    for setting_name, setting_value in app_settings.items():
                        if isinstance(setting_value, str) and 'APPLICATIONINSIGHTS' in setting_name.upper():
                            for potential_insights in resources:
                                if potential_insights.get('type') == 'microsoft.insights/components':
                                    if potential_insights.get('name') and potential_insights['name'] in setting_value:
                                        potential_dependencies[resource_id].add(potential_insights['id'])
                    
                    # Look for database connection strings
                    conn_strings = env_vars.get('connectionStrings', {})
                    for conn_name, conn_value in conn_strings.items():
                        if isinstance(conn_value, str):
                            # SQL Database dependencies
                            if 'database.windows.net' in conn_value or 'sql.azuresynapse.net' in conn_value:
                                for potential_sql in resources:
                                    potential_sql_type = potential_sql.get('type')
                                    if potential_sql_type in ['microsoft.sql/servers', 'microsoft.sql/servers/databases']:
                                        if potential_sql.get('name') and potential_sql['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_sql['id'])
                            
                            # Storage Account dependencies
                            if 'blob.core.windows.net' in conn_value or 'table.core.windows.net' in conn_value or 'queue.core.windows.net' in conn_value or 'file.core.windows.net' in conn_value:
                                for potential_storage in resources:
                                    if potential_storage.get('type') == 'microsoft.storage/storageaccounts':
                                        if potential_storage.get('name') and potential_storage['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_storage['id'])
                            
                            # Cosmos DB dependencies (MongoDB, SQL API, etc.)
                            if 'cosmos.azure.com' in conn_value or 'documents.azure.com' in conn_value:
                                for potential_cosmos in resources:
                                    if potential_cosmos.get('type') == 'microsoft.documentdb/databaseaccounts':
                                        if potential_cosmos.get('name') and potential_cosmos['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_cosmos['id'])
                            
                            # PostgreSQL dependencies
                            if 'postgres.database.azure.com' in conn_value:
                                for potential_pg in resources:
                                    potential_pg_type = potential_pg.get('type')
                                    if potential_pg_type in ['microsoft.dbforpostgresql/servers', 'microsoft.dbforpostgresql/flexibleservers']:
                                        if potential_pg.get('name') and potential_pg['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_pg['id'])
                            
                            # MySQL dependencies
                            if 'mysql.database.azure.com' in conn_value:
                                for potential_mysql in resources:
                                    potential_mysql_type = potential_mysql.get('type')
                                    if potential_mysql_type in ['microsoft.dbformysql/servers', 'microsoft.dbformysql/flexibleservers']:
                                        if potential_mysql.get('name') and potential_mysql['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_mysql['id'])
                            
                            # Service Bus dependencies
                            if 'servicebus.windows.net' in conn_value:
                                for potential_sb in resources:
                                    if potential_sb.get('type') == 'microsoft.servicebus/namespaces':
                                        if potential_sb.get('name') and potential_sb['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_sb['id'])
                            
                            # Event Hub dependencies
                            if 'servicebus.windows.net' in conn_value and 'EntityPath=' in conn_value:
                                for potential_eh in resources:
                                    if potential_eh.get('type') == 'microsoft.eventhub/namespaces':
                                        if potential_eh.get('name') and potential_eh['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_eh['id'])
                            
                            # Redis Cache dependencies
                            if 'redis.cache.windows.net' in conn_value:
                                for potential_redis in resources:
                                    if potential_redis.get('type') == 'microsoft.cache/redis':
                                        if potential_redis.get('name') and potential_redis['name'] in conn_value:
                                            potential_dependencies[resource_id].add(potential_redis['id'])
                
                # Enhanced detection for Key Vault secret references
                if env_vars:
                    app_settings = env_vars.get('appSettings', {})
                    for setting_name, setting_value in app_settings.items():
                        if isinstance(setting_value, str):
                            # Key Vault secret references (format: @Microsoft.KeyVault(SecretUri=...))
                            if '@Microsoft.KeyVault' in setting_value or 'vault.azure.net' in setting_value:
                                for potential_kv in resources:
                                    if potential_kv.get('type') == 'microsoft.keyvault/vaults':
                                        if potential_kv.get('name') and potential_kv['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_kv['id'])
                            
                            # Service Bus connection strings in app settings
                            if 'servicebus.windows.net' in setting_value:
                                for potential_sb in resources:
                                    if potential_sb.get('type') == 'microsoft.servicebus/namespaces':
                                        if potential_sb.get('name') and potential_sb['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_sb['id'])
                            
                            # SignalR/Web PubSub connection strings
                            if 'webpubsub.azure.com' in setting_value or 'service.signalr.net' in setting_value:
                                for potential_signalr in resources:
                                    potential_signalr_type = potential_signalr.get('type')
                                    if potential_signalr_type in ['microsoft.signalrservice/signalr', 'microsoft.signalrservice/webpubsub']:
                                        if potential_signalr.get('name') and potential_signalr['name'] in setting_value:
                                            potential_dependencies[resource_id].add(potential_signalr['id'])
                
                # Check for App Insights connection in properties (confirmed dependency)
                if properties and 'siteConfig' in properties and properties.get('siteConfig') is not None:
                    site_config = properties.get('siteConfig', {})
                    app_settings = site_config.get('appSettings', []) # Ensure default is list
                    if app_settings and isinstance(app_settings, list):
                        for setting in app_settings:
                            if isinstance(setting, dict) and setting.get('name') == 'APPLICATIONINSIGHTS_CONNECTION_STRING' and 'value' in setting:
                                conn_string = setting['value']
                                for potential_insights in resources:
                                    if potential_insights.get('type') == 'microsoft.insights/components' and potential_insights.get('name') and potential_insights['name'] in conn_string:
                                        confirmed_dependencies[resource_id].add(potential_insights['id'])
        
        elif resource_type == 'microsoft.insights/components':
            # Application Insights may depend on storage accounts for logs (potential dependency)
            if specific_config:
                for potential_storage in resources:
                    if potential_storage.get('type') == 'microsoft.storage/storageaccounts':
                        # Check if storage account is referenced in App Insights config
                        if potential_storage.get('name') and potential_storage['name'] in json.dumps(specific_config):
                            potential_dependencies[resource_id].add(potential_storage['id'])
        
        elif resource_type == 'microsoft.apimanagement/service':
            # APIM often connected to App Insights (potential dependency)
            for potential_insights in resources:
                if potential_insights.get('type') == 'microsoft.insights/components':
                    potential_dependencies[resource_id].add(potential_insights['id'])
            
            # Enhanced APIM dependency detection using configuration (potential dependencies)
            if specific_config:
                # Look for backend services, named values, etc.
                config_str = json.dumps(specific_config)
                for potential_dep in resources:
                    potential_dep_type = potential_dep.get('type')
                    if potential_dep_type in ['microsoft.web/sites', 'microsoft.storage/storageaccounts', 'microsoft.keyvault/vaults']:
                        if potential_dep.get('name') and potential_dep['name'] in config_str:
                            potential_dependencies[resource_id].add(potential_dep['id'])
        
        elif resource_type == 'microsoft.keyvault/vaults':
            # Key Vault may be referenced by other services
            # This is typically a reverse dependency, but we can detect some patterns
            if specific_config:
                access_policies = specific_config.get('accessPolicies', [])
                if not isinstance(access_policies, list):
                    log_failure(f"Unexpected format for 'accessPolicies' in Key Vault {resource_id}. Expected list, got {type(access_policies)}.")
                    access_policies = []
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
                    if potential_storage.get('type') == 'microsoft.storage/storageaccounts':
                        if potential_storage.get('name') and potential_storage['name'] in config_str:
                            potential_dependencies[resource_id].add(potential_storage['id'])
            
            # VMs depend on their network interfaces (confirmed dependency)
            if properties and 'networkProfile' in properties:
                network_interfaces = properties.get('networkProfile', {}).get('networkInterfaces', [])
                if not isinstance(network_interfaces, list):
                    log_failure(f"Unexpected format for 'networkInterfaces' in VM {resource_id}. Expected list, got {type(network_interfaces)}.")
                    network_interfaces = []
                for nic in network_interfaces:
                    if isinstance(nic, dict) and 'id' in nic:
                        confirmed_dependencies[resource_id].add(nic['id'])
        
        elif resource_type == 'microsoft.compute/virtualmachinescalesets':
            # VMSS depend on various resources (potential dependencies from config)
            if specific_config:
                # Check for dependencies on storage accounts (for diagnostics, disks)
                config_str = json.dumps(specific_config)
                for potential_storage in resources:
                    if potential_storage.get('type') == 'microsoft.storage/storageaccounts':
                        if potential_storage.get('name') and potential_storage['name'] in config_str:
                            potential_dependencies[resource_id].add(potential_storage['id'])
            
            # VMSS depend on their network configurations and load balancers (confirmed dependencies)
            if properties and 'virtualMachineProfile' in properties:
                vm_profile = properties.get('virtualMachineProfile', {})
                network_profile = vm_profile.get('networkProfile', {})
                
                # Network interface configurations dependencies
                nic_configs = network_profile.get('networkInterfaceConfigurations', [])
                if not isinstance(nic_configs, list):
                    log_failure(f"Unexpected format for 'networkInterfaceConfigurations' in VMSS {resource_id}. Expected list, got {type(nic_configs)}.")
                    nic_configs = []
                
                for nic_config in nic_configs:
                    if isinstance(nic_config, dict):
                        ip_configs = nic_config.get('ipConfigurations', [])
                        if not isinstance(ip_configs, list):
                            log_failure(f"Unexpected format for 'ipConfigurations' in VMSS {resource_id} NIC config. Expected list, got {type(ip_configs)}.")
                            ip_configs = []
                        
                        for ip_config in ip_configs:
                            if isinstance(ip_config, dict):
                                # Subnet dependencies (confirmed)
                                subnet = ip_config.get('subnet')
                                if subnet and isinstance(subnet, dict) and 'id' in subnet:
                                    # This points to a subnet, we need to find the parent VNet
                                    subnet_id = subnet['id']
                                    for potential_vnet in resources:
                                        if potential_vnet.get('type') == 'microsoft.network/virtualnetworks':
                                            if potential_vnet.get('id') and potential_vnet['id'] in subnet_id:
                                                confirmed_dependencies[resource_id].add(potential_vnet['id'])
                                
                                # Load balancer backend pool dependencies (confirmed)
                                lb_backend_pools = ip_config.get('loadBalancerBackendAddressPools', [])
                                if not isinstance(lb_backend_pools, list):
                                    log_failure(f"Unexpected format for 'loadBalancerBackendAddressPools' in VMSS {resource_id}. Expected list, got {type(lb_backend_pools)}.")
                                    lb_backend_pools = []
                                
                                for pool in lb_backend_pools:
                                    if isinstance(pool, dict) and 'id' in pool:
                                        # Extract load balancer ID from the backend pool ID
                                        pool_id = pool['id']
                                        # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/loadBalancers/{lb}/backendAddressPools/{pool}
                                        lb_id_parts = pool_id.split('/')
                                        if len(lb_id_parts) >= 9:
                                            lb_id = '/'.join(lb_id_parts[:9])  # Get the load balancer ID
                                            confirmed_dependencies[resource_id].add(lb_id)
                                
                                # Load balancer inbound NAT pool dependencies (confirmed)
                                lb_inbound_nat_pools = ip_config.get('loadBalancerInboundNatPools', [])
                                if not isinstance(lb_inbound_nat_pools, list):
                                    log_failure(f"Unexpected format for 'loadBalancerInboundNatPools' in VMSS {resource_id}. Expected list, got {type(lb_inbound_nat_pools)}.")
                                    lb_inbound_nat_pools = []
                                
                                for nat_pool in lb_inbound_nat_pools:
                                    if isinstance(nat_pool, dict) and 'id' in nat_pool:
                                        # Extract load balancer ID from the NAT pool ID
                                        nat_pool_id = nat_pool['id']
                                        lb_id_parts = nat_pool_id.split('/')
                                        if len(lb_id_parts) >= 9:
                                            lb_id = '/'.join(lb_id_parts[:9])  # Get the load balancer ID
                                            confirmed_dependencies[resource_id].add(lb_id)
            
            # VMSS may depend on Application Gateway backend pools (potential dependencies)
            if network_info:
                associated_load_balancers = network_info.get('associatedLoadBalancers', [])
                for lb_name in associated_load_balancers:
                    # Find load balancer resources by name
                    for potential_lb in resources:
                        if potential_lb.get('type') == 'microsoft.network/loadbalancers' and potential_lb.get('name') == lb_name:
                            confirmed_dependencies[resource_id].add(potential_lb['id'])
        
        elif resource_type == 'microsoft.storage/storageaccounts':
            # Storage accounts may have network restrictions pointing to VNets (confirmed dependency)
            if specific_config and 'networkRuleSet' in specific_config:
                network_rules = specific_config.get('networkRuleSet', {})
                virtual_network_rules = network_rules.get('virtualNetworkRules', [])
                if not isinstance(virtual_network_rules, list):
                    log_failure(f"Unexpected format for 'virtualNetworkRules' in Storage Account {resource_id}. Expected list, got {type(virtual_network_rules)}.")
                    virtual_network_rules = []
                for vnet_rule in virtual_network_rules:
                    if isinstance(vnet_rule, dict) and 'id' in vnet_rule:
                        # This points to a subnet, we need to find the parent VNet
                        subnet_id = vnet_rule['id']
                        for potential_vnet in resources:
                            if potential_vnet.get('type') == 'microsoft.network/virtualnetworks':
                                if potential_vnet.get('id') and potential_vnet['id'] in subnet_id:
                                    confirmed_dependencies[resource_id].add(potential_vnet['id'])
    
    # Add common implicit dependencies based on resource types (potential dependencies)
    for resource in resources:
        resource_id = resource.get('id')
        resource_type = resource.get('type')

        if not resource_id:
            continue
        
        # Add implicit dependency for dashboard -> App Insights
        if resource_type == 'microsoft.portal/dashboards':
            for potential_dep in resources:
                if potential_dep.get('type') == 'microsoft.insights/components':
                    potential_dependencies[resource_id].add(potential_dep['id'])
        
        # Container App Environment -> App Insights
        if resource_type == 'microsoft.app/managedenvironments':
            for potential_dep in resources:
                if potential_dep.get('type') == 'microsoft.insights/components':
                    potential_dependencies[resource_id].add(potential_dep['id'])
    
    return confirmed_dependencies, potential_dependencies

def get_resource_data(subscription_id: str, enhanced_mode: bool = False, resource_group_ids_to_include: List[str] = [], resource_types_to_include: List[str] = []) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Collect all Azure resource data needed for visualization.
    
    Args:
        subscription_id: The Azure subscription ID
        enhanced_mode: If True, only gather basic resource information
        resource_group_ids_to_include: List of resource group IDs to include in the data
        resource_types_to_include: List of resource types to include in the data
    Returns:
        A tuple containing (resources, resource_groups, confirmed_dependencies, potential_dependencies)
    """
    if subscription_id == "":
        print("Error: Could not determine Azure subscription ID. Exiting.")
        sys.exit(1)
            
    truncated_sub_id = truncate_subscription_id(subscription_id)
    print(f"Using subscription: {truncated_sub_id}")
    
    # Get resources and resource groups
    print("Fetching resource groups...")
    resource_groups = list_resource_groups(subscription_id, resource_group_ids_to_include)
    print(f"Found {len(resource_groups)} resource groups")
    
    # Get resources (basic or enhanced mode)
    resources = list_resources(subscription_id, enhanced_mode, resource_group_ids_to_include, resource_types_to_include)
    print(f"Found {len(resources)} resources {'(enhanced mode)' if enhanced_mode else '(basic mode)'}")
    
    # Analyze dependencies using enhanced resource data
    confirmed_dependencies, potential_dependencies = get_resource_dependencies(subscription_id, resources)
    
    # Print summary of enhanced data collected
    enhanced_count = sum(1 for r in resources if any(key in r for key in ['networkInfo', 'environmentVariables', 'specificConfiguration']))
    function_app_count = sum(1 for r in resources if r.get('type') == 'microsoft.web/sites' and r.get('kind', '').lower() == 'functionapp')
    print(f"Enhanced {enhanced_count}/{len(resources)} resources with detailed information")
    if function_app_count > 0:
        print(f"Processed {function_app_count} Function Apps with comprehensive configuration data")
    
    # Print dependency summary
    total_confirmed_deps = sum(len(deps) for deps in confirmed_dependencies.values())
    total_potential_deps = sum(len(deps) for deps in potential_dependencies.values())
    print(f"Discovered {total_confirmed_deps} confirmed dependencies and {total_potential_deps} potential dependencies")
    
    return subscription_id, resources, resource_groups, confirmed_dependencies, potential_dependencies

def remove_none(d):
    if isinstance(d, dict):
        clean_d = {}
        for k,v in d.items():
            clean_v = remove_none(v)
            if clean_v:
                clean_d[k] = clean_v
        return clean_d #{k: remove_none(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [remove_none(i) for i in d if i is not None]
    else:
        return d
    
def main():
    parser = argparse.ArgumentParser(description='Generate Azure resource dependency graph with enhanced resource discovery')
    parser.add_argument('--subscription', '-s', type=str, help='Azure subscription ID (if not provided, uses current subscription)')
    parser.add_argument('--potential-deps', action='store_true', help='Exclude potential dependencies from the diagram')
    parser.add_argument('--output', '-o', type=str, default='azure_resource_graph', help='Output file path prefix')
    parser.add_argument('--data', action='store_true', help='Use existing data file instead of fetching from Azure')
    parser.add_argument('--html', action='store_true', help='Skip HTML visualization generation')
    parser.add_argument('--md', action='store_true', help='Skip Markdown visualization generation')
    parser.add_argument('--enhanced-mode', action='store_true', help='Use basic resource discovery without enhanced details (faster but less comprehensive)')
    parser.add_argument('--resourcegroup-ids', type=str, help='Comma-separated list of resourceGroupIDs to filter resources by')
    parser.add_argument('--resource-types', type=str, help='Comma-separated list of resource types to filter resources by (without Microsoft. prefix, e.g., "Web/sites,Storage/storageAccounts")')
    args = parser.parse_args()

    # Determine whether to collect data or use existing file
    data_file = f"{args.output}.json"
    
    subscription_id: str = args.subscription
    resource_types_to_include: List[str] = []
    resource_group_ids_to_include: List[str] = []

    if not args.resourcegroup_ids:
        print(f"Resource groups to include: ALL")
    else:
        resource_group_ids_to_include = [pid.strip() for pid in args.resourcegroup_ids.split(',')]
        print(f"Resource groups to include: {resource_group_ids_to_include}")

    if not args.resource_types:
        print(f"Resource types to include: ALL")
    else:
        resource_types_to_include = [rt.strip() for rt in args.resource_types.split(',')]
        print(f"Resource types to include: {resource_types_to_include}")

    resources: List[Dict[str, Any]] = []
    resource_groups: List[Dict[str, Any]] = []
    confirmed_dependencies: Dict[str, Set[str]] = {}
    potential_dependencies: Dict[str, Set[str]] = {}

    if args.data:
        # Query Azure for resource data
        subscription_id, resources, resource_groups, confirmed_dependencies, potential_dependencies = get_resource_data(subscription_id, args.enhanced_mode, resource_group_ids_to_include, resource_types_to_include)
                
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
                'enhanced_mode': args.enhanced_mode,
                'total_resources': len(resources),
                'total_confirmed_dependencies': total_confirmed_deps,
                'total_potential_dependencies': total_potential_deps,
                'enhanced_resources': sum(1 for r in resources if any(key in r for key in ['networkInfo', 'environmentVariables', 'specificConfiguration'])) if not args.enhanced_mode else 0,
                'filtered_by_resource_types': args.resource_types.split(',') if args.resource_types else None
            }
        }
        
        try:
            with open(data_file, 'w') as f:
                #json.dump(data, f, indent=2)
                json.dump(remove_none(data), f, indent=2)
            print(f"Resource data saved to {data_file}")
            if not args.enhanced_mode:
                print(f"Enhanced data includes network info, environment variables, and detailed configurations")
        except IOError as e:
            log_failure(f"Error saving data to file {data_file}: {e}")


    data_from_output = None
    with open(data_file, 'r') as f:
        data_from_output = json.load(f)
        # Print complete dependency data JSON with markers
        print("\n" + "="*80)
        print("DEPENDENCY DATA JSON OUTPUT START")
        print("="*80)
        print(json.dumps(remove_none(data_from_output), indent=2, default=str))
        print("="*80)
        print("DEPENDENCY DATA JSON OUTPUT END")
        print("="*80 + "\n")
        
    
    subscription_id = data_from_output['subscription_id']
    resources = data_from_output['resources']
    resource_groups = data_from_output['resource_groups']
    confirmed_dependencies = data_from_output['confirmed_dependencies']
    potential_dependencies = data_from_output['potential_dependencies']


    include_potential_deps = args.potential_deps

    # Generate HTML output if requested
    if args.html:
        try:
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
        except ImportError:
            log_failure("Could not import 'arg_html'. HTML visualization will be skipped. Ensure 'arg_html.py' is in the same directory.")
        except Exception as e:
            log_failure(f"Error generating HTML diagram: {e}")

    # Generate Markdown output if requested
    if args.md:
        try:
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
                if args.resource_types:
                    f.write(f"- Filtered by resource types: {args.resource_types}\n")
                f.write("\n```mermaid\n")
                f.write(mermaid_diagram)
                f.write("\n```\n")
            
            print(f"Markdown diagram saved to {md_file}")
        except ImportError:
            log_failure("Could not import 'arg_mermaid'. Markdown visualization will be skipped. Ensure 'arg_mermaid.py' is in the same directory.")
        except Exception as e:
            log_failure(f"Error generating Markdown diagram: {e}")
    
    # Print final summary
    mode_msg = "basic mode (faster, less comprehensive)" if not args.enhanced_mode else "enhanced mode (comprehensive resource analysis)"
    print(f"\n✅ Resource graph generation completed using {mode_msg}")

    if args.resourcegroup_ids:
        print(f"Processed resources filtered by resource group IDs: {args.resourcegroup_ids}")
    
    if args.resource_types:
        print(f"Processed resources filtered by resource types: {args.resource_types}")
    
    if include_potential_deps:
        print("Included both confirmed and potential dependencies.")
    else:
        print("Included only confirmed dependencies. Potential dependencies were excluded.")
    
    if args.enhanced_mode:
        print("Enhanced features included:")
        print("  - Network information (IPs, hostnames, endpoints)")
        print("  - Environment variables and configuration settings")
        print("  - Resource-specific detailed configurations")
        print("  - Advanced dependency detection using configuration data")
        print("  - Comprehensive Function App analysis (metadata, VNET integration, private endpoints, hybrid connections)")
    else:
        print("To get more detailed resource information and better dependency detection, run with --enhanced-mode")
        print("Enhanced mode includes comprehensive Function App configuration analysis")

    if _failed_operations_log:
        print("\n--- Summary of Failed Operations (Non-Fatal) ---")
        for msg in _failed_operations_log:
            print(f"- {msg}")
        print("-------------------------------------------------")

if __name__ == "__main__":
    # Check prerequisites
    if not check_az_cli_installed():
        print("Error: Azure CLI not found. Please install it first: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)
    
    if not check_az_cli_logged_in():
        print("Error: Not logged in to Azure. Please run 'az login' first.")
        sys.exit(1)
    
    main()
