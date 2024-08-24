import ccxt
import time
import json
import threading
from queue import Queue
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

# 初始化交易所
exchanges = {
    'binance': ccxt.binance(),
    'coinbase': ccxt.coinbase()
}

# 设置BTC数量阈值
threshold = 0.5

# 用于存储大额订单
large_orders = defaultdict(lambda: {'bids': {}, 'asks': {}})

# 设置时间窗口（例如，保留最近1小时的数据）
TIME_WINDOW = timedelta(hours=1)

# 创建一个队列用于线程间通信
order_queue = Queue()

def create_order_key(price, amount):
    # 使用Decimal来确保精确的浮点数比较
    return f"{Decimal(price):.8f}_{Decimal(amount):.8f}"

def clean_old_orders(orders_dict, current_time):
    for side in ['bids', 'asks']:
        orders_dict[side] = {k: v for k, v in orders_dict[side].items() 
                             if current_time - v['timestamp'] <= TIME_WINDOW}

def fetch_and_write_orders():
    while True:
        current_time = datetime.now()
        for exchange_id, exchange in exchanges.items():
            try:
                order_book = exchange.fetch_order_book('BTC/USDT')
                new_orders = defaultdict(lambda: {'bids': {}, 'asks': {}})
                
                for side in ['bids', 'asks']:
                    for price, amount in order_book[side]:
                        if amount >= threshold:
                            order_key = create_order_key(price, amount)
                            new_orders[exchange_id][side][order_key] = {
                                'price': price,
                                'amount': amount,
                                'timestamp': current_time
                            }
                
                # 更新large_orders，只保留新订单和仍然有效的旧订单
                for side in ['bids', 'asks']:
                    large_orders[exchange_id][side] = {
                        **{k: v for k, v in large_orders[exchange_id][side].items() 
                           if current_time - v['timestamp'] <= TIME_WINDOW},
                        **new_orders[exchange_id][side]
                    }
                
            except Exception as e:
                print(f"获取{exchange_id}数据时出错: {str(e)}")
        
        # 将当前的large_orders放入队列
        order_queue.put(dict(large_orders))
        
        time.sleep(1)  # 每秒拉取一次数据

def analyze_and_output():
    last_output_time = time.time()
    while True:
        if time.time() - last_output_time >= 30:  # 每5秒输出一次结果
            if not order_queue.empty():
                current_orders = order_queue.get()
                save_and_print_results(current_orders)
            last_output_time = time.time()
        time.sleep(0.1)  # 小睡避免CPU占用过高

def save_and_print_results(current_orders):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = {
        "timestamp": timestamp,
        "orders": {}
    }
    
    print(f"\n结果更新时间: {timestamp}")
    
    for exchange_id, orders in current_orders.items():
        results["orders"][exchange_id] = {"买单": [], "卖单": []}
        
        print(f"\n{exchange_id.upper()}:")
        for side, side_cn in [('bids', '买单'), ('asks', '卖单')]:
            if orders[side]:
                total_amount = sum(order['amount'] for order in orders[side].values())
                order_count = len(orders[side])
                print(f"{side_cn}汇总: {order_count}笔, 总量: {total_amount:.4f} BTC")
                
                # 只保存汇总信息到结果中
                results["orders"][exchange_id][side_cn] = {
                    "count": order_count,
                    "total_amount": total_amount
                }
    
    # 将结果保存到文件
    with open('large_orders.json', 'a') as f:
        json.dump(results, f)
        f.write('\n')

if __name__ == "__main__":
    # 创建并启动拉取和写入线程
    fetch_thread = threading.Thread(target=fetch_and_write_orders)
    fetch_thread.daemon = True
    fetch_thread.start()

    # 创建并启动分析和输出线程
    analyze_thread = threading.Thread(target=analyze_and_output)
    analyze_thread.daemon = True
    analyze_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程序正在退出...")