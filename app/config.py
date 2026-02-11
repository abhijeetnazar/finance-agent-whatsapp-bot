import json
import os
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("finance-agent")

@lru_cache(maxsize=1)
def load_agent_config():
    """
    Loads agent configuration from JSON file.
    Cached to prevent repeated file I/O.
    """
    config_path = "app/agent_config.json"
    instr_path = "app/instructions.md"
    try:
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        
        if os.path.exists(instr_path):
            with open(instr_path, "r") as f:
                config["instructions"] = f.read()
                
        return config
    except Exception as e:
        logger.error(f"Error loading agent config: {e}")
        return {}

# Load config once at module level
AGENT_CONFIG = load_agent_config()
ALLOWED_NUMBERS = AGENT_CONFIG.get("allowed_numbers", [])
