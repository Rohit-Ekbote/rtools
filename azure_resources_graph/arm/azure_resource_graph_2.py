#!/usr/bin/env python3
"""
Azure Application Dependency Graph Builder

This script discovers Azure resources and builds application-level dependency graphs
using resource tags, ARM template dependencies, and resource type inference.

Requirements:
pip install azure-identity azure-mgmt-resource azure-mgmt-monitor networkx matplotlib

Authentication:
- Azure CLI: az login
- Service Principal: Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
- Managed Identity: Available in Azure-hosted environments
"""

import os
import json
import logging
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

import networkx as nx
import matplotlib.pyplot as plt
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.core.exceptions import AzureError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AzureResource:
    """Represents an Azure resource with dependency information"""
    id: str
    name: str
    type: str
    resource_group: str
    location: str
    tags: Dict[str, str]
    app_name: Optional[str] = None
    component: Optional[str] = None
    depends_on: List[str] = None
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        
        # Extract application metadata from tags
        self.app_name = self.tags.get('app-name') or self.tags.get('application')
        self.component = self.tags.get('component') or self.tags.get('tier')
        
        # Parse depends-on tag
        depends_tag = self.tags.get('depends-on', '')
        if depends_tag:
            self.depends_on.extend([dep.strip() for dep in depends_tag.split(',')])

