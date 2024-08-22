import requests
import threading
from tabulate import tabulate
from datetime import datetime
from colorama import Fore, Style, init
import sys

# 初始化 colorama
init(autoreset=True)

class StockThread(threading.Thread):
    def __init__(self, symbol, name, note=''):
        threading.Thread.__init__(self)
        self.symbol = symbol
        self.name = name
        self.note = note
        self.price = None
        self.change = None
        self.last_update = None

    def run(self):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            self.price = data['chart']['result'][0]['meta']['regularMarketPrice']
            previous_close = data['chart']['result'][0]['meta']['previousClose']
            
            self.change = ((self.price - previous_close) / previous_close) * 100
            self.last_update = datetime.now()
        except Exception as e:
            print(f"Error fetching data for {self.symbol}: {str(e)}")
            self.price = 'N/A'
            self.change = 'N/A'

def color_change(change):
    if isinstance(change, float):
        if change > 0:
            return Fore.GREEN + f"+{change:.2f}%" + Style.RESET_ALL
        elif change < 0:
            return Fore.RED + f"{change:.2f}%" + Style.RESET_ALL
        else:
            return f"{change:.2f}%"
    else:
        return 'N/A'

def main():
    symbols = ['SPY', '^DJI', '^IXIC', 'NVDA', 'AAPL', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'BRK-B', 'JPM', 'DX-Y.NYB']
    names = ['S&P 500 (SPY)', 'Dow Jones', 'NASDAQ', 'NVIDIA', 'Apple', 'Tesla', 'Microsoft', 'Amazon', 'Alphabet', 'Meta', 'Berkshire Hathaway', 'JPMorgan Chase', 'US Dollar Index']
    notes = ['', '', '', '', '', '', '科技巨头', '电商巨头', 'Google母公司', '前Facebook', '沃伦·巴菲特的公司', '大型银行代表', '']
    
    while True:
        threads = [StockThread(symbol, name, note) for symbol, name, note in zip(symbols, names, notes)]
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 收集数据
        data = []
        current_time = datetime.now()
        for thread in threads:
            if thread.last_update:
                delay = (current_time - thread.last_update).total_seconds()
                data.append([
                    f"{thread.name} {Fore.YELLOW}{thread.note}{Style.RESET_ALL}" if thread.note else thread.name,
                    f"{thread.price:.2f}" if isinstance(thread.price, float) else thread.price, 
                    color_change(thread.change),
                    f"{delay:.2f}s"
                ])
            else:
                data.append([f"{thread.name} {Fore.YELLOW}{thread.note}{Style.RESET_ALL}" if thread.note else thread.name, 'N/A', 'N/A', 'N/A'])

        # 打印美化后的输出
        print("\n" + "=" * 80)
        print(Fore.CYAN + Style.BRIGHT + f"Market Update: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (EST)" + Style.RESET_ALL)
        print("=" * 80)
        
        headers = ['Stock/Index', 'Price', 'Change', 'Delay']
        print(tabulate(data, headers=headers, tablefmt='pretty', numalign="right"))
        
        print("=" * 80 + "\n")

        sys.stdout.flush()
        # time.sleep(5)  # 每5秒更新一次，可以根据需要调整

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + "=" * 80)
        print(Fore.YELLOW + "Program terminated by user." + Style.RESET_ALL)
        print("=" * 80 + "\n")