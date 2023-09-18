import math


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



# The comparison between linear and exponential 
# Linear result: 
# each step result: 1 0.00156 0.00156 2
# each step result: 2 0.003588 0.002912 4
# each step result: 3 0.0062244 0.00423696 4
# each step result: 4 0.009651719999999999 0.006267495 6
# each step result: 5 0.014107235999999999 0.008405606181818182 6
# each step result: 6 0.019899406799999998 0.011470619679999999 8
# each step result: 7 0.02742922884 0.014830326871578947 8
# each step result: 8 0.037217997492 0.0194944249175 10
# each step result: 9 0.0499433967396 0.02474424764544828 10

# exponential 1.8 result: 
# each step result: 1 0.00156 0.00156 1
# each step result: 2 0.003588 0.002912 2
# each step result: 3 0.0062244 0.0045682000000000006 3
# each step result: 4 0.009651719999999999 0.00687889090909091 5
# each step result: 5 0.014107235999999999 0.009922404631578946 8
# each step result: 6 0.019899406799999998 0.014155072218181818 14
# each step result: 7 0.02742922884 0.019876691451724136 25

    def orderSize(self, buy_count):
        if buy_count < 8 :
            return max(math.floor(math.floor(1.8**buy_count/2.5)+1),1)
        else :
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

        r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP")


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
        print("============ The order created at ",session.ticker_simulator.current_ticker['time'],price)
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
                        delete = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP').json()
                        
                        print("\n///////////////////////////////////////////////\n")
                        print("//// take profits at the prices of:", last_price)
                        print("\n///////////////////////////////////////////////\n")

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

                        print("\n///////////////////////////////////////////////\n")
                        print("//// take profits at the prices of:", last_price)
                        print("\n///////////////////////////////////////////////\n")

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



class TrapAlgorithm:
    def __init__(self, ws_endpoint="wss://api.hitbtc.com/api/3/ws/public", asset="XRP"):
        self.ws_endpoint = ws_endpoint
        self.asset = asset
        self.buy_init = 0.0
        self.sell_init = 0.0
        self.stride = 0.0005
        self.buy_count = 0
        self.sell_count = 0
        self.multipule = 10
        self.threshold = 50


    def trap(self, session, last_price):
        active_posts = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()['positions']

        if active_posts is None:
            if last_price <= self.sell_init:
                order_data = {
                    'symbol': 'XRPUSDT_PERP',
                    'side': 'sell',
                    'time_in_force': 'Day',
                    'quantity': self.multipule,
                    'price': self.sell_init,
                    'type': 'limit'
                }                
                self.issueOrder(session, order_data)     

            elif last_price >= self.buy_init:
                order_data = {
                    'symbol': 'XRPUSDT_PERP',
                    'side': 'buy',
                    'time_in_force': 'Day',
                    'quantity': self.multipule,
                    'price': self.buy_init,
                    'type': 'limit'
                }
                self.issueOrder(session, order_data) 

            else:
                return
        else:
            price_entry = float(active_posts[0]["price_entry"])
            size_quantity = abs(float(active_posts[0]["quantity"]))


            # create order based on the price difference grid
            if size_quantity > 0 :                 
                if (math.floor((last_price - price_entry)/self.stride)) > self.buy_count :
                    grid_price= price_entry + self.buy_count * self.stride 
                    side = "sell"
                    order_data = {
                        'symbol': 'XRPUSDT_PERP',
                        'side': side,
                        'time_in_force': 'Day',
                        'quantity': size_quantity,
                        'price': grid_price,
                        'type': 'stopLimit',
                        'stop_price': grid_price * 1.0002
                    }
                    
                    self.issueOrder(session, order_data)                                                      
                    self.buy_count = max(self.buy_count, math.floor((last_price - price_entry)/self.stride))
                    print("current price and buy_count", price_entry, last_price, self.buy_count, grid_price )
                elif   (self.buy_count >=3 and  (self.buy_count -1) <= (math.floor((last_price - price_entry)/self.stride)) and  (math.floor((last_price - price_entry)/self.stride)) <= self.buy_count) :
                    deletePosition = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP').json()
                    deleteOrder = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP")
                else:
                    return

            elif size_quantity < 0 :
                if (math.floor((price_entry - last_price)/self.stride)) > self.sell_count :
                    grid_price= price_entry - self.sell_count * self.stride 
                    side = "buy"
                    order_data = {
                        'symbol': 'XRPUSDT_PERP',
                        'side': side,
                        'time_in_force': 'Day',
                        'quantity': math.abs(size_quantity),
                        'price': grid_price,
                        'type': 'stopLimit',
                        'stop_price': grid_price * 0.9998
                    }

                    self.issueOrder(session, order_data)                    
                    self.sell_count = max(self.sell_count, math.floor((price_entry - last_price)/self.stride)) 
                    print("current price and buy_count",price_entry, last_price, self.sell_count, grid_price )
                elif (self.sell_count >=3 and (self.sell_count -1) <= (math.floor((price_entry - last_price)/self.stride)) and (math.floor((price_entry - last_price)/self.stride)) <= self.sell_count) :
                    deletePosition = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP').json()                    
                    deleteOrder = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP")
                    return



    def issueOrder(self, session, order_data):
        response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
        print(response)



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
            self.buy_init = last_price + self.stride
            self.sell_init = last_price - self.stride
            self.buy_count = 1
            self.sell_count = 1
        else:

            deletePosition = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP').json()
            print("Cancel all the position at the price of:", last_price)
            deleteOrder = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()
            print("Cancel all the orders, restart the positions" )

        return