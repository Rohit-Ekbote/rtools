#!/bin/bash

source vars

export CODE_PATH=/home/rundev/code
export RTOOLS_PATH=/home/rundev/rtools
export MOUNT_PATH=/home/rundev/md
export RSCRIPTS=$RTOOLS_PATH/devcontainer/rscripts

export HOST_PORT=3105
export PORT=3105

export DB_FORWARD_HOST_PORT=5050
export DB_FORWARD_PORT=5050

# Help text
usage() {
    echo "Usage: $0 [--force]"
    echo "Starts development container"
    echo ""
    echo "Options:"
    echo "  --force    Force recreation of container by removing existing one if it exists"
    echo ""
    exit 1
}

# Process arguments
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if container exists and handle accordingly
if docker ps -a --filter "name=${DEV_CONTAINER}" --format "{{.Names}}" | grep -wq ${DEV_CONTAINER}; then
    if [ "$FORCE" = true ]; then
        echo "Removing existing container..."
        docker rm -f $DEV_CONTAINER
    else
        echo "Error: Container '$DEV_CONTAINER' already exists. Use --force to recreate it."
        exit 1
    fi
fi




docker run -dit \
    --privileged \
    -e RSCRIPTS=$RTOOLS_PATH/devcontainer/rscripts \
    -e PORT=$PORT \
    -v $HOST_CODE_PATH:$CODE_PATH \
    -v $HOST_MOUNT_PATH:$MOUNT_PATH \
    -v $HOST_RTOOLS_PATH:$RTOOLS_PATH \
    -p $HOST_PORT:$PORT \
    -p $DB_FORWARD_HOST_PORT:$DB_FORWARD_PORT \
    --name $DEV_CONTAINER \
    ${IMAGE_NAME}:${IMAGE_TAG} 
