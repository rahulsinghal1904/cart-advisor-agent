#!/usr/bin/env python
"""
Direct patching script for the price_scraper module.

This script directly modifies the price_scraper.py file to fix the Target and Best Buy
scraping methods without changing the Amazon implementation.
"""
import os
import sys
import re
import logging
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to the price_scraper.py file (relative to the workspace root)
PRICE_SCRAPER_PATH = "src/e_commerce_agent/providers/price_scraper.py"

# Backup file suffix
BACKUP_SUFFIX = ".bak"

def create_backup(file_path):
    """Create a backup of the file before modifying it."""
    backup_path = file_path + BACKUP_SUFFIX
    
    # Check if backup already exists
    if os.path.exists(backup_path):
        logger.info(f"Backup already exists: {backup_path}")
        return
    
    # Create backup
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        sys.exit(1)

def restore_from_backup(file_path):
    """Restore the file from backup."""
    backup_path = file_path + BACKUP_SUFFIX
    
    # Check if backup exists
    if not os.path.exists(backup_path):
        logger.error(f"Backup not found: {backup_path}")
        return False
    
    # Restore from backup
    try:
        shutil.copy2(backup_path, file_path)
        logger.info(f"Restored from backup: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore from backup: {str(e)}")
        return False

def patch_target_method(content):
    """Patch the scrape_target method."""
    # Define the replacement implementation for Target
    target_replacement = """
    async def scrape_target(self, url):
        """Patched implementation for Target scraping."""
        from .simple_provider import SimplePriceProvider
        
        logger.info(f"[PATCHED] Using improved Target scraper for: {url}")
        
        # Use the SimplePriceProvider for reliable Target scraping
        provider = SimplePriceProvider()
        return await provider.get_product_details(url)
    """
    
    # Look for scrape_target method
    pattern = r'(\s+async\s+def\s+scrape_target\s*\([^)]*\)[\s\S]*?(?=\s+async\s+def|\s*$))'
    
    # Replace the method
    new_content = re.sub(pattern, target_replacement, content)
    
    # Check if the replacement worked
    if new_content == content:
        logger.warning("Failed to find and replace scrape_target method")
        return content
    
    logger.info("Successfully patched scrape_target method")
    return new_content

def patch_bestbuy_method(content):
    """Patch the scrape_bestbuy method."""
    # Define the replacement implementation for Best Buy
    bestbuy_replacement = """
    async def scrape_bestbuy(self, url):
        """Patched implementation for Best Buy scraping."""
        from .simple_provider import SimplePriceProvider
        
        logger.info(f"[PATCHED] Using improved Best Buy scraper for: {url}")
        
        # Use the SimplePriceProvider for reliable Best Buy scraping
        provider = SimplePriceProvider()
        return await provider.get_product_details(url)
    """
    
    # Look for scrape_bestbuy method
    pattern = r'(\s+async\s+def\s+scrape_bestbuy\s*\([^)]*\)[\s\S]*?(?=\s+async\s+def|\s*$))'
    
    # Replace the method
    new_content = re.sub(pattern, bestbuy_replacement, content)
    
    # Check if the replacement worked
    if new_content == content:
        logger.warning("Failed to find and replace scrape_bestbuy method")
        return content
    
    logger.info("Successfully patched scrape_bestbuy method")
    return new_content

def patch_file():
    """Patch the price_scraper.py file."""
    file_path = PRICE_SCRAPER_PATH
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    # Create backup
    create_backup(file_path)
    
    # Read file content
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read file: {str(e)}")
        sys.exit(1)
    
    # Patch Target method
    content = patch_target_method(content)
    
    # Patch Best Buy method
    content = patch_bestbuy_method(content)
    
    # Write patched content
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Successfully patched file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to write patched file: {str(e)}")
        sys.exit(1)

def main():
    """Main function."""
    print("="*80)
    print("PRICE SCRAPER PATCHER")
    print("="*80)
    print("This script directly patches the price_scraper.py file")
    print("to fix Target and Best Buy scraping methods.")
    print("The Amazon implementation is preserved.")
    print("="*80)
    
    # Check if user wants to patch
    while True:
        choice = input("Do you want to patch the price_scraper.py file? (y/n/restore): ").lower()
        
        if choice == 'y':
            patch_file()
            print("✅ Successfully patched price_scraper.py")
            print("You can now run the e-commerce agent normally:")
            print("  python -m src.e_commerce_agent.e_commerce_agent")
            break
        elif choice == 'n':
            print("Operation canceled. No changes were made.")
            break
        elif choice == 'restore':
            if restore_from_backup(PRICE_SCRAPER_PATH):
                print("✅ Successfully restored price_scraper.py from backup")
            else:
                print("❌ Failed to restore from backup")
            break
        else:
            print("Invalid choice. Please enter 'y', 'n', or 'restore'.")

if __name__ == "__main__":
    main() 