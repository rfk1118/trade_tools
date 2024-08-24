import ccxt
import threading
import time
from tabulate import tabulate
from datetime import datetime
from colorama import Fore, Style, init
import csv
import os

# 初始化 colorama
init(autoreset=True)

class ExchangeThread(threading.Thread):
    def __init__(self, exchange_id):
        threading.Thread.__init__(self)
        self.exchange_id = exchange_id
        self.spot_price = {}
        self.futures_price = {}
        self.open_interest = None
        self.last_update = None

    def run(self):
        exchange = getattr(ccxt, self.exchange_id)({'enableRateLimit': True})
        symbols = {
            'BTC': {'spot': 'BTC/USDT', 'futures': 'BTC/USDT:USDT'},
            'ETH': {'spot': 'ETH/USDT', 'futures': 'ETH/USDT:USDT'},
            'BNB': {'spot': 'BNB/USDT', 'futures': 'BNB/USDT:USDT'},
            'SOL': {'spot': 'SOL/USDT', 'futures': 'SOL/USDT:USDT'}
        }
        
        if self.exchange_id == 'coinbase':
            symbols = {
                'BTC': {'spot': 'BTC-USD', 'futures': 'BTC-USD'},
                'ETH': {'spot': 'ETH-USD', 'futures': 'ETH-USD'}
            }

        while True:
            try:
                for symbol, prices in symbols.items():
                    spot_symbol = prices['spot']
                    futures_symbol = prices['futures']
                    
                    # 获取现货价格
                    spot_ticker = exchange.fetch_ticker(spot_symbol)
                    self.spot_price[symbol] = spot_ticker['last']

                    # 获取合约价格
                    if self.exchange_id != 'coinbase':
                        futures_ticker = exchange.fetch_ticker(futures_symbol)
                        self.futures_price[symbol] = futures_ticker['last']
                    else:
                        self.futures_price[symbol] = self.spot_price[symbol]

                # 只为币安获取合约持仓量
                if self.exchange_id == 'binance':
                    try:
                        oi = exchange.fapiPublicGetOpenInterest({'symbol': 'BTCUSDT'})
                        self.open_interest = float(oi['openInterest'])
                    except Exception as e:
                        print(f"Error fetching open interest from Binance: {str(e)}")
                        self.open_interest = None
                else:
                    self.open_interest = None

                self.last_update = datetime.now()
            except Exception as e:
                print(f"Error fetching data from {self.exchange_id}: {str(e)}")
                self.spot_price = self.futures_price = self.open_interest = None
            time.sleep(1)  # 每秒更新一次

def format_price(price):
    return f"{price:.2f}" if price is not None else "N/A"

def calculate_difference(spot_price, futures_price):
    if spot_price is None or futures_price is None:
        return "N/A"
    diff = futures_price - spot_price
    return f"{diff:.2f}"

def color_difference(diff):
    if diff == "N/A":
        return diff
    diff_float = float(diff)
    if diff_float > 0:
        return Fore.RED + diff + Style.RESET_ALL
    elif diff_float < 0:
        return Fore.GREEN + diff + Style.RESET_ALL
    else:
        return diff

def save_data_to_file(data):
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f"crypto_data_{today}.csv"
    
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            headers = ['Timestamp', 'Exchange', 'BTC Spot', 'BTC Futures', 'BTC Diff', 'ETH Spot', 'BNB Spot', 'SOL Spot', 'Open Interest', 'Delay']
            writer.writerow(headers)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for row in data:
            # Remove color codes from BTC Diff
            row[3] = row[3].replace(Fore.RED, '').replace(Fore.GREEN, '').replace(Style.RESET_ALL, '')
            writer.writerow([timestamp] + row)

def main():
    exchanges = ['binance', 'okx', 'gateio', 'coinbase']
    threads = [ExchangeThread(exchange) for exchange in exchanges]

    for thread in threads:
        thread.start()

    while True:
        table_data = []
        for thread in threads:
            if thread.last_update:
                delay = (datetime.now() - thread.last_update).total_seconds()
                exchange_data = [thread.exchange_id.capitalize()]
                
                # BTC 显示现货、期货和差价
                btc_spot = format_price(thread.spot_price.get('BTC'))
                btc_futures = format_price(thread.futures_price.get('BTC'))
                btc_diff = calculate_difference(thread.spot_price.get('BTC'), thread.futures_price.get('BTC'))
                btc_colored_diff = color_difference(btc_diff)
                exchange_data.extend([btc_spot, btc_futures, btc_colored_diff])
                
                # ETH, BNB, SOL 只显示现货价格
                for symbol in ['ETH', 'BNB', 'SOL']:
                    spot_price = format_price(thread.spot_price.get(symbol))
                    exchange_data.append(spot_price)
                
                open_interest = f"{thread.open_interest:.2f}" if thread.open_interest is not None else "N/A"
                exchange_data.extend([open_interest, f"{delay:.2f}s"])
                table_data.append(exchange_data)
            else:
                table_data.append([thread.exchange_id.capitalize()] + ['N/A'] * 7)

        headers = ['Exchange', 'BTC Spot', 'BTC Futures', 'BTC Diff', 'ETH Spot', 'BNB Spot', 'SOL Spot', 'Open Interest', 'Delay']

        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(tabulate(table_data, headers=headers, tablefmt='fancy_grid'))
        
        # Save data to file
        save_data_to_file(table_data)
        
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")