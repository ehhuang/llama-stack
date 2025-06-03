#!/usr/bin/env bash

# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

# Set environment variables with defaults
export POSTGRES_USER=${POSTGRES_USER:-llamastack}
export POSTGRES_DB=${POSTGRES_DB:-llamastack}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-llamastack}
export INFERENCE_MODEL=${INFERENCE_MODEL:-meta-llama/Llama-3.2-3B-Instruct}
export SAFETY_MODEL=${SAFETY_MODEL:-meta-llama/Llama-Guard-3-1B}
export TAVILY_SEARCH_API_KEY=${TAVILY_SEARCH_API_KEY:-}

# Verify variables are set
echo "🔧 Environment variables:"
echo "  POSTGRES_USER: $POSTGRES_USER"
echo "  POSTGRES_DB: $POSTGRES_DB"
echo "  INFERENCE_MODEL: $INFERENCE_MODEL"
echo "  SAFETY_MODEL: $SAFETY_MODEL"
echo ""

set -euo pipefail
set -x

# Note: Using --validate=false due to cluster OpenAPI validation issues
# The YAML content is valid (variables confirmed above), but cluster-side validation is failing
envsubst < ./vllm-k8s.yaml.template | kubectl apply -f -
envsubst < ./vllm-safety-k8s.yaml.template | kubectl apply -f -
envsubst < ./postgres-k8s.yaml.template | kubectl apply -f -
envsubst < ./chroma-k8s.yaml.template | kubectl apply -f -

kubectl create configmap llama-stack-config --from-file=stack_run_config.yaml \
  --dry-run=client -o yaml > stack-configmap.yaml

kubectl apply -f stack-configmap.yaml

envsubst < ./stack-k8s.yaml.template | kubectl apply -f -
envsubst < ./ingress-k8s.yaml.template | kubectl apply -f -
envsubst < ./ui-k8s.yaml.template | kubectl apply -f -

echo ""
echo "🚀 Deployment completed using AWS ALB!"
echo ""
echo "Next steps:"
echo "1. Wait for ALB to be ready (may take 2-3 minutes):"
echo "   kubectl get ingress llama-stack-ingress -w"
echo ""
echo "2. Get your application URL:"
echo "   kubectl get ingress llama-stack-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
echo ""
echo "3. Check pod status:"
echo "   kubectl get pods"
echo ""
echo "4. Once ready, access your application at:"
echo "   UI: http://<ALB-HOSTNAME>/"
echo "   API: http://<ALB-HOSTNAME>/v1/"
