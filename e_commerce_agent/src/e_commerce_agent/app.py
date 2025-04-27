import logging
import os
import sys
from e_commerce_agent.src.e_commerce_agent.e_commerce_agent import ECommerceAgent
from sentient_agent_framework import DefaultServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Print debug info
        logger.info("Starting application")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        
        # Get environment variables with very explicit error handling
        try:
            port_str = os.environ.get("PORT")
            logger.info(f"PORT environment variable is: '{port_str}'")
            if port_str is None:
                logger.warning("PORT environment variable not set, defaulting to 8000")
                port = 8000
            else:
                try:
                    port = int(port_str)
                    logger.info(f"Using PORT: {port}")
                except ValueError:
                    logger.error(f"Failed to parse PORT environment variable: '{port_str}', using default 8000")
                    port = 8000
        except Exception as e:
            logger.error(f"Error processing PORT environment variable: {e}")
            port = 8000
        
        # Always use 0.0.0.0 for container deployments
        host = "0.0.0.0"
        logger.info(f"Using host: {host}")
        
        # Initialize the agent
        logger.info("Initializing ECommerceAgent")
        agent = ECommerceAgent("ECommerceAgent")
        
        # Initialize the server
        logger.info("Initializing DefaultServer")
        server = DefaultServer(agent)
        
        # Start the server
        logger.info(f"Starting server on {host}:{port}")
        server.start(host=host, port=port)
        
    except Exception as e:
        logger.critical(f"Fatal error during application startup: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 