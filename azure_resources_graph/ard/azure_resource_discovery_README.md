# Azure Resource Discovery Scripts

This repository contains two comprehensive scripts for discovering and analyzing Azure resources using Azure CLI commands. Both scripts provide identical functionality but in different languages for different preferences.

## 🎯 Purpose

These scripts discover all Azure resources in your subscription and gather comprehensive information including:

- **Basic Resource Information**: Name, type, location, resource group, tags
- **Network Information**: IP addresses, FQDNs, hostnames, endpoints
- **Environment Variables**: App settings, connection strings (for supported resources)
- **Resource-Specific Configurations**: VM sizes, storage SKUs, database settings, etc.
- **Security Configurations**: Key vault policies, network access rules

## 📋 Prerequisites

### Required
- **Azure CLI**: Must be installed and accessible via `az` command
- **Azure Login**: Must be logged in (`az login`)
- **Permissions**: Read access to the subscription/resources you want to discover

### Optional (Recommended)
- **jq**: For better JSON formatting and processing (especially for bash script)
- **Python 3.6+**: For the Python script

## 📁 Files

- `azure_resource_discovery.py` - Python implementation
- `azure_resource_discovery.sh` - Bash shell implementation
- `README_azure_discovery.md` - This documentation

## 🚀 Usage

### Python Script

```bash
# Basic usage (current subscription context)
./azure_resource_discovery.py

# Specify subscription
./azure_resource_discovery.py --subscription "12345678-1234-1234-1234-123456789012"

# Save output to file
./azure_resource_discovery.py --output "azure_resources.json"

# Full featured run with verbose output
./azure_resource_discovery.py -s "subscription-id" -o "report.json" -v

# Show help
./azure_resource_discovery.py --help
```

### Bash Script

```bash
# Basic usage (current subscription context)
./azure_resource_discovery.sh

# Specify subscription
./azure_resource_discovery.sh --subscription "12345678-1234-1234-1234-123456789012"

# Save output to file
./azure_resource_discovery.sh --output "azure_resources.json"

# Full featured run with verbose output
./azure_resource_discovery.sh -s "subscription-id" -o "report.json" -v

# Show help
./azure_resource_discovery.sh --help
```

## 📊 Output Structure

The scripts generate a comprehensive JSON report with the following structure:

```json
{
  "discoveryMetadata": {
    "timestamp": "2024-01-15T10:30:00.000Z",
    "subscription": {
      "id": "subscription-id",
      "name": "subscription-name",
      "tenantId": "tenant-id"
    },
    "totalResourcesFound": 42,
    "toolVersion": "1.0.0"
  },
  "resources": [
    {
      "id": "/subscriptions/.../resourceGroups/rg1/providers/Microsoft.Web/sites/myapp",
      "name": "myapp",
      "type": "Microsoft.Web/sites",
      "location": "eastus",
      "resourceGroup": "rg1",
      "tags": {
        "environment": "production",
        "owner": "team-alpha"
      },
      "properties": { ... },
      "networkInfo": {
        "defaultHostName": "myapp.azurewebsites.net",
        "hostNames": ["myapp.azurewebsites.net"],
        "outboundIpAddresses": ["40.1.2.3", "40.1.2.4"]
      },
      "environmentVariables": {
        "appSettings": {
          "WEBSITE_NODE_DEFAULT_VERSION": "14.15.1",
          "DATABASE_URL": "..."
        },
        "connectionStrings": {
          "DefaultConnection": "Server=..."
        }
      },
      "specificConfiguration": {
        "sku": "Standard",
        "workerCount": 1
      }
    }
  ]
}
```

## 🔍 Supported Resource Types

The scripts provide specialized discovery for these resource types:

### Compute Resources
- **Virtual Machines**: VM size, OS type, network interfaces, IP addresses
- **Virtual Machine Scale Sets**: Configuration and instances
- **Container Instances**: Environment variables, IP addresses

### Storage Resources
- **Storage Accounts**: SKU, access tier, endpoints, encryption settings
- **Disk**: Size, type, encryption status

### Networking Resources
- **Public IP Addresses**: IP address, FQDN, allocation method
- **Load Balancers**: Frontend IPs, backend pools
- **Network Security Groups**: Security rules
- **Virtual Networks**: Address space, subnets

### Web & Mobile
- **App Services**: Hostnames, app settings, connection strings, IP addresses
- **Function Apps**: Function app settings, runtime configuration
- **API Management**: Endpoints, policies

### Databases
- **SQL Databases**: Edition, service tier, collation, max size
- **SQL Servers**: Admin login, firewall rules
- **Cosmos DB**: Consistency policy, endpoints
- **MySQL/PostgreSQL**: Configuration, firewall rules

### Identity & Security
- **Key Vaults**: SKU, access policies, network rules
- **Managed Identity**: Client ID, principal ID

### Analytics & Monitoring
- **Log Analytics Workspaces**: Retention policy, pricing tier
- **Application Insights**: Application type, sampling settings

## 🔧 Command Line Options

Both scripts support the same command-line options:

| Option | Short | Description |
|--------|-------|-------------|
| `--subscription` | `-s` | Azure subscription ID (uses current context if not provided) |
| `--output` | `-o` | Output file path (prints to stdout if not provided) |
| `--verbose` | `-v` | Enable verbose output with progress details |
| `--help` | `-h` | Show help message and examples |

## 📖 Examples

### Discover All Resources in Current Subscription
```bash
./azure_resource_discovery.py
```

### Target Specific Subscription and Save to File
```bash
./azure_resource_discovery.py \
  --subscription "12345678-1234-1234-1234-123456789012" \
  --output "production_resources.json"
```

### Verbose Output for Debugging
```bash
./azure_resource_discovery.sh -v -o "debug_output.json"
```

### Process Output with jq (for bash script)
```bash
./azure_resource_discovery.sh | jq '.resources[] | select(.type == "Microsoft.Web/sites")'
```

## 🛠️ Error Handling

The scripts include comprehensive error handling:

- **Authentication Issues**: Checks for Azure CLI login status
- **Permission Errors**: Gracefully handles resources you don't have access to
- **Network Timeouts**: Continues processing other resources if one fails
- **Invalid Subscriptions**: Validates subscription access before processing

## 🚨 Security Considerations

### Information Sensitivity
- Scripts may retrieve sensitive information like connection strings and app settings
- Environment variables could contain secrets
- Use appropriate access controls for output files

### Permissions Required
- **Reader** role at subscription level (minimum)
- Additional permissions may be needed for specific resource types:
  - **Website Contributor** for App Service environment variables
  - **Key Vault Reader** for key vault configurations

### Best Practices
1. Review output before sharing
2. Use secure file permissions for output files
3. Consider excluding sensitive resource types if not needed
4. Run with least-privilege accounts when possible

## 📋 Troubleshooting

### Common Issues

**Azure CLI Not Found**
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

**Not Logged In**
```bash
# Login to Azure
az login
```

**Permission Denied**
```bash
# Check current account
az account show

# List available subscriptions
az account list --output table

# Set default subscription
az account set --subscription "subscription-id"
```

**jq Not Found (for bash script)**
```bash
# Install jq
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# CentOS/RHEL
sudo yum install jq
```

### Performance Tips

1. **Use Specific Subscriptions**: Avoid running on subscriptions with thousands of resources
2. **Filter Resources**: Consider modifying scripts to filter by resource group if needed
3. **Parallel Processing**: The Python script includes some parallel processing capabilities
4. **Output to File**: Always use `-o` for large datasets to avoid terminal overflow

## 📈 Future Enhancements

Potential improvements for these scripts:

- **Resource Filtering**: Add options to filter by resource type, location, or tags
- **Parallel Processing**: Enhance concurrent resource processing
- **Additional Resource Types**: Add support for more Azure services
- **Export Formats**: Support for CSV, Excel, or other formats
- **Incremental Discovery**: Cache and update only changed resources
- **Integration**: REST API version for programmatic usage

## 🤝 Contributing

Feel free to enhance these scripts by:

1. Adding support for new resource types
2. Improving error handling
3. Adding new output formats
4. Optimizing performance
5. Adding filtering capabilities

## 📄 License

These scripts are provided as-is for educational and operational purposes. Modify and use according to your organization's policies and requirements. 