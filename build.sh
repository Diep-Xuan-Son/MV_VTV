#!/bin/bash
IMAGE_NAME=dixuson/mv_vtv
docker build -t $IMAGE_NAME -f Dockerfile_controller .
docker image push $IMAGE_NAME