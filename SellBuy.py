from websocket import create_connection
import websocket
import json
import time
import requests
import math
import string
import secrets


session = requests.session()
session.proxies = {
    'http': 'http://127.0.0.1:10900',
    'https': 'http://127.0.0.1:10900',
}

session.auth = ("ZTTen-xc8YAxDydaWNgXI6QzJt89ah0I", "lPsul5B7dUF82QwUkRTAsf0rlHm4cxE9")
# session.auth = ()

class TradingAlgorithmSellBuy:
    def __init__(self, ws_endpoint="wss://api.hitbtc.com/api/3/ws/public", asset="XRP"):
        self.ws_endpoint = ws_endpoint
        self.asset = asset
        self.stride = 0.0
        self.multipule = 4
        self.last_post = False
        self.sell_order_price = 0
        self.buy_order_price = 0        
        self.sell_order_id = ""
        self.buy_order_id = ""

    def get_last_price(self, session):

        price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        last_price = float(price_query["XRPUSDT_PERP"]["last"])
        return last_price

    def generate_hash(self, input_string):
        characters = string.ascii_letters + string.digits
        random_string = ''.join(secrets.choice(characters) for _ in range(16))
        return random_string

    def find_grid_number(self, sum, stride):
        if stride <= 0 or sum <= 0:
            raise ValueError("Invalid inputs. Ensure q and price are greater than 0.")
        grid_sum = 0.0
        grid_number = 0
        while grid_sum < sum:
            grid_number += 1
            grid_sum += self.stride*1.3**grid_number
        return grid_number



    def grid_caculator (self, last_price, price_entry):
        # This is loss function caculator, if the last_price larger than the price_entry, sell; other wise, buy
        grid_mumber = self.find_grid_number( abs(last_price - price_entry), self.stride)

        if last_price > price_entry:
            grid_price = price_entry + (self.stride)*((1.3)**(grid_mumber+1) -1 )/ (1.3 - 1)
            print("caculate the remedy price and grid number:", grid_price, grid_mumber)
            return grid_price, grid_number

        else: 
            grid_price = price_entry - (self.stride)*((1.3)**(grid_mumber+1) -1 )/ (1.3 - 1)
            print("caculate the remedy price and number2:", grid_price, grid_mumber)
            return grid_price, grid_number

    
    


    def check_order_exists(self, session, order_id):
        # Construct the URL for querying the order by its ID
        url = 'https://api.hitbtc.com/api/3/futures/order/'+str(order_id)

        # Send a GET request to the API
        response = session.get(url).json()

        # Check if the response contains an "id" field to determine if the order exists
        if 'client_order_id' in response:
            return True
        else:
            return False

    def start(self, session): 
        ####  the self price is set lower than the buy price, so we even have the chance to profits
        price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        last_price = float(price_query["XRPUSDT_PERP"]["last"])
        activeOrders = session.get('https://api.hitbtc.com/api/3/futures/order').json()
        
        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()
        self.stride = last_price * 0.0008    
         
        self.sell_order_price = last_price + self.stride*1.25
        self.buy_order_price = last_price - self.stride*1.25 
        self.sell_order_id = self.generate_hash("buy")
        self.buy_order_id = self.generate_hash("sell")
        # priceTmp = 0.0
        # if (len(activeOrders) >0):
        #     for orderEle in activeOrders: 
        #         if (orderEle["side"] == "buy"):
        #             if ((orderEle["price"] + self.stride*1.25) < self.buy_order_id) :
        #                 self.buy_order_price = orderEle["price"] + self.stride*1.25
        #                 self.buy_order_id = orderEle["client_order_id"]
        #         else :
        #             if ((orderEle["price"] - self.stride*1.25) > self.buy_order_id) :
        #                 self.sell_order_price = orderEle["price"]  - self.stride*1.25
        #                 self.sell_order_id = orderEle["client_order_id"]                    
        print("The init params are:",self.stride,self.sell_order_price, self.buy_order_price,  self.sell_order_id,self.buy_order_id)

        

    def issueOrder(self, session, side, price, quantity, orderType):

        # the inside for, position already, need to take profit, use stopMarket lock the profits
        # the start is initialization, use takeprofit limit to make it hard to settle on the position easy, risk protection
        # the delete is the 

        if orderType == 'inside' :
            if side == 'buy' :
                new_buy_order_id = self.generate_hash("buy")
                order_data = {
                    'client_order_id': new_buy_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': side,
                    'quantity': quantity,
                    'type': 'stopMarket',
                    'stop_price': self.buy_order_price
                }
                self.buy_order_id = new_buy_order_id
            else : 
                new_sell_order_id = self.generate_hash("sell")                
                order_data = {
                    'client_order_id': new_sell_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': side,
                    'quantity': quantity,
                    'type': 'stopMarket',
                    'stop_price': self.sell_order_price
                }
                self.sell_order_id = new_sell_order_id
            #  issue the new order 
            response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()


        elif orderType == 'start' :
            if side == 'buy' :
                new_buy_order_id = self.generate_hash("buy")
                order_data = {
                    'client_order_id': new_buy_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': side,
                    'quantity': quantity,
                    'type': 'takeProfitLimit',
                    'stop_price': price - self.stride*0.75,
                    'price': price - self.stride*1.25
                }
                self.buy_order_id = new_buy_order_id
            else : 
                new_sell_order_id = self.generate_hash("sell")                
                order_data = {
                    'client_order_id': new_sell_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': side,
                    'quantity': quantity,
                    'type': 'takeProfitLimit',
                    'stop_price': price+self.stride*0.75,
                    'price': price + self.stride*1.25                    
                }
                self.sell_order_id = new_sell_order_id
            #  issue the new order 
            response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
   
        elif orderType == 'replace': 
            if side == 'sell':
                new_sell_order_id = self.generate_hash("sell")
                order_Data_sell = {
                    'quantity': quantity, 
                    'price': price, 
                    'new_client_order_id': new_sell_order_id
                    }
                response = session.patch('https://api.hitbtc.com/api/3/futures/order/'+str(self.sell_order_id), data = order_Data_sell).json()
                self.sell_order_id = new_sell_order_id
            else:
                new_buy_order_id = self.generate_hash("buy")
                order_Data_buy = {
                    'quantity': quantity, 
                    'price': price, 
                    'new_client_order_id': new_buy_order_id
                    }
                response = session.patch('https://api.hitbtc.com/api/3/futures/order/'+str(self.buy_order_id), data = order_Data_buy).json()
                self.buy_order_id = new_buy_order_id

        elif orderType == 'delete': 
            if side == 'sell':
                orderid = str(self.sell_order_id)
            else:
                orderid = str(self.buy_order_id)
            response = session.delete('https://api.hitbtc.com/api/3/futures/order/'+orderid).json()
        else:
            return 
        #  print the order result
        print("============ The order created: ===========\n")
        print(response)  



    def updateOrder(self, session, last_price):

        active_posts = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()['positions']
        # activeOrders = session.get('https://api.hitbtc.com/api/3/futures/order').json()
        # print("The last_price,sell_order_price are : ",last_price, self.sell_order_price,self.buy_order_price)

        if active_posts is None : 
        # if (True): 
            if self.last_post == True:
                self.start(session) 
                self.last_post = False
                return

            if ((last_price - self.sell_order_price) > self.stride)  :
                self.sell_order_price = self.stride * math.floor(last_price/self.stride )
                print("The last_price,sell_order_price are : ",last_price, self.sell_order_price)
                if ((self.check_order_exists(session, self.sell_order_id))):
                    print("update sell init order")
                    self.issueOrder(session, 'sell', self.sell_order_price, self.multipule, 'delete')
                    self.issueOrder(session, 'sell', self.sell_order_price, self.multipule, 'start')
                else:
                    print("init sell order")
                    self.issueOrder(session, 'sell', self.sell_order_price, self.multipule, 'start')

            if ((self.buy_order_price - last_price) > self.stride) :
                self.buy_order_price = self.stride * (math.floor(last_price/self.stride) + 1)
                print("The last_price, buy_order_price are : ",last_price, self.buy_order_price)
                if ((self.check_order_exists(session, self.buy_order_id))):
                    print("update buy init order")                    
                    self.issueOrder(session, 'buy', self.buy_order_price, self.multipule, 'delete')
                    self.issueOrder(session, 'buy', self.buy_order_price, self.multipule, 'start')
                else:
                    print("init buy order")
                    self.issueOrder(session, 'buy', self.buy_order_price, self.multipule, 'start')

            self.last_post = False
        else:
            # print("Position is ready")
            size_quantity = float(active_posts[0]["quantity"])
            price_entry = float(active_posts[0]["price_entry"])
            price_liquidation = float(active_posts[0]["price_liquidation"])

            if self.last_post == False:
                responseDelete = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()
                print("Clean up the legacy orders",responseDelete)
                self.sell_order_price = price_entry + 0.5*self.stride
                self.buy_order_price = price_entry - 0.5*self.stride
                self.last_post = True



            if (size_quantity > 0) :
                #  this is the profits process
                if ((last_price - self.sell_order_price) > self.stride)  or (last_price - price_entry) > self.stride :
                    self.sell_order_price = self.stride * math.floor(last_price/self.stride )                                            
                    if (self.check_order_exists(session, self.sell_order_id)): 
                        print("update  sell order, last_price,sell_order_price : ",last_price, self.sell_order_price)                    
                        self.issueOrder(session, 'sell', self.sell_order_price, size_quantity, 'replace')
                    else:
                        self.issueOrder(session, 'sell', self.sell_order_price, size_quantity, 'inside')  
                # the loss action 
                elif (last_price < price_entry) :  

                    print("In loss mode")
                    loss_price, loss_quanity = self.grid_caculator(last_price, price_entry)
                    self.issueOrder(session, 'buy', loss_price, loss_quanity, 'start')
                else: 
                    return
                    
                    
                    

            else:
                if ((self.buy_order_price - last_price) > self.stride) or (price_entry - last_price) > self.stride:
                    self.buy_order_price = self.stride * (math.floor(last_price/self.stride) + 1)
                    if (self.check_order_exists(session, self.buy_order_id)):
                        print("update  buy order, last_price,sell_order_price : ",last_price, self.sell_order_price)                    
                        self.issueOrder(session, 'buy', self.buy_order_price, abs(size_quantity), 'replace')
                    else:
                        self.issueOrder(session, 'buy', self.buy_order_price, abs(size_quantity), 'inside')
                elif (last_price > price_entry) :
                    loss_price, loss_quanity = self.grid_caculator(last_price, price_entry)
                    self.issueOrder(session, 'sell', loss_price, loss_quanity, 'start')
                else: 
                    return
            self.last_post = True

def on_message(ws, message):
    data = json.loads(message)
    
    # Use the trading algorithm instance to access methods and data
    last_price = trading_algo.get_last_price(session)
    tick_data = data["data"]["XRPUSDT_PERP"]
    print("The XRP ticker ask bid last prices, sell buy order prices, IDs:", tick_data["a"], tick_data["b"], last_price, trading_algo.sell_order_price,trading_algo.buy_order_price, trading_algo.buy_order_id, trading_algo.sell_order_id)
    
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
    trading_algo = TradingAlgorithmSellBuy()  # Create an instance of the TradingAlgorithm class
    run_websocket()
    # ws = websocket.WebSocketApp("wss://api.hitbtc.com/api/3/ws/public",
    #                             on_message=on_message,
    #                             on_error=on_error,
    #                             on_close=on_close,
    #                             on_open=on_open)

    # ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port="10900", proxy_type="http")