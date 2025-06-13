#!/usr/bin/env python3
"""
Generate Human-Readable Dependency Report

This script reads the azure_resource_graph.json file and generates a comprehensive
human-readable dependency report in Markdown format.
"""

import json
import argparse
from datetime import datetime
from typing import Dict, List, Set
from collections import defaultdict

def load_data(json_file: str) -> Dict:
    """Load data from JSON file"""
    with open(json_file, 'r') as f:
        return json.load(f)

def get_resource_display_name(resource: Dict) -> str:
    """Get a human-readable display name for a resource"""
    name = resource.get('name', 'Unknown')
    resource_type = resource.get('type', '').split('/')[-1] if resource.get('type') else 'Unknown'
    location = resource.get('location', 'Unknown')
    return f"{name} ({resource_type})"

def get_resource_type_category(resource_type: str) -> str:
    """Categorize resource types for better organization"""
    type_lower = resource_type.lower()
    
    if 'compute' in type_lower or 'virtualmachines' in type_lower:
        return "💻 Compute"
    elif 'web' in type_lower or 'sites' in type_lower or 'serverfarms' in type_lower:
        return "🌐 Web & App Services"
    elif 'app/' in type_lower and 'container' in type_lower:
        return "📦 Container Apps"
    elif 'storage' in type_lower:
        return "💾 Storage"
    elif 'sql' in type_lower or 'database' in type_lower or 'documentdb' in type_lower or 'postgresql' in type_lower or 'mysql' in type_lower:
        return "🗄️ Databases"
    elif 'keyvault' in type_lower:
        return "🔐 Security"
    elif 'insights' in type_lower or 'operationalinsights' in type_lower:
        return "📊 Monitoring"
    elif 'network' in type_lower or 'publicip' in type_lower or 'loadbalancer' in type_lower:
        return "🌐 Networking"
    elif 'apimanagement' in type_lower:
        return "🔌 API Management"
    elif 'containerregistry' in type_lower:
        return "📦 Container Registry"
    elif 'signalr' in type_lower or 'webpubsub' in type_lower:
        return "📡 Real-time Communication"
    elif 'servicebus' in type_lower or 'eventhub' in type_lower:
        return "📨 Messaging"
    elif 'logic' in type_lower:
        return "⚡ Logic Apps"
    else:
        return "🔧 Other Services"

