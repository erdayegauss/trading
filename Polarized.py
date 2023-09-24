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

session.auth = ("5oZmOm5bhoo577V_eDyPAqi7bvgsfEud", "YJhSsmyR1sFsrYXHExrYeeNx4mKKPeVn")

class TradingAlgorithm:
    def __init__(self, ws_endpoint="wss://api.hitbtc.com/api/3/ws/public", asset="XRP"):
        self.ws_endpoint = ws_endpoint
        self.asset = asset
        self.buy_init = 0.0
        self.sell_init = 0.0
        self.stride = 0.0
        self.multipule = 5
        self.threshold = 15
        self.buy_grid = 0
        self.sell_grid = 0 
        self.last_post = False
        self.sell_grid_init = 0
        self.buy_grid_init = 0        


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
        # self.incremental = math.floor( float(marginAccount['leverage']) * marginBalance / last_price )

        ####  the self price is set lower than the buy price, so we even have the chance to profits
        if active_posts is None:
            self.stride = last_price * 0.0012             
            self.sell_init = last_price - self.stride
            self.buy_init = last_price + self.stride
            self.sell_grid = 0
            self.buy_grid = 0
            self.sell_grid_init = -1
            self.buy_grid_init = -1

        else:
            price_entry = float(active_posts[0]["price_entry"])
            self.stride = last_price * 0.0012             
            self.sell_init = price_entry - self.stride
            self.buy_init = price_entry + self.stride
            self.sell_grid = max(math.floor((last_price - price_entry) / self.stride)-1, 0)
            self.buy_grid = max(math.floor((last_price - price_entry) / self.stride)-1, 0) 
            self.sell_grid_init = -1
            self.buy_grid_init = -1
        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()
        

    def issueOrder(self, session, side, price, quantity, orderType):

        if orderType == "stop" :
            if side == "sell":
                if quantity < 0:
                    order_data = {
                        'symbol': 'XRPUSDT_PERP',
                        'side': "sell",
                        'time_in_force': 'Day',
                        'quantity': self.multipule,
                        'type': 'takeProfitLimit',
                        'stop_price': price+self.stride*0.75,
                        'price': price + self.stride*1.25
                    }                   
                else :
                    order_data = {
                        'symbol': 'XRPUSDT_PERP',
                        'side': "sell",
                        'quantity': abs(quantity),
                        'type': 'stopMarket',
                        'stop_price': price - self.stride*0.01
                    }
            else :
                if quantity < 0:
                    order_data = {
                        'symbol': 'XRPUSDT_PERP',
                        'side': "buy",
                        'quantity': abs(quantity),
                        'type': 'stopMarket',
                        'stop_price': price + self.stride*0.01
                    }                     
                else :
                    order_data = {
                        'symbol': 'XRPUSDT_PERP',
                        'side': "buy",
                        'time_in_force': 'Day',
                        'quantity': self.multipule,
                        'type': 'takeProfitLimit',
                        'stop_price': price - self.stride*0.75,
                        'price': price - self.stride*1.25
                    }                                                      
        else: 
            order_data = {
                'symbol': 'XRPUSDT_PERP',
                'side': side,
                'time_in_force': 'Day',
                'quantity': self.multipule,
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
                self.last_post = False
            if len(activeOrders) == 0 :            
                if last_price < self.sell_init:
                    self.issueOrder(session, "sell", last_price, self.multipule, "limit")
                elif last_price > self.buy_init:                
                    self.issueOrder(session, "buy", last_price, self.multipule, "limit")
                else:
                    return
            self.last_post = False

        else:

            size_quantity = float(active_posts[0]["quantity"])
            price_entry = float(active_posts[0]["price_entry"])
            price_liquidation = float(active_posts[0]["price_liquidation"])
            if last_price > price_entry:
                grid_tmp = math.floor((last_price - price_entry) / self.stride)

                print("The price_entry, grid_tmp, sell_grid is: ",price_entry, grid_tmp, self.sell_grid)

                if (grid_tmp > self.sell_grid ) :
                    if (len(activeOrders) >= 1):
                        # delete the old order if available
                        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()

                    print("Inside the sell process")
                    # prepare the new order data
                    OrderSide = "sell"
                    OrderPrice = price_entry + grid_tmp*self.stride
                    OrderQuantity = size_quantity
                    
                    # The stopmarket order ensures the order executed
                    self.issueOrder(session, OrderSide, OrderPrice, OrderQuantity, "stop")                        
                    self.sell_grid = max(self.sell_grid, grid_tmp)

                    # reset the buy_grid
                    self.buy_grid = 0                    

            elif last_price < price_entry :
                grid_tmp = math.floor((price_entry - last_price ) / self.stride)

                print("The price_entry, grid_tmp, buy_grid is: ",price_entry, grid_tmp, self.buy_grid)

                if (grid_tmp > self.buy_grid) : 
                    if (len(activeOrders) >= 1):
                        # delete the old order if available
                        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()

                    print("Inside the buy process")
                    # prepare the new order data
                    OrderSide = "buy"
                    OrderPrice = price_entry - grid_tmp*self.stride
                    OrderQuantity = size_quantity

                    self.issueOrder(session, OrderSide, OrderPrice, OrderQuantity, "stop")                      
                    self.buy_grid = max(self.buy_grid, grid_tmp)
                    self.sell_grid = 0
            else :
                return

            self.last_post = True

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
    run_websocket()
    # ws = websocket.WebSocketApp("wss://api.hitbtc.com/api/3/ws/public",
    #                             on_message=on_message,
    #                             on_error=on_error,
    #                             on_close=on_close,
    #                             on_open=on_open)

    # ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port="10900", proxy_type="http")
