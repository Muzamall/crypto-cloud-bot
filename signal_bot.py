import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import feedparser
import re
import time
from datetime import datetime, timezone, timedelta

# Connect to exchange
EXCHANGE = ccxt.binance({'enableRateLimit': True})

# Your Active Discord Webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1562382541699293255/6_fCfqIbtzuwbVhJID1HObgd5MQTJX1SmrbBINL9DGFOQrYmqibNbGPJWzJWfsCVMfYy"

# Expanded Top 50 High-Volume Altcoins Basket
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'NEAR/USDT',
    'PEPE/USDT', 'RENDER/USDT', 'FET/USDT', 'INJ/USDT', 'ARB/USDT',
    'OP/USDT', 'MATIC/USDT', 'TIA/USDT', 'SEI/USDT', 'ATOM/USDT',
    'FIL/USDT', 'APT/USDT', 'HBAR/USDT', 'RNDR/USDT', 'ICP/USDT',
    'STX/USDT', 'IMX/USDT', 'NEAR/USDT', 'GRT/USDT', 'AR/USDT',
    'LTC/USDT', 'BCH/USDT', 'ETC/USDT', 'UNI/USDT', 'AAVE/USDT',
    'MKR/USDT', 'SNX/USDT', 'CRV/USDT', 'DYDX/USDT', 'PENDLE/USDT',
    'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT', 'JUP/USDT', 'PYTH/USDT',
    'STRK/USDT', 'MANA/USDT', 'SAND/USDT', 'AXS/USDT', 'GALA/USDT'
]
TIMEFRAME = '15m'

sent_signals = set()
sent_news = set()

def get_pakistan_time():
    pkt_zone = timezone(timedelta(hours=5))
    return datetime.now(pkt_zone)

def send_discord_alert(message):
    payload = {"content": message}
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code in [200, 204]:
            print("✅ Discord alert sent successfully!")
        else:
            print(f"❌ Failed to send Discord alert: {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")

def clean_html(raw_text):
    """Removes HTML tags and messy code from news summaries"""
    cleanr = re.compile('<.*?>')
    cleansed = re.sub(cleanr, '', raw_text)
    return cleansed.strip()

def analyze_news_sentiment(title, summary=""):
    text = (title + " " + summary).lower()
    
    bullish_words = ['accumulate', 'approval', 'approved', 'buy', 'bullish', 'recovery', 'license', 'etf inflow', 'partnership', 'surge', 'record high', 'overtakes']
    bearish_words = ['hack', 'hacked', 'hackers', 'loot', 'stolen', 'exploit', 'bug', 'dump', 'bearish', 'lawsuit', 'sec charge', 'ban', 'crash', 'default']
    
    sentiment = "⚪ NEUTRAL / INFORMATIONAL"
    if any(word in text for word in bullish_words):
        sentiment = "🟢 BULLISH (Market / Coin Impact)"
    elif any(word in text for word in bearish_words):
        sentiment = "🔴 BEARISH (Risk Warning)"
        
    macro_tag = "Global Crypto Market"
    if 'us' in text or 'sec' in text or 'fed' in text or 'jpmorgan' in text or 'galaxy' in text:
        macro_tag = "🇺🇸 US Macro / Institutional Context"
    elif 'brazil' in text or 'eu' in text or 'europe' in text:
        macro_tag = "🇪🇺 / 🌐 International Regulatory Event"
    elif 'solana' in text or 'sol' in text:
        macro_tag = "⚡ Solana Ecosystem"
    elif 'bitcoin' in text or 'btc' in text:
        macro_tag = "🪙 Bitcoin / Macro Asset"

    return sentiment, macro_tag

def check_fundamental_news():
    print("📰 Scanning authentic news sources...")
    rss_sources = [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/"
    ]
    
    for url in rss_sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = entry.title
                link = entry.link
                raw_summary = entry.get('summary', '')
                summary = clean_html(raw_summary)[:180] # Cleaned text snippet
                
                news_id = title
                if news_id not in sent_news:
                    sentiment, macro_tag = analyze_news_sentiment(title, summary)
                    pkt_time_str = get_pakistan_time().strftime('%Y-%m-%d %H:%M:%S')
                    
                    news_msg = (
                        f"📊 **INSTITUTIONAL FUNDAMENTAL UPDATE**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"• **Headline:** `{title}`\n"
                        f"• **Market Sentiment:** **{sentiment}**\n"
                        f"• **Category:** `{macro_tag}`\n"
                        f"• **Summary:** {summary}...\n"
                        f"• **Time (PKT):** `{pkt_time_str}`\n"
                        f"• **Link:** <{link}>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    send_discord_alert(news_msg)
                    sent_news.add(news_id)
        except Exception as e:
            print(f"Error fetching news from {url}: {e}")

def scan_market():
    pkt_time_str = get_pakistan_time().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🔍 Scanning Top 50 Altcoins & News at {pkt_time_str} PKT...")
    
    check_fundamental_news()
    
    for symbol in SYMBOLS:
        try:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=250)
            if not ohlcv or len(ohlcv) < 250: continue
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['swing_low'] = df['low'].rolling(window=12).min().shift(1)
            df['swing_high'] = df['high'].rolling(window=12).max().shift(1)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'],length=200)
            
            i = len(df) - 2
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            candle_time = df.index[i]
            
            if pd.isna(row['swing_low']) or pd.isna(row['swing_high']) or pd.isna(row['atr']) or row['atr'] == 0 or pd.isna(row['ema_50']) or pd.isna(row['ema_200']):
                continue
                
            is_macro_bullish = float(row['ema_50']) > float(row['ema_200'])
            is_macro_bearish = float(row['ema_50']) < float(row['ema_200'])
            
            signal_key = f"{symbol}_{candle_time}"
            if signal_key in sent_signals:
                continue
            
            if is_macro_bullish and (row['low'] <= row['swing_low']) and (row['close'] > prev_row['high'] and row['close'] > row['open']):
                entry = row['close']
                atr = row['atr']
                sl = row['low'] - (0.5 * atr)
                tp = entry + (2.5 * atr)
                
                pkt_candle_time = candle_time.tz_localize('UTC').tz_convert('Asia/Karachi') if candle_time.tzinfo is None else candle_time.tz_convert('Asia/Karachi')
                
                alert_msg = (
                    f"🟢 **NEW TECHNICAL LONG SIGNAL** 🟢\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• **Symbol:** `{symbol}` (15m)\n"
                    f"• **Entry:** `{entry:.4f}` | **SL:** `{sl:.4f}` | **TP:** `{tp:.4f}` (1:2.5 R:R)\n"
                    f"• **Time (PKT):** `{pkt_candle_time.strftime('%Y-%m-%d %H:%M')}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                send_discord_alert(alert_msg)
                sent_signals.add(signal_key)
                continue

            if is_macro_bearish and (row['high'] >= row['swing_high']) and (row['close'] < prev_row['low'] and row['close'] < row['open']):
                entry = row['close']
                atr = row['atr']
                sl = row['high'] + (0.5 * atr)
                tp = entry - (2.5 * atr)
                
                pkt_candle_time = candle_time.tz_localize('UTC').tz_convert('Asia/Karachi') if candle_time.tzinfo is None else candle_time.tz_convert('Asia/Karachi')
                
                alert_msg = (
                    f"🔴 **NEW TECHNICAL SHORT SIGNAL** 🔴\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• **Symbol:** `{symbol}` (15m)\n"
                    f"• **Entry:** `{entry:.4f}` | **SL:** `{sl:.4f}` | **TP:** `{tp:.4f}` (1:2.5 R:R)\n"
                    f"• **Time (PKT):** `{pkt_candle_time.strftime('%Y-%m-%d %H:%M')}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                send_discord_alert(alert_msg)
                sent_signals.add(signal_key)

        except Exception as e:
            continue

if __name__ == "__main__":
    print("🚀 Real-Time 50-Coin Intelligence Bot Online...")
    send_discord_alert("⚙️ **Bot Online & Clean!** HTML tags removed from summaries. Scanning Top 50 Altcoins continuously.")
    
    while True:
        scan_market()
        time.sleep(30)