import os
import requests
import json
from ulid import ULID

def call_assistant(prompt: str):
    # Generate valid ULIDs
    query_id = str(ULID())
    processor_id = str(ULID())
    activity_id = str(ULID())
    request_id = str(ULID())
    
    # Get service URL from environment
    service_url = os.getenv('SERVICE_URL', '') + '/assist'
    
    # Create payload with proper format
    payload = {
        "session": {
            "processor_id": processor_id,
            "activity_id": activity_id,
            "request_id": request_id,
            "interactions": []
        },
        "query": {
            "id": query_id,
            "prompt": prompt
        }
    }
    
    # Make request
    response = requests.post(
        service_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True
    )
    
    return response.json()