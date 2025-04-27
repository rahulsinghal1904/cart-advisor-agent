import asyncio
import json
import os
from dotenv import load_dotenv
from ulid import ULID

from src.e_commerce_agent.e_commerce_agent import ECommerceAgent
from sentient_agent_framework import (
    Query, 
    ResponseHandler
)
from sentient_agent_framework.implementation.default_session import DefaultSession

# Custom response handler for test purposes
class TestResponseHandler(ResponseHandler):
    def __init__(self):
        self.events = []
    
    async def emit_text_block(self, event_name, content):
        print(f"[{event_name}] {content}")
        self.events.append({"type": "text_block", "name": event_name, "content": content})
    
    async def emit_json(self, event_name, content):
        print(f"[{event_name}] {json.dumps(content, indent=2)}")
        self.events.append({"type": "json", "name": event_name, "content": content})
    
    async def emit_error(self, event_name, content):
        print(f"[ERROR: {event_name}] {json.dumps(content, indent=2)}")
        self.events.append({"type": "error", "name": event_name, "content": content})
    
    def create_text_stream(self, event_name):
        print(f"[{event_name}] Starting text stream...")
        
        class TestStreamEmitter:
            def __init__(self, parent, event_name):
                self.parent = parent
                self.event_name = event_name
                self.content = []
            
            async def emit_chunk(self, chunk):
                print(chunk, end="", flush=True)
                self.content.append(chunk)
            
            async def complete(self):
                print("\n[STREAM COMPLETE]")
                self.parent.events.append({
                    "type": "text_stream", 
                    "name": self.event_name, 
                    "content": "".join(self.content)
                })
        
        return TestStreamEmitter(self, event_name)
    
    async def complete(self):
        print("\n[RESPONSE COMPLETE]")


async def test_agent():
    """Test the E-Commerce Agent with a sample query."""
    load_dotenv()
    
    # Create agent
    agent = ECommerceAgent(name="E-Commerce Price Comparison Test")
    
    # Create test session - the constructor seems to have different parameters
    # Create a session object manually that implements the protocol
    session = {
        "processor_id": "test_processor",
        "activity_id": "test_activity",
        "request_id": "test_request",
        "interactions": []
    }
    
    # Sample queries to test
    sample_queries = [
        # Query with Amazon URL
        Query(
            id=ULID(),
            prompt="Is this a good deal? https://www.amazon.com/dp/B07ZPKN6YR"
        ),
        # Query with no URL
        Query(
            id=ULID(),
            prompt="Are Apple AirPods a good deal right now?"
        ),
        # Query with multiple URLs
        Query(
            id=ULID(),
            prompt="Which of these is a better deal? https://www.amazon.com/dp/B07ZPKN6YR or https://www.bestbuy.com/site/airpods-pro-2nd-generation-with-magsafe-case-usb%E2%80%91c-white/4900964.p?skuId=4900964"
        )
    ]
    
    # Choose which query to test
    query_index = 0  # Change this to test different queries
    query = sample_queries[query_index]
    
    # Create response handler
    response_handler = TestResponseHandler()
    
    # Process the query
    print(f"\nTesting query: {query.prompt}\n")
    print("-" * 80)
    await agent.assist(session, query, response_handler)
    print("-" * 80)
    
    # You can examine response_handler.events for all events emitted


if __name__ == "__main__":
    asyncio.run(test_agent()) 