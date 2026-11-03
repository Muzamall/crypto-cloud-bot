import ccxt
import pandas as pd
import pandas_ta as ta
from collections import defaultdict
import time

EXCHANGE = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'NEAR/USDT',
    'PEPE/USDT', 'RENDER/USDT', 'FET/USDT', 'INJ/USDT', 'ARB/USDT',
    'OP/USDT', 'POL/USDT', 'TIA/USDT', 'SEI/USDT', 'ATOM/USDT',
    'FIL/USDT', 'APT/USDT', 'HBAR/USDT', 'ICP/USDT',
    'STX/USDT', 'IMX/USDT', 'GRT/USDT', 'AR/USDT',
    'LTC/USDT', 'BCH/USDT', 'ETC/USDT', 'UNI/USDT', 'AAVE/USDT',
    'MKR/USDT', 'SNX/USDT', 'CRV/USDT', 'DYDX/USDT', 'PENDLE/USDT',
    'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT', 'JUP/USDT', 'PYTH/USDT',
    'STRK/USDT', 'MANA/USDT', 'SAND/USDT', 'AXS/USDT', 'GALA/USDT'
]

TIMEFRAME = '15m'
LIMIT = 800          # ~8 days of 15m data (enough for last week)
ATR_MULT_SL = 0.5
ATR_MULT_TP = 2.5

def run_last_week_backtest():
    print("⌛ Backtesting the Live Bot Strategy on Last ~7-8 Days...\n")

    performance = defaultdict(lambda: {
        'buy_wins': 0, 'buy_losses': 0,
        'sell_wins': 0, 'sell_losses': 0,
        'net_r': 0.0
    })

    global_buy_wins = 0
    global_buy_losses = 0
    global_sell_wins = 0
    global_sell_losses = 0

    for idx, symbol in enumerate(SYMBOLS, 1):
        print(f"[{idx}/{len(SYMBOLS)}] {symbol}...", end=" ")
        try:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
            if not ohlcv or len(ohlcv) < 250:
                print("→ Skipped")
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Indicators (exactly as live bot)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['swing_low'] = df['low'].rolling(window=12).min().shift(1)
            df['swing_high'] = df['high'].rolling(window=12).max().shift(1)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'], length=200)

            df = df.dropna().reset_index()
            trades = 0

            for i in range(50, len(df) - 20):
                row = df.iloc[i]
                prev = df.iloc[i-1]

                if pd.isna(row['atr']) or row['atr'] == 0:
                    continue

                is_macro_bullish = row['ema_50'] > row['ema_200']
                is_macro_bearish = row['ema_50'] < row['ema_200']

                # ========== LONG ==========
                if is_macro_bullish:
                    if (row['low'] <= row['swing_low']) and (row['close'] > prev['high']) and (row['close'] > row['open']):
                        entry = row['close']
                        atr = row['atr']
                        sl = row['low'] - (ATR_MULT_SL * atr)
                        risk = entry - sl
                        if risk <= 0:
                            continue
                        tp = entry + (ATR_MULT_TP * atr)

                        # Simulate
                        result = None
                        for j in range(i+1, min(i+50, len(df))):
                            f = df.iloc[j]
                            if f['low'] <= sl:
                                result = 'LOSS'
                                break
                            if f['high'] >= tp:
                                result = 'WIN'
                                break

                        if result == 'WIN':
                            # Approximate R (since TP is ATR based, not exact RR)
                            r_multiple = (tp - entry) / risk
                            performance[symbol]['buy_wins'] += 1
                            performance[symbol]['net_r'] += r_multiple
                            global_buy_wins += 1
                            trades += 1
                        elif result == 'LOSS':
                            performance[symbol]['buy_losses'] += 1
                            performance[symbol]['net_r'] -= 1.0
                            global_buy_losses += 1
                            trades += 1

                # ========== SHORT ==========
                elif is_macro_bearish:
                    if (row['high'] >= row['swing_high']) and (row['close'] < prev['low']) and (row['close'] < row['open']):
                        entry = row['close']
                        atr = row['atr']
                        sl = row['high'] + (ATR_MULT_SL * atr)
                        risk = sl - entry
                        if risk <= 0:
                            continue
                        tp = entry - (ATR_MULT_TP * atr)

                        result = None
                        for j in range(i+1, min(i+50, len(df))):
                            f = df.iloc[j]
                            if f['high'] >= sl:
                                result = 'LOSS'
                                break
                            if f['low'] <= tp:
                                result = 'WIN'
                                break

                        if result == 'WIN':
                            r_multiple = (entry - tp) / risk
                            performance[symbol]['sell_wins'] += 1
                            performance[symbol]['net_r'] += r_multiple
                            global_sell_wins += 1
                            trades += 1
                        elif result == 'LOSS':
                            performance[symbol]['sell_losses'] += 1
                            performance[symbol]['net_r'] -= 1.0
                            global_sell_losses += 1
                            trades += 1

            print(f"→ {trades} trades")

        except Exception as e:
            print(f"→ Error: {str(e)[:60]}")
            continue

        time.sleep(0.25)

    # ==================== REPORT ====================
    print("\n" + "="*85)
    print(f"{'SYMBOL':<12} | {'BUY (W/L)':<12} | {'SELL (W/L)':<12} | {'TRADES':<8} | {'NET R':>8}")
    print("-"*85)

    for symbol, data in performance.items():
        total = data['buy_wins'] + data['buy_losses'] + data['sell_wins'] + data['sell_losses']
        if total == 0:
            continue
        buy_str = f"{data['buy_wins']}W/{data['buy_losses']}L"
        sell_str = f"{data['sell_wins']}W/{data['sell_losses']}L"
        print(f"{symbol:<12} | {buy_str:<12} | {sell_str:<12} | {total:<8} | {data['net_r']:>+7.1f} R")

    print("="*85)

    total_buy = global_buy_wins + global_buy_losses
    total_sell = global_sell_wins + global_sell_losses
    total_trades = total_buy + total_sell
    total_wins = global_buy_wins + global_sell_wins
    total_losses = global_buy_losses + global_sell_losses

    # Note: Net R is approximate because TP is ATR-based
    total_net = sum(d['net_r'] for d in performance.values())

    winrate = (total_wins / total_trades * 100) if total_trades > 0 else 0

    print(f"\n📈 LONG  → Trades: {total_buy} | {global_buy_wins}W / {global_buy_losses}L")
    print(f"📉 SHORT → Trades: {total_sell} | {global_sell_wins}W / {global_sell_losses}L")
    print(f"\n🎯 FINAL RESULTS (Last ~7-8 Days):")
    print(f"   Total Trades     : {total_trades}")
    print(f"   Wins / Losses    : {total_wins} / {total_losses}")
    print(f"   Win Rate         : {winrate:.2f}%")
    print(f"   Net Profit       : {total_net:+.1f} R (approx)")
    print("="*85)

if __name__ == "__main__":
    run_last_week_backtest()