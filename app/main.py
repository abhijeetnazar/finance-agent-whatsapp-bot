import os
import json
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
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

from app.config import ALLOWED_NUMBERS

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
async def webhook_post(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp messages asynchronously."""
    try:
        body = await request.json()
        # print(f"DEBUG: Webhook received body: {body}")
        
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
            clean_number = from_number.replace("+", "")
            if ALLOWED_NUMBERS and clean_number not in ALLOWED_NUMBERS:
                # logger.warning(f"Unauthorized access attempt from {from_number}")
                return {"status": "unauthorized"}
            
            if text_body:
                # Offload processing to background task
                background_tasks.add_task(process_message_background, from_number, text_body)
                
        return {"status": "ok"}
    
    except Exception as e:
        # logger.error(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def process_message_background(from_number: str, text_body: str):
    """
    Background task to process the message with the AI agent.
    This runs after the webhook returns 200 OK.
    """
    try:
        full_prompt = f"User (Phone: {from_number}): {text_body}"
        
        # Create message content object
        message = types.Content(
            role="user",
            parts=[types.Part(text=full_prompt)]
        )
        
        # Create or get session
        try:
            session = await session_service.create_session(
                app_name="whatsapp-investment-bot",
                user_id=from_number,
                session_id=from_number
            )
        except Exception:
            # Session likely exists
            pass
        
        # Run agent in threadpool to avoid blocking async loop
        from starlette.concurrency import run_in_threadpool
        
        result = await run_in_threadpool(
            runner.run, 
            user_id=from_number, 
            session_id=from_number, 
            new_message=message
        )
        
        # Extract response text
        ai_text = ""
        for event in result:
            if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        ai_text += part.text
            elif hasattr(event, 'text') and event.text:
                ai_text += event.text
        
        # Send response via WhatsApp API
        if ai_text:
            await send_whatsapp_message(from_number, ai_text)
            
    except Exception as e:
        print(f"Error in background task: {e}") # Replace with logger later if needed

@app.get("/")
def read_root():
    return {"message": "WhatsApp Investment Bot is running!"}
