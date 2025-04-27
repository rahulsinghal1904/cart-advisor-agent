# CartAdvisor

An intelligent agent that helps users determine if product prices represent good deals by analyzing prices across major e-commerce platforms.

## Features

- Real-time price scraping from Amazon, Walmart, and Best Buy
- Detailed product analysis including:
  - Current prices and price history
  - Product features and specifications
  - Ratings and reviews
  - Availability status
- Price comparison across multiple retailers
- Alternative product suggestions
- Deal analysis with confidence scoring
- Personalized recommendations

## Prerequisites

- Python 3.11 or higher
- Fireworks AI API key
- Playwright for web scraping

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd e-commerce-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

5. Create a `.env` file in the `e_commerce_agent` directory with your Fireworks AI API key:
```
FIREWORKS_API_KEY=your_api_key_here
MODEL_BASE_URL=https://api.fireworks.ai/inference/v1
MODEL_NAME=accounts/fireworks/models/llama4-maverick-instruct-basic
```

## Usage

1. Start the agent server:
```bash
cd e_commerce_agent
python -m src.e_commerce_agent.e_commerce_agent
```

2. The server will start on `http://localhost:8000`

3. Send requests to the `/assist` endpoint:
```bash
curl -X POST http://localhost:8000/assist \
  -H "Content-Type: application/json" \
  -d '{
    "session": {
      "processor_id": "test_processor",
      "activity_id": "test_activity",
      "request_id": "test_request",
      "interactions": []
    },
    "query": {
      "id": "test_query",
      "prompt": "Is this a good deal? https://www.amazon.com/dp/B07ZPKN6YR"
    }
  }'
```

## Example Queries

1. Product URL Analysis:
   - "Is this a good deal? https://www.amazon.com/dp/B07ZPKN6YR"
   - "Can you analyze this product? https://www.bestbuy.com/site/airpods-pro-2nd-generation-with-magsafe-case-usb%E2%80%91c-white/4900964.p?skuId=4900964"

2. Price Comparison:
   - "Compare prices for Sony WH-1000XM4 headphones across different stores"
   - "Find the best deal for an iPhone 14 Pro"

3. Deal Analysis:
   - "Is $299 a good price for AirPods Pro?"
   - "Should I buy this laptop now or wait for a sale?"

## Response Format

The agent provides detailed analysis including:
- Product details (title, price, features, rating)
- Price comparisons across retailers
- Alternative product suggestions
- Deal analysis with confidence scoring
- Personalized recommendations

## Supported Retailers

- Amazon
- Walmart
- Best Buy

## Error Handling

The agent includes robust error handling for:
- Network timeouts
- Scraping failures
- Invalid URLs
- Missing product information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Fireworks AI for the language model
- Playwright for web scraping capabilities
- The open-source community for various tools and libraries
