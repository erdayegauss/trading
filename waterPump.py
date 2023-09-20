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
        self.buy_init = 0.0
        self.sell_init = 0.0
        self.stride = 0.0
        self.multipule = 1
        self.threshold = 1
        self.buy_grid = 0
        self.sell_grid = 0 
        self.last_post = False


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

        ####  the self price is set lower than the buy price, so we even have the chance to profits
        if active_posts is None:
            self.stride = last_price * 0.0012             
            self.sell_init = last_price + self.stride*0.5
            self.buy_init = last_price - self.stride*0.5 
            self.sell_grid = 0
            self.buy_grid = 0
        else:
            price_entry = float(active_posts[0]["price_entry"])
            self.stride = last_price * 0.0012             
            self.sell_init = price_entry + self.stride
            self.buy_init = price_entry - self.stride
            self.sell_grid = max(math.floor((last_price - price_entry) / self.stride), 0)
            self.buy_grid = max(math.floor((last_price - price_entry) / self.stride), 0) 
            # self.sell_grid = 0
            # self.buy_grid = 0
        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()

    def issueOrder(self, session, side, price, quantity, orderType):

        if orderType == "takeProfitLimit" :
            if side == "sell": 
                order_data = {
                    'symbol': 'XRPUSDT_PERP',
                    'side': "sell",
                    'time_in_force': 'Day',
                    'quantity': quantity,
                    'price': price ,
                    'type': 'takeProfitLimit',
                    'stop_price': price * 1.0003
                }
            else: 
               order_data = {
                    'symbol': 'XRPUSDT_PERP',
                    'side': "buy",
                    'time_in_force': 'Day',
                    'quantity': quantity,
                    'price': price ,
                    'type': 'takeProfitLimit',
                    'stop_price': price * 0.9999
                }                
        else: 
            order_data = {
                'symbol': 'XRPUSDT_PERP',
                'side': side,
                'time_in_force': 'Day',
                'quantity': quantity,
                'price': price ,
                'type': 'limit'
            }            
        #  issue the new order 
        response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
        print("============ The order created: ===========\n")
        print(response)     


    def updateOrder(self, session, last_price):

        active_posts = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()['positions']
        activeOrders = session.get('https://api.hitbtc.com/api/3/futures/order').json()

        if active_posts is None : 
            if self.last_post == True:
                self.start(session) 
            if len(activeOrders) == 0 :            
                if last_price >= self.sell_init:
                    print("we will sell one")
                    self.issueOrder(session, "sell", last_price, self.multipule, "limit")
                elif last_price <= self.buy_init:                
                    print("we will buy one")
                    self.issueOrder(session, "buy", last_price, self.multipule, "limit")
                else:
                    return

        else:

            self.last_post = True
            size_quantity = abs(float(active_posts[0]["quantity"]))
            price_entry = float(active_posts[0]["price_entry"])
            price_liquidation = float(active_posts[0]["price_liquidation"])
            grid_tmp = abs(math.floor((last_price - price_entry) / self.stride))
            if last_price > price_entry:

                # delete the old order if available
                if (len(activeOrders) >= 1) and ((price_entry + grid_tmp*self.stride) > activeOrders[0]['price']) : 
                    #  first delte the old order if order available
                    r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()

                print("The grid_tmp and sell_grid is: ", grid_tmp, self.sell_grid)

                if (last_price > (price_entry + (self.sell_grid + 0.5)*self.stride) ) :

                    print("Inside the sell process")
                    # prepare the new order data
                    OrderSide = "sell"
                    OrderPrice = price_entry + grid_tmp*self.stride
                    OrderQuantity = size_quantity

                    self.issueOrder(session, OrderSide, OrderPrice, OrderQuantity, "takeProfitLimit")                        
                    self.sell_grid = grid_tmp                  

            elif last_price < price_entry :

                # delete the old order if available
                if (len(activeOrders) >= 1) and ((price_entry - grid_tmp*self.stride) < activeOrders[0]['price']) :  
                    #  first delte the old order if available
                    r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json() 

                print("The grid_tmp and sell_grid is: ", grid_tmp, self.sell_grid)

                if (last_price < (price_entry - (self.sell_grid + 0.5)*self.stride)) :               
                    print("Inside the buy process")


                    # prepare the new order data
                    OrderSide = "buy"
                    OrderPrice = price_entry - grid_tmp*self.stride
                    OrderQuantity = size_quantity

                    self.issueOrder(session, OrderSide, OrderPrice, OrderQuantity, "takeProfitLimit")                      
                    self.buy_grid = grid_tmp
            else :
                return

def on_message(ws, message):
    data = json.loads(message)
    
    # Use the trading algorithm instance to access methods and data
    last_price = trading_algo.get_last_price(session)
    tick_data = data["data"]["XRPUSDT_PERP"]
    print("The XRP ticker ask bid, last, sell buy prices, buy sell counts are:", tick_data["a"], tick_data["b"], last_price, trading_algo.sell_init,trading_algo.buy_init, trading_algo.buy_grid, trading_algo.sell_grid)
    
    # Call the create_orders method from the trading algorithm
    trading_algo.updateOrder(session, last_price)

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
    # run_websocket()
    ws = websocket.WebSocketApp("wss://api.hitbtc.com/api/3/ws/public",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                on_open=on_open)

    ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port="10900", proxy_type="http")