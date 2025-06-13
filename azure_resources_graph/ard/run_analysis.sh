#!/bin/bash

# Azure Resource Dependency Graph Analysis Script
# This script runs the dependency graph builder with common options

# Check if input file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <azure_resource_discovery.json> [OPTIONS]"
    echo ""
    echo "Examples:"
    echo "  $0 azure_resource_discovery.json                    # Basic analysis with Mermaid chart"
    echo "  $0 azure_resource_discovery.json --no-chart         # Analysis without chart generation"
    echo "  $0 azure_resource_discovery.json --direction LR     # Use left-to-right direction"
    echo "  $0 azure_resource_discovery.json --export-json deps.json  # Export to JSON"
    exit 1
fi

INPUT_FILE="$1"
shift  # Remove first argument so we can pass remaining args to Python script

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: File '$INPUT_FILE' not found!"
    exit 1
fi

# No dependencies to install - script uses only Python standard library

# Run the analysis
echo "Running Azure Resource Dependency Graph Analysis..."
echo "Input file: $INPUT_FILE"
echo ""

python build_dependency_graph.py "$INPUT_FILE" "$@"

echo ""
echo "Analysis complete!"

# Show generated files
echo "Generated files:"
ls -la *.mmd *.json 2>/dev/null | grep -E "\.(mmd|json)$" || echo "No output files found"

# If Mermaid file was generated, show usage tips
if [ -f "azure_dependency_graph.mmd" ]; then
    echo ""
    echo "To view the Mermaid chart:"
    echo "  - Visit https://mermaid.live and paste the content"
    echo "  - Use a Mermaid preview extension in VS Code"
    echo "  - Embed in GitHub/GitLab markdown files"
fi 