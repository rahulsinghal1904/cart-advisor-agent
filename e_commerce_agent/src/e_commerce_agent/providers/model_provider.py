from datetime import datetime
from langchain_core.prompts import PromptTemplate
from openai import AsyncOpenAI
from typing import AsyncIterator

class ModelProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.fireworks.ai/inference/v1",
        model: str = "fireworks/mixtral-8x7b-instruct"
    ):
        """ Initializes model, sets up OpenAI client, configures system prompt."""

        # Model provider API key
        self.api_key = api_key
        # Model provider URL
        self.base_url = base_url
        # Identifier for specific model that should be used
        self.model = model
        # Temperature setting for response randomness
        self.temperature = 0.0
        # Maximum number of tokens for responses
        self.max_tokens = None
        self.date_context = datetime.now().strftime("%Y-%m-%d")

        # Set up model API
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        # Set up system prompt
        system_prompt_template = PromptTemplate(
            input_variables=["date_today"],
            template=(
                "You are an expert e-commerce price comparison assistant that helps users determine "
                "if product prices represent good deals. Your expertise extends beyond just pricing - "
                "you consider a holistic approach that weighs multiple factors:\n\n"
                "1. Price and value for money\n"
                "2. Customer ratings and review volume\n"
                "3. Product availability and shipping speed\n"
                "4. Product features and specifications\n"
                "5. Seller reputation and service quality\n\n"
                "You analyze products across Amazon, Walmart, Best Buy, and other retailers to provide "
                "balanced recommendations based on this holistic evaluation. You understand that the "
                "cheapest option isn't always the best value. Today's date is {date_today}."
            )
        )
        self.system_prompt = system_prompt_template.format(date_today=self.date_context)


    async def query_stream(
        self,
        query: str
    ) -> AsyncIterator[str]:
        """Sends query to model and yields the response in chunks."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            # If streaming fails, try non-streaming as fallback
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                yield response.choices[0].message.content
            except Exception as e2:
                error_message = str(e2)
                if "Model not found" in error_message:
                    raise Exception("The specified model is not available. Please check the model name and try again.")
                elif "API key" in error_message:
                    raise Exception("Invalid API key. Please check your Fireworks API key.")
                else:
                    raise Exception(f"Failed to get response from model: {error_message}")


    async def query(
        self,
        query: str
    ) -> str:
        """Sends query to model and returns the complete response as a string."""
        
        chunks = []
        async for chunk in self.query_stream(query=query):
            chunks.append(chunk)
        response = "".join(chunks)
        return response 