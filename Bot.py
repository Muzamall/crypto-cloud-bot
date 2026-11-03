import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime, timezone

# Connect to exchange
EXCHANGE = ccxt.binance({'enableRateLimit': True})

# Your Active Discord Webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1562382541699293255/6_fCfqIbtzuwbVhJID1HObgd5MQTJX1SmrbBINL9DGFOQrYmqibNbGPJWzJWfsCVMfYy"

# Top 15 High-Volume Altcoins Basket
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'NEAR/USDT',
    'PEPE/USDT', 'RENDER/USDT', 'FET/USDT', 'INJ/USDT', 'ARB/USDT'
]
TIMEFRAME = '15m'

# Track sent signals to avoid duplicate alerts for the same candle
sent_signals = set()

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

def scan_market():
    current_time_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🔍 Scanning 15 Altcoins for setups at {current_time_str} UTC...")
    
    for symbol in SYMBOLS:
        try:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
            if not ohlcv: 
                continue
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Indicators
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['swing_low'] = df['low'].rolling(window=20).min().shift(1)
            df['swing_high'] = df['high'].rolling(window=20).max().shift(1)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'], length=200)
            
            # Check the latest completed candle (-2) to avoid repainting
            i = len(df) - 2
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            candle_time = df.index[i]
            
            swing_low_val = row['swing_low']
            swing_high_val = row['swing_high']
            ema_50 = row['ema_50']
            ema_200 = row['ema_200']
            
            if pd.isna(swing_low_val) or pd.isna(swing_high_val) or pd.isna(row['atr']) or row['atr'] == 0 or pd.isna(ema_50) or pd.isna(ema_200):
                continue
                
            is_macro_bullish = ema_50 > ema_200
            is_macro_bearish = ema_50 < ema_200
            
            signal_key = f"{symbol}_{candle_time}"
            if signal_key in sent_signals:
                continue
            
            # 1. Long CHoCH Setup
            is_sweep_low = row['low'] <= swing_low_val
            is_structure_break_up = row['close'] > prev_row['high'] and row['close'] > row['open']
            
            if is_macro_bullish and is_sweep_low and is_structure_break_up:
                entry_price = row['close']
                atr = row['atr']
                sl = row['low'] - (0.5 * atr)
                tp = entry_price + (2.5 * atr)
                
                alert_msg = (
                    f"🟢 **NEW INSTITUTIONAL LONG SIGNAL** 🟢\n"
                    f"----------------------------------------\n"
                    f"• **Symbol:** `{symbol}`\n"
                    f"• **Timeframe:** `15m`\n"
                    f"• **Entry Price:** `{entry_price:.4f}`\n"
                    f"• **Stop Loss (SL):** `{sl:.4f}`\n"
                    f"• **Take Profit (TP):** `{tp:.4f}` (1:2.5 R:R)\n"
                    f"• **Time:** `{candle_time.strftime('%Y-%m-%d %H:%M')} UTC`\n"
                    f"----------------------------------------"
                )
                send_discord_alert(alert_msg)
                sent_signals.add(signal_key)
                continue

            # 2. Short CHoCH Setup
            is_sweep_high = row['high'] >= swing_high_val
            is_structure_break_down = row['close'] < prev_row['low'] and row['close'] < row['open']
            
            if is_macro_bearish and is_sweep_high and is_structure_break_down:
                entry_price = row['close']
                atr = row['atr']
                sl = row['high'] + (0.5 * atr)
                tp = entry_price - (2.5 * atr)
                
                alert_msg = (
                    f"🔴 **NEW INSTITUTIONAL SHORT SIGNAL** 🔴\n"
                    f"----------------------------------------\n"
                    f"• **Symbol:** `{symbol}`\n"
                    f"• **Timeframe:** `15m`\n"
                    f"• **Entry Price:** `{entry_price:.4f}`\n"
                    f"• **Stop Loss (SL):** `{sl:.4f}`\n"
                    f"• **Take Profit (TP):** `{tp:.4f}` (1:2.5 R:R)\n"
                    f"• **Time:** `{candle_time.strftime('%Y-%m-%d %H:%M')} UTC`\n"
                    f"----------------------------------------"
                )
                send_discord_alert(alert_msg)
                sent_signals.add(signal_key)

        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

if __name__ == "__main__":
    print("🚀 Signal Bot Initializing...")
    # Send a startup notification to verify webhook connectivity
    send_discord_alert("⚙️ **Trading Signal Bot Online & Active!** Scanning Top 15 Altcoins on 15m Timeframe...")
    
    while True:
        scan_market()
        print("⏳ Scan complete. Waiting 15 minutes for next candle cycle...")
        time.sleep(900)