def generate_dependency_report(data: Dict, output_file: str = "dependency_report.md"):
    """Generate a comprehensive dependency report"""
    
    # Extract data
    subscription_id = data.get('subscription_id', 'Unknown')
    resources = data.get('resources', [])
    resource_groups = data.get('resource_groups', [])
    confirmed_deps = data.get('confirmed_dependencies', {})
    potential_deps = data.get('potential_dependencies', {})
    metadata = data.get('metadata', {})
    
    # Create resource lookup
    resource_lookup = {r['id']: r for r in resources}
    
    # Organize resources by type and resource group
    resources_by_type = defaultdict(list)
    resources_by_rg = defaultdict(list)
    
    for resource in resources:
        resource_type = resource.get('type', 'Unknown')
        resource_group = resource.get('resourceGroup', 'Unknown')
        resources_by_type[get_resource_type_category(resource_type)].append(resource)
        resources_by_rg[resource_group].append(resource)
    
    # Generate report
    report = []
    
    # Header
    report.append("# Azure Resource Dependency Report")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Subscription:** {subscription_id[:10]}...")
    report.append("")
    
    # Executive Summary
    report.append("## 📋 Executive Summary")
    report.append("")
    total_resources = len(resources)
    total_resource_groups = len(resource_groups)
    total_confirmed_deps = sum(len(deps) for deps in confirmed_deps.values())
    total_potential_deps = sum(len(deps) for deps in potential_deps.values())
    enhanced_resources = metadata.get('enhanced_resources', 0)
    
    report.append(f"- **Total Resources:** {total_resources}")
    report.append(f"- **Resource Groups:** {total_resource_groups}")
    report.append(f"- **Confirmed Dependencies:** {total_confirmed_deps}")
    report.append(f"- **Potential Dependencies:** {total_potential_deps}")
    report.append(f"- **Enhanced Resources:** {enhanced_resources} (with detailed configuration analysis)")
    report.append("")
    
    # Resource Overview by Type
    report.append("## 🏗️ Resource Overview by Type")
    report.append("")
    
    for category in sorted(resources_by_type.keys()):
        resource_list = resources_by_type[category]
        report.append(f"### {category}")
        report.append("")
        
        for resource in sorted(resource_list, key=lambda x: x.get('name', '')):
            display_name = get_resource_display_name(resource)
            location = resource.get('location', 'Unknown')
            resource_group = resource.get('resourceGroup', 'Unknown')
            
            # Count dependencies
            resource_id = resource['id']
            confirmed_count = len(confirmed_deps.get(resource_id, []))
            potential_count = len(potential_deps.get(resource_id, []))
            
            dep_info = ""
            if confirmed_count > 0 or potential_count > 0:
                dep_info = f" - Dependencies: {confirmed_count} confirmed, {potential_count} potential"
            
            report.append(f"- **{display_name}**")
            report.append(f"  - Location: {location}")
            report.append(f"  - Resource Group: {resource_group}")
            if dep_info:
                report.append(f"  {dep_info}")
            report.append("")
    
    # Dependency Analysis
    report.append("## 🔗 Dependency Analysis")
    report.append("")
    
    # Find resources with the most dependencies
    resources_with_deps = []
    for resource_id, deps in confirmed_deps.items():
        if resource_id in resource_lookup:
            resource = resource_lookup[resource_id]
            confirmed_count = len(deps)
            potential_count = len(potential_deps.get(resource_id, []))
            total_deps = confirmed_count + potential_count
            
            if total_deps > 0:
                resources_with_deps.append({
                    'resource': resource,
                    'confirmed': confirmed_count,
                    'potential': potential_count,
                    'total': total_deps
                })
    
    # Sort by total dependencies
    resources_with_deps.sort(key=lambda x: x['total'], reverse=True)
    
    if resources_with_deps:
        report.append("### 📊 Resources with Most Dependencies")
        report.append("")
        
        for item in resources_with_deps[:10]:  # Top 10
            resource = item['resource']
            display_name = get_resource_display_name(resource)
            confirmed = item['confirmed']
            potential = item['potential']
            
            report.append(f"- **{display_name}**: {confirmed} confirmed + {potential} potential = {confirmed + potential} total")
        
        report.append("")
    
    # Detailed Dependencies
    report.append("### 🔍 Detailed Dependencies")
    report.append("")
    
    for item in resources_with_deps:
        resource = item['resource']
        resource_id = resource['id']
        display_name = get_resource_display_name(resource)
        
        confirmed_list = confirmed_deps.get(resource_id, [])
        potential_list = potential_deps.get(resource_id, [])
        
        if confirmed_list or potential_list:
            report.append(f"#### {display_name}")
            report.append("")
            
            if confirmed_list:
                report.append("**🔴 Confirmed Dependencies:**")
                for dep_id in confirmed_list:
                    if dep_id in resource_lookup:
                        dep_resource = resource_lookup[dep_id]
                        dep_display_name = get_resource_display_name(dep_resource)
                        report.append(f"- {dep_display_name}")
                report.append("")
            
            if potential_list:
                report.append("**🟠 Potential Dependencies:**")
                for dep_id in potential_list:
                    if dep_id in resource_lookup:
                        dep_resource = resource_lookup[dep_id]
                        dep_display_name = get_resource_display_name(dep_resource)
                        report.append(f"- {dep_display_name}")
                report.append("")
    
    # Resource Groups Analysis
    report.append("## 📁 Resource Groups Analysis")
    report.append("")
    
    for rg_name in sorted(resources_by_rg.keys()):
        rg_resources = resources_by_rg[rg_name]
        report.append(f"### {rg_name}")
        report.append("")
        report.append(f"**Resources:** {len(rg_resources)}")
        report.append("")
        
        # Count dependencies within and outside the resource group
        internal_deps = 0
        external_deps = 0
        
        for resource in rg_resources:
            resource_id = resource['id']
            all_deps = list(confirmed_deps.get(resource_id, [])) + list(potential_deps.get(resource_id, []))
            
            for dep_id in all_deps:
                if dep_id in resource_lookup:
                    dep_resource = resource_lookup[dep_id]
                    if dep_resource.get('resourceGroup') == rg_name:
                        internal_deps += 1
                    else:
                        external_deps += 1
        
        if internal_deps > 0 or external_deps > 0:
            report.append(f"**Dependencies:**")
            report.append(f"- Internal (within RG): {internal_deps}")
            report.append(f"- External (cross-RG): {external_deps}")
            report.append("")
        
        # List resource types in this RG
        type_counts = defaultdict(int)
        for resource in rg_resources:
            resource_type = resource.get('type', 'Unknown').split('/')[-1]
            type_counts[resource_type] += 1
        
        if type_counts:
            report.append("**Resource Types:**")
            for res_type, count in sorted(type_counts.items()):
                report.append(f"- {res_type}: {count}")
            report.append("")
    
    # Enhanced Features Summary
    if metadata.get('enhanced_mode', False):
        report.append("## 🚀 Enhanced Analysis Features")
        report.append("")
        report.append("This report was generated using enhanced resource discovery, which includes:")
        report.append("")
        report.append("- **🔍 Environment Variables Analysis**: Detection of connection strings and configuration")
        report.append("- **🌐 Network Information**: IP addresses, hostnames, and endpoints")
        report.append("- **🔐 Secret References**: Key Vault references and secret patterns")
        report.append("- **⚙️ Resource-Specific Configurations**: Detailed service configurations")
        report.append("- **🔗 Advanced Dependency Detection**: URL parsing and pattern matching")
        report.append("")
        
        # Connection string examples found
        connection_examples = []
        for resource in resources:
            env_vars = resource.get('environmentVariables', {})
            if env_vars:
                app_settings = env_vars.get('appSettings', {})
                for key, value in app_settings.items():
                    if isinstance(value, str) and any(pattern in value.lower() for pattern in ['connection', 'endpoint', 'key=']):
                        connection_examples.append(f"- **{resource.get('name', 'Unknown')}**: {key}")
                        if len(connection_examples) >= 5:  # Limit examples
                            break
                if len(connection_examples) >= 5:
                    break
        
        if connection_examples:
            report.append("### 🔗 Connection Strings Detected")
            report.append("")
            for example in connection_examples:
                report.append(example)
            report.append("")
    
    # Recommendations
    report.append("## 💡 Recommendations")
    report.append("")
    
    # Find potential issues
    if external_deps > internal_deps * 2:
        report.append("- **🔄 Cross-Resource Group Dependencies**: Consider consolidating related resources into the same resource groups")
    
    if total_potential_deps > total_confirmed_deps:
        report.append("- **🔍 Review Potential Dependencies**: Many potential dependencies detected - review for accuracy")
    
    orphaned_resources = [r for r in resources if not confirmed_deps.get(r['id']) and not potential_deps.get(r['id'])]
    if len(orphaned_resources) > len(resources) * 0.3:
        report.append("- **🏝️ Isolated Resources**: Many resources appear to have no dependencies - verify if this is intentional")
    
    report.append("- **📊 Regular Reviews**: Periodically review dependencies to ensure architecture alignment")
    report.append("- **🔐 Security**: Ensure connection strings and secrets are properly secured in Key Vault")
    report.append("")
    
    # Footer
    report.append("---")
    report.append("")
    report.append("*This report was generated automatically from Azure Resource Graph data with enhanced dependency detection.*")
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Generate human-readable dependency report from JSON data')
    parser.add_argument('--input', '-i', default='azure_resource_graph.json', help='Input JSON file')
    parser.add_argument('--output', '-o', default='dependency_report.md', help='Output Markdown file')
    args = parser.parse_args()
    
    try:
        print(f"Loading data from {args.input}...")
        data = load_data(args.input)
        
        print("Generating dependency report...")
        output_file = generate_dependency_report(data, args.output)
        
        print(f"✅ Dependency report generated: {output_file}")
        
        # Print summary
        resources = data.get('resources', [])
        confirmed_deps = data.get('confirmed_dependencies', {})
        potential_deps = data.get('potential_dependencies', {})
        
        total_confirmed = sum(len(deps) for deps in confirmed_deps.values())
        total_potential = sum(len(deps) for deps in potential_deps.values())
        
        print(f"📊 Summary:")
        print(f"   - Resources analyzed: {len(resources)}")
        print(f"   - Confirmed dependencies: {total_confirmed}")
        print(f"   - Potential dependencies: {total_potential}")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find input file '{args.input}'")
        print("   Make sure to run azure_resource_graph.py first to generate the JSON data")
    except Exception as e:
        print(f"❌ Error generating report: {str(e)}")

if __name__ == "__main__":
    main() 