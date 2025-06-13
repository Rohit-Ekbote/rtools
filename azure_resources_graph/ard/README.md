# Azure Resource Dependency Graph Builder

This script analyzes Azure Resource Discovery JSON files and builds a dependency graph showing relationships between Azure resources. Outputs Mermaid diagram format for easy embedding in documentation.

## Features

- **Resource Extraction**: Parses Azure resource discovery JSON files and extracts all resources
- **Dependency Analysis**: Identifies various types of dependencies between resources:
  - Direct resource ID references
  - Container App managed environment dependencies
  - Metric alert scope dependencies
  - Autoscale target dependencies
  - Service endpoint dependencies (ServiceBus, KeyVault, Storage, etc.)
  - Container registry dependencies from container images
  - Storage account dependencies
- **Mermaid Chart Generation**: Creates Mermaid flowchart diagrams with:
  - Different shapes for different resource types
  - Color-coded resources by type
  - Directional arrows showing dependencies
  - Clean, readable format for documentation
- **Multiple Output Formats**: Supports Mermaid chart and JSON export
- **Flexible Chart Directions**: Supports TD (top-down), LR (left-right), and other orientations

## Installation

No external dependencies required! The script uses only Python standard library modules.

## Usage

### Basic Usage

```bash
python build_dependency_graph.py azure_resource_discovery.json
```

This will:
- Parse the JSON file
- Extract resources and dependencies
- Print a summary to the console
- Generate a Mermaid chart saved as `azure_dependency_graph.mmd`

### Advanced Usage

```bash
# Specify custom output file and direction
python build_dependency_graph.py azure_resource_discovery.json --output my_graph.mmd --direction LR

# Export dependency data to JSON
python build_dependency_graph.py azure_resource_discovery.json --export-json dependencies.json

# Skip chart generation (summary only)
python build_dependency_graph.py azure_resource_discovery.json --no-chart
```

### Command Line Options

- `json_file`: Path to the Azure resource discovery JSON file (required)
- `--output`, `-o`: Output file for the Mermaid chart (default: `azure_dependency_graph.mmd`)
- `--direction`: Chart direction (`TD`, `TB`, `BT`, `RL`, `LR`) (default: `TD`)
  - `TD`/`TB`: Top to bottom
  - `BT`: Bottom to top  
  - `LR`: Left to right
  - `RL`: Right to left
- `--export-json`: Export dependency data to JSON file
- `--no-chart`: Skip chart generation and only print summary

## Output

### Console Summary
The script prints a detailed summary including:
- Total number of resources
- Resource types and counts
- Detailed dependency relationships

### Mermaid Chart
Creates a `.mmd` file containing Mermaid flowchart syntax with:
- Resources as nodes with different shapes based on type
- Dependencies as directed arrows
- Color-coded resource types
- Resource names and types as labels
- Clean, readable format

### JSON Export
Optionally exports structured dependency data including:
- Complete resource information
- Dependency relationships
- Summary statistics

## Using the Mermaid Chart

The generated `.mmd` file can be used in:
- **GitHub/GitLab**: Mermaid charts render automatically in markdown files
- **Documentation sites**: Most support Mermaid diagrams
- **Mermaid Live Editor**: https://mermaid.live for viewing and editing
- **VS Code**: Mermaid preview extensions available

Example of embedding in markdown:
```markdown
```mermaid
flowchart TD
    app1[Web App<br/>(sites)] --> vault1[Key Vault<br/>(vaults)]
    app1 --> storage1[(Storage Account<br/>(storageAccounts))]
```
```

## Supported Resource Types

The script recognizes and provides unique shapes/colors for:
- **Storage Accounts** - Database cylinder shape
- **Key Vaults** - Rectangle shape
- **PostgreSQL Flexible Servers** - Hexagon shape
- **Web Apps** - Circle shape
- **App Service Plans** - Rounded rectangle
- **Container Registries** - Rectangle shape
- **Container App Managed Environments** - Hexagon shape
- **Container Apps** - Double circle shape
- **Logic Apps** - Stadium shape
- **Action Groups** - Rectangle shape
- **Metric Alerts** - Rectangle shape
- **Autoscale Settings** - Rectangle shape
- **Service Bus Namespaces** - Hexagon shape
- **Log Analytics Workspaces** - Rectangle shape
- **Event Grid System Topics** - Circle shape

## Dependency Types Detected

1. **Direct Resource References**: Resources that directly reference other resources by ID
2. **Container App Dependencies**: Container apps that depend on managed environments
3. **Metric Alert Dependencies**: Alerts that monitor specific resources
4. **Autoscale Dependencies**: Autoscale settings that target specific resources
5. **Service Endpoint Dependencies**: Resources that connect to Azure services via endpoints
6. **Container Registry Dependencies**: Container apps that pull images from registries
7. **Storage Dependencies**: Resources that use storage accounts

## Example Output

### Console Summary
```
=== Azure Resource Dependency Graph Summary ===
Total resources: 33
Total dependencies: 12

=== Resource Types ===
  Microsoft.App/containerApps: 6
  Microsoft.App/managedEnvironments: 2
  Microsoft.ContainerRegistry/registries: 2
  Microsoft.Storage/storageAccounts: 3
  Microsoft.Web/sites: 4
  ...

=== Dependencies ===
ca-web-ojcjiczjudu42 depends on:
  - cae-ojcjiczjudu42
  - crojcjiczjudu42

app-autoscale depends on:
  - plan-ojcjiczjudu42
```

### Mermaid Chart
```mermaid
flowchart TD
    ca_web_ojcjiczjudu42((ca-web-ojcjiczjudu42<br/>(containerApps))) --> cae_ojcjiczjudu42{{cae-ojcjiczjudu42<br/>(managedEnvironments)}}
    ca_web_ojcjiczjudu42 --> crojcjiczjudu42[crojcjiczjudu42<br/>(registries)]
    app_autoscale[app-autoscale<br/>(autoscaleSettings)] --> plan_ojcjiczjudu42(plan-ojcjiczjudu42<br/>(serverfarms))
```

## Troubleshooting

- Ensure the JSON file is valid and follows the Azure Resource Discovery format
- For large graphs, consider using `--direction LR` for better readability
- The script handles special characters in resource names automatically
- Mermaid chart files can be viewed in any text editor or Mermaid-compatible viewer 