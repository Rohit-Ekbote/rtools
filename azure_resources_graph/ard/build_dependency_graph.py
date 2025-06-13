#!/usr/bin/env python3
"""
Azure Resource Dependency Graph Builder

This script reads an Azure resource discovery JSON file and builds a dependency graph
showing relationships between Azure resources. Outputs Mermaid diagram format.
"""

import json
import re
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import argparse
import os

class AzureResourceGraphBuilder:
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.resources = {}
        self.dependencies = defaultdict(set)
        self.resource_types = {}
        
        # Load the JSON data
        with open(json_file_path, 'r') as f:
            self.data = json.load(f)
    
    def extract_resources(self):
        """Extract all resources from the JSON structure"""
        resources_data = self.data.get('resources', {})
        
        for subscription_name, subscription_data in resources_data.items():
            resource_groups = subscription_data.get('resourceGroups', {})
            
            for rg_name, rg_data in resource_groups.items():
                for resource_type, resources in rg_data.items():
                    for resource_name, resource_info in resources.items():
                        resource_id = resource_info.get('id', f"/{subscription_name}/{rg_name}/{resource_type}/{resource_name}")
                        
                        self.resources[resource_id] = {
                            'name': resource_name,
                            'type': resource_type,
                            'resource_group': rg_name,
                            'subscription': subscription_name,
                            'location': resource_info.get('location', 'unknown'),
                            'properties': resource_info.get('properties', {}),
                            'data': resource_info
                        }
                        
                        self.resource_types[resource_id] = resource_type
    
    def extract_dependencies(self):
        """Extract dependencies between resources"""
        for resource_id, resource_info in self.resources.items():
            self._find_dependencies(resource_id, resource_info)
    
    def _find_dependencies(self, resource_id: str, resource_info: Dict):
        """Find dependencies for a specific resource"""
        resource_data = resource_info['data']
        
        # 1. Direct resource ID references
        self._find_resource_id_references(resource_id, resource_data)
        
        # 2. Managed environment dependencies (Container Apps)
        self._find_managed_environment_deps(resource_id, resource_data)
        
        # 3. Metric alert dependencies
        self._find_metric_alert_deps(resource_id, resource_data)
        
        # 4. Autoscale dependencies
        self._find_autoscale_deps(resource_id, resource_data)
        
        # 5. Service endpoint dependencies
        self._find_service_endpoint_deps(resource_id, resource_data)
        
        # 6. Container registry dependencies
        self._find_container_registry_deps(resource_id, resource_data)
        
        # 7. Storage account dependencies
        self._find_storage_deps(resource_id, resource_data)
    
    def _find_resource_id_references(self, resource_id: str, data: Any):
        """Find direct Azure resource ID references"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['managedEnvironmentId', 'environmentId', 'targetResourceUri', 'metricResourceUri']:
                    if isinstance(value, str) and value.startswith('/subscriptions/'):
                        self.dependencies[resource_id].add(value)
                else:
                    self._find_resource_id_references(resource_id, value)
        elif isinstance(data, list):
            for item in data:
                self._find_resource_id_references(resource_id, item)
    
    def _find_managed_environment_deps(self, resource_id: str, resource_data: Dict):
        """Find Container App managed environment dependencies"""
        props = resource_data.get('properties', {})
        if 'managedEnvironmentId' in props:
            env_id = props['managedEnvironmentId']
            self.dependencies[resource_id].add(env_id)
    
    def _find_metric_alert_deps(self, resource_id: str, resource_data: Dict):
        """Find metric alert dependencies"""
        props = resource_data.get('properties', {})
        if 'scopes' in props:
            for scope in props['scopes']:
                if scope.startswith('/subscriptions/'):
                    self.dependencies[resource_id].add(scope)
    
    def _find_autoscale_deps(self, resource_id: str, resource_data: Dict):
        """Find autoscale setting dependencies"""
        props = resource_data.get('properties', {})
        if 'targetResourceUri' in props:
            target = props['targetResourceUri']
            self.dependencies[resource_id].add(target)
        
        # Check metric triggers
        profiles = props.get('profiles', [])
        for profile in profiles:
            rules = profile.get('rules', [])
            for rule in rules:
                metric_trigger = rule.get('metricTrigger', {})
                if 'metricResourceUri' in metric_trigger:
                    self.dependencies[resource_id].add(metric_trigger['metricResourceUri'])
    
    def _find_service_endpoint_deps(self, resource_id: str, resource_data: Dict):
        """Find service endpoint dependencies"""
        # Look for service endpoints in webhook URLs, connection strings, etc.
        data_str = json.dumps(resource_data)
        
        # Find Azure service endpoints
        azure_patterns = [
            r'https://([^.]+)\.servicebus\.windows\.net',
            r'https://([^.]+)\.vault\.azure\.net',
            r'https://([^.]+)\.blob\.core\.windows\.net',
            r'https://([^.]+)\.azurecr\.io',
            r'https://([^.]+)\.postgres\.database\.azure\.com'
        ]
        
        for pattern in azure_patterns:
            matches = re.findall(pattern, data_str)
            for match in matches:
                # Try to find the corresponding resource
                for rid, rinfo in self.resources.items():
                    if rinfo['name'] == match or match in rinfo['name']:
                        self.dependencies[resource_id].add(rid)
    
    def _find_container_registry_deps(self, resource_id: str, resource_data: Dict):
        """Find container registry dependencies from container images"""
        # Look for container images
        props = resource_data.get('properties', {})
        template = props.get('template', {})
        containers = template.get('containers', [])
        
        for container in containers:
            image = container.get('image', '')
            if '.azurecr.io/' in image:
                registry_name = image.split('.azurecr.io/')[0]
                # Find the registry resource
                for rid, rinfo in self.resources.items():
                    if rinfo['type'] == 'Microsoft.ContainerRegistry/registries' and registry_name in rinfo['name']:
                        self.dependencies[resource_id].add(rid)
    
    def _find_storage_deps(self, resource_id: str, resource_data: Dict):
        """Find storage account dependencies"""
        # Look for storage endpoints
        props = resource_data.get('properties', {})
        if 'primaryEndpoints' in props:
            endpoints = props['primaryEndpoints']
            for endpoint_type, endpoint_url in endpoints.items():
                if endpoint_url:
                    # This is a storage account itself, not a dependency
                    continue
        
        # Look for references to storage accounts in other resources
        data_str = json.dumps(resource_data)
        storage_pattern = r'https://([^.]+)\.(?:blob|file|queue|table)\.core\.windows\.net'
        matches = re.findall(storage_pattern, data_str)
        
        for match in matches:
            for rid, rinfo in self.resources.items():
                if rinfo['type'] == 'Microsoft.Storage/storageAccounts' and match in rinfo['name']:
                    self.dependencies[resource_id].add(rid)
    
    def _sanitize_name_for_mermaid(self, name: str) -> str:
        """Sanitize resource names for Mermaid diagram compatibility"""
        # Replace special characters that might break Mermaid syntax
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = 'r_' + sanitized
        return sanitized or 'unnamed'
    
    def _get_resource_shape(self, resource_type: str) -> str:
        """Get Mermaid shape for different resource types"""
        shape_map = {
            'Microsoft.Storage/storageAccounts': '[({})]',
            'Microsoft.KeyVault/vaults': '[{}]',
            'Microsoft.DBforPostgreSQL/flexibleServers': '{{{}}}',
            'Microsoft.Web/sites': '({})',
            'Microsoft.Web/serverfarms': '({}))',
            'Microsoft.ContainerRegistry/registries': '[{}]',
            'Microsoft.App/managedEnvironments': '{{{}}}',
            'Microsoft.App/containerApps': '(({}))',
            'Microsoft.Logic/workflows': '[({})]',
            'Microsoft.Insights/ActionGroups': '[{}]',
            'Microsoft.Insights/metricAlerts': '[{}]',
            'Microsoft.Insights/autoscaleSettings': '[{}]',
            'Microsoft.ServiceBus/Namespaces': '{{{}}}',
            'Microsoft.OperationalInsights/workspaces': '[{}]',
            'Microsoft.EventGrid/systemTopics': '({})'
        }
        return shape_map.get(resource_type, '[{}]')
    
    def generate_mermaid_chart(self, output_file: str = 'azure_dependency_graph.mmd', direction: str = 'TD'):
        """Generate Mermaid flowchart diagram"""
        if not self.resources:
            print("No resources found to generate chart")
            return
        
        mermaid_lines = []
        mermaid_lines.append(f"flowchart {direction}")
        mermaid_lines.append("")
        
        # Create node definitions with resource type information
        resource_id_map = {}
        for i, (resource_id, resource_info) in enumerate(self.resources.items()):
            sanitized_id = self._sanitize_name_for_mermaid(resource_info['name'])
            resource_id_map[resource_id] = sanitized_id
            
            resource_type_short = resource_info['type'].split('/')[-1]
            shape = self._get_resource_shape(resource_info['type'])
            node_label = f"{resource_info['name']}<br/>({resource_type_short})"
            
            mermaid_lines.append(f"    {sanitized_id}{shape.format(node_label)}")
        
        mermaid_lines.append("")
        
        # Add dependencies as edges
        for resource_id, deps in self.dependencies.items():
            if resource_id in resource_id_map:
                source_id = resource_id_map[resource_id]
                for dep_id in deps:
                    if dep_id in resource_id_map:
                        target_id = resource_id_map[dep_id]
                        mermaid_lines.append(f"    {source_id} --> {target_id}")
        
        mermaid_lines.append("")
        
        # Add styling for different resource types
        mermaid_lines.append("    %% Styling")
        type_colors = {
            'Microsoft.Storage/storageAccounts': '#FF6B6B',
            'Microsoft.KeyVault/vaults': '#4ECDC4',
            'Microsoft.DBforPostgreSQL/flexibleServers': '#45B7D1',
            'Microsoft.Web/sites': '#96CEB4',
            'Microsoft.Web/serverfarms': '#FECA57',
            'Microsoft.ContainerRegistry/registries': '#FF9FF3',
            'Microsoft.App/managedEnvironments': '#54A0FF',
            'Microsoft.App/containerApps': '#5F27CD',
            'Microsoft.Logic/workflows': '#00D2D3',
            'Microsoft.Insights/ActionGroups': '#FF9F43',
            'Microsoft.Insights/metricAlerts': '#EE5A24',
            'Microsoft.Insights/autoscaleSettings': '#0984E3',
            'Microsoft.ServiceBus/Namespaces': '#A29BFE',
            'Microsoft.OperationalInsights/workspaces': '#FD79A8',
            'Microsoft.EventGrid/systemTopics': '#FDCB6E'
        }
        
        # Group resources by type for styling
        type_groups = defaultdict(list)
        for resource_id, resource_info in self.resources.items():
            if resource_id in resource_id_map:
                resource_type = resource_info['type']
                type_groups[resource_type].append(resource_id_map[resource_id])
        
        # Apply styles to each resource type group
        for resource_type, node_ids in type_groups.items():
            color = type_colors.get(resource_type, '#DDD')
            class_name = f"class{len(mermaid_lines)}"
            mermaid_lines.append(f"    classDef {class_name} fill:{color},stroke:#333,stroke-width:2px;")
            nodes_list = ','.join(node_ids)
            mermaid_lines.append(f"    class {nodes_list} {class_name};")
        
        # Write to file
        mermaid_content = '\n'.join(mermaid_lines)
        with open(output_file, 'w') as f:
            f.write(mermaid_content)
        
        print(f"Mermaid chart saved as {output_file}")
        
        # Also print the chart content for easy copying
        print("\n=== Mermaid Chart Content ===")
        print(mermaid_content)
        print("=" * 50)
    
    def print_summary(self):
        """Print a summary of the resources and dependencies"""
        print("\n=== Azure Resource Dependency Graph Summary ===")
        print(f"Total resources: {len(self.resources)}")
        print(f"Total dependencies: {sum(len(deps) for deps in self.dependencies.values())}")
        
        print("\n=== Resource Types ===")
        type_counts = defaultdict(int)
        for resource_info in self.resources.values():
            type_counts[resource_info['type']] += 1
        
        for resource_type, count in sorted(type_counts.items()):
            print(f"  {resource_type}: {count}")
        
        print("\n=== Dependencies ===")
        for resource_id, deps in self.dependencies.items():
            if deps:
                resource_name = self.resources[resource_id]['name']
                print(f"\n{resource_name} depends on:")
                for dep_id in deps:
                    if dep_id in self.resources:
                        dep_name = self.resources[dep_id]['name']
                        print(f"  - {dep_name}")
    
    def export_to_json(self, output_file: str = 'dependency_graph.json'):
        """Export the dependency graph to JSON format"""
        graph_data = {
            'resources': self.resources,
            'dependencies': {k: list(v) for k, v in self.dependencies.items()},
            'summary': {
                'total_resources': len(self.resources),
                'total_dependencies': sum(len(deps) for deps in self.dependencies.values())
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        print(f"Dependency graph exported to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Build Azure Resource Dependency Graph')
    parser.add_argument('json_file', help='Path to Azure resource discovery JSON file')
    parser.add_argument('--output', '-o', default='azure_dependency_graph.mmd', 
                       help='Output file for the Mermaid chart (default: azure_dependency_graph.mmd)')
    parser.add_argument('--direction', choices=['TD', 'TB', 'BT', 'RL', 'LR'], 
                       default='TD', help='Mermaid chart direction (TD=top-down, LR=left-right, etc.)')
    parser.add_argument('--export-json', help='Export dependency data to JSON file')
    parser.add_argument('--no-chart', action='store_true', help='Skip chart generation (only print summary)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file):
        print(f"Error: File {args.json_file} not found")
        return 1
    
    # Build the dependency graph
    builder = AzureResourceGraphBuilder(args.json_file)
    
    print("Extracting resources...")
    builder.extract_resources()
    
    print("Analyzing dependencies...")
    builder.extract_dependencies()
    
    # Print summary
    builder.print_summary()
    
    # Export to JSON if requested
    if args.export_json:
        builder.export_to_json(args.export_json)
    
    # Generate Mermaid chart
    if not args.no_chart:
        print(f"\nGenerating Mermaid chart...")
        builder.generate_mermaid_chart(args.output, args.direction)
    
    return 0

if __name__ == '__main__':
    exit(main()) 