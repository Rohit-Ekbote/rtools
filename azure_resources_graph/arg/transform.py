#!/usr/bin/env python3
"""
Transform Azure Resource Graph data into a nested structure.

This script transforms Azure Resource Graph data from the format:
{"subscription_id": "...", "resources": [...]}

Into the format:
{"<subscriptionID>": {"<resourceGroupName>": {"<resourceType>": {"<resourceID>": {<resource details>}}}}}
"""

import json
import argparse
import sys
import re
from pathlib import Path


def extract_subscription_from_resource_id(resource_id):
    """Extract subscription ID from Azure resource ID."""
    match = re.search(r'/subscriptions/([^/]+)', resource_id)
    return match.group(1) if match else None


def transform_resources(input_data):
    """
    Transform resources from flat list to nested structure.
    
    Args:
        input_data (dict): Input data with 'resources' key containing list of resources
        
    Returns:
        dict: Transformed data in nested format
    """
    transformed = {}
    
    # Get subscription ID from the top level or extract from first resource
    subscription_id = input_data.get('subscription_id')
    
    resources = input_data.get('resources', [])
    
    for resource in resources:
        # Extract resource information
        #resource_id = resource.get('id', '')
        #if 'id' in resource:
        #    del resource['id']
        resource_group = resource.get('resourceGroup', '')
        if 'resourceGroup' in resource:
            del resource['resourceGroup']
        resource_type = resource.get('type', '').lower()
        if 'type' in resource:
            del resource['type']
        resource_name = resource.get('name', '')
        if 'name' in resource:
            del resource['name']
        
        # If subscription_id is not available at top level, extract from resource ID
        if not subscription_id:
            subscription_id = extract_subscription_from_resource_id(resource_id)
        
        if not subscription_id or not resource_group or not resource_type or not resource_name:
            print(f"Warning: Skipping resource with missing required fields: {resource_name}", file=sys.stderr)
            continue
        
        # Initialize nested structure
        if subscription_id not in transformed:
            transformed[subscription_id] = {}
        
        if resource_group not in transformed[subscription_id]:
            transformed[subscription_id][resource_group] = {}
        
        if resource_type not in transformed[subscription_id][resource_group]:
            transformed[subscription_id][resource_group][resource_type] = {}
        
        # Store the resource details using resource ID as key
        transformed[subscription_id][resource_group][resource_type][resource_name] = resource
    
    return transformed


def main():
    """Main function to handle command line arguments and file processing."""
    parser = argparse.ArgumentParser(
        description='Transform Azure Resource Graph data into nested structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transform.py --input rdebug.json --output transformed.json
  python transform.py --input azure_resource_graph.json --output output.json
        """
    )
    
    parser.add_argument(
        '--source', 
        required=True,
        help='Input JSON file containing Azure Resource Graph data'
    )
    
    
    args = parser.parse_args()
    
    input_path = args.source + ".json"
    output_path = args.source + "_transformed.json"
    # Validate input file exists
    ipath = Path(input_path)
    if not ipath.exists():
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load input data
        print(f"Loading data from {input_path}...")
        with open(input_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        # Validate input format
        if not isinstance(input_data, dict):
            print("Error: Input file must contain a JSON object.", file=sys.stderr)
            sys.exit(1)
        
        if 'resources' not in input_data:
            print("Error: Input file must contain a 'resources' key.", file=sys.stderr)
            sys.exit(1)
        
        if not isinstance(input_data['resources'], list):
            print("Error: 'resources' value must be a list.", file=sys.stderr)
            sys.exit(1)
        
        # Transform the data
        print(f"Transforming {len(input_data['resources'])} resources...")
        transformed_data = transform_resources(input_data)
        
        # Calculate statistics
        total_subscriptions = len(transformed_data)
        total_resource_groups = sum(len(rgs) for rgs in transformed_data.values())
        total_resource_types = sum(
            len(rts) for subs in transformed_data.values() 
            for rts in subs.values()
        )
        total_resources = sum(
            len(resources) for subs in transformed_data.values()
            for rgs in subs.values() for resources in rgs.values()
        )
        
        print(f"Transformation complete:")
        print(f"  - {total_subscriptions} subscription(s)")
        print(f"  - {total_resource_groups} resource group(s)")
        print(f"  - {total_resource_types} resource type(s)")
        print(f"  - {total_resources} resource(s)")
        
        # Save transformed data
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Saving transformed data to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=2, ensure_ascii=False)
        
        print("Transformation completed successfully!")
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main() 