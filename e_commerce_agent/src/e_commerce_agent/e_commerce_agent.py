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
        model_api_key = os.getenv("MODEL_API_KEY")
        if not model_api_key or model_api_key == "your_openai_api_key_here":
            raise ValueError("MODEL_API_KEY is not set or is a placeholder. Please provide a valid API key in the .env file.")
        
        model_base_url = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1")
        model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")  # Updated to correct model name
        
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
                 await response_handler.emit_error("MODEL_ERROR", {"message": f"Failed to get response from model: {e}"})
            
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
                await response_handler.emit_json(
                    "PRODUCT_ERROR", {"url": url, "error": error_message}
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
                await response_handler.emit_error("MODEL_ERROR", {"message": f"Failed to generate summary: {e}"})
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
You are an expert e-commerce price comparison assistant.

User query: {user_query}

Based on the following product information, alternatives, and deal analyses, create a helpful, 
concise response for the user that directly answers their question about whether the product(s) 
are good deals or not. 
"""
        if has_errors:
            prompt += "\nNote: There were errors retrieving information for one or more products. The analysis might be incomplete.\n"

        prompt += f"""
Product Details:
{self._format_product_details(product_details)}

Alternative Products:
{self._format_alternatives(alternatives)}

Deal Analysis:
{self._format_deal_analyses(deal_analyses)}

In your response:
1. Directly address the user's query: '{user_query}'
2. For each successfully analyzed product, clearly state if it's a good deal and why, based on the 'Deal Analysis'.
3. If errors occurred for any URL, mention that you couldn't analyze it fully.
4. If better alternatives were found, recommend them specifically (e.g., 'Walmart has it for $X, which is Y% cheaper').
5. If applicable, suggest when might be a better time to purchase (e.g., wait for sales events if the price isn't great).
6. Be conversational but concise. Avoid generic phrases like "Based on the information...". Directly present the findings.
"""
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
    # Create an instance of the ECommerceAgent
    agent = ECommerceAgent(name="E-Commerce Price Comparison Agent")
    # Create a server to handle requests to the agent
    server = DefaultServer(agent)
    # Run the server
    logger.info("Starting ECommerceAgent server...")
    server.run()