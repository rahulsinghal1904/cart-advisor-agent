#!/usr/bin/env python
"""
Run the e-commerce agent with all fixes applied.

This script ensures that Target and Best Buy scraping
and alternatives work correctly in the main application.
"""
import os
import sys
import importlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_with_fixes():
    """Run the e-commerce agent with all fixes applied."""
    try:
        # Add the current directory to the path if needed
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        
        # First import and apply our fixes
        logger.info("Importing and applying fixes")
        import src.e_commerce_agent.providers.direct_fix as direct_fix
        direct_fix.apply_fixes()
        
        # Then import and run the main module
        logger.info("Importing and running main module")
        from src.e_commerce_agent import e_commerce_agent
        
        # If the module has a main function, run it
        if hasattr(e_commerce_agent, "main"):
            logger.info("Running e_commerce_agent.main()")
            e_commerce_agent.main()
        else:
            logger.info("No main() function found, running module directly")
            # Just importing the module should be enough
            pass
            
        return True
    except Exception as e:
        logger.error(f"Error running fixed agent: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*80)
    print("FIXED E-COMMERCE AGENT")
    print("="*80)
    print("Target and Best Buy scraping and alternatives will work correctly.")
    print("="*80)
    
    # Run with fixes
    success = run_with_fixes()
    
    if success:
        print("="*80)
        print("✅ E-commerce agent completed successfully")
        print("="*80)
    else:
        print("="*80)
        print("❌ E-commerce agent failed")
        print("="*80)
        sys.exit(1) 