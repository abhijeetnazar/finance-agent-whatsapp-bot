import asyncio
import os
import json
import time
from tasks.celery import celery_app
from app.agent import create_agent
from app.whatsapp import send_whatsapp_message
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google import genai
from google.genai import types

from app.tools import redis_client

@celery_app.task
def process_dynamic_subscriptions():
    """
    Check Redis Sorted Set for due tasks and execute them.
    """
    current_time = time.time()
    # Get all tasks due up to now
    due_tasks = redis_client.zrangebyscore("scheduled_tasks", 0, current_time)
    
    print(f"DEBUG: Checking for due tasks at {current_time}. Found: {len(due_tasks)}")
    
    if not due_tasks:
        return f"No due tasks found at {current_time}."

    agent = create_agent()
    session_service = InMemorySessionService()
    runner = Runner(app_name="whatsapp-investment-bot", agent=agent, session_service=session_service)
    results = []
    
    # Process tasks in threadpool to avoid blocking if many
    for task_json in due_tasks:
        # Remove the task from Redis immediately to prevent duplicate processing
        # We will add it back with new time if it's recurring
        redis_client.zrem("scheduled_tasks", task_json)
        
        try:
            task = json.loads(task_json)
            phone_number = str(task.get("phone_number"))
            topic = task.get("topic")
            interval = task.get("interval_seconds", 3600)
            is_one_time = task.get("is_one_time", False)
            end_time = task.get("end_time", -1)
            
            # Create session if it doesn't exist (mirroring working app/main.py logic)
            async def init_session():
                try:
                    await session_service.create_session(
                        app_name="whatsapp-investment-bot",
                        user_id=phone_number,
                        session_id=phone_number
                    )
                    print(f"DEBUG: Created new session for {phone_number} in worker")
                except Exception as e:
                    print(f"DEBUG: Session already exists or note: {e}")
            
            asyncio.run(init_session())
            
            # Execute Agent
            message = types.Content(
                role="user",
                parts=[types.Part(text=f"Provide a brief investment update for: {topic}")]
            )
            
            # Run agent (blocking call)
            print(f"DEBUG: Worker calling runner.run() for {phone_number} on {topic}")
            try:
                result = runner.run(user_id=phone_number, session_id=phone_number, new_message=message)
                print(f"DEBUG: runner.run() generator returned, starting event consumption")
                summary_text = ""
                event_count = 0
                for event in result:
                    event_count += 1
                    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                summary_text += part.text
                    elif hasattr(event, 'text') and event.text:
                        summary_text += event.text
                
                print(f"DEBUG: Processed {event_count} events for {topic}, extracted {len(summary_text)} chars")
                
                if summary_text:
                    print(f"DEBUG: Sending summary to {phone_number}")
                    asyncio.run(send_whatsapp_message(phone_number, summary_text))
                    results.append(f"Sent {topic} to {phone_number}")
                else:
                    print(f"DEBUG: No summary text generated for {topic}")
            except Exception as e:
                print(f"ERROR: Worker agent execution failed for {topic}: {str(e)}")
                import traceback
                traceback.print_exc()
                results.append(f"Error: {str(e)}")

            # Reschedule if not one-time and (forever OR time remaining)
            # We use a buffer of half the interval to ensure we don't skip the last requested update
            # even if there's slight processing drift.
            if not is_one_time and (end_time == -1 or current_time + (interval / 2) < end_time):
                next_run = current_time + interval
                redis_client.zadd("scheduled_tasks", {task_json: next_run})
                results.append(f"Rescheduled for {next_run}")
            else:
                 results.append(f"Task completed/expired (Current: {current_time}, End: {end_time})")

        except Exception as e:
             results.append(f"Failed to process task: {e}")
             
    return f"Processed {len(due_tasks)} tasks. Details: {results}"

@celery_app.task
def send_market_summary(to_number: str):
    """Fallback legacy task."""
    agent = create_agent()
    session_service = InMemorySessionService()
    runner = Runner(app_name="whatsapp-investment-bot", agent=agent, session_service=session_service)
    message = types.Content(
        role="user",
        parts=[types.Part(text="Provide a brief summary of today's investment market highlights.")]
    )
    result = runner.run(user_id=to_number, session_id=to_number, new_message=message)
    
    # Extract text from result
    summary_text = ""
    for event in result:
        if hasattr(event, 'text') and event.text:
            summary_text += event.text
    
    if summary_text:
        asyncio.run(send_whatsapp_message(to_number, summary_text))
    return f"Legacy summary sent to {to_number}"
