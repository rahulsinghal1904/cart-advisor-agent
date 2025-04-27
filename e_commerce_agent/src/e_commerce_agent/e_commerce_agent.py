import logging
import os
import re
from typing import AsyncIterator, Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv
from sentient_agent_framework import (
    AbstractAgent,
    DefaultServer,
    Query,
    ResponseHandler
)
from sentient_agent_framework.interface.session import Session

from .providers.model_provider import ModelProvider
from .providers.price_scraper import PriceScraper
# Removed mock provider import
# from src.e_commerce_agent.providers.mock_provider import MockModelProvider 

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ECommerceAgent(AbstractAgent):
    def __init__(
            self,
            name: str
    ):
        super().__init__(name)

        # Set up model provider
        model_api_key = os.getenv("FIREWORKS_API_KEY")  # Changed to use Fireworks API key
        if not model_api_key or model_api_key == "your_fireworks_api_key_here":
            raise ValueError("FIREWORKS_API_KEY is not set or is a placeholder. Please provide a valid API key in the .env file.")
        
        model_base_url = os.getenv("MODEL_BASE_URL", "https://api.fireworks.ai/inference/v1")  # Changed to Fireworks API URL
        model_name = os.getenv("MODEL_NAME", "accounts/fireworks/models/llama4-maverick-instruct-basic")  # Changed to the specified model
        
        # Always use the real ModelProvider
        self._model_provider = ModelProvider(
            api_key=model_api_key,
            base_url=model_base_url,
            model=model_name
        )
        logger.info(f"Initialized ModelProvider with model: {model_name}")

        # Set up price scraper
        self._price_scraper = PriceScraper()


    # Implement the assist method as required by the AbstractAgent class
    async def assist(
            self,
            session: Session,
            query: Query,
            response_handler: ResponseHandler
    ):
        """Process user query about e-commerce product prices and deals."""
        logger.info(f"Received query: {query.prompt}")
        
        # Extract product URLs from the user's query
        urls = self._extract_urls(query.prompt)
        logger.info(f"Extracted URLs: {urls}")
        
        if not urls:
            # No URLs found, ask the model to help
            logger.info("No URLs found, using model for general response.")
            await response_handler.emit_text_block(
                "INFO", "No product URLs detected. Analyzing your query to understand what you're looking for."
            )
            
            # Generate a response based on user query without URLs
            final_response_stream = response_handler.create_text_stream("FINAL_RESPONSE")
            response_query = (
                f"The user has asked about e-commerce pricing but no specific product URL was provided. "
                f"Their query was: '{query.prompt}'. Please provide a helpful response about how to check if "
                f"something is a good deal, or ask for more specific information about what product they're "
                f"interested in. Don't apologize for not having a URL."
            )
            try:
                async for chunk in self._model_provider.query_stream(response_query):
                    await final_response_stream.emit_chunk(chunk)
                await final_response_stream.complete()
            except Exception as e:
                logger.error(f"Error generating general response: {e}")
                await response_handler.emit_error(str(e), 500, {"type": "MODEL_ERROR"})
            
            await response_handler.complete()
            return
        
        # Process each URL found in the query
        await response_handler.emit_text_block(
            "ANALYZING", f"Analyzing product information from {len(urls)} URL(s)..."
        )
        
        all_product_details = []
        all_alternatives = []
        all_deal_analyses = []
        has_errors = False
        
        # Process each URL
        for url in urls:
            logger.info(f"Processing URL: {url}")
            # Fetch product details
            product_details = await self._price_scraper.get_product_details(url)
            all_product_details.append(product_details)
            
            if product_details.get("status") == "success":
                logger.info(f"Successfully scraped details for {url}")
                # Emit product details
                await response_handler.emit_json(
                    "PRODUCT_DETAILS", product_details
                )
                
                # Find alternatives
                alternatives = await self._price_scraper.find_alternatives(product_details)
                all_alternatives.append(alternatives)
                logger.info(f"Found {len(alternatives)} alternatives for {url}")
                
                # Emit alternatives
                if alternatives:
                    await response_handler.emit_json(
                        "ALTERNATIVES", {"product_url": url, "alternatives": alternatives}
                    )
                
                # Analyze if it's a good deal
                deal_analysis = await self._price_scraper.analyze_deal(product_details, alternatives)
                all_deal_analyses.append(deal_analysis)
                logger.info(f"Deal analysis for {url}: {deal_analysis}")
                
                # Emit deal analysis
                await response_handler.emit_json(
                    "DEAL_ANALYSIS", {"product_url": url, "analysis": deal_analysis}
                )
            else:
                has_errors = True
                error_message = product_details.get("message", "Unknown error")
                logger.error(f"Failed to scrape {url}: {error_message}")
                # Emit error for this product
                await response_handler.emit_error(
                    error_message=error_message,
                    error_code=404,
                    details={"product_url": url}
                )
        
        # Generate final summary response
        final_response_stream = response_handler.create_text_stream("FINAL_RESPONSE")
        logger.info("Generating final summary response from model.")
        
        summary_prompt = self._generate_summary_prompt(
            query.prompt, all_product_details, all_alternatives, all_deal_analyses, has_errors
        )
        
        try:
            async for chunk in self._model_provider.query_stream(summary_prompt):
                await final_response_stream.emit_chunk(chunk)
            await final_response_stream.complete()
            logger.info("Finished streaming final response.")
        except Exception as e:
            logger.error(f"Error generating summary response: {e}")
            # Try emitting an error if the stream hasn't started properly
            try:
                await final_response_stream.complete() # Need to complete the stream even on error
                await response_handler.emit_error(str(e), 500, {"type": "MODEL_ERROR"})
            except Exception as emit_err:
                logger.error(f"Failed to emit error after model failure: {emit_err}")
        
        await response_handler.complete()
        logger.info("Assist method completed.")


    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from the user's prompt."""
        # Simple regex pattern to match URLs
        url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s]*)?'
        )
        
        # Find all URLs in the text
        found_urls = url_pattern.findall(text)
        
        # Filter to only include supported e-commerce sites
        supported_urls = []
        for url in found_urls:
            domain = urlparse(url).netloc.lower()
            if any(site in domain for site in ["amazon.com", "walmart.com", "bestbuy.com"]):
                supported_urls.append(url)
        
        return supported_urls


    def _generate_summary_prompt(
        self,
        user_query: str,
        product_details: List[Dict[str, Any]],
        alternatives: List[List[Dict[str, Any]]],
        deal_analyses: List[Dict[str, Any]],
        has_errors: bool
    ) -> str:
        """Generate a prompt for the final summary response."""
        prompt = f"""
You are an expert e-commerce price comparison assistant. Your task is to provide a detailed analysis of the product(s) and whether they represent good deals.

User query: {user_query}

Based on the following product information, alternatives, and deal analyses, create a comprehensive response that:
1. Directly addresses the user's question about whether the product(s) are good deals
2. Provides a detailed analysis of each product's value proposition
3. Compares prices across different retailers
4. Considers product features, ratings, and availability
5. Makes specific recommendations

Product Details:
{self._format_product_details(product_details)}

Alternative Products:
{self._format_alternatives(alternatives)}

Deal Analysis:
{self._format_deal_analyses(deal_analyses)}

In your response:
1. Start with a clear, direct answer about whether the product is a good deal
2. For each product:
   - Summarize the key features and specifications
   - Compare the price with alternatives
   - Consider the product's rating and reviews
   - Evaluate the availability and condition (if applicable)
3. If better alternatives were found:
   - Explain why they might be better options
   - Compare specific features and prices
4. Provide specific recommendations:
   - Whether to buy now or wait for better deals
   - Which retailer offers the best value
   - Any potential concerns or considerations
5. Be detailed but concise, focusing on the most relevant information for the user's decision

Important guidelines:
- Write in a conversational, personalized tone
- Don't repeat the user's question
- Don't use markdown formatting or special characters
- Use clear, simple language
- Structure the response with clear sections and bullet points
- Focus on helping the user make an informed decision
"""
        if has_errors:
            prompt += "\nNote: There were errors retrieving information for one or more products. The analysis might be incomplete.\n"

        logger.debug(f"Generated summary prompt: {prompt}")
        return prompt


    def _format_product_details(self, product_details: List[Dict[str, Any]]) -> str:
        """Format product details for the prompt."""
        formatted = []
        for i, product in enumerate(product_details):
            url = product.get('url', 'Unknown URL')
            formatted.append(f"Product {i+1} ({url}):")
            if product.get("status") == "success":
                formatted.append(f"- Title: {product.get('title', 'N/A')}")
                formatted.append(f"- Source: {product.get('source', 'N/A')}")
                formatted.append(f"- Price: {product.get('price_text', 'N/A')}")
                formatted.append(f"- Rating: {product.get('rating', 'N/A')}")
                formatted.append(f"- Availability: {product.get('availability', 'N/A')}")
                if product.get("features"):
                    formatted.append("- Key features:")
                    for feature in product.get("features", [])[:3]: # Show top 3
                        formatted.append(f"  * {feature}")
            else:
                formatted.append(f"- Error retrieving details: {product.get('message', 'Unknown error')}")
            formatted.append("")
        
        return "\n".join(formatted).strip()


    def _format_alternatives(self, alternatives_list: List[List[Dict[str, Any]]]) -> str:
        """Format alternatives for the prompt."""
        if not any(alternatives_list):
            return "No alternative products found or compared."
        
        formatted = []
        for i, alternatives in enumerate(alternatives_list):
            if alternatives:
                formatted.append(f"Alternatives Compared for Product {i+1}:")
                for j, alt in enumerate(alternatives):
                    alt_price_str = f"${alt.get('price')}" if alt.get('price') else "N/A"
                    formatted.append(f"- {alt.get('source', 'Unknown').capitalize()}: {alt_price_str} ({alt.get('reason', 'Comparison')})")
                formatted.append("")
            # Optionally mention if no alternatives were found for a specific product if needed
            # else:
            #     formatted.append(f"No alternatives found for Product {i+1}.")
            #     formatted.append("")
        
        # If all lists were empty, return the initial message
        if not formatted:
            return "No alternative products found or compared."

        return "\n".join(formatted).strip()


    def _format_deal_analyses(self, deal_analyses: List[Dict[str, Any]]) -> str:
        """Format deal analyses for the prompt."""
        if not deal_analyses:
             return "No deal analysis available."
             
        formatted = []
        for i, analysis in enumerate(deal_analyses):
            # Only format if analysis was successful (corresponds to successful product scrape)
            if analysis: 
                formatted.append(f"Deal Analysis for Product {i+1}:")
                formatted.append(f"- Is it a good deal? {'Yes' if analysis.get('is_good_deal', False) else 'No'}")
                formatted.append(f"- Confidence: {analysis.get('confidence', 'Unknown')}")
                
                if analysis.get("reasons"):
                    formatted.append("- Summary:")
                    for reason in analysis.get("reasons", []):
                        formatted.append(f"  * {reason}")
                formatted.append("")
            # No need to explicitly mention failed analysis here, handled in product details format

        if not formatted:
             return "No deal analysis available (likely due to scraping errors)."
             
        return "\n".join(formatted).strip()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting ECommerceAgent server on 0.0.0.0:{port}...")
    
    agent = ECommerceAgent(name="E-Commerce Price Comparison Agent")
    server = DefaultServer(agent)

    uvicorn.run(server._app, host="0.0.0.0", port=port)


