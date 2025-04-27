#!/bin/bash
set -e

# Variables
PROJECT_ID="cart-advisor"
SERVICE_NAME="my-service-name"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
SERVICE_URL="https://$SERVICE_NAME-$PROJECT_ID.a.run.app"

# Load API key from .env
FIREWORKS_API_KEY=$(grep "FIREWORKS_API_KEY" /Users/js/Personal/hackathon/sentient-tbn-ecommerce/e_commerce_agent/.env | cut -d '=' -f2)

# Build with platform specification
docker buildx build --platform linux/amd64 -t $IMAGE_NAME .

# Push to Container Registry
gcloud auth configure-docker -q
docker push $IMAGE_NAME

# Deploy to Cloud Run with proper configuration
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "MODEL_API_KEY=$FIREWORKS_API_KEY" \
  --set-env-vars "SERVICE_URL=$SERVICE_URL" \
  --memory 1Gi \
  --cpu 1