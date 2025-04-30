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
from .providers.price_provider import PriceProvider
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

        # Initialize the unified price provider that combines multiple data sources
        self._price_provider = PriceProvider()
        logger.info("Initialized PriceProvider with multi-tier API and scraping strategy")


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
        
        # Create a status stream for progress updates
        status_stream = response_handler.create_text_stream("STATUS_UPDATES")
        
        if not urls:
            # No URLs found, ask the model to help
            logger.info("No URLs found, using model for general response.")
            await status_stream.emit_chunk("No product URLs detected. Analyzing your query to understand what you're looking for.")
            
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
                await status_stream.complete()
            except Exception as e:
                logger.error(f"Error generating general response: {e}")
                error_stream = response_handler.create_text_stream("ERROR")
                await error_stream.emit_chunk(f"Error: {str(e)}")
                await error_stream.complete()
            
            await response_handler.complete()
            return
        
        # Process each URL found in the query
        await status_stream.emit_chunk(f"Analyzing product information from {len(urls)} URL(s)...\n")
        
        all_product_details = []
        all_alternatives = []
        all_deal_analyses = []
        has_errors = False
        
        # Stream for product details
        product_details_stream = response_handler.create_text_stream("PRODUCT_DETAILS")
        alternatives_stream = response_handler.create_text_stream("ALTERNATIVES")
        deal_analysis_stream = response_handler.create_text_stream("DEAL_ANALYSIS")
        
        # Process each URL
        for i, url in enumerate(urls):
            logger.info(f"Processing URL: {url}")
            await status_stream.emit_chunk(f"Processing URL {i+1}/{len(urls)}: {url}\n")
            
            # Fetch product details using the PriceProvider (with multi-source strategy)
            product_details = await self._price_provider.get_product_details(url)
            all_product_details.append(product_details)
            
            if product_details.get("status") == "success":
                logger.info(f"Successfully retrieved details for {url} via {product_details.get('provider', 'unknown')}")
                # Stream product details
                title = product_details.get('title', 'Unknown Product')
                price = product_details.get('price_text', 'Price unknown')
                source = product_details.get('source', 'unknown')
                provider = product_details.get('provider', 'unknown')
                
                details_text = f"\n--- Product Details: {title} ---\n"
                details_text += f"Source: {source.capitalize()}\n"
                details_text += f"Price: {price}\n"
                details_text += f"Rating: {product_details.get('rating', 'No ratings')}\n"
                details_text += f"Availability: {product_details.get('availability', 'Unknown')}\n"
                details_text += f"Data Source: {provider.capitalize()}\n"
                
                if product_details.get("data_source"):
                    details_text += f"- Method: {product_details.get('data_source', 'N/A')}\n"
                if product_details.get("features"):
                    details_text += "Features:\n"
                    for feature in product_details.get("features", [])[:3]:
                        details_text += f"• {feature}\n"
                
                await product_details_stream.emit_chunk(details_text)
                
                # Find alternatives
                alternatives = await self._price_provider.find_alternatives(product_details)
                all_alternatives.append(alternatives)
                logger.info(f"Found {len(alternatives)} alternatives for {url}")
                
                # Stream alternatives
                if alternatives:
                    alt_text = f"\n--- Alternative Options for {title} ---\n"
                    for alt in alternatives:
                        alt_source = alt.get('source', 'Unknown').capitalize()
                        alt_price = f"${alt.get('price')}" if alt.get('price') else "Price unknown"
                        alt_reason = alt.get('reason', '')
                        alt_text += f"{alt_source}: {alt_price} - {alt_reason}\n"
                        
                        # Add holistic information if available
                        if alt.get('holistic_score'):
                            alt_text += f"  • Holistic Score: {alt.get('holistic_score')}/100\n"
                        if alt.get('rating'):
                            alt_text += f"  • Rating: {alt.get('rating')}\n"
                        if alt.get('review_count'):
                            alt_text += f"  • Reviews: {alt.get('review_count')}\n"
                        if alt.get('availability'):
                            alt_text += f"  • Availability: {alt.get('availability')}\n"
                        alt_text += "\n"
                    
                    await alternatives_stream.emit_chunk(alt_text)
                
                # Analyze if it's a good deal
                deal_analysis = await self._price_provider.analyze_deal(product_details, alternatives)
                all_deal_analyses.append(deal_analysis)
                logger.info(f"Deal analysis for {url}: {deal_analysis}")
                
                # Stream deal analysis
                is_good_deal = deal_analysis.get('is_good_deal', False)
                confidence = deal_analysis.get('confidence', 'unknown')
                
                analysis_text = f"\n--- Deal Analysis for {title} ---\n"
                analysis_text += f"Verdict: {'This is a GOOD DEAL ✓' if is_good_deal else 'This is NOT the best deal ✗'}\n"
                analysis_text += f"Confidence: {confidence.capitalize()}\n"
                
                # Add holistic score if available
                if deal_analysis.get('holistic_score'):
                    analysis_text += f"Holistic Score: {deal_analysis.get('holistic_score')}/100 (considers price, ratings, reviews, availability)\n"
                
                if deal_analysis.get("reasons"):
                    analysis_text += "Analysis:\n"
                    for reason in deal_analysis.get("reasons", []):
                        analysis_text += f"• {reason}\n"
                
                await deal_analysis_stream.emit_chunk(analysis_text)
                
            else:
                has_errors = True
                error_message = product_details.get("message", "Unknown error")
                error_details = product_details.get("error_details", "")
                logger.error(f"Failed to retrieve details for {url}: {error_message}")
                if error_details:
                    logger.error(f"Error details: {error_details}")
                
                # Stream error information
                error_text = f"\n--- Error Processing {url} ---\n"
                error_text += f"Error: {error_message}\n"
                if error_details:
                    error_text += f"Detail: {error_details}\n"
                error_text += "Unable to analyze this product. Please try a different URL or check if the product page is accessible.\n"
                
                await product_details_stream.emit_chunk(error_text)
        
        # Complete the intermediate streams
        await product_details_stream.complete()
        await alternatives_stream.complete()
        await deal_analysis_stream.complete()
        await status_stream.emit_chunk("Analysis complete. Generating final recommendation...\n")
        
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
            # Stream an error message
            error_stream = response_handler.create_text_stream("ERROR")
            await error_stream.emit_chunk(f"Error generating final recommendation: {str(e)}")
            await error_stream.complete()
        
        # Complete all streams
        await status_stream.complete()
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
        
        # Filter to only include supported e-commerce sites (expanded supported sites)
        supported_urls = []
        for url in found_urls:
            domain = urlparse(url).netloc.lower()
            if any(site in domain for site in ["amazon.com", "walmart.com", "bestbuy.com", "target.com", "ebay.com"]):
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

