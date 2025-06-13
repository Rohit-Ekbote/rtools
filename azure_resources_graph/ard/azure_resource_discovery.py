#!/usr/bin/env python3
"""
Azure Resource Discovery Script

This script discovers all Azure resources in the current subscription context
and gathers comprehensive information including:
- Basic resource information
- Tags
- Configuration details
- Environment variables (where applicable)
- Network information (IP addresses, FQDNs)
- Resource-specific configurations
"""

import json
import subprocess
import sys
import traceback
from typing import Dict, List, Any, Optional
import argparse
from datetime import datetime


class AzureResourceDiscovery:
    def __init__(self, subscription_id: Optional[str] = None):
        self.subscription_id = subscription_id
        self.resources_data = []
        
    def run_az_command(self, command: List[str]) -> Dict[str, Any]:
        """Execute Azure CLI command and return JSON result"""
        try:
            if self.subscription_id:
                command.extend(['--subscription', self.subscription_id])
            
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

    def get_current_subscription(self) -> Dict[str, Any]:
        """Get current subscription information"""
        return self.run_az_command(['az', 'account', 'show'])

    def discover_all_resources(self) -> List[Dict[str, Any]]:
        """Discover all resources in the subscription"""
        print("🔍 Discovering all resources...")
        resources = self.run_az_command(['az', 'resource', 'list'])
        
        if isinstance(resources, list):
            print(f"📊 Found {len(resources)} resources")
            return resources
        return []

    def get_resource_details(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific resource"""
        resource_id = resource.get('id', '')
        resource_type = resource.get('type', '')
        
        # Get basic resource details
        details = self.run_az_command([
            'az', 'resource', 'show',
            '--ids', resource_id
        ])
        
        # Add network information if applicable
        network_info = self.get_network_information(resource)
        if network_info:
            details['networkInfo'] = network_info
            
        # Add environment variables for supported resource types
        env_vars = self.get_environment_variables(resource)
        if env_vars:
            details['environmentVariables'] = env_vars
            
        # Add resource-specific configurations
        specific_config = self.get_resource_specific_config(resource)
        if specific_config:
            details['specificConfiguration'] = specific_config
            
        return details

    def get_network_information(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get network information for addressable resources"""
        resource_type = resource.get('type', '').lower()
        resource_group = resource.get('resourceGroup', '')
        name = resource.get('name', '')
        network_info = {}
        
        try:
            # Virtual Machines
            if 'microsoft.compute/virtualmachines' in resource_type:
                vm_details = self.run_az_command([
                    'az', 'vm', 'show',
                    '--resource-group', resource_group,
                    '--name', name,
                    '--show-details'
                ])
                if vm_details:
                    network_info.update({
                        'privateIps': vm_details.get('privateIps', []),
                        'publicIps': vm_details.get('publicIps', []),
                        'fqdns': vm_details.get('fqdns', [])
                    })
            
            # Public IP Addresses
            elif 'microsoft.network/publicipaddresses' in resource_type:
                pip_details = self.run_az_command([
                    'az', 'network', 'public-ip', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if pip_details:
                    network_info.update({
                        'ipAddress': pip_details.get('ipAddress'),
                        'fqdn': pip_details.get('dnsSettings', {}).get('fqdn'),
                        'allocationMethod': pip_details.get('publicIPAllocationMethod')
                    })
            
            # Load Balancers
            elif 'microsoft.network/loadbalancers' in resource_type:
                lb_details = self.run_az_command([
                    'az', 'network', 'lb', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if lb_details:
                    frontend_ips = []
                    for frontend in lb_details.get('frontendIPConfigurations', []):
                        if frontend.get('publicIPAddress'):
                            frontend_ips.append(frontend['publicIPAddress'].get('id', '').split('/')[-1])
                    network_info['frontendIPs'] = frontend_ips
            
            # App Services
            elif 'microsoft.web/sites' in resource_type:
                app_details = self.run_az_command([
                    'az', 'webapp', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if app_details:
                    network_info.update({
                        'defaultHostName': app_details.get('defaultHostName'),
                        'hostNames': app_details.get('hostNames', []),
                        'outboundIpAddresses': app_details.get('outboundIpAddresses', '').split(',') if app_details.get('outboundIpAddresses') else []
                    })
            
            # Storage Accounts
            elif 'microsoft.storage/storageaccounts' in resource_type:
                storage_details = self.run_az_command([
                    'az', 'storage', 'account', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if storage_details:
                    primary_endpoints = storage_details.get('primaryEndpoints', {})
                    network_info['endpoints'] = primary_endpoints
            
        except Exception as e:
            print(f"Error getting network info for {name}: {str(e)}")
            
        return network_info

    def get_environment_variables(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get environment variables for supported resources"""
        resource_type = resource.get('type', '').lower()
        resource_group = resource.get('resourceGroup', '')
        name = resource.get('name', '')
        env_vars = {}
        
        try:
            # App Service / Web Apps
            if 'microsoft.web/sites' in resource_type:
                app_settings = self.run_az_command([
                    'az', 'webapp', 'config', 'appsettings', 'list',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if isinstance(app_settings, list):
                    env_vars['appSettings'] = {setting['name']: setting['value'] for setting in app_settings}
                
                # Get connection strings
                conn_strings = self.run_az_command([
                    'az', 'webapp', 'config', 'connection-string', 'list',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if isinstance(conn_strings, list):
                    env_vars['connectionStrings'] = {cs['name']: cs['value'] for cs in conn_strings}
            
            # Function Apps
            elif 'microsoft.web/sites' in resource_type and resource.get('kind', '').lower() == 'functionapp':
                func_settings = self.run_az_command([
                    'az', 'functionapp', 'config', 'appsettings', 'list',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if isinstance(func_settings, list):
                    env_vars['functionAppSettings'] = {setting['name']: setting['value'] for setting in func_settings}
            
            # Container Instances
            elif 'microsoft.containerinstance/containergroups' in resource_type:
                container_details = self.run_az_command([
                    'az', 'container', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
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

    def get_resource_specific_config(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Get resource-specific configuration details"""
        resource_type = resource.get('type', '').lower()
        resource_group = resource.get('resourceGroup', '')
        name = resource.get('name', '')
        config = {}
        
        try:
            # Virtual Machines - Get VM size, OS info, etc.
            if 'microsoft.compute/virtualmachines' in resource_type:
                vm_details = self.run_az_command([
                    'az', 'vm', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
                if vm_details:
                    config.update({
                        'vmSize': vm_details.get('hardwareProfile', {}).get('vmSize'),
                        'osType': vm_details.get('storageProfile', {}).get('osDisk', {}).get('osType'),
                        'imageReference': vm_details.get('storageProfile', {}).get('imageReference'),
                        'adminUsername': vm_details.get('osProfile', {}).get('adminUsername')
                    })
            
            # Storage Accounts - Get SKU, access tier, etc.
            elif 'microsoft.storage/storageaccounts' in resource_type:
                storage_details = self.run_az_command([
                    'az', 'storage', 'account', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
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
                    db_details = self.run_az_command([
                        'az', 'sql', 'db', 'show',
                        '--resource-group', resource_group,
                        '--server', server_name,
                        '--name', name
                    ])
                    if db_details:
                        config.update({
                            'edition': db_details.get('edition'),
                            'serviceLevelObjective': db_details.get('serviceLevelObjective'),
                            'maxSizeBytes': db_details.get('maxSizeBytes'),
                            'collation': db_details.get('collation')
                        })
            
            # Key Vaults
            elif 'microsoft.keyvault/vaults' in resource_type:
                kv_details = self.run_az_command([
                    'az', 'keyvault', 'show',
                    '--resource-group', resource_group,
                    '--name', name
                ])
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

    def _build_hierarchical_structure(self, detailed_resources: Dict[str, Any], subscription_name: str, subscription_id: str) -> Dict[str, Any]:
        """Build hierarchical structure: subscription -> resource group -> resource type -> resource name"""
        hierarchical = {
            subscription_name: {
                'subscriptionId': subscription_id,
                'resourceGroups': {}
            }
        }
        
        for resource_id, resource_details in detailed_resources.items():
            resource_group = resource_details.get('resourceGroup', 'Unknown')
            resource_type = resource_details.get('type', 'Unknown')
            resource_name = resource_details.get('name', 'Unknown')
            
            # Initialize resource group if not exists
            if resource_group not in hierarchical[subscription_name]['resourceGroups']:
                hierarchical[subscription_name]['resourceGroups'][resource_group] = {}
            
            # Initialize resource type if not exists
            if resource_type not in hierarchical[subscription_name]['resourceGroups'][resource_group]:
                hierarchical[subscription_name]['resourceGroups'][resource_group][resource_type] = {}
            
            # Clean resource details by removing redundant keys
            cleaned_details = self._clean_resource_details(resource_details)
            
            # Add resource to hierarchy
            hierarchical[subscription_name]['resourceGroups'][resource_group][resource_type][resource_name] = cleaned_details
        
        return hierarchical
    
    def _clean_resource_details(self, resource_details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove keys that are already part of the hierarchical path"""
        # Keys to remove as they're already represented in the hierarchy
        keys_to_remove = {
            'resourceGroup', 'type', 'name', 'subscriptionId'
        }
        
        cleaned = {}
        for key, value in resource_details.items():
            if key not in keys_to_remove:
                cleaned[key] = value
        
        return cleaned

    def generate_report(self, output_file: str = None):
        """Generate comprehensive resource discovery report"""
        print("🚀 Starting Azure Resource Discovery...")
        
        # Get subscription info
        subscription_info = self.get_current_subscription()
        subscription_name = subscription_info.get('name', 'Unknown')
        subscription_id = subscription_info.get('id', 'Unknown')
        print(f"📋 Current Subscription: {subscription_name} ({subscription_id})")
        
        # Discover all resources
        resources = self.discover_all_resources()
        
        if not resources:
            print("❌ No resources found or unable to access resources")
            return
        
        # Process each resource
        detailed_resources = {}
        for i, resource in enumerate(resources, 1):
            print(f"🔄 Processing resource {i}/{len(resources)}: {resource.get('name', 'Unknown')}")
            
            resource_id = resource.get('id', '')
            try:
                detailed_info = self.get_resource_details(resource)
                if resource_id in detailed_resources:
                    print(f"🔄 Resource {resource_id} already exists")
                else:
                    detailed_resources[resource_id] = detailed_info
            except Exception as e:
                print(f"⚠️  Error processing resource {resource.get('name', 'Unknown')}: {str(e)}")
                detailed_resources[resource_id] = resource  # Add basic info if detailed processing fails
        
        # Build hierarchical structure: subscription -> resource group -> resource type -> resource name
        hierarchical_resources = self._build_hierarchical_structure(detailed_resources, subscription_name, subscription_id)
        
        # Prepare final report
        report = {
            'discoveryMetadata': {
                'timestamp': datetime.now().isoformat(),
                'subscription': subscription_info,
                'totalResourcesFound': len(detailed_resources),
                'toolVersion': '1.0.0'
            },
            'resources': hierarchical_resources
        }
        
        # Output report
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"📄 Report saved to: {output_file}")
        else:
            print("\n" + "="*80)
            print("AZURE RESOURCE DISCOVERY REPORT")
            print("="*80)
            print(json.dumps(report, indent=2, default=str))
        
        # Print summary
        resource_types = {}
        resource_groups = set()
        total_resources = 0
        
        # Count resources from hierarchical structure
        for subscription_name, subscription_data in hierarchical_resources.items():
            for rg_name, rg_data in subscription_data.get('resourceGroups', {}).items():
                resource_groups.add(rg_name)
                for res_type, resources in rg_data.items():
                    resource_types[res_type] = resource_types.get(res_type, 0) + len(resources)
                    total_resources += len(resources)
        
        print(f"\n📊 Summary:")
        print(f"   Total Resources: {total_resources}")
        print(f"   Resource Groups: {len(resource_groups)}")
        print(f"   Resource Types:")
        for res_type, count in sorted(resource_types.items()):
            print(f"     - {res_type}: {count}")
        print(f"   Resource Groups: {', '.join(sorted(resource_groups))}")


def main():
    parser = argparse.ArgumentParser(description='Discover and analyze Azure resources')
    parser.add_argument('--subscription', '-s', help='Azure subscription ID (uses current context if not provided)')
    parser.add_argument('--output', '-o', help='Output file path (prints to stdout if not provided)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Check if Azure CLI is installed and user is logged in
    try:
        subprocess.run(['az', 'account', 'show'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Azure CLI is not installed or you're not logged in.")
        print("   Please install Azure CLI and run 'az login' first.")
        sys.exit(1)
    
    # Initialize discovery
    discovery = AzureResourceDiscovery(subscription_id=args.subscription)
    
    try:
        discovery.generate_report(output_file=args.output)
        print("✅ Discovery completed successfully!")
    except KeyboardInterrupt:
        print("\n🛑 Discovery interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main() 