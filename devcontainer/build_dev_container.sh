#!/bin/bash

source vars

docker build -f ${DOCKER_FILE} -t ${IMAGE_NAME} .

