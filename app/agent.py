import os
import json
from google.adk.agents import Agent
from app.tools import (
    get_yahoo_finance_data,
    get_multi_tickers_data,
    search_finance_news,
    get_sector_analysis,
    screen_market_by_valuation,
    schedule_investment_reminder,
    cancel_investment_reminders,
    list_investment_schedules
)

# --- Agent Core ---

def load_config():
    """Loads agent configuration from JSON and Markdown files."""
    base_dir = os.path.dirname(__file__)
    config_path = os.path.join(base_dir, "agent_config.json")
    instr_path = os.path.join(base_dir, "instructions.md")
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    if os.path.exists(instr_path):
        with open(instr_path, "r") as f:
            config["instructions"] = f.read()
            
    return config

def create_agent():
    """Creates and configures the investment agent."""
    config = load_config()
    
    agent = Agent(
        name=config["name"],
        description=config["description"],
        model="gemini-3-flash-preview",
        instruction=config["instructions"],
        tools=[
            get_yahoo_finance_data,
            get_multi_tickers_data,
            search_finance_news,
            get_sector_analysis,
            screen_market_by_valuation,
            schedule_investment_reminder,
            cancel_investment_reminders,
            list_investment_schedules
        ]
    )
    return agent

# Create root_agent at module level for ADK web UI
root_agent = create_agent()

if __name__ == "__main__":
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    
    bot = create_agent()
    session_service = InMemorySessionService()
    runner = Runner(app_name="whatsapp-investment-bot", agent=bot, session_service=session_service)
    
    message = types.Content(
        role="user",
        parts=[types.Part(text="What is the price of AAPL?")]
    )
    
    result = runner.run(user_id="test", session_id="test", new_message=message)
    for event in result:
        if hasattr(event, 'text') and event.text:
            print(event.text)
