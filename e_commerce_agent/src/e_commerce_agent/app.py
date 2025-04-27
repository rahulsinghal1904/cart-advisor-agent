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
        port_str = os.environ.get("PORT")
        if port_str:
            logger.info(f"PORT environment variable is: '{port_str}'")
        else:
            logger.warning("PORT environment variable not set; Cloud Run will inject default")

        # Initialize the agent
        logger.info("Initializing ECommerceAgent")
        agent = ECommerceAgent("ECommerceAgent")
        
        # Initialize the server
        logger.info("Initializing DefaultServer")
        server = DefaultServer(agent)
        
        # 🚀 FIX: Start the server correctly
        logger.info("Running server using DefaultServer.run()")
        server.run()

    except Exception as e:
        logger.critical(f"Fatal error during application startup: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
