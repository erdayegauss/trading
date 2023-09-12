from websocket import create_connection
import websocket
import json
from hashlib import sha256
from hmac import HMAC
import time
import requests
import math

session = requests.session()
session.proxies = {
    'http': 'http://127.0.0.1:10900',
    'https': 'http://127.0.0.1:10900',
}
session.auth = ("ZTTen-xc8YAxDydaWNgXI6QzJt89ah0I", "lPsul5B7dUF82QwUkRTAsf0rlHm4cxE9")
ws_endpoint = "wss://api.hitbtc.com/api/3/ws/public"
asset = "XRP"

buy_price_prev = 0.0  # Initialize the previous price as None
sell_price_prev = 0.0
stride = 0.0  # Initial stride value
buy_count=1
sell_count=1




multipule = 2 

##### after liquidation, just fewer leverage, let's just stick to the  algorithm, and wait for future result.




def orderSize(buy_count):
    return max(math.floor(buy_count / 2) + 1, 1)

def accumulate_Order(N):
    x_accumulated = 0
    for i in range(1, N + 1):
        x_accumulated += orderSize(i)
    return x_accumulated


def orderCounts(x):
    N = 1
    while True:
        accumulated_x = accumulate_Order(N)
        if accumulated_x >= x:
            return N
        N += 1


def start(session):
    global sell_price_prev,buy_price_prev, buy_count, sell_count, stride, multipule # Declare the variable as global

    price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
    last_price = float(price_query["XRPUSDT_PERP"]["last"])


    
# The stride: 0.0012 of the last price 
# the stride geometrically increasing, 0.0012*1.3^n
# n up to 6, the result is (1.3^7 -1)/(1.3-1) *0.0012 = 0.021


    marginAccount = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()
    
    active_posts = marginAccount['positions']
    marginBalance = float(marginAccount['currencies'][0]['margin_balance'])


    multipule = math.floor( marginBalance/0.5 ) +1



    if  active_posts == None :

        stride = last_price * 0.0012
        sell_price_prev =  last_price + stride
        buy_price_prev =  last_price - stride
        buy_count = 1 
        sell_count = 1

    else :
        size_quantity = abs(float(active_posts[0]["quantity"])) 
        price_entry = float(active_posts[0]["price_entry"])
    
        stride = last_price * 0.0012 * 1.3**(orderCounts(size_quantity))
        sell_price_prev =  price_entry + stride
        buy_price_prev =  price_entry - stride
        buy_count = orderCounts(size_quantity/multipule) + 1 
        sell_count = orderCounts(size_quantity/multipule) + 1


    r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()



   

def updateOrder(session, asset, side, price, quantity):
    global buy_count, sell_count, sell_price_prev, buy_price_prev, stride

    order_data = {
        'symbol': f'{asset}USDT_PERP',
        'side': side,
        'time_in_force': 'Day',
        'quantity': quantity,
        'price': price,
        'type': 'limit'
    }

    response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()

    print("============ The order created: ===========\n")
    print(response)

# update the buy_price_prev and sell_price_prev
    if side == "buy" :
        buy_price_prev = price - stride
        buy_count = buy_count + 1
        stride = stride * 1.3
    elif side == "sell" :
        sell_price_prev = price + stride
        sell_count = sell_count + 1
        stride = stride * 1.3
    return response


def create_orders(session, asset, last_price):

    active_posts = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()['positions']


    if  active_posts == None :
        if (last_price <= buy_price_prev) :
            updateOrder(session, asset,"buy", last_price, multipule)
        elif (last_price >= sell_price_prev) :
            updateOrder(session, asset,"sell", last_price, multipule)
        else :
            return

    else :
        size_quantity = float(active_posts[0]["quantity"])   
        price_entry = float(active_posts[0]["price_entry"])
        price_liquidation = float(active_posts[0]["price_liquidation"])

        if ( price_entry > price_liquidation ) :
            if (last_price > price_entry) :
                if (( last_price - price_entry)/ price_entry >= 0.005) :
                    delete = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP', json={"price": last_price }).json()
                    start(session)
                    return
                else:
                    return
                   
            else :
                if last_price <= min(buy_price_prev,(price_entry*0.999)) and ( size_quantity < 15.0*multipule ) :
                    buy = updateOrder(session, asset, "buy", last_price, orderSize(buy_count)*multipule )
                    return buy
                else :
                    return


        elif ( price_entry < price_liquidation ) :
            if (last_price < price_entry) :
                if (( price_entry - last_price)/ last_price >= 0.005) :
                    delete = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP', json={"price": last_price }).json()                   
                    start(session)
                    return
                else:
                    return
            else :
                if last_price >= max(sell_price_prev,(price_entry*1.001)) and ( size_quantity < 15.0*multipule ) :
                    sell = updateOrder(session, asset, "sell", last_price,  orderSize(sell_count)*multipule )
                    return sell
                else :
                    return
        

def on_message(ws, message):
    data = json.loads(message)
    
    price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
    last_price = float(price_query["XRPUSDT_PERP"]["last"])

    # Process the data and define your custom logic
    tick_data = data["data"]["XRPUSDT_PERP"]
    print("The XRP ticker ask bid, last, sell buy prices, buy sell counts are:", tick_data["a"], tick_data["b"], last_price,sell_price_prev, buy_price_prev,buy_count, sell_count)
    buy_bid_price = float(tick_data["b"])
    sell_ask_price = float(tick_data["a"])
    # put long short positions pair
    create_order=create_orders(session, asset, last_price)

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Closed:", close_status_code, close_msg)

def on_open(ws):
    start(session)
    print("Subscribe to the XRPUSDT ticker data")
    ws.send('{"method": "subscribe", "ch": "ticker/3s", "params": {"symbols": ["XRPUSDT_PERP"]}}, "id": 13579')


def run_websocket():  # 86400 seconds in a day

    while True:
        try:
            ws = websocket.WebSocketApp(ws_endpoint,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close,
                                        on_open=on_open)

            ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port="10900", proxy_type="http")


        except Exception as e:
            print(f"WebSocket connection error: {e}")
            print("Attempting to reconnect in 5 seconds...")
            time.sleep(5)

    print("WebSocket connection will not attempt to reconnect after one day.")




if __name__ == "__main__":
    # run_websocket()
    run_websocket()

    # timestamp = time.time()
    # api_key = ""
    # secret = ""
    # window = 10000
    # message = str(timestamp)
    # websocket.enableTrace(False)

    # ws = websocket.WebSocketApp("wss://api.hitbtc.com/api/3/ws/public",
    #                             on_message=on_message,
    #                             on_error=on_error,
    #                             on_close=on_close,
    #                             on_open=on_open)

    # # ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port="10900", proxy_type="http")
    # ws.run_forever()
