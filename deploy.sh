#!/bin/sh
set -eu
cd "$(dirname "$0")"
kubectl create configmap signal-files --from-file=app.py --from-file=index.html --from-file=services.json --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/deployment.yaml
kubectl rollout restart deployment/signal
kubectl rollout status deployment/signal --timeout=120s