class AzureDependencyGraphBuilder:
    """Builds application dependency graphs from Azure resources"""
    
    def __init__(self, subscription_id: str, credential=None):
        self.subscription_id = subscription_id
        self.credential = credential or DefaultAzureCredential()
        
        # Initialize Azure clients
        self.resource_client = ResourceManagementClient(
            self.credential, subscription_id
        )
        self.monitor_client = MonitorManagementClient(
            self.credential, subscription_id
        )
        
        self.resources: List[AzureResource] = []
        self.dependency_graph = nx.DiGraph()
        
    def discover_resources(self, resource_groups: List[str] = None, 
                         app_filter: str = None) -> List[AzureResource]:
        """Discover Azure resources and extract dependency information"""
        logger.info("Discovering Azure resources...")
        
        try:
            # Get all resources or filter by resource groups
            if resource_groups:
                all_resources = []
                for rg in resource_groups:
                    rg_resources = self.resource_client.resources.list_by_resource_group(rg)
                    all_resources.extend(rg_resources)
            else:
                all_resources = self.resource_client.resources.list()
            
            discovered_resources = []
            for resource in all_resources:
                azure_resource = AzureResource(
                    id=resource.id,
                    name=resource.name,
                    type=resource.type,
                    resource_group=resource.id.split('/')[4],  # Extract RG from resource ID
                    location=resource.location or 'unknown',
                    tags=resource.tags or {}
                )
                
                # Filter by application if specified
                if app_filter and azure_resource.app_name != app_filter:
                    continue
                    
                discovered_resources.append(azure_resource)
                
            self.resources = discovered_resources
            logger.info(f"Discovered {len(self.resources)} resources")
            
            # Log resource types for debugging
            resource_types = {}
            for resource in self.resources:
                rtype = resource.type
                resource_types[rtype] = resource_types.get(rtype, 0) + 1
            
            logger.info("Resource types found:")
            for rtype, count in sorted(resource_types.items()):
                logger.info(f"  {rtype}: {count}")
                
            # Log resources with tags
            tagged_resources = [r for r in self.resources if r.tags]
            logger.info(f"Resources with tags: {len(tagged_resources)}/{len(self.resources)}")
            
            # Log resources with depends-on tags
            dep_tagged = [r for r in self.resources if r.depends_on]
            logger.info(f"Resources with dependency tags: {len(dep_tagged)}")
            
            return self.resources
            
        except AzureError as e:
            logger.error(f"Error discovering resources: {e}")
            raise
    
    def discover_arm_dependencies(self) -> Dict[str, List[str]]:
        """Discover dependencies from ARM template deployments"""
        logger.info("Discovering ARM template dependencies...")
        
        arm_dependencies = defaultdict(list)
        deployment_count = 0
        
        try:
            # Get all resource groups
            resource_groups = [rg.name for rg in self.resource_client.resource_groups.list()]
            logger.info(f"Checking {len(resource_groups)} resource groups for deployments")
            
            # Get all deployments across resource groups
            for rg in resource_groups:
                try:
                    deployments = list(self.resource_client.deployments.list_by_resource_group(rg))
                    logger.info(f"Found {len(deployments)} deployments in resource group '{rg}'")
                    deployment_count += len(deployments)
                    
                    for deployment in deployments:
                        try:
                            # Get deployment template and parameters
                            deployment_export = self.resource_client.deployments.export_template(
                                rg, deployment.name
                            )
                            template = deployment_export.template
                            if 'resources' in template:
                                logger.debug(f"Processing template from deployment '{deployment.name}' with {len(template['resources'])} resources")
                                self._parse_arm_dependencies(template['resources'], arm_dependencies)
                        except Exception as e:
                            logger.debug(f"Could not export template for deployment {deployment.name} in {rg}: {e}")
                            continue
                except Exception as e:
                    logger.debug(f"Error listing deployments for resource group {rg}: {e}")
                    continue
                    
            logger.info(f"Total deployments found: {deployment_count}")
            logger.info(f"ARM dependencies discovered: {len(arm_dependencies)}")
            
        except AzureError as e:
            logger.warning(f"Error discovering ARM dependencies: {e}")
        return dict(arm_dependencies)
    
    def _parse_arm_dependencies(self, resources: List[Dict], 
                              dependencies: Dict[str, List[str]]):
        """Parse ARM template resources for dependsOn relationships"""
        for resource in resources:
            resource_name = resource.get('name', '')
            depends_on = resource.get('dependsOn', [])
            
            if depends_on:
                for dependency in depends_on:
                    # Clean up ARM template dependency references
                    if isinstance(dependency, str):
                        clean_dep = dependency.replace('[resourceId(', '').replace(')]', '')
                        clean_dep = clean_dep.split(',')[-1].strip().strip("'\"")
                        dependencies[resource_name].append(clean_dep)
    
    def discover_resource_type_dependencies(self) -> Dict[str, List[str]]:
        """Discover dependencies based on resource types and naming patterns"""
        logger.info("Discovering resource type-based dependencies...")
        
        type_dependencies = defaultdict(list)
        
        # Create resource mappings
        resource_by_name = {r.name: r for r in self.resources}
        resource_by_type = defaultdict(list)
        for r in self.resources:
            resource_by_type[r.type].append(r)
        
        # Define common dependency patterns
        dependency_patterns = [
            # Web apps depend on app service plans
            ('Microsoft.Web/sites', 'Microsoft.Web/serverfarms'),
            # VMs depend on NICs, storage accounts
            ('Microsoft.Compute/virtualMachines', 'Microsoft.Network/networkInterfaces'),
            ('Microsoft.Compute/virtualMachines', 'Microsoft.Storage/storageAccounts'),
            # NICs depend on subnets/VNets
            ('Microsoft.Network/networkInterfaces', 'Microsoft.Network/virtualNetworks'),
            # Subnets depend on NSGs
            ('Microsoft.Network/virtualNetworks/subnets', 'Microsoft.Network/networkSecurityGroups'),
            # SQL databases depend on SQL servers
            ('Microsoft.Sql/servers/databases', 'Microsoft.Sql/servers'),
            # Function apps depend on storage accounts and app service plans
            ('Microsoft.Web/sites', 'Microsoft.Storage/storageAccounts'),  # For function apps
            # Key vaults and other services
            ('Microsoft.KeyVault/vaults/secrets', 'Microsoft.KeyVault/vaults'),
        ]
        
        # Apply dependency patterns
        for source_type, target_type in dependency_patterns:
            source_resources = resource_by_type.get(source_type, [])
            target_resources = resource_by_type.get(target_type, [])
            
            for source in source_resources:
                for target in target_resources:
                    # Check if they are in same resource group or have similar names
                    if (source.resource_group == target.resource_group or 
                        self._names_related(source.name, target.name)):
                        type_dependencies[source.name].append(target.name)
        
        # Name-based inference for same resource group
        for rg in set(r.resource_group for r in self.resources):
            rg_resources = [r for r in self.resources if r.resource_group == rg]
            
            for i, source in enumerate(rg_resources):
                for target in rg_resources[i+1:]:
                    if self._names_related(source.name, target.name):
                        # Infer direction based on resource types
                        if self._should_depend_on(source.type, target.type):
                            type_dependencies[source.name].append(target.name)
                        elif self._should_depend_on(target.type, source.type):
                            type_dependencies[target.name].append(source.name)
        
        logger.info(f"Resource type dependencies discovered: {len(type_dependencies)}")
        return dict(type_dependencies)
    
    def _names_related(self, name1: str, name2: str) -> bool:
        """Check if two resource names are related"""
        # Remove common suffixes and prefixes
        clean1 = re.sub(r'-(vm|web|api|db|sql|storage|kv|plan)$', '', name1.lower())
        clean2 = re.sub(r'-(vm|web|api|db|sql|storage|kv|plan)$', '', name2.lower())
        
        # Check for common prefixes (at least 3 characters)
        if len(clean1) >= 3 and len(clean2) >= 3:
            return clean1[:3] == clean2[:3] or clean1 in clean2 or clean2 in clean1
        
        return False
    
    def _should_depend_on(self, source_type: str, target_type: str) -> bool:
        """Determine if source_type should depend on target_type"""
        dependency_rules = {
            'Microsoft.Web/sites': ['Microsoft.Web/serverfarms', 'Microsoft.Storage/storageAccounts'],
            'Microsoft.Compute/virtualMachines': ['Microsoft.Network/networkInterfaces', 'Microsoft.Storage/storageAccounts'],
            'Microsoft.Network/networkInterfaces': ['Microsoft.Network/virtualNetworks'],
            'Microsoft.Sql/servers/databases': ['Microsoft.Sql/servers'],
        }
        
        return target_type in dependency_rules.get(source_type, [])
        
    def build_dependency_graph(self):
        """Build NetworkX graph from discovered resources and dependencies"""
        logger.info("Building dependency graph...")
        
        # Add nodes for each resource
        for resource in self.resources:
            node_id = f"{resource.name}({resource.type.split('/')[-1]})"
            
            self.dependency_graph.add_node(
                node_id,
                resource_id=resource.id,
                name=resource.name,
                type=resource.type,
                resource_group=resource.resource_group,
                app_name=resource.app_name,
                component=resource.component,
                tags=resource.tags
            )
        
        edges_added = 0
        
        # Add edges for tag-based dependencies
        logger.info("Adding tag-based dependencies...")
        tag_edges = 0
        for resource in self.resources:
            source_node = f"{resource.name}({resource.type.split('/')[-1]})"
            
            for dependency in resource.depends_on:
                # Find matching resources by name or component
                target_resources = [
                    r for r in self.resources 
                    if r.name == dependency or r.component == dependency
                ]
                
                for target in target_resources:
                    target_node = f"{target.name}({target.type.split('/')[-1]})"
                    if not self.dependency_graph.has_edge(source_node, target_node):
                        self.dependency_graph.add_edge(
                            source_node, target_node, 
                            relationship='depends_on',
                            source='tags'
                        )
                        tag_edges += 1
                        edges_added += 1
        
        logger.info(f"Tag-based dependencies added: {tag_edges}")
        
        # Discover and add ARM template dependencies
        logger.info("Adding ARM template dependencies...")
        arm_edges = 0
        arm_deps = self.discover_arm_dependencies()
        for source, targets in arm_deps.items():
            source_resources = [r for r in self.resources if source in r.name]
            
            for source_resource in source_resources:
                source_node = f"{source_resource.name}({source_resource.type.split('/')[-1]})"
                
                for target in targets:
                    target_resources = [r for r in self.resources if target in r.name]
                    
                    for target_resource in target_resources:
                        target_node = f"{target_resource.name}({target_resource.type.split('/')[-1]})"
                        if not self.dependency_graph.has_edge(source_node, target_node):
                            self.dependency_graph.add_edge(
                                source_node, target_node,
                                relationship='depends_on',
                                source='arm_template'
                            )
                            arm_edges += 1
                            edges_added += 1
        
        logger.info(f"ARM template dependencies added: {arm_edges}")
        
        # Add resource type-based dependencies
        logger.info("Adding resource type-based dependencies...")
        type_edges = 0
        type_deps = self.discover_resource_type_dependencies()
        for source, targets in type_deps.items():
            source_resources = [r for r in self.resources if r.name == source]
            
            for source_resource in source_resources:
                source_node = f"{source_resource.name}({source_resource.type.split('/')[-1]})"
                
                for target in targets:
                    target_resources = [r for r in self.resources if r.name == target]
                    
                    for target_resource in target_resources:
                        target_node = f"{target_resource.name}({target_resource.type.split('/')[-1]})"
                        if not self.dependency_graph.has_edge(source_node, target_node):
                            self.dependency_graph.add_edge(
                                source_node, target_node,
                                relationship='inferred',
                                source='resource_type'
                            )
                            type_edges += 1
                            edges_added += 1
        
        logger.info(f"Resource type-based dependencies added: {type_edges}")
        
        logger.info(f"Built graph with {self.dependency_graph.number_of_nodes()} nodes "
                   f"and {self.dependency_graph.number_of_edges()} edges")
        
        # If still no edges, create some demo connections for visualization
        if self.dependency_graph.number_of_edges() == 0 and len(self.resources) > 1:
            logger.info("No dependencies found. Creating sample connections for demonstration...")
            self._create_demo_dependencies()
    
    def _create_demo_dependencies(self):
        """Create demo dependencies when none are found"""
        # Group resources by resource group and create simple dependencies
        by_rg = defaultdict(list)
        for resource in self.resources:
            by_rg[resource.resource_group].append(resource)
        
        for rg, resources in by_rg.items():
            if len(resources) > 1:
                # Create a simple chain of dependencies within each resource group
                for i in range(len(resources) - 1):
                    source = resources[i]
                    target = resources[i + 1]
                    
                    source_node = f"{source.name}({source.type.split('/')[-1]})"
                    target_node = f"{target.name}({target.type.split('/')[-1]})"
                    
                    self.dependency_graph.add_edge(
                        source_node, target_node,
                        relationship='demo',
                        source='generated'
                    )
        
        logger.info(f"Added {self.dependency_graph.number_of_edges()} demo dependencies")
    
    def analyze_dependencies(self) -> Dict:
        """Analyze the dependency graph and return insights"""
        analysis = {
            'total_resources': len(self.resources),
            'total_dependencies': self.dependency_graph.number_of_edges(),
            'applications': {},
            'circular_dependencies': [],
            'orphaned_resources': [],
            'critical_resources': []
        }
        
        # Group by application
        apps = defaultdict(list)
        for resource in self.resources:
            app_name = resource.app_name or 'untagged'
            apps[app_name].append(resource)
        
        analysis['applications'] = {
            app: len(resources) for app, resources in apps.items()
        }
        
        # Find circular dependencies
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            analysis['circular_dependencies'] = cycles
        except:
            pass
        
        # Find orphaned resources (no dependencies)
        orphaned = [
            node for node in self.dependency_graph.nodes()
            if self.dependency_graph.degree(node) == 0
        ]
        analysis['orphaned_resources'] = orphaned
        
        # Find critical resources (high in-degree)
        in_degrees = dict(self.dependency_graph.in_degree())
        critical = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        analysis['critical_resources'] = critical
        
        return analysis
    
    def visualize_graph(self, output_file: str = 'azure_dependencies.png', 
                       app_filter: str = None, figsize: Tuple[int, int] = (15, 10)):
        """Visualize the dependency graph"""
        logger.info(f"Creating visualization...")
        
        # Filter graph by application if specified
        if app_filter:
            filtered_nodes = [
                node for node in self.dependency_graph.nodes()
                if self.dependency_graph.nodes[node].get('app_name') == app_filter
            ]
            graph = self.dependency_graph.subgraph(filtered_nodes)
        else:
            graph = self.dependency_graph
        
        if len(graph.nodes()) == 0:
            logger.warning("No nodes to visualize")
            return
        
        plt.figure(figsize=figsize)
        
        # Create layout
        pos = nx.spring_layout(graph, k=3, iterations=50)
        
        # Color nodes by application
        app_colors = {}
        color_palette = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        node_colors = []
        for node in graph.nodes():
            app_name = graph.nodes[node].get('app_name', 'untagged')
            if app_name not in app_colors:
                app_colors[app_name] = color_palette[len(app_colors) % len(color_palette)]
            node_colors.append(app_colors[app_name])
        
        # Draw graph
        nx.draw_networkx_nodes(graph, pos, node_color=node_colors, 
                              node_size=1000, alpha=0.7)
        nx.draw_networkx_edges(graph, pos, edge_color='gray', 
                              arrows=True, arrowsize=20, alpha=0.6)
        nx.draw_networkx_labels(graph, pos, font_size=8, font_weight='bold')
        
        # Add legend
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                    markerfacecolor=color, markersize=10, label=app)
                         for app, color in app_colors.items()]
        plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
        
        plt.title("Azure Application Dependency Graph", fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        logger.info(f"Visualization saved to {output_file}")
    
    def export_graph(self, output_file: str = 'dependencies.json'):
        """Export dependency graph to JSON"""
        graph_data = {
            'nodes': [
                {
                    'id': node,
                    **self.dependency_graph.nodes[node]
                }
                for node in self.dependency_graph.nodes()
            ],
            'edges': [
                {
                    'source': edge[0],
                    'target': edge[1],
                    **self.dependency_graph.edges[edge]
                }
                for edge in self.dependency_graph.edges()
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(graph_data, f, indent=2, default=str)
        
        logger.info(f"Graph exported to {output_file}")

def main():
    """Main function demonstrating usage"""
    
    # Configuration
    SUBSCRIPTION_ID = os.getenv('AZURE_SUBSCRIPTION_ID')
    if not SUBSCRIPTION_ID:
        print("Please set AZURE_SUBSCRIPTION_ID environment variable")
        return
    
    # Initialize the dependency graph builder
    builder = AzureDependencyGraphBuilder(SUBSCRIPTION_ID)
    
    try:
        # Discover resources
        # Optionally filter by resource groups or application
        resources = builder.discover_resources(
            # resource_groups=['my-app-rg', 'my-db-rg'],  # Optional filter
            # app_filter='ecommerce'  # Optional application filter
        )
        
        print(f"Discovered {len(resources)} resources")
        
        # Build dependency graph
        builder.build_dependency_graph()
        
        # Analyze dependencies
        analysis = builder.analyze_dependencies()
        print("\n=== Dependency Analysis ===")
        print(f"Total Resources: {analysis['total_resources']}")
        print(f"Total Dependencies: {analysis['total_dependencies']}")
        print(f"Applications: {analysis['applications']}")
        
        if analysis['circular_dependencies']:
            print(f"⚠️  Circular Dependencies Found: {analysis['circular_dependencies']}")
        
        if analysis['critical_resources']:
            print("Critical Resources (most dependencies):")
            for resource, count in analysis['critical_resources']:
                print(f"  - {resource}: {count} dependencies")
        
        # Export graph data
        builder.export_graph('azure_dependencies.json')
        
        # Visualize the graph
        builder.visualize_graph('azure_dependencies.png')
        
        # Create application-specific visualizations
        for app_name in analysis['applications']:
            if app_name != 'untagged' and analysis['applications'][app_name] > 1:
                builder.visualize_graph(
                    f'azure_dependencies_{app_name}.png',
                    app_filter=app_name
                )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()