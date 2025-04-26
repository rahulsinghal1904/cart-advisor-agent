from typing import AsyncIterator

class MockModelProvider:
    """A mock model provider for testing without an actual OpenAI API key."""
    
    def __init__(self, *args, **kwargs):
        self.system_prompt = "Mock model provider for testing"
    
    async def query_stream(self, query: str) -> AsyncIterator[str]:
        """Returns a mocked streaming response."""
        response = "This is a mock response from the model. I am analyzing the product details but not making real API calls."
        # Split the response into chunks to simulate streaming
        chunks = [response[i:i+10] for i in range(0, len(response), 10)]
        
        for chunk in chunks:
            yield chunk
    
    async def query(self, query: str) -> str:
        """Returns a mocked response."""
        return "This is a mock response from the model. I am analyzing the product details but not making real API calls." 