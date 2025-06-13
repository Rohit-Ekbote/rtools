#!/usr/bin/env python3
"""
Azure Resource Dependency Graph Generator - HTML Visualization Module

This module contains functions for generating interactive HTML visualizations of Azure resources.
"""

import json
from typing import Dict, List, Set

def truncate_subscription_id(subscription_id: str) -> str:
    """
    Truncate subscription ID to first 10 characters plus ellipsis.
    
    Args:
        subscription_id: The full Azure subscription ID
        
    Returns:
        Truncated subscription ID
    """
    return subscription_id[:10] + "..."

def generate_html_diagram(subscription_id: str, resources: List[dict], resource_groups: List[dict], 
                          confirmed_dependencies: Dict[str, Set[str]], potential_dependencies: Dict[str, Set[str]], 
                          include_potential_deps: bool = True,
                          output_file: str = "azure_resources_diagram.html") -> None:
    """
    Generate an interactive HTML diagram of Azure resources and their dependencies.
    
    Args:
        subscription_id: The Azure subscription ID
        resources: List of resource objects
        resource_groups: List of resource group objects
        confirmed_dependencies: Dictionary mapping resource IDs to sets of confirmed dependent resource IDs
        potential_dependencies: Dictionary mapping resource IDs to sets of potential dependent resource IDs
        include_potential_deps: Whether to include potential dependencies in the diagram
        output_file: Output HTML file path
    """
    # Get human-readable type names
    type_display_names = {
        'microsoft.app/containerapps': 'Container App',
        'microsoft.app/managedenvironments': 'Container App Environment',
        'microsoft.web/sites': 'Web App',
        'microsoft.web/serverfarms': 'App Service Plan',
        'microsoft.web/staticsites': 'Static Site',
        'microsoft.containerregistry/registries': 'Container Registry',
        'microsoft.keyvault/vaults': 'Key Vault',
        'microsoft.dbforpostgresql/flexibleservers': 'PostgreSQL',
        'microsoft.sql/servers': 'SQL Server',
        'microsoft.sql/servers/databases': 'SQL Database',
        'microsoft.documentdb/databaseaccounts': 'Cosmos DB',
        'microsoft.storage/storageaccounts': 'Storage Account',
        'microsoft.servicebus/namespaces': 'Service Bus',
        'microsoft.signalrservice/webpubsub': 'Web PubSub',
        'microsoft.signalrservice/signalr': 'SignalR Service',
        'microsoft.insights/components': 'App Insights',
        'microsoft.insights/actiongroups': 'Action Group',
        'microsoft.insights/metricalerts': 'Metric Alert',
        'microsoft.operationalinsights/workspaces': 'Log Analytics',
        'microsoft.apimanagement/service': 'API Management',
        'microsoft.network/networkwatchers': 'Network Watcher',
        'microsoft.network/virtualnetworks': 'Virtual Network',
        'microsoft.network/networksecuritygroups': 'Network Security Group',
        'microsoft.network/publicipaddresses': 'Public IP',
        'microsoft.network/applicationgateways': 'Application Gateway',
        'microsoft.network/loadbalancers': 'Load Balancer',
        'microsoft.network/frontdoors': 'Front Door',
        'microsoft.cdn/profiles': 'CDN Profile',
        'microsoft.cdn/profiles/endpoints': 'CDN Endpoint',
        'microsoft.portal/dashboards': 'Dashboard',
        'microsoft.logic/workflows': 'Logic App',
        'microsoft.eventgrid/systemtopics': 'Event Grid',
        'microsoft.eventgrid/topics': 'Event Grid Topic',
        'microsoft.eventhub/namespaces': 'Event Hub',
        'microsoft.cache/redis': 'Redis Cache',
        'microsoft.cognitiveservices/accounts': 'Cognitive Service',
        'microsoft.machinelearningservices/workspaces': 'ML Workspace',
        'microsoft.compute/virtualmachines': 'Virtual Machine',
        'microsoft.compute/virtualmachinescalesets': 'VM Scale Set',
        'microsoft.containerservice/managedclusters': 'AKS Cluster',
        'microsoft.datafactory/factories': 'Data Factory',
        'microsoft.synapse/workspaces': 'Synapse Workspace',
        'microsoft.batch/batchaccounts': 'Batch Account',
        'microsoft.search/searchservices': 'Search Service',
        'microsoft.dbformysql/flexibleservers': 'MySQL Server',
        'microsoft.dbformariadb/servers': 'MariaDB Server',
        'microsoft.devices/iothubs': 'IoT Hub',
        'microsoft.notificationhubs/namespaces': 'Notification Hub'
    }
    
    # Function to get display name based on resource kind
    def get_display_name(resource_type: str, resource: dict) -> str:
        display_name = type_display_names.get(resource_type, resource_type.split('/')[-1].capitalize())
        
        # Special handling based on resource kind
        if resource_type == 'microsoft.web/sites' and resource.get('kind'):
            kind = resource.get('kind', '').lower()
            if 'functionapp' in kind:
                return 'Function App'
            elif 'api' in kind:
                return 'API App'
            elif 'container' in kind:
                return 'Container Web App'
            elif 'linux' in kind:
                return 'Linux Web App'
        
        # Special handling for storage accounts based on kind
        elif resource_type == 'microsoft.storage/storageaccounts' and resource.get('kind'):
            kind = resource.get('kind', '').lower()
            if kind == 'blobstorage':
                return 'Blob Storage'
            elif kind == 'filestorage':
                return 'File Storage'
            elif kind == 'blockblobstorage':
                return 'Block Blob Storage'
            elif 'storagev2' in kind:
                return 'Storage Account v2'
        
        # Special handling for Cosmos DB based on kind
        elif resource_type == 'microsoft.documentdb/databaseaccounts' and resource.get('kind'):
            kind = resource.get('kind', '').lower()
            if kind == 'mongodb':
                return 'Cosmos DB (MongoDB)'
            elif kind == 'cassandra':
                return 'Cosmos DB (Cassandra)'
            elif kind == 'gremlin':
                return 'Cosmos DB (Gremlin)'
            elif kind == 'table':
                return 'Cosmos DB (Table)'
            
        return display_name
    
    # Create nodes and links for D3.js
    nodes = []
    links = []
    
    # Create a map of node IDs to indices
    node_indices = {}
    
    # Add subscription as the first node
    nodes.append({
        "id": subscription_id,
        "name": f"Subscription {truncate_subscription_id(subscription_id)}",
        "type": "subscription",
        "group": 0,
        "level": 0
    })
    node_indices[subscription_id] = 0
    
    # Add resource groups
    for i, rg in enumerate(resource_groups):
        node_index = len(nodes)
        nodes.append({
            "id": rg["id"],
            "name": rg["name"],
            "type": "resourceGroup",
            "group": 1,
            "level": 1
        })
        node_indices[rg["id"]] = node_index
        
        # Link resource group to subscription
        links.append({
            "source": node_indices[subscription_id],
            "target": node_index,
            "value": 1,
            "type": "contains"
        })
    
    # Add resources
    for resource in resources:
        # Find resource group for this resource
        rg_id = None
        for rg in resource_groups:
            if rg['name'] == resource['resourceGroup']:
                rg_id = rg['id']
                break
        
        # Skip if resource group not found
        if not rg_id:
            continue
        
        # Get display name
        display_name = get_display_name(resource['type'], resource)
        
        # Create node
        node_index = len(nodes)
        nodes.append({
            "id": resource["id"],
            "name": resource["name"],
            "display_name": display_name,
            "type": resource["type"],
            "kind": resource.get("kind", ""),
            "group": 2,
            "level": 2
        })
        node_indices[resource["id"]] = node_index
        
        # Link resource to resource group
        links.append({
            "source": node_indices[rg_id],
            "target": node_index,
            "value": 1,
            "type": "contains"
        })
    
    # Add confirmed dependencies
    for resource_id, deps in confirmed_dependencies.items():
        if resource_id in node_indices:
            source_index = node_indices[resource_id]
            for dep_id in deps:
                if dep_id in node_indices:
                    target_index = node_indices[dep_id]
                    links.append({
                        "source": source_index,
                        "target": target_index,
                        "value": 2,
                        "type": "depends"
                    })
    
    # Add potential dependencies if requested
    if include_potential_deps:
        for resource_id, deps in potential_dependencies.items():
            if resource_id in node_indices:
                source_index = node_indices[resource_id]
                for dep_id in deps:
                    if dep_id in node_indices:
                        target_index = node_indices[dep_id]
                        links.append({
                            "source": source_index,
                            "target": target_index,
                            "value": 2,
                            "type": "potential"
                        })

    # Create the HTML file
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure Resource Graph - Interactive</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            overflow: hidden;
            background-color: #f0f0f0;
        }
        
        #graph-container {
            width: 100vw;
            height: 100vh;
            position: relative;
        }
        
        .links line {
            stroke-opacity: 0.6;
            stroke-width: 1px;
        }
        
        .nodes circle {
            stroke: #fff;
            stroke-width: 1.5px;
        }
        
        .node-label {
            font-size: 12px;
            pointer-events: none;
            background-color: rgba(255, 255, 255, 0.8);
            padding: 2px 4px;
            border-radius: 2px;
        }
        
        .tooltip {
            position: absolute;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            pointer-events: none;
            opacity: 0;
            z-index: 100;
        }
        
        .controls {
            position: absolute;
            top: 10px;
            left: 10px;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            z-index: 50;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .controls button {
            padding: 5px 10px;
            cursor: pointer;
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 3px;
            transition: background-color 0.2s;
        }
        
        .controls button:hover {
            background-color: #e8e8e8;
        }
        
        .controls button.active {
            background-color: #4CAF50;
            color: white;
        }
        
        .legend {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            z-index: 50;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }
        
        .legend-color {
            width: 15px;
            height: 15px;
            margin-right: 5px;
            border-radius: 50%;
        }
        
        .selected {
            stroke: #000;
            stroke-width: 2px;
        }
    </style>
</head>
<body>
    <div id="graph-container">
        <div class="controls">
            <button id="zoom-in" title="Zoom In">+</button>
            <button id="zoom-out" title="Zoom Out">-</button>
            <button id="reset" title="Reset View">Reset</button>
            <button id="toggle-labels" title="Show/Hide Labels">Toggle Labels</button>
            <button id="toggle-potential" title="Show/Hide Potential Dependencies" class="active">Hide Potential Dependencies</button>
        </div>
        <div class="legend">
            <h3>Legend</h3>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #1f77b4;"></div>
                <span>Subscription</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #ff7f0e;"></div>
                <span>Resource Group</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #2ca02c;"></div>
                <span>Resource</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: transparent; border: 2px solid #aaa;"></div>
                <span>Contains Relationship</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: transparent; border: 2px solid #ff0000;"></div>
                <span>Confirmed Dependency</span>
            </div>
            <div class="legend-item potential-dependency">
                <div class="legend-color" style="background-color: transparent; border: 2px dashed #ff7f0e;"></div>
                <span>Potential Dependency</span>
            </div>
        </div>
        <div class="tooltip"></div>
    </div>
    
    <script>
        // Data
        const graphData = {
            nodes: NODES_PLACEHOLDER,
            links: LINKS_PLACEHOLDER
        };
        
        // Create SVG
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        // Create zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });
        
        svg.call(zoom);
        
        const g = svg.append("g");
        
        // Create tooltip
        const tooltip = d3.select(".tooltip");
        
        // Create simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.links).distance(100))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("x", d3.forceX(width / 2).strength(0.1))
            .force("y", d3.forceY(height / 2).strength(0.1));
        
        // Define node colors
        const colorScale = d3.scaleOrdinal()
            .domain([0, 1, 2])
            .range(["#1f77b4", "#ff7f0e", "#2ca02c"]);
        
        // Create links
        const link = g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(graphData.links)
            .enter().append("line")
            .attr("stroke", d => {
                if (d.type === "depends") return "#ff0000";
                if (d.type === "potential") return "#ff7f0e";
                return "#aaa";
            })
            .attr("stroke-dasharray", d => d.type === "potential" ? "5,5" : "0")
            .attr("class", d => {
                const sourceId = typeof d.source === 'object' ? d.source.id : graphData.nodes[d.source].id;
                const targetId = typeof d.target === 'object' ? d.target.id : graphData.nodes[d.target].id;
                const linkType = d.type;
                return `link ${sourceId.replace(/[^a-zA-Z0-9]/g, '_')} ${targetId.replace(/[^a-zA-Z0-9]/g, '_')} link-type-${linkType}`;
            });
        
        // Create nodes
        const node = g.append("g")
            .attr("class", "nodes")
            .selectAll("g")
            .data(graphData.nodes)
            .enter().append("g")
            .attr("class", d => `node ${d.id.replace(/[^a-zA-Z0-9]/g, '_')}`)
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        // Add circles to nodes
        node.append("circle")
            .attr("r", d => d.group === 0 ? 15 : d.group === 1 ? 10 : 7)
            .attr("fill", d => colorScale(d.group))
            .on("mouseover", handleMouseOver)
            .on("mouseout", handleMouseOut)
            .on("click", handleClick);
        
        // Add labels to nodes
        const labels = node.append("text")
            .attr("class", "node-label")
            .attr("dx", 12)
            .attr("dy", ".35em")
            .text(d => {
                if (d.type === "subscription") return "Subscription";
                if (d.type === "resourceGroup") return d.name;
                return d.display_name ? `${d.display_name}: ${d.name}` : d.name;
            })
            .style("display", "none");  // Hide labels initially
        
        // Track selected node
        let selectedNode = null;
        
        // Track whether potential dependencies are visible
        let potentialDepsVisible = true;
        
        // Handle node hover - only show tooltip, no highlighting
        function handleMouseOver(event, d) {
            // Only show tooltip
            tooltip.style("opacity", 1)
                .html(() => {
                    if (d.type === "subscription") {
                        return `<strong>Subscription</strong><br>${d.name}`;
                    } else if (d.type === "resourceGroup") {
                        return `<strong>Resource Group</strong><br>${d.name}`;
                    } else {
                        let html = `<strong>${d.display_name || d.type.split('/').pop()}</strong><br>`;
                        html += `Name: ${d.name}<br>`;
                        html += `Type: ${d.type}<br>`;
                        if (d.kind) html += `Kind: ${d.kind}<br>`;
                        return html;
                    }
                })
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }
        
        // Handle mouse out - just hide tooltip
        function handleMouseOut() {
            tooltip.style("opacity", 0);
        }
        
        // Handle node click
        function handleClick(event, d) {
            // Clear previous selection
            if (selectedNode) {
                d3.selectAll(".node circle").classed("selected", false);
                resetHighlighting();
                
                // Hide all labels if they're not toggled on
                if (!labelsVisible) {
                    labels.style("display", "none");
                }
            }
            
            if (selectedNode === d) {
                // Clicking the same node again deselects it
                selectedNode = null;
            } else {
                // Select new node
                selectedNode = d;
                d3.select(event.currentTarget).classed("selected", true);
                highlightConnections(d);
                
                // Show labels for the clicked node and all connected nodes
                const nodeId = d.id.replace(/[^a-zA-Z0-9]/g, '_');
                d3.select(`.node.${nodeId} .node-label`).style("display", "block");
                
                // For each connected link, also show label for the node at the other end
                d3.selectAll(`.link.${nodeId}`).each(function() {
                    const linkData = d3.select(this).datum();
                    let connectedId;
                    
                    if (typeof linkData.source === 'object' && typeof linkData.target === 'object') {
                        connectedId = (linkData.source.id === d.id ? linkData.target.id : linkData.source.id);
                    } else {
                        const sourceNode = graphData.nodes[linkData.source];
                        const targetNode = graphData.nodes[linkData.target];
                        connectedId = (sourceNode.id === d.id ? targetNode.id : sourceNode.id);
                    }
                    
                    d3.select(`.node.${connectedId.replace(/[^a-zA-Z0-9]/g, '_')} .node-label`).style("display", "block");
                });
            }
            
            // Prevent event from propagating to SVG
            event.stopPropagation();
        }
        
        // Click on the background to deselect
        svg.on("click", () => {
            if (selectedNode) {
                d3.selectAll(".node circle").classed("selected", false);
                resetHighlighting();
                selectedNode = null;
                
                // Hide all labels if they're not toggled on
                if (!labelsVisible) {
                    labels.style("display", "none");
                }
            }
        });
        
        function highlightConnections(d) {
            const nodeId = d.id.replace(/[^a-zA-Z0-9]/g, '_');
            
            // Fade all nodes and links
            d3.selectAll(".link").style("opacity", 0.1);
            d3.selectAll(".node circle").style("opacity", 0.1);
            
            // Highlight current node
            d3.select(`.node.${nodeId} circle`).style("opacity", 1);
            
            // Highlight connected links and nodes
            const connectedLinks = d3.selectAll(`.link.${nodeId}`);
            
            // Create a set to track all connected nodes
            const connectedNodeIds = new Set();
            
            // Filter links based on potential dependency visibility
            connectedLinks.each(function() {
                const linkElement = d3.select(this);
                
                // Skip potential dependencies if they're hidden
                if (!potentialDepsVisible && linkElement.classed("link-type-potential")) {
                    return;
                }
                
                linkElement.style("opacity", 1).style("stroke-width", 2);
                
                // Extract and highlight connected node
                const linkData = linkElement.datum();
                let targetId;
                
                if (typeof linkData.source === 'object' && typeof linkData.target === 'object') {
                    targetId = (linkData.source.id === d.id ? linkData.target.id : linkData.source.id);
                } else {
                    const sourceNode = graphData.nodes[linkData.source];
                    const targetNode = graphData.nodes[linkData.target];
                    targetId = (sourceNode.id === d.id ? targetNode.id : sourceNode.id);
                }
                
                // Add to our set of connected nodes
                connectedNodeIds.add(targetId);
                
                // Highlight the connected node
                const targetSafeId = targetId.replace(/[^a-zA-Z0-9]/g, '_');
                d3.select(`.node.${targetSafeId} circle`).style("opacity", 1);
            });
        }
        
        function resetHighlighting() {
            // Reset all highlights
            d3.selectAll(".link").style("opacity", 0.6).style("stroke-width", 1);
            d3.selectAll(".node circle").style("opacity", 1);
        }
        
        // Simulation tick
        simulation.on("tick", () => {
            link
                .attr("x1", d => {
                    return typeof d.source === 'object' ? d.source.x : graphData.nodes[d.source].x;
                })
                .attr("y1", d => {
                    return typeof d.source === 'object' ? d.source.y : graphData.nodes[d.source].y;
                })
                .attr("x2", d => {
                    return typeof d.target === 'object' ? d.target.x : graphData.nodes[d.target].x;
                })
                .attr("y2", d => {
                    return typeof d.target === 'object' ? d.target.y : graphData.nodes[d.target].y;
                });
            
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // Controls
        d3.select("#zoom-in").on("click", () => {
            svg.transition().call(zoom.scaleBy, 1.5);
        });
        
        d3.select("#zoom-out").on("click", () => {
            svg.transition().call(zoom.scaleBy, 0.75);
        });
        
        d3.select("#reset").on("click", () => {
            svg.transition().call(zoom.transform, d3.zoomIdentity);
        });
        
        // Toggle labels
        let labelsVisible = false;
        d3.select("#toggle-labels").on("click", () => {
            labelsVisible = !labelsVisible;
            labels.style("display", labelsVisible ? "block" : "none");
            d3.select("#toggle-labels").classed("active", labelsVisible);
        });
        
        // Toggle potential dependencies
        d3.select("#toggle-potential").on("click", () => {
            potentialDepsVisible = !potentialDepsVisible;
            d3.selectAll(".link-type-potential").style("visibility", potentialDepsVisible ? "visible" : "hidden");
            d3.select(".potential-dependency").style("visibility", potentialDepsVisible ? "visible" : "hidden");
            
            // Re-highlight connections if a node is selected
            if (selectedNode) {
                highlightConnections(selectedNode);
            }
            
            const button = d3.select("#toggle-potential");
            button.classed("active", potentialDepsVisible);
            button.text(potentialDepsVisible ? "Hide Potential Dependencies" : "Show Potential Dependencies");
        });
        
        // Initial zoom to fit
        const initialTransform = d3.zoomIdentity
            .translate(width / 2, height / 2)
            .scale(0.8)
            .translate(-width / 2, -height / 2);
        
        svg.call(zoom.transform, initialTransform);
    </script>
</body>
</html>
    """
    
    # Convert data to JSON and insert into HTML template
    nodes_json = json.dumps(nodes)
    links_json = json.dumps(links)
    html_content = html_content.replace("NODES_PLACEHOLDER", nodes_json)
    html_content = html_content.replace("LINKS_PLACEHOLDER", links_json)
    
    # Write HTML file
    with open(output_file, "w") as f:
        f.write(html_content)
    
    print(f"Interactive HTML diagram saved to {output_file}") 