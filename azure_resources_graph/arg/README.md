# Azure Resource Dependency Graph Generator

This tool generates a visual dependency graph of resources in your Azure subscription, helping you understand the relationships between different Azure services.

## Features

- **Automatic Resource Discovery**: Scans your Azure subscription for all resources
- **Dependency Analysis**: Identifies both confirmed and potential dependencies between resources
- **Visual Diagram**: Generates a Mermaid.js diagram showing the resource hierarchy and relationships
- **Resource Grouping**: Organizes resources by resource group and type for clarity
- **Customizable Output**: Save the diagram to a Markdown file for easy sharing

## Prerequisites

- Python 3.6 or later
- Azure CLI installed and configured
- Azure Resource Graph enabled for your subscription

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/azure-resource-graph.git
cd azure-resource-graph
```

2. Make the script executable:

```bash
chmod +x azure_resource_graph.py
```

## Usage

Run the tool with your Azure subscription to generate both data and visualizations:

```bash
./azure_resource_graph.py --data --html --md
```

By default, the tool uses your current Azure CLI subscription. You can specify a different subscription:

```bash
./azure_resource_graph.py --subscription "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" --data --html --md
```

The output will be saved with the prefix `azure_resource_graph` by default. You can specify a different output prefix:

```bash
./azure_resource_graph.py --output "my_resources" --data --html --md
```

This will generate:
- `my_resources.json` - Raw resource data
- `my_resources.html` - Interactive HTML visualization
- `my_resources.md` - Mermaid diagram in Markdown format

### Options

| Option | Description |
|--------|-------------|
| `--subscription`, `-s` | Specify the Azure subscription ID (if not provided, uses current subscription) |
| `--output`, `-o` | Specify the output file path prefix (default: azure_resource_graph) |
| `--potential-deps` | Include potential dependencies in the diagram |
| `--data` | Query Azure for resource data instead of using existing data file |
| `--html` | Generate interactive HTML visualization |
| `--md` | Generate Mermaid diagram in Markdown format |
| `--enhanced-mode` | Use enhanced resource discovery with detailed information (slower but more comprehensive) |
| `--resourcegroup-ids` | Comma-separated list of resource group IDs to filter resources by |
| `--resource-types` | Comma-separated list of resource types to filter resources by (without Microsoft. prefix, e.g., "Web/sites,Storage/storageAccounts") |

### Dependency Types

The tool identifies two types of dependencies:

1. **Confirmed Dependencies** (solid lines): Direct connections found in resource properties that explicitly reference other resources.
2. **Potential Dependencies** (dotted lines): Inferred connections based on common architectural patterns (can be included with `--potential-deps`).

### Filtering Resources

You can filter resources by resource type or resource group:

```bash
# Filter by resource types (without Microsoft. prefix)
./azure_resource_graph.py --resource-types "Web/sites,Storage/storageAccounts,KeyVault/vaults" --data --html --md

# Filter by resource groups
./azure_resource_graph.py --resourcegroup-ids "rg-prod-web,rg-prod-data" --data --html --md

# Combine filters
./azure_resource_graph.py --resource-types "Web/sites,App/containerApps" --resourcegroup-ids "rg-prod-web" --data --html --md
```

#### Common Resource Types (without Microsoft. prefix)

| Resource Type | Description |
|---------------|-------------|
| `Web/sites` | App Services (Web Apps) |
| `Storage/storageAccounts` | Storage Accounts |
| `KeyVault/vaults` | Key Vaults |
| `App/containerApps` | Container Apps |
| `App/managedEnvironments` | Container App Environments |
| `Compute/virtualMachines` | Virtual Machines |
| `Network/virtualNetworks` | Virtual Networks |
| `Sql/servers` | SQL Servers |
| `Sql/servers/databases` | SQL Databases |
| `Insights/components` | Application Insights |
| `ContainerRegistry/registries` | Container Registries |

Example:
```bash
# Include only confirmed dependencies
./azure_resource_graph.py --data --html --md

# Include potential dependencies for better insight
./azure_resource_graph.py --potential-deps --data --html --md

# Use enhanced mode for detailed resource analysis
./azure_resource_graph.py --enhanced-mode --potential-deps --data --html --md
```

## Example Output

The tool generates a Markdown file containing a Mermaid.js diagram. Here's an example:

```mermaid
graph TD;
    A[Subscription<br/>2a0cf760-b...]
    
    %% Resource Groups
    A --> B["RG: rg-contoso-01-app"]
    A --> C["RG: rg-contoso-01-data"]
    
    %% Compute Resources
    B --> J["Container App<br/>app-api-ojcjiczjudu42"]
    B --> K["Container App Environment<br/>cae-ojcjiczjudu42"]
    
    %% Data Resources
    C --> Q["PostgreSQL<br/>psql-db-ojcjiczjudu42"]
    C --> R["Key Vault<br/>kv-ojcjiczjudu42"]
    
    %% Dependencies
    J --> K
    J --> V
    
    %% Potential Dependencies
    J -.-> Q
    J -.-> R
```

## Interpretation

In the generated diagram:

- **Solid lines** represent confirmed dependencies between resources
- **Dotted lines** represent potential dependencies based on common architectural patterns
- Resources are organized by resource group and then by type

## How It Works

1. The tool uses Azure CLI to authenticate and access your Azure subscription
2. It queries the Azure Resource Graph to discover all resources and resource groups
3. It analyzes resource properties to identify dependencies
4. For certain resource types, it applies heuristics to detect potential dependencies
5. Finally, it generates a Mermaid.js diagram showing the resource hierarchy and relationships

## Documentation

For more details on how the tool works and how to extend it:

- [DEPENDENCIES.md](DEPENDENCIES.md) - Detailed explanation of how resource dependencies are detected
- [EXTENDING.md](EXTENDING.md) - Guide for extending the tool to support additional Azure resource types

## Limitations

- The tool can only detect dependencies that are explicitly defined in resource properties
- Some dependencies might be missed if they're not reflected in the Azure Resource Graph
- The tool cannot detect dependencies outside the subscription boundary

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 