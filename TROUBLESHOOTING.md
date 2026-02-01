# WhatsApp Bot Troubleshooting Guide

## Common Issues and Solutions

### 1. Bot Not Responding to Messages

If your bot is not responding to WhatsApp messages, check the following:

#### A. Verify Webhook is Accessible
1. Make sure your Cloudflare tunnel is running:
   ```bash
   cloudflared tunnel run --url http://localhost:8000 whatsapp-bot
   ```
2. Test the webhook endpoint locally:
   ```bash
   curl http://localhost:8000/webhook
   ```
   You should see: `"Invalid request"`

3. Test the webhook from Meta's side:
   - Go to Meta Developer Portal → WhatsApp → Configuration
   - Click "Test" next to your webhook URL
   - It should show a success message

#### B. Check Docker Logs
View the application logs to see if requests are coming in:
```bash
docker compose logs -f app
```

Look for:
- `INFO:     Started server process`
- Any incoming POST requests to `/webhook`
- Any error messages

#### C. Verify Environment Variables
Ensure your `.env` file has all required values:
- `WHATSAPP_PHONE_NUMBER_ID` - from Meta Developer Portal
- `WHATSAPP_ACCESS_TOKEN` - from Meta Developer Portal
- `WHATSAPP_VERIFY_TOKEN` - must match what you set in Meta webhook config
- `GOOGLE_API_KEY` - from Google AI Studio

#### D. Test the Agent Locally
Run the agent test directly:
```bash
docker compose exec app python -c "from app.agent import create_agent; agent = create_agent(); print(agent.run('Hello').text)"
```

#### E. Check WhatsApp Message Format
The bot expects messages in this format from Meta:
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "phone_number",
          "text": {"body": "message_text"}
        }]
      }
    }]
  }]
}
```

### 2. Webhook Verification Failing

If Meta can't verify your webhook:
- Ensure `WHATSAPP_VERIFY_TOKEN` in `.env` matches exactly what you entered in Meta
- Check that your tunnel/domain is publicly accessible
- Verify the webhook URL ends with `/webhook`

### 3. Agent Errors

If you see errors related to the agent:
- Check that `GOOGLE_API_KEY` is valid
- Verify you have access to Gemini 1.5 Flash model
- Check Docker logs for specific error messages

### 4. Debugging Steps

1. **Enable verbose logging** - Add to `app/main.py`:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Test webhook manually** with curl:
   ```bash
   curl -X POST http://localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"1234567890","text":{"body":"test"}}]}}]}]}'
   ```

3. **Check Redis connection**:
   ```bash
   docker compose exec redis redis-cli ping
   ```
   Should return: `PONG`

### 5. Quick Restart

If all else fails, restart the entire stack:
```bash
docker compose down
docker compose up --build
```
