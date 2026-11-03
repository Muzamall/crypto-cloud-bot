import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import feedparser
import re
from datetime import datetime, timezone, timedelta

# Connect to exchange
EXCHANGE = ccxt.binance({'enableRateLimit': True})

# GitHub / Cloud Discord Webhook URL (Yahan apna cloud channel ka webhook dalein)
WEBHOOK_URL = "https://discord.com/api/webhooks/1567090121688481893/nNCcIwVyBCS2ep7USOuEt5SolEjZ0sKnT41hIkAvqJbMWvEgUbSLac4v3ZAm1nFj-tni"
# Top 50 High-Volume Altcoins Basket
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

def get_pakistan_time():
    pkt_zone = timezone(timedelta(hours=5))
    return datetime.now(pkt_zone)

def send_discord_alert(message):
    payload = {"content": message}
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code in [200, 204]:
            print("✅ Cloud Discord alert sent successfully!")
        else:
            print(f"❌ Failed to send Discord alert: {response.text}")
    except Exception as e:
        print(f"Error sending webhook: {e}")

def clean_html(raw_text):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_text).strip()

def scan_market():
    pkt_time_str = get_pakistan_time().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🔍 Cloud Scan Executing Top 50 Altcoins at {pkt_time_str} PKT...")
    
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
            df['ema_200'] = ta.ema(df['close'], length=200)
            
            i = len(df) - 2
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            candle_time = df.index[i]
            
            if pd.isna(row['swing_low']) or pd.isna(row['swing_high']) or pd.isna(row['atr']) or row['atr'] == 0 or pd.isna(row['ema_50']) or pd.isna(row['ema_200']):
                continue
                
            is_macro_bullish = float(row['ema_50']) > float(row['ema_200'])
            is_macro_bearish = float(row['ema_50']) < float(row['ema_200'])
            
            if is_macro_bullish and (row['low'] <= row['swing_low']) and (row['close'] > prev_row['high'] and row['close'] > row['open']):
                entry = row['close']
                atr = row['atr']
                sl = row['low'] - (0.5 * atr)
                tp = entry + (2.5 * atr)
                
                pkt_candle_time = candle_time.tz_localize('UTC').tz_convert('Asia/Karachi') if candle_time.tzinfo is None else candle_time.tz_convert('Asia/Karachi')
                
                alert_msg = (
                    f"☁️ **GITHUB CLOUD - LONG SIGNAL** 🟢\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• **Symbol:** `{symbol}` (15m)\n"
                    f"• **Entry:** `{entry:.4f}` | **SL:** `{sl:.4f}` | **TP:** `{tp:.4f}` (1:2.5 R:R)\n"
                    f"• **Time (PKT):** `{pkt_candle_time.strftime('%Y-%m-%d %H:%M')}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                send_discord_alert(alert_msg)
                continue

            if is_macro_bearish and (row['high'] >= row['swing_high']) and (row['close'] < prev_row['low'] and row['close'] < row['open']):
                entry = row['close']
                atr = row['atr']
                sl = row['high'] + (0.5 * atr)
                tp = entry - (2.5 * atr)
                
                pkt_candle_time = candle_time.tz_localize('UTC').tz_convert('Asia/Karachi') if candle_time.tzinfo is None else candle_time.tz_convert('Asia/Karachi')
                
                alert_msg = (
                    f"☁️ **GITHUB CLOUD - SHORT SIGNAL** 🔴\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• **Symbol:** `{symbol}` (15m)\n"
                    f"• **Entry:** `{entry:.4f}` | **SL:** `{sl:.4f}` | **TP:** `{tp:.4f}` (1:2.5 R:R)\n"
                    f"• **Time (PKT):** `{pkt_candle_time.strftime('%Y-%m-%d %H:%M')}`\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                send_discord_alert(alert_msg)

        except Exception as e:
            continue

if __name__ == "__main__":
    print("🚀 GitHub Cloud Scan Started...")
    scan_market()
    print("✅ Cloud Scan Finished.")