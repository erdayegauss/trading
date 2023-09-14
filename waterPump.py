from websocket import create_connection
import websocket
import json
import time
import requests
import math

session = requests.session()
session.proxies = {
    'http': 'http://127.0.0.1:10900',
    'https': 'http://127.0.0.1:10900',
}

session.auth = ("ZTTen-xc8YAxDydaWNgXI6QzJt89ah0I", "lPsul5B7dUF82QwUkRTAsf0rlHm4cxE9")

class TradingAlgorithm:
    def __init__(self, ws_endpoint="wss://api.hitbtc.com/api/3/ws/public", asset="XRP"):
        self.ws_endpoint = ws_endpoint
        self.asset = asset
        self.buy_price_prev = 0.0
        self.sell_price_prev = 0.0
        self.stride = 0.0
        self.buy_count = 1
        self.sell_count = 1
        self.multipule = 2
        self.threshold = 50

# base = 1.8
# def orderSize1(buy_count):
#     return max(math.floor(math.floor(1.8**buy_count/2.5)+1),1)


# def accumulate_Order1(N):
#     x_accumulated = 0
#     for i in range(1, N + 1):
#         x_accumulated += orderSize1(i)
#     return x_accumulated

# def orderCounts1(x):
#     N = 1
#     while True:
#         accumulated_x = accumulate_Order1(N)
#         if accumulated_x >= x:
#             return N
#         N += 1


    def orderSize(self, buy_count):
        return max(math.floor(buy_count / 2) + 1, 1)

    def accumulate_Order(self, N):
        x_accumulated = 0
        for i in range(1, N + 1):
            x_accumulated += self.orderSize(i)
        return x_accumulated

    def orderCounts(self, x):
        N = 1
        while True:
            accumulated_x = self.accumulate_Order(N)
            if accumulated_x >= x:
                return N
            N += 1

    def get_last_price(self, session):

        price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        last_price = float(price_query["XRPUSDT_PERP"]["last"])
        return last_price

    def start(self, session):
        price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        last_price = float(price_query["XRPUSDT_PERP"]["last"])

        marginAccount = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()
        active_posts = marginAccount['positions']
        marginBalance = float(marginAccount['currencies'][0]['margin_balance'])
        # self.multipule = math.floor(marginBalance / 0.5) + 1
        # self.threshold = math.floor( float(marginAccount['leverage']) * marginBalance / last_price )

        if active_posts is None:
            self.stride = last_price * 0.0012
            self.sell_price_prev = last_price + self.stride
            self.buy_price_prev = last_price - self.stride
            self.buy_count = 1
            self.sell_count = 1
        else:
            size_quantity = abs(float(active_posts[0]["quantity"]))
            price_entry = float(active_posts[0]["price_entry"])

            self.stride = last_price * 0.0012 * 1.3 ** (self.orderCounts(size_quantity))
            self.sell_price_prev = price_entry + self.stride
            self.buy_price_prev = price_entry - self.stride
            self.buy_count = self.orderCounts(size_quantity / self.multipule) + 1
            self.sell_count = self.orderCounts(size_quantity / self.multipule) + 1

        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()

    def updateOrder(self, session, side, price, quantity):
        order_data = {
            'symbol': 'XRPUSDT_PERP',
            'side': side,
            'time_in_force': 'Day',
            'quantity': quantity,
            'price': price,
            'type': 'limit'
        }

        response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
        print("============ The order created: ===========\n")
        print(response)

        if side == "buy":
            self.buy_price_prev = price - self.stride
            self.buy_count += 1
            self.stride *= 1.3
        elif side == "sell":
            self.sell_price_prev = price + self.stride
            self.sell_count += 1
            self.stride *= 1.3
        return response

    def create_orders(self, session, last_price):
        active_posts = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()['positions']

        if active_posts is None:
            if last_price <= self.buy_price_prev:
                self.updateOrder(session, "buy", last_price, self.multipule)
            elif last_price >= self.sell_price_prev:
                self.updateOrder(session, "sell", last_price, self.multipule)
            else:
                return
        else:
            size_quantity = float(active_posts[0]["quantity"])
            price_entry = float(active_posts[0]["price_entry"])
            price_liquidation = float(active_posts[0]["price_liquidation"])

            if price_entry > price_liquidation:
                if last_price > price_entry:
                    if (last_price - price_entry) / price_entry >= 0.005:
                        delete = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP',
                                                json={"price": last_price}).json()
                        self.start(session)
                        return
                    else:
                        return
                else:
                    if last_price <= min(self.buy_price_prev, (price_entry * 0.999)) and (size_quantity < self.threshold):
                        buy = self.updateOrder(session, "buy", last_price, self.orderSize(self.buy_count) * self.multipule)
                        return buy
                    else:
                        return
            elif price_entry < price_liquidation:
                if last_price < price_entry:
                    if (price_entry - last_price) / last_price >= 0.005:
                        delete = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP',
                                                json={"price": last_price}).json()
                        self.start(session)
                        return
                    else:
                        return
                else:
                    if last_price >= max(self.sell_price_prev, (price_entry * 1.001)) and (size_quantity < self.threshold):
                        sell = self.updateOrder(session, "sell", last_price, self.orderSize(self.sell_count) * self.multipule)
                        return sell
                    else:
                        return

def on_message(ws, message):
    data = json.loads(message)
    
    # Use the trading algorithm instance to access methods and data
    last_price = trading_algo.get_last_price(session)
    tick_data = data["data"]["XRPUSDT_PERP"]
    print("The XRP ticker ask bid, last, sell buy prices, buy sell counts are:", tick_data["a"], tick_data["b"], last_price, trading_algo.sell_price_prev, trading_algo.buy_price_prev, trading_algo.buy_count, trading_algo.sell_count)
    
    # Call the create_orders method from the trading algorithm
    trading_algo.create_orders(session, last_price)

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Closed:", close_status_code, close_msg)

def on_open(ws):
    trading_algo.start(session)
    print("Subscribe to the XRPUSDT ticker data")
    ws.send('{"method": "subscribe", "ch": "ticker/3s", "params": {"symbols": ["XRPUSDT_PERP"]}}, "id": 13579")')

def run_websocket():
    while True:
        try:
            ws = websocket.WebSocketApp(trading_algo.ws_endpoint,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close,
                                        on_open=on_open)
            ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port="10900", proxy_type="http")

        except Exception as e:
            print("WebSocket connection error: ", {e})
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)
    print("WebSocket connection will not attempt to reconnect after one day.")

if __name__ == "__main__":
    trading_algo = TradingAlgorithm()  # Create an instance of the TradingAlgorithm class
    run_websocket()
