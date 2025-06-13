# Enhanced Azure Resource Graph Features

## Overview
The `azure_resource_graph.py` script has been significantly enhanced with comprehensive resource discovery capabilities, inspired by the `azure_resource_discovery.py` implementation. The script now provides much more detailed information about Azure resources and improved dependency detection.

## Key Enhancements

### 1. Enhanced Resource Information Collection
- **Network Information**: Collects IP addresses, hostnames, FQDNs, and network endpoints for various resource types
- **Environment Variables**: Gathers application settings, connection strings, and environment configurations
- **Resource-Specific Configurations**: Collects detailed configurations specific to each Azure service type

### 2. Supported Resource Types for Enhanced Data
- **Virtual Machines**: VM sizes, OS information, network details, storage configurations
- **App Services/Web Apps**: Application settings, connection strings, hostnames, outbound IPs
- **Storage Accounts**: SKUs, access tiers, network rules, primary endpoints
- **SQL Databases**: Edition, service objectives, collation settings
- **Key Vaults**: SKUs, access policies, deployment settings
- **Public IP Addresses**: IP allocations, FQDNs, allocation methods
- **Load Balancers**: Frontend IP configurations
- **Container Instances**: Environment variables for containers
- **Function Apps**: Function-specific application settings

### 3. Advanced Dependency Detection
The enhanced dependency detection now uses:
- **Environment Variables Analysis**: Detects dependencies through connection strings and app settings
- **Network Configuration**: Identifies dependencies through network rules and endpoints
- **Resource-Specific Properties**: Uses detailed configurations to find relationships
- **Cross-Reference Analysis**: Matches resource names and IDs across all collected data

### 4. Enhanced Dependency Patterns
- **Database Connections**: Automatically detects SQL Database dependencies from connection strings
- **Storage Dependencies**: Identifies Storage Account usage from blob/table endpoints
- **Application Insights**: Enhanced detection of App Insights connections
- **Key Vault References**: Detects Key Vault usage in configurations
- **Network Dependencies**: VNet rules, subnet associations, network interface dependencies

### 5. Performance Options
- **Enhanced Mode (Default)**: Comprehensive resource analysis with detailed information
- **Basic Mode (`--basic-mode`)**: Faster execution with basic resource information only

## Usage Examples

### Enhanced Mode (Recommended)
```bash
python azure_resource_graph.py
```
This provides the most comprehensive analysis with all enhanced features.

### Basic Mode (Faster)
```bash
python azure_resource_graph.py --basic-mode
```
This provides faster execution with basic resource information.

### Enhanced Mode with Custom Output
```bash
python azure_resource_graph.py -o my_enhanced_graph
```
Saves enhanced data to `my_enhanced_graph.json`, `my_enhanced_graph.html`, and `my_enhanced_graph.md`.

## Output Enhancements

### JSON Output
The JSON output now includes:
- Enhanced resource properties with `networkInfo`, `environmentVariables`, and `specificConfiguration`
- Metadata section with statistics about enhanced data collection
- More comprehensive dependency mappings

### HTML Visualization
The HTML output benefits from enhanced data by:
- Displaying more detailed resource information
- Better dependency visualization based on comprehensive analysis
- Enhanced tooltips with network and configuration details

### Markdown Visualization
The Markdown output includes:
- More accurate dependency relationships
- Enhanced resource descriptions with detailed configurations

## Technical Implementation

### New Functions Added
1. `get_network_information()` - Collects network-related information
2. `get_environment_variables()` - Gathers environment variables and app settings
3. `get_resource_specific_config()` - Collects service-specific configurations
4. `list_resources_basic()` - Basic resource listing for performance mode
5. Enhanced `get_resource_dependencies()` - Uses all collected data for dependency detection

### Data Structure Enhancements
Resources now include additional fields:
- `networkInfo`: Network-related information (IPs, hostnames, endpoints)
- `environmentVariables`: App settings, connection strings, environment configurations
- `specificConfiguration`: Resource-type-specific detailed configurations
- `properties`: Enhanced properties from Azure Resource Graph

## Benefits

1. **More Accurate Dependencies**: Better detection of actual resource relationships
2. **Comprehensive Resource Inventory**: Detailed information for security, compliance, and management
3. **Enhanced Troubleshooting**: Network and configuration details aid in problem resolution
4. **Better Visualization**: More informative diagrams and reports
5. **Flexible Performance**: Choose between comprehensive analysis or faster execution

## Migration Notes

- The enhanced mode is backward compatible with existing usage
- Existing JSON files will continue to work but won't have enhanced data
- Use `--basic-mode` if you need the previous behavior for performance reasons
- Enhanced features require appropriate Azure CLI permissions for detailed resource access

## Performance Considerations

- Enhanced mode takes longer due to detailed API calls for each resource
- Basic mode provides similar performance to the original implementation
- Enhanced data collection is done in parallel where possible
- Failed resource enhancements fall back to basic information gracefully 