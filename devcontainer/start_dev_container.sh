#!/bin/bash

source vars

export RTOOLS_PATH=/Users/rohitekbote/wd/code/github.com/Rohit-Ekbote/rtools

export HOST_CODE_PATH=/Users/rohitekbote/wd/code/github.com/
export CODE_PATH=/root/code
export RSCRIPTS_PATH=$CODE_PATH/Rohit-Ekbote/rtools/devcontainer/rscripts

#export HOST_PLATFORM_SRC_PATH=/Users/rohitekbote/wd/468-platform
#export PLATFORM_SRC_PATH=${CODE_PATH}/468-platform

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
    -e RSCRIPTS_PATH=$RSCRIPTS_PATH \
    -e CODE_PATH=$CODE_PATH \
    -e PORT=$PORT \
    -v $HOST_CODE_PATH:$CODE_PATH \
    -p $HOST_PORT:$PORT \
    -p $DB_FORWARD_HOST_PORT:$DB_FORWARD_PORT \
    --name $DEV_CONTAINER \
    ${IMAGE_NAME}:${IMAGE_TAG} 
