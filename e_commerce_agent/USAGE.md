# E-Commerce Price Comparison Agent Usage Guide

This guide explains how to use and customize the E-Commerce Price Comparison Agent.

## Overview

This agent fetches prices of items listed on various e-commerce websites (Amazon, Walmart, Best Buy), analyzes whether they represent a good deal, and suggests alternatives when appropriate. The agent uses the Sentient Agent Framework to provide a rich streaming experience through events.

## Use Cases

1. **Price Evaluation**: "Is this laptop on Amazon a good deal? [URL]"
2. **Price Comparison**: "Which of these two TVs is a better value? [URL1] [URL2]"
3. **Deal Recommendations**: "I want to buy headphones, can you recommend a good deal?"
4. **Price Tracking**: "Has this product [URL] been cheaper in the past?"

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- git (to clone the repository)

### Step-by-Step Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Sentient-Agent-Framework-Examples.git
   cd Sentient-Agent-Framework-Examples
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Create a virtual environment
   python -m venv .venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   # .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   # Install the required packages
   pip install -r e_commerce_agent/requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the `e_commerce_agent` directory with the following content:
   ```
   MODEL_API_KEY=your_openai_api_key_here
   MODEL_BASE_URL=https://api.openai.com/v1
   MODEL_NAME=gpt-4
   ```
   Replace `your_openai_api_key_here` with your actual OpenAI API key.

## Running the Agent

### Server Mode

To run the agent as a web server that can handle HTTP requests:

1. **Ensure you're in the project root directory**:
   ```bash
   cd /path/to/Sentient-Agent-Framework-Examples
   ```

2. **Activate the virtual environment** (if not already activated):
   ```bash
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   # .venv\Scripts\activate
   ```

3. **Run the agent server**:
   ```bash
   # Navigate to the e_commerce_agent directory
   cd e_commerce_agent
   
   # Run the agent server
   python -m src.e_commerce_agent.e_commerce_agent
   ```

   You should see output indicating that the server is running. The server will be available at `http://0.0.0.0:8000` with the `/assist` endpoint.

4. **Verify the server is running**:
   Open a new terminal window and use curl to test the server:
   ```bash
   curl -N -s -X POST "http://0.0.0.0:8000/assist" \
   -H "Content-Type: application/json" \
   -d '{
       "query": {
           "id": "test_query",
           "prompt": "Is this a good deal? https://www.amazon.com/dp/B07ZPKN6YR"
       },
       "session": {
           "processor_id": "test_processor",
           "activity_id": "test_activity",
           "request_id": "test_request",
           "interactions": []
       }
   }'
   ```

eg query: curl -N --location 'http://0.0.0.0:8000/assist' \
--header 'Content-Type: application/json' \
--data-raw '{ "query": { "id": "01HPCNFQQ8KBFB6ZJVX7Y4BZJG", "prompt": "Is this a good deal? https://www.amazon.com/New-Balance-Casual-Comfort-Trainer/dp/B07B421VFD/ref=asc_df_B07B421VFD?mcid=1a773dd6b9163e2cac24ee3ca619244a&hvociid=12394447866350848685-B07B421VFD-&hvexpln=73&tag=hyprod-20&linkCode=df0&hvadid=721245378154&hvpos=&hvnetw=g&hvrand=12394447866350848685&hvpone=&hvptwo=&hvqmt=&hvdev=c&hvdvcmdl=&hvlocint=&hvlocphy=9022196&hvtargid=pla-2281435181738&psc=1" }, "session" : { "processor_id": "curl_real_test_1", "activity_id": "01HPCNFRGCVZZX86JZA2A7J8E9", "request_id": "01HPCNFS0P7G5M3YXE8K9D0N1T", "interactions": [] } }'


### Testing Mode

For development and testing, you can use the included test script:

1. **Ensure you're in the project root directory**:
   ```bash
   cd /path/to/Sentient-Agent-Framework-Examples
   ```

2. **Activate the virtual environment** (if not already activated):
   ```bash
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   # .venv\Scripts\activate
   ```

3. **Run the test script**:
   ```bash
   # Navigate to the e_commerce_agent directory
   cd e_commerce_agent
   
   # Run the test script
   python -m src.e_commerce_agent.test_agent
   ```

   The test script has three sample queries that you can modify by editing the `test_agent.py` file.

### Modifying Test Queries

You can customize the test queries by editing the `src/e_commerce_agent/test_agent.py` file:

1. Open the file in your preferred editor
2. Locate the sample queries near the top of the file
3. Modify the URLs or prompts to test different scenarios
4. Save the file and run the test script again

## Troubleshooting

### Common Issues

1. **Server won't start**:
   - Check that your Python version is 3.9 or higher
   - Ensure all dependencies are installed correctly
   - Verify your API key is set correctly in the `.env` file

2. **API key errors**:
   - Make sure your MODEL_API_KEY is valid and not expired
   - Check that the .env file is in the correct location

3. **URL scraping fails**:
   - The agent supports Amazon, Walmart, and Best Buy URLs
   - Ensure the URL format is correct and publicly accessible
   - Some websites might block scraping attempts

4. **"Module not found" errors**:
   - Ensure you're running the commands from the correct directory
   - Make sure your virtual environment is activated
   - Try reinstalling dependencies: `pip install -r e_commerce_agent/requirements.txt`

## Agent Event Types

The agent emits the following event types:

1. **INFO**: General information messages
2. **ANALYZING**: Progress updates during analysis
3. **PRODUCT_DETAILS**: JSON data about the product being analyzed
4. **ALTERNATIVES**: JSON data about alternative products or sources
5. **DEAL_ANALYSIS**: JSON data with the deal evaluation results
6. **PRODUCT_ERROR**: JSON data when there's an error processing a product URL
7. **FINAL_RESPONSE**: Streamed text with the agent's final assessment and recommendations

## Customization

### Model Provider

You can customize the language model used by changing the environment variables:

- `MODEL_API_KEY`: Your API key
- `MODEL_BASE_URL`: Optional custom base URL
- `MODEL_NAME`: Model name (e.g., gpt-4, gpt-3.5-turbo)

### Price Scraper

The price scraper in `providers/price_scraper.py` can be extended to:

1. Support additional e-commerce platforms
2. Improve scraping accuracy for specific websites
3. Add more advanced price comparison features
4. Implement real alternative product search (currently uses mock data)

## API Example

Here's how to call the agent's API endpoint:

```bash
curl -N --location 'http://0.0.0.0:8000/assist' \
--header 'Content-Type: application/json' \
--data '{
    "query": {
        "id": "unique_id",
        "prompt": "Is this a good deal? https://www.amazon.com/dp/B07ZPKN6YR"
    },
    "session" : {
        "processor_id": "Example processor ID",
        "activity_id": "activity_id",
        "request_id": "request_id",
        "interactions": []
    }
}'
```

## Limitations

1. The current implementation uses simplified web scraping which may break if websites change their structure
2. Alternative product suggestions are currently mocked and not real search results
3. Price history data is not currently implemented, but could be added as a future enhancement
4. The agent requires direct product URLs rather than search terms (though it can guide users if no URL is provided)

## Future Enhancements

1. Add price history tracking
2. Implement real alternative product search
3. Add support for more e-commerce platforms
4. Add product category recognition to provide more specific deal recommendations
5. Implement user preference profiles for personalized recommendations 