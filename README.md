# 🚀 Setup Guide: WhatsApp Investment Bot

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24.0+-blue?style=for-the-badge&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Stack-red?style=for-the-badge&logo=redis&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini%203-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Business%20API-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)

This comprehensive guide provides detailed instructions on how to configure the **WhatsApp Investment Bot**, obtain necessary API credentials, and deploy the system using Docker.

---

## 🔑 1. Google API Credentials

The bot utilizes **Gemini 2.0 Flash** via the Google Gen AI SDK to provide real-time investment analysis and natural language processing.

### Step A: 🏗️ Google AI Studio (Recommended)
This is the fastest method to obtain an API key if you have a Google account.

1. 🌐 Navigate to **[Google AI Studio](https://aistudio.google.com/)**.
2. 👤 Sign in with your Google Account.
3. 👈 Select **Get API key** from the left navigation sidebar.
4. ➕ Click **Create API key in new project**.
5. 📋 Copy the generated key safely. You will use this as `GOOGLE_API_KEY`.

> [!NOTE]
> Ensure your Google account has access to the Gemini models. Pro subscriptions may offer higher rate limits.

---

## 📱 2. WhatsApp Business API Setup

We use the Meta Graph API to send and receive WhatsApp messages. This requires setting up a Meta App and a System User for authentication.

### Step A: 👤 Create Meta App
1. 🌐 Log in to the **[Meta Developers Portal](https://developers.facebook.com/)**.
2. 🖱️ Click **My Apps** > **Create App**.
3. ➡️ Select **Other** > **Next**.
4. 🏢 Select **Business** as the app type.
5. 🏷️ Enter an **App Name** (e.g., "FinanceAgent") and create the app.

### Step B: 📦 Add WhatsApp Product
1. 📉 On the App Dashboard, locate the **WhatsApp** tile and click **Set up**.
2. 🏦 Select or create a **Meta Business Account** (MBA) when prompted.

### Step C: 🆔 Retrieve Basic Credentials
Navigate to **WhatsApp** > **API Setup** in the left sidebar.
1. 📞 **Phone Number ID**: Note this ID; it corresponds to `WHATSAPP_PHONE_NUMBER_ID`.
2. 📲 **Recipient Number**: Add your personal phone number to the "To" field for testing purposes.

### Step D: 🛡️ Create System User (Permanent Token)
> [!IMPORTANT]
> The "Temporary Access Token" shown on the dashboard expires in 24 hours ⏳. For a production-ready bot, you **must** create a System User.

1. ⚙️ Go to **[Meta Business Settings](https://business.facebook.com/settings/)**.
2. 👥 Navigate to **Users** > **System Users**.
3. ➕ Click **Add**, name it "BotAdmin", and assign the **Admin** role.
4. 🔑 Click **Generate New Token**.
5. 📱 Select your **App** from the dropdown menu.
6. ✅ **Required Permissions**: Check the boxes for:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
7. 📋 Click **Generate Token**. This is your permanent `WHATSAPP_ACCESS_TOKEN`.

---

## ⚙️ 3. Environment Configuration

You must create two configuration files derived from the provided examples.

### Step A: 📝 Environment Variables (`.env`)
The `.env` file stores sensitive secrets.

1. 📄 Duplicate `.env.example` to create `.env`.
   ```bash
   # Windows
   copy .env.example .env
   # Linux/Mac
   cp .env.example .env
   ```
2. ✏️ Edit `.env` with your credentials:
   ```env
   WHATSAPP_PHONE_NUMBER_ID=123456789...       # From Step 2C
   WHATSAPP_ACCESS_TOKEN=EAAG...                # Permanent Token from Step 2D
   WHATSAPP_VERIFY_TOKEN=my_secure_token        # Create a random string (you will need this for Step 5)
   GOOGLE_API_KEY=AIzr...                       # From Step 1A
   ```

### Step B: 📋 Application Config (`agent_config.json`)
This file controls application-level settings and security whitelists.

1. 📄 Duplicate the example config:
   ```bash
   # Windows
   copy app\agent_config.json.example app\agent_config.json
   # Linux/Mac
   cp app/agent_config.json.example app/agent_config.json
   ```
2. ✏️ Edit `app/agent_config.json`:
   - **allowed_numbers**: **Critical for security.** Only numbers listed here will receive responses. Format must include country code without `+` (e.g., `919988776655`).
   ```json
   {
     "name": "InvestmentBot",
     "description": "Your AI Financial Assistant",
     "allowed_numbers": [
       "919876543210", 
       "15550199888"
     ]
   }
   ```

---

## 🏃 4. Application Deployment

Before configuring webhooks, the application must be running to handle the verification challenge.

1. 🐳 Ensure **Docker Desktop** is running.
2. 🚀 Build and start the services:
   ```bash
   docker compose up --build -d
   ```
3. 🔍 Verify connection:
   ```bash
   docker compose ps
   ```
   *You should see `finance-agent-app`, `finance-agent-worker`, `finance-agent-beat`, and `finance-agent-redis` all in `Up` status.*

---

## 🌐 5. Webhook Configuration

To receive messages from WhatsApp, Meta sends HTTP POST requests to your server. Since your bot is running locally, you must expose port `8000` to the internet.

### Option 1: ☁️ Cloudflare Tunnel (Recommended)
**Stability:** High | **Persistence:** Yes (with domain) 🏰
1. **Prerequisites**: A Cloudflare account and a registered domain.
2. **Commands**:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create finance-bot
   cloudflared tunnel route dns finance-bot your-domain.com
   cloudflared tunnel run --url http://localhost:8000 finance-bot
   ```
   *Result: Your bot is accessible at `https://your-domain.com`.*

### Option 2: 🔧 Ngrok (Testing)
**Stability:** Medium | **Persistence:** No (Free Tier) ⏱️
1. **Setup**: Install [ngrok](https://ngrok.com/).
2. **Run**:
   ```bash
   ngrok http 8000
   ```
3. 📋 Copy the `https` forwarding URL (e.g., `https://a1b2c3d4.ngrok-free.app`).

### Option 3: 💻 LocalTunnel (Open Source)
**Stability:** Variable | **Persistence:** No-Ip-Based 🔓
1. **Run**:
   ```bash
   npx localtunnel --port 8000
   ```
2. 📋 Copy the URL.

### Final Step: 🔗 Register Webhook in Meta
1. 🌐 Go to your **Meta App Dashboard** > **WhatsApp** > **Configuration**.
2. ✏️ Click **Edit** next to Webhook.
   - **Callback URL**: `https://your-tunnel-url.com/webhook`
   - **Verify Token**: Must match `WHATSAPP_VERIFY_TOKEN` from your `.env` file.
3. ✅ Click **Verify and Save**.
   > [!WARNING]
   > If verification fails, ensure your Docker container is running and the tunnel URL is reachable.
4. 🔔 **Subscribe to Events**:
   - Scroll to "Webhook fields".
   - Click **Manage**.
   - **Subscribe** to `messages`. **(Crucial)**

---

## ✅ Post-Setup Verification
1. 📱 Send a WhatsApp message ("Hi" or "Help") from a whitelisted number to your test business number.
2. 📜 Watch the logs for activity:
   ```bash
   docker compose logs -f app
   ```
