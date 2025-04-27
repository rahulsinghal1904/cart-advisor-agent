#!/bin/bash
set -e

# Variables
PROJECT_ID="your-project-id"
SERVICE_NAME="your-service-name"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

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
  --set-env-vars "MODEL_API_KEY=your-model-api-key" \
  --memory 1Gi \
  --cpu 1