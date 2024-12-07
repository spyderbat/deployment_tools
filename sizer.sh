#!/bin/bash

kubectl apply -f god.yaml 2>&1 > /dev/null
sleep 30
kubectl logs deployment/spyderbat-recommendation-tool
kubectl delete -f god.yaml 2>&1 > /dev/null
