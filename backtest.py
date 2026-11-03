import ccxt
import pandas as pd
import pandas_ta as ta
from collections import defaultdict

# Connect to Exchange
EXCHANGE = ccxt.binance({'enableRateLimit': True})

# Top 50 High-Volume Altcoins Basket
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT', 'NEAR/USDT',
    'PEPE/USDT', 'RENDER/USDT', 'FET/USDT', 'INJ/USDT', 'ARB/USDT',
    'OP/USDT', 'MATIC/USDT', 'TIA/USDT', 'SEI/USDT', 'ATOM/USDT',
    'FIL/USDT', 'APT/USDT', 'HBAR/USDT', 'RNDR/USDT', 'ICP/USDT',
    'STX/USDT', 'IMX/USDT', 'GRT/USDT', 'AR/USDT',
    'LTC/USDT', 'BCH/USDT', 'ETC/USDT', 'UNI/USDT', 'AAVE/USDT',
    'MKR/USDT', 'SNX/USDT', 'CRV/USDT', 'DYDX/USDT', 'PENDLE/USDT',
    'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT', 'JUP/USDT', 'PYTH/USDT',
    'STRK/USDT', 'MANA/USDT', 'SAND/USDT', 'AXS/USDT', 'GALA/USDT'
]
TIMEFRAME = '15m'

def run_detailed_backtest():
    print(f"⌛ Running Detailed Per-Coin Backtest across Top 50 Altcoins (15m)...\n")
    
    # Dictionary to store performance per symbol
    performance = defaultdict(lambda: {
        'buy_wins': 0, 'buy_losses': 0, 
        'sell_wins': 0, 'sell_losses': 0, 
        'net_r': 0.0
    })

    limit = 1000
    
    for symbol in SYMBOLS:
        try:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=limit)
            if not ohlcv or len(ohlcv) < 250: 
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Indicators
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            df['swing_low'] = df['low'].rolling(window=15).min().shift(1)
            df['swing_high'] = df['high'].rolling(window=15).max().shift(1)
            df['ema_50'] = ta.ema(df['close'], length=50)
            df['ema_200'] = ta.ema(df['close'], length=200)
            df['volume_sma'] = ta.sma(df['volume'], length=20)

            # Simulation Engine
            for i in range(200, len(df) - 10):
                row = df.iloc[i]
                prev_row = df.iloc[i-1]

                if pd.isna(row['swing_low']) or pd.isna(row['swing_high']) or pd.isna(row['atr']) or row['atr'] == 0 or pd.isna(row['ema_50']) or pd.isna(row['ema_200']):
                    continue

                is_macro_bullish = row['ema_50'] > row['ema_200']
                is_macro_bearish = row['ema_50'] < row['ema_200']
                has_volume = row['volume'] > row['volume_sma']

                # 1. BUY / LONG Trade Signal Detection
                if is_macro_bullish and has_volume and (row['low'] <= row['swing_low']) and (row['close'] > prev_row['high'] and row['close'] > row['open']):
                    entry = row['close']
                    sl = row['low'] - (0.5 * row['atr'])
                    tp = entry + (2.5 * row['atr'])
                    
                    trade_result = None
                    for j in range(i + 1, min(i + 40, len(df))):
                        future_row = df.iloc[j]
                        if future_row['low'] <= sl:
                            trade_result = 'LOSS'
                            break
                        elif future_row['high'] >= tp:
                            trade_result = 'WIN'
                            break

                    if trade_result == 'WIN':
                        performance[symbol]['buy_wins'] += 1
                        performance[symbol]['net_r'] += 2.5
                    elif trade_result == 'LOSS':
                        performance[symbol]['buy_losses'] += 1
                        performance[symbol]['net_r'] -= 1.0

                # 2. SELL / SHORT Trade Signal Detection
                elif is_macro_bearish and has_volume and (row['high'] >= row['swing_high']) and (row['close'] < prev_row['low'] and row['close'] < row['open']):
                    entry = row['close']
                    sl = row['high'] + (0.5 * row['atr'])
                    tp = entry - (2.5 * row['atr'])

                    trade_result = None
                    for j in range(i + 1, min(i + 40, len(df))):
                        future_row = df.iloc[j]
                        if future_row['high'] >= sl:
                            trade_result = 'LOSS'
                            break
                        elif future_row['low'] <= tp:
                            trade_result = 'WIN'
                            break

                    if trade_result == 'WIN':
                        performance[symbol]['sell_wins'] += 1
                        performance[symbol]['net_r'] += 2.5
                    elif trade_result == 'LOSS':
                        performance[symbol]['sell_losses'] += 1
                        performance[symbol]['net_r'] -= 1.0

        except Exception as e:
            continue

    # Print Detailed Report
    print("📊 ================= DETAILED PER-COIN PERFORMANCE ================= 📊")
    print(f"{'SYMBOL':<12} | {'BUY (W/L)':<12} | {'SELL (W/L)':<12} | {'TOTAL TRADES':<14} | {'NET PROFIT':<10}")
    print("-" * 72)

    grand_total_trades = 0
    grand_total_wins = 0
    grand_total_losses = 0
    total_net_r = 0.0

    for symbol, data in performance.items():
        b_wins = data['buy_wins']
        b_losses = data['buy_losses']
        s_wins = data['sell_wins']
        s_losses = data['sell_losses']
        
        total_coin_trades = b_wins + b_losses + s_wins + s_losses
        if total_coin_trades == 0:
            continue
            
        coin_wins = b_wins + s_wins
        coin_losses = b_losses + s_losses
        net_r = data['net_r']

        grand_total_trades += total_coin_trades
        grand_total_wins += coin_wins
        grand_total_losses += coin_losses
        total_net_r += net_r

        buy_str = f"{b_wins}W/{b_losses}L"
        sell_str = f"{s_wins}W/{s_losses}L"
        
        print(f"{symbol:<12} | {buy_str:<12} | {sell_str:<12} | {total_coin_trades:<14} | {net_r:>+6.1f} R")

    overall_wr = (grand_total_wins / grand_total_trades * 100) if grand_total_trades > 0 else 0
    print("=" * 72)
    print(f"📈 **AGGREGATE SUMMARY:**")
    print(f"• Total Trades Executed : {grand_total_trades}")
    print(f"• Total Wins / Losses   : {grand_total_wins} Wins / {grand_total_losses} Losses")
    print(f"• Overall Win Rate      : {overall_wr:.2f}%")
    print(f"• Total Net Profit      : {total_net_r:+.1f} R")
    print("========================================================================\n")

if __name__ == "__main__":
    run_detailed_backtest()