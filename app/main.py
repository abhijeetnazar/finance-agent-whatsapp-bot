import os
import json
from fastapi import FastAPI, Request, HTTPException
from app.agent import create_agent
from app.whatsapp import send_whatsapp_message
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI()
agent = create_agent()
session_service = InMemorySessionService()
runner = Runner(app_name="whatsapp-investment-bot", agent=agent, session_service=session_service)

# Load allowed numbers from config
with open("app/agent_config.json", "r") as f:
    config_data = json.load(f)
ALLOWED_NUMBERS = config_data.get("allowed_numbers", [])

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

@app.get("/webhook")
async def verify_webhook(request: Request):
    # Meta's verification step
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    return "Invalid request"

@app.post("/webhook")
async def webhook_post(request: Request):
    """Handle incoming WhatsApp messages."""
    try:
        body = await request.json()
        print(f"DEBUG: Webhook received body: {body}")
        
        # Extract message data
        entry = body.get("entry", [])
        if not entry:
            return {"status": "ok"}
        
        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "ok"}
        
        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        
        if messages:
            msg = messages[0]
            from_number = msg.get("from")
            text_body = msg.get("text", {}).get("body")
            
            # Check if phone number is allowed
            # Normalize by removing '+' if present
            clean_number = from_number.replace("+", "")
            if ALLOWED_NUMBERS and clean_number not in ALLOWED_NUMBERS:
                print(f"WARNING: Unauthorized access attempt from {from_number}")
                return {"status": "unauthorized"}
            
            if text_body:
                # Include context about the sender so the agent can use the phone number for scheduling
                full_prompt = f"User (Phone: {from_number}): {text_body}"
                
                # Create message content object
                message = types.Content(
                    role="user",
                    parts=[types.Part(text=full_prompt)]
                )
                
                # Create or get session for this user
                # The session_service will handle whether the session exists or not
                try:
                    # Try to create a new session
                    session = await session_service.create_session(
                        app_name="whatsapp-investment-bot",
                        user_id=from_number,
                        session_id=from_number
                    )
                except Exception as e:
                    # If session already exists, that's fine - we can still use it
                    # The runner will use the existing session
                    print(f"Session info: {str(e)}")
                    pass
                
                # Get response from AI Agent using Runner
                # Using from_number as both user_id and session_id for persistent conversations
                print(f"DEBUG: About to call runner.run() for user {from_number}")
                from starlette.concurrency import run_in_threadpool
                try:
                    # Run the blocking runner.run method in a separate thread
                    result = await run_in_threadpool(
                        runner.run, 
                        user_id=from_number, 
                        session_id=from_number, 
                        new_message=message
                    )
                    print(f"DEBUG: runner.run() returned, processing events...")
                except Exception as e:
                    print(f"ERROR: runner.run() failed: {e}")
                    import traceback
                    traceback.print_exc()
                    result = []
                
                # Extract the text from the result
                ai_text = ""
                for event in result:
                    # Handle different event structures
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                ai_text += part.text
                    elif hasattr(event, 'text') and event.text:
                        ai_text += event.text
                
                # Send response back to WhatsApp
                if ai_text:
                    await send_whatsapp_message(from_number, ai_text)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
def read_root():
    return {"message": "WhatsApp Investment Bot is running!"}
