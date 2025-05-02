#!/usr/bin/env python
"""
Fix script to add missing scraper methods to the PriceScraper class.
This addresses the issue of having duplicate class definitions in the codebase.
"""

import re
import os

# Path to the price_scraper.py file
file_path = 'src/e_commerce_agent/providers/price_scraper.py'

# Read the file content
with open(file_path, 'r') as f:
    content = f.read()

# Check if there are two class definitions
class_defs = re.findall(r'class PriceScraper:', content)
if len(class_defs) > 1:
    print(f"Found {len(class_defs)} PriceScraper class definitions. First one will be kept, others removed.")

# Find the scrape_target and scrape_bestbuy methods from the second class
target_method = re.search(r'async def scrape_target\(self, url: str\) -> Dict\[str, Any\]:(.*?)async def', content, re.DOTALL)
bestbuy_method = re.search(r'async def scrape_bestbuy\(self, url: str\) -> Dict\[str, Any\]:(.*?)async def', content, re.DOTALL)

if target_method and bestbuy_method:
    # Extract the method bodies
    target_method_text = target_method.group(0)
    bestbuy_method_text = bestbuy_method.group(0)
    
    # Find the end of the first PriceScraper class - where we want to add these methods
    first_class_end = content.find("class PriceScraper:", content.find("class PriceScraper:") + 1)
    
    if first_class_end != -1:
        # Insert the methods before the second class definition
        modified_content = content[:first_class_end] + "\n    # Added critical methods\n    " + target_method_text + "\n    " + bestbuy_method_text + "\n\n" + content[first_class_end:]
        
        # Create backup
        backup_path = file_path + '.bak'
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"Backup created at {backup_path}")
        
        # Write the modified file
        with open(file_path, 'w') as f:
            f.write(modified_content)
        print(f"File updated with missing methods")
    else:
        print("Could not find a good location to insert the methods.")
else:
    print("Could not find target or BestBuy scraper methods in the file.") 