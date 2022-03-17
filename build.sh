#!/usr/bin/env bash
docker build . -t modbot:latest
docker build -f Tools.Dockerfile . -t modbot:tools