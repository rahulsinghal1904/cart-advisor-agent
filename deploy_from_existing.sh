#!/bin/bash
set -e

gcloud run deploy my-service-name \
  --image gcr.io/cart-advisor/my-service-name:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "MODEL_API_KEY=$(grep "FIREWORKS_API_KEY" e_commerce_agent/.env | cut -d '=' -f2)" \
  --set-env-vars "SERVICE_URL=https://my-service-name-cart-advisor.a.run.app" \
  --memory 1Gi \
  --cpu 1