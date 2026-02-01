import os
import redis
import json
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

# Initialize Redis client (centralized)
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

def get_yahoo_finance_data(symbol: str) -> str:
    """
    Fetches real-time stock data, company information, and key statistics for a single ticker.
    Args:
        symbol: The stock ticker symbol (e.g., 'AAPL', 'NVDA').
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        summary = info.get("longBusinessSummary", "No summary available.")
        currency = info.get("currency", "USD")
        day_high = info.get("dayHigh")
        day_low = info.get("dayLow")
        rev_growth = info.get("revenueGrowth", "N/A")
        
        data_str = (
            f"--- {symbol} Report ---\n"
            f"💰 Price: {current_price} {currency} (Range: {day_low} - {day_high})\n"
            f"🏢 Market Cap: {market_cap:,} {currency}\n"
            f"📈 Revenue Growth: {rev_growth}\n"
            f"📝 Summary: {summary[:400]}...\n"
        )
        return data_str
    except Exception as e:
        return f"Error fetching data for {symbol}: {str(e)}"

def get_multi_tickers_data(symbols_string: str) -> str:
    """
    Fetches current prices for multiple stock symbols at once.
    Args:
        symbols_string: Space-separated tickers (e.g., 'AAPL MSFT GOOG').
    """
    try:
        tickers = yf.Tickers(symbols_string)
        results = f"--- Multi-Ticker Snapshot ({symbols_string}) ---\n"
        for sym in symbols_string.split():
            info = tickers.tickers[sym].info
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            results += f"🔹 {sym}: {current_price} {info.get('currency', 'USD')}\n"
        return results
    except Exception as e:
        return f"Error fetching multi-ticker data: {str(e)}"

def search_finance_news(query: str) -> str:
    """
    Searches for the latest market news and quotes based on a query.
    Args:
        query: Search term (e.g., 'AI stocks', 'Nvidia news').
    """
    try:
        search = yf.Search(query, max_results=5)
        news = search.news
        if not news:
            return f"No news found for '{query}'."
        
        news_str = f"--- Latest News for '{query}' ---\n"
        for item in news:
            title = item.get("title")
            publisher = item.get("publisher")
            link = item.get("link")
            news_str += f"📰 {title} ({publisher})\n🔗 {link}\n\n"
        return news_str
    except Exception as e:
        return f"Error searching news for {query}: {str(e)}"

def get_sector_analysis(sector_name: str) -> str:
    """
    Gets information and top companies for a market sector.
    Args:
        sector_name: e.g., 'technology', 'healthcare', 'financial-services', 'energy'.
    """
    try:
        # Normalize sector name for yfinance
        formatted_name = sector_name.lower().strip().replace(" ", "-")
        
        if not hasattr(yf, "Sector"):
            return "Error: Your version of yfinance doesn't support sector analysis. Please update to 0.2.x or higher."

        s = yf.Sector(formatted_name)
        
        try:
            top_companies = [c.get("symbol") for q in [s.top_companies] for c in q[:5]] if hasattr(s, 'top_companies') and s.top_companies is not None else []
        except:
            top_companies = []
            
        analysis = f"--- 🏢 {sector_name.title()} Sector Analysis ---\n"
        
        if not top_companies and not hasattr(s, "overview"):
            return f"Data unavailable for sector: {sector_name}. Try 'technology', 'energy', or 'healthcare'."

        if top_companies:
            analysis += f"📈 Notable Companies: {', '.join(top_companies)}\n"
        
        if hasattr(s, 'overview') and s.overview:
            analysis += f"📝 Outlook: {s.overview[:200]}...\n"
            
        return analysis
    except Exception as e:
        print(f"DEBUG: Sector Error: {str(e)}")
        return f"Error fetching sector info for '{sector_name}': {str(e)}. Try a major industry name."

def screen_market_by_valuation(criteria: str = "undervalued_growth") -> str:
    """
    Uses the yfinance Screener to find stocks matching a specific strategy.
    Args:
        criteria: One of 'undervalued_growth', 'day_gainers', 'day_losers', 'most_actives', 'growth_technology_stocks', 'most_shorted_stocks'.
    """
    try:
        lookup = {
            "undervalued growth": "undervalued_growth_stocks",
            "growth stocks": "undervalued_growth_stocks",
            "gainers": "day_gainers",
            "top gainers": "day_gainers",
            "losers": "day_losers",
            "actives": "most_actives",
            "most active": "most_actives",
            "shorted": "most_shorted_stocks",
            "tech": "growth_technology_stocks",
            "technology": "growth_technology_stocks",
            "undervalued": "undervalued_large_caps",
            "small cap": "small_cap_gainers"
        }
        
        criteria_key = criteria.lower().strip()
        criteria_key = lookup.get(criteria_key, criteria_key.replace(" ", "_"))
        
        # Validation for yfinance 1.1.0+ strictness
        valid_keys = [
            "aggressive_small_caps", "conservative_foreign_funds", "day_gainers", "day_losers",
            "growth_technology_stocks", "high_yield_bond", "most_actives", "most_shorted_stocks",
            "portfolio_anchors", "small_cap_gainers", "top_mutual_funds", 
            "undervalued_growth_stocks", "undervalued_large_caps"
        ]
        
        if criteria_key not in valid_keys:
             # Try to find a close match or fallback
             if "growth" in criteria_key: criteria_key = "undervalued_growth_stocks"
             elif "undervalued" in criteria_key: criteria_key = "undervalued_large_caps"
             elif "active" in criteria_key: criteria_key = "most_actives"
             elif "loser" in criteria_key: criteria_key = "day_losers"
             elif "gainer" in criteria_key: criteria_key = "day_gainers"
             elif "tech" in criteria_key: criteria_key = "growth_technology_stocks"
             elif "small" in criteria_key: criteria_key = "small_cap_gainers"
             else:
                  # If we still don't have a valid key, default to gainers to avoid 404
                  criteria_key = "day_gainers"

        results_data = None
        
        if hasattr(yf, "screen"):
            try:
                results_data = yf.screen(criteria_key)
            except Exception as e:
                if "404" in str(e) or "not a predefined" in str(e).lower():
                    results_data = yf.screen("day_gainers")
                    criteria_key = "day_gainers (fallback)"
                else:
                    raise e
        elif hasattr(yf, "Screener"):
            scr = yf.Screener()
            scr.set_predefined_body(criteria_key)
            results_data = scr.response
        else:
            return "Error: Unsupported yfinance version."

        if not results_data or "quotes" not in results_data:
            return f"No live market data found for strategy: {criteria_key}."
            
        quotes = results_data.get("quotes", [])[:5]
        if not quotes:
            return f"Successfully screened for {criteria_key}, but no stocks matched."
        
        resp = f"🚀 Top 5 stocks for strategy: {criteria_key.upper().replace('_', ' ')}\n\n"
        for q in quotes:
            symbol = q.get('symbol', 'N/A')
            price = q.get('regularMarketPrice', 'N/A')
            change = q.get('regularMarketChangePercent', 0)
            name = q.get('shortName', symbol)
            resp += f"🔹 **{symbol}** ({name}): ${price} ({change:+.2f}%)\n"
        
        return resp
    except Exception as e:
        return f"Error screening market: {str(e)}."

def schedule_investment_reminder(phone_number: str, interval: str, duration: str = "forever", topic: str = "general market") -> str:
    """
    Schedules a repeatable or one-time investment reminder.
    Args:
        phone_number: The user's WhatsApp phone number.
        interval: How often to send update (e.g., '5 minutes', '1 hour', '1 day').
        duration: How long to keep sending (e.g., 'once', '2 days', 'forever').
        topic: The specific investment topic.
    """
    import time
    import re

    def parse_to_seconds(text: str) -> int:
        text = text.lower().strip()
        units = {'minute': 60, 'min': 60, 'hour': 3600, 'hr': 3600, 'day': 84600}
        match = re.match(r"(\d+)\s*([a-z]+)", text)
        if match:
            val, unit = int(match.group(1)), match.group(2)
            for k, v in units.items():
                if unit.startswith(k):
                    return val * v
        return 3600

    interval_seconds = parse_to_seconds(interval)
    current_time = time.time()
    next_run = current_time + interval_seconds
    
    is_one_time = duration.lower() == "once"
    end_time = -1
    
    if not is_one_time and duration.lower() != "forever":
        duration_seconds = parse_to_seconds(duration)
        end_time = current_time + duration_seconds + (interval_seconds / 2)

    task_data = {
        "phone_number": phone_number,
        "topic": topic,
        "interval_seconds": interval_seconds,
        "is_one_time": is_one_time,
        "end_time": end_time
    }
    
    redis_client.zadd("scheduled_tasks", {json.dumps(task_data): next_run})
    duration_msg = "just once" if is_one_time else (f"every {interval} for {duration}" if end_time > 0 else f"every {interval} forever")
    return f"Scheduled {topic} update for {phone_number} {duration_msg}."

def cancel_investment_reminders(phone_number: str, topic: str = None) -> str:
    """
    Cancels or stops active investment reminders for a user.
    Args:
        phone_number: The user's WhatsApp phone number.
        topic: The specific topic to stop. If None, stops all for this number.
    """
    try:
        all_tasks = redis_client.zrange("scheduled_tasks", 0, -1)
        removed_count = 0
        
        for task_json in all_tasks:
            task_data = json.loads(task_json)
            if task_data.get("phone_number") == phone_number:
                if topic:
                    if topic.lower() in task_data.get("topic", "").lower():
                        redis_client.zrem("scheduled_tasks", task_json)
                        removed_count += 1
                else:
                    redis_client.zrem("scheduled_tasks", task_json)
                    removed_count += 1
        
        if removed_count == 0:
            return "No active reminders found for your number."
            
        return f"Successfully stopped {removed_count} active reminder(s)."
    except Exception as e:
        return f"Error cancelling reminders: {str(e)}"

def list_investment_schedules(phone_number: str) -> str:
    """
    Lists all active scheduled investment reminders for a user.
    Args:
        phone_number: The user's WhatsApp phone number.
    """
    try:
        # Get all tasks and their scores (next run times)
        all_tasks_with_scores = redis_client.zrange("scheduled_tasks", 0, -1, withscores=True)
        user_tasks = []
        
        import datetime
        
        for task_json, next_run_ts in all_tasks_with_scores:
            task_data = json.loads(task_json)
            if str(task_data.get("phone_number")) == str(phone_number):
                topic = task_data.get("topic", "general market")
                interval_secs = task_data.get("interval_seconds", 3600)
                is_one_time = task_data.get("is_one_time", False)
                end_time = task_data.get("end_time", -1)
                
                # Format interval
                if interval_secs < 3600:
                    interval_str = f"{interval_secs // 60} min"
                elif interval_secs < 86400:
                    interval_str = f"{interval_secs // 3600} hr"
                else:
                    interval_str = f"{interval_secs // 86400} day"
                
                next_run_str = datetime.datetime.fromtimestamp(next_run_ts).strftime('%H:%M')
                
                status = "Once" if is_one_time else f"Every {interval_str}"
                user_tasks.append(f"⏰ **{topic}** ({status}) - Next: {next_run_str}")
        
        if not user_tasks:
            return "You have no active scheduled reminders."
            
        resp = "📋 **Your Active Schedules:**\n" + "\n".join(user_tasks)
        return resp
    except Exception as e:
        return f"Error listing schedules: {str(e)}"
