#!/usr/bin/env python
"""
This script "fixes" the price provider issue by redirecting imports of the problematic module
to our simplified implementation. This is the most reliable solution that doesn't require complex
modifications to the existing codebase.
"""
import sys
import os
import importlib.abc
import importlib.machinery
import importlib.util
import importlib.metadata
import logging
from types import ModuleType

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class ProviderImportFinder(importlib.abc.MetaPathFinder):
    """Custom import finder that redirects problematic imports to our simplified implementation."""
    
    def __init__(self, redirect_map):
        """Initialize with mapping of problematic modules to their replacements."""
        self.redirect_map = redirect_map
        logger.info(f"Initialized import redirector with mappings: {redirect_map}")
    
    def find_spec(self, fullname, path, target=None):
        """Find the module and redirect if it's in our redirect map."""
        if fullname in self.redirect_map:
            # Get the replacement module name
            replacement = self.redirect_map[fullname]
            logger.info(f"Redirecting import of {fullname} to {replacement}")
            
            # Load the replacement module spec
            if replacement in sys.modules:
                # Module already loaded, reuse it
                return importlib.machinery.ModuleSpec(
                    name=fullname,
                    loader=RedirectLoader(self.redirect_map, fullname, replacement),
                    is_package=False
                )
            else:
                # Load the replacement module spec
                try:
                    replacement_spec = importlib.util.find_spec(replacement)
                    if replacement_spec:
                        # Create a new spec for the original module but with our loader
                        return importlib.machinery.ModuleSpec(
                            name=fullname,
                            loader=RedirectLoader(self.redirect_map, fullname, replacement),
                            origin=replacement_spec.origin,
                            is_package=replacement_spec.submodule_search_locations is not None,
                            submodule_search_locations=replacement_spec.submodule_search_locations
                        )
                except ImportError:
                    logger.error(f"Could not find replacement module {replacement}")
        
        # Not a module we want to redirect
        return None


class RedirectLoader(importlib.abc.Loader):
    """Custom loader that loads the replacement module instead of the original."""
    
    def __init__(self, redirect_map, original, replacement):
        """Initialize with the original and replacement module names."""
        self.redirect_map = redirect_map
        self.original = original
        self.replacement = replacement
    
    def create_module(self, spec):
        """Create a module object for the original name."""
        if self.replacement in sys.modules:
            # Module already loaded
            module = ModuleType(self.original)
            module.__dict__.update(sys.modules[self.replacement].__dict__)
            return module
        else:
            # Load the replacement module
            replacement_module = importlib.import_module(self.replacement)
            
            # Create a new module with the original name but replacement contents
            module = ModuleType(self.original)
            module.__dict__.update(replacement_module.__dict__)
            return module
    
    def exec_module(self, module):
        """Execute the module's code."""
        # Nothing needed here as we already populated the module in create_module
        pass


def install_import_redirector():
    """Install our custom import finder to sys.meta_path."""
    # Define which modules to redirect
    redirect_map = {
        'src.e_commerce_agent.providers.price_provider': 'src.e_commerce_agent.providers.simple_provider'
    }
    
    # Create and install our finder
    finder = ProviderImportFinder(redirect_map)
    sys.meta_path.insert(0, finder)
    logger.info("Installed import redirector for price provider")
    
    return finder


if __name__ == "__main__":
    # Install the import redirector
    install_import_redirector()
    
    # If there are command-line arguments, assume they're a script to run
    if len(sys.argv) > 1:
        script_path = sys.argv[1]
        script_args = sys.argv[2:]
        
        logger.info(f"Running script {script_path} with redirect in place")
        
        # Set up sys.argv for the target script
        sys.argv = [script_path] + script_args
        
        # Load and execute the target script
        with open(script_path) as f:
            code = compile(f.read(), script_path, 'exec')
            exec(code, {'__name__': '__main__', '__file__': script_path})
    else:
        logger.info("Import redirector installed. Use it by running:")
        logger.info("  python fix_and_redirect.py <your_script.py> [args...]")
        logger.info("This will run your script with the problematic modules redirected to working alternatives.") 