When analyzing products, it is CRITICAL to use a HOLISTIC APPROACH rather than focusing solely on price:
1. Price is important but should be just ONE FACTOR in your analysis
2. Customer ratings and reviews are extremely important indicators of quality and satisfaction
3. The number of reviews provides confidence in the rating score
4. Product availability and shipping speed are important factors for time-sensitive purchases
5. Feature differences between alternatives should be carefully considered

Based on the following product information, alternatives, and deal analyses, create a comprehensive response that:
1. Directly addresses the user's question about whether the product(s) are good deals
2. Provides a detailed analysis of each product's value proposition
3. Compares products holistically across different retailers
4. Uses a balanced approach that weighs price, ratings, reviews, and availability
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
   - EMPHASIZE the product's rating and reviews (higher ratings generally indicate better quality)
   - Evaluate the availability and shipping options
3. If better alternatives were found:
   - Explain why they might be better options, considering BOTH price AND non-price factors
   - Make it clear when a slightly higher price might be worth it for better reviews/ratings
   - Highlight when a cheaper option might have drawbacks in terms of quality/ratings
4. Provide specific recommendations:
   - Whether to buy now or wait for better deals
   - Which retailer offers the best OVERALL VALUE (not just the cheapest price)
   - Any potential concerns or considerations about quality or service
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
                formatted.append(f"- Data Source: {product.get('provider', 'N/A').capitalize()}")
                if product.get("data_source"):
                    formatted.append(f"- Method: {product.get('data_source', 'N/A')}")
                if product.get("features"):
                    formatted.append("- Key features:")
                    for feature in product.get("features", [])[:3]: # Show top 3
                        formatted.append(f"  * {feature}")
            else:
                formatted.append(f"- Error retrieving details: {product.get('message', 'Unknown error')}")
                if product.get("error_details"):
                    formatted.append(f"- Error details: {product.get('error_details', 'N/A')}")
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
                    
                    # Add additional holistic information if available
                    if alt.get('holistic_score'):
                        formatted.append(f"  * Holistic Score: {alt.get('holistic_score')}/100")
                    if alt.get('rating'):
                        formatted.append(f"  * Rating: {alt.get('rating')}")
                    if alt.get('review_count'):
                        formatted.append(f"  * Reviews: {alt.get('review_count')}")
                    if alt.get('availability'):
                        formatted.append(f"  * Availability: {alt.get('availability')}")
                    
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
                
                # Add holistic score if available
                if analysis.get('holistic_score'):
                    formatted.append(f"- Holistic Score: {analysis.get('holistic_score')}/100")
                
                if analysis.get("reasons"):
                    formatted.append("- Summary:")
                    for reason in analysis.get("reasons", []):
                        formatted.append(f"  * {reason}")
                formatted.append("")
            # No need to explicitly mention failed analysis here, handled in product details format

        if not formatted:
             return "No deal analysis available (likely due to scraping errors)."
             
        return "\n".join(formatted).strip()


def main():
    """Main function to run the agent as a standalone server."""
    import uvicorn
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting ECommerceAgent server on 0.0.0.0:{port}...")
    
    agent = ECommerceAgent(name="E-Commerce Price Comparison Agent")
    server = DefaultServer(agent)

    # Add CORS middleware to the FastAPI app
    app = server._app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development; restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add middleware to ensure proper event stream headers
    @app.middleware("http")
    async def add_sse_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/assist":
            response.headers["Content-Type"] = "text/event-stream"
            response.headers["Cache-Control"] = "no-cache"
            response.headers["Connection"] = "keep-alive"
            response.headers["Transfer-Encoding"] = "chunked"
        return response

    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()


