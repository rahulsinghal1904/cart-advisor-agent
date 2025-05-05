#!/usr/bin/env python3

# This script will fix the syntax error in the price_scraper.py file

with open('src/e_commerce_agent/providers/price_scraper.py', 'r') as f:
    content = f.read()

# Make sure the file doesn't end with a docstring that's not closed
if content.strip().endswith("'costco'"):
    # Add a newline at the end to ensure the file is properly terminated
    with open('src/e_commerce_agent/providers/price_scraper.py', 'a') as f:
        f.write('\n')
    print("Added newline to properly terminate the file")
else:
    print("File does not end with expected pattern. Manual inspection may be needed.")
    
print("Done!") 