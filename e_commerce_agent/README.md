# E-Commerce Price Comparison Agent

This agent fetches prices of items listed on various e-commerce websites like Amazon, Walmart, and Best Buy, analyzes whether they represent a good deal, and suggests alternatives when appropriate.

## Features

- **Multi-Platform Price Comparison**: Checks prices across Amazon, Walmart, and Best Buy
- **Deal Assessment**: Evaluates if a price is a good deal based on historical data and competitive analysis
- **Alternative Suggestions**: Recommends alternative products or platforms when better deals are available
- **Rich Response Format**: Uses Sentient Chat's event system to provide detailed, structured responses

## Installation

1. Create a virtual environment:
```
python -m venv .venv
```

2. Activate the virtual environment:
```
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```


## Running the Agent

```
cd e_commerce_agent
python -m src.e_commerce_agent.e_commerce_agent
```

## API Usage

Send requests to the agent's API endpoint:

```
curl -N --location 'http://0.0.0.0:8000/assist' \
--header 'Content-Type: application/json' \
--data '{
    "query": {
        "id": "unique_id",
        "prompt": "Is this Amazon laptop deal for $899 good? https://www.amazon.com/example-laptop-link"
    },
    "session" : {
        "processor_id": "Example processor ID",
        "activity_id": "activity_id",
        "request_id": "request_id",
        "interactions": []
    }
}'
```

## Environment Variables

- `MODEL_API_KEY`: Your API key for the LLM provider
- `MODEL_BASE_URL`: (Optional) Custom base URL for the model API
- `MODEL_NAME`: The model to use (e.g., gpt-4, gpt-3.5-turbo)

## Contributors

This agent was built using the [Sentient Agent Framework](https://github.com/sentient-agi/Sentient-Agent-Framework). 
