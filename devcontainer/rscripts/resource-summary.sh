#!/bin/bash

echo "Fetching Cluster Resource Summary..."

# Get total allocatable CPU across all nodes
TOTAL_ALLOCATABLE_CPU=$(kubectl get nodes -o jsonpath="{range .items[*]}{.status.allocatable.cpu}{'\n'}{end}" | awk '{s+=$1} END {print s}')

# Get total allocatable memory across all nodes (in MiB)
TOTAL_ALLOCATABLE_MEM=$(kubectl get nodes -o jsonpath="{range .items[*]}{.status.allocatable.memory}{'\n'}{end}" | awk '{s+=$1} END {print s/1024/1024}')

# Get total CPU requests across all pods (sum across all containers)
TOTAL_REQUESTS_CPU=$(kubectl get pod -A -o jsonpath="{.items[*].spec.containers[*].resources.requests.cpu}" | tr ' ' '\n' | awk '{sum+=$1} END {print sum}')

# Get total CPU limits across all pods (sum across all containers)
TOTAL_LIMITS_CPU=$(kubectl get pod -A -o jsonpath="{.items[*].spec.containers[*].resources.limits.cpu}" | tr ' ' '\n' | awk '{sum+=$1} END {print sum}')

# Get total memory requests across all pods (sum across all containers, converted to GiB)
TOTAL_REQUESTS_MEM=$(kubectl get pod -A -o jsonpath="{.items[*].spec.containers[*].resources.requests.memory}" | tr ' ' '\n' | sed 's/Ki//;s/Mi/*1024/;s/Gi/*1024*1024/' | bc | awk '{sum+=$1} END {print sum/1024/1024}')

# Get total memory limits across all pods (sum across all containers, converted to GiB)
TOTAL_LIMITS_MEM=$(kubectl get pod -A -o jsonpath="{.items[*].spec.containers[*].resources.limits.memory}" | tr ' ' '\n' | sed 's/Ki//;s/Mi/*1024/;s/Gi/*1024*1024/' | bc | awk '{sum+=$1} END {print sum/1024/1024}')

# Print results
echo "--------------------------------------------"
echo "💾  Cluster Allocatable Resources:"
echo "   🖥️  CPU: $TOTAL_ALLOCATABLE_CPU millicores"
echo "   📦  Memory: $TOTAL_ALLOCATABLE_MEM GiB"
echo ""
echo "🛠️  Pod Resource Requests & Limits:"
echo "   ⚡ Total CPU Requests: $TOTAL_REQUESTS_CPU millicores"
echo "   🔥 Total CPU Limits: $TOTAL_LIMITS_CPU millicores"
echo "   💽 Total Memory Requests: $TOTAL_REQUESTS_MEM GiB"
echo "   🚀 Total Memory Limits: $TOTAL_LIMITS_MEM GiB"
echo "--------------------------------------------"

