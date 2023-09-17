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
        print("============ The order created at ",session.ticker_simulator.current_ticker['time'],session.position.price_entry)
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
                        print("take profits at the prices of:", last_price)
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
                        print("take profits at the price of:", last_price)
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
        self.buy_price_prev = 0.0
        self.sell_price_prev = 0.0
        self.stride = 0.0005
        self.buy_count = 1
        self.sell_count = 1
        self.multipule = 2
        self.threshold = 50
        self.last_price = 0.0
        self.grid = 0


    def trap(self, session, price):
        active_posts = session       
        price_entry = active_posts[0].price_entry
        quantity = active_posts[0].quantity
    
        self.grid = math.floor((price - price_entry)/self.stride)

        # create order based on that
        if (abs(math.floor((price - price_entry)/self.stride))  > abs(self.grid)) :

            grid_price= price_entry + self.grid * self.stride 

            order_data = {
                'symbol': 'XRPUSDT_PERP',
                'side': "buy",
                'time_in_force': 'Day',
                'quantity': -quantity,
                'price': grid_price,
                'type': 'stopLimit',
                'stop_price': grid_price * 1.0002
            }
            self.grid = math.floor((price - price_entry)/self.stride)

            # response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
            # print("============ The order created: ===========\n")
            # print(response)

            # Create an Order object
            order = Order(order_data)
            order.fill_order(session[0])
            print("============ The order created: ===========\n")
            print(order_data)

            timespot = date_obj = datetime.datetime.fromtimestamp(timestamps[index] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            print("the position info:",  timespot, session[0].price_entry, session[0].quantity )


        
    def start(self, session):

        # price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        # last_price = float(price_query["XRPUSDT_PERP"]["last"])

        # marginAccount = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()
        # active_posts = marginAccount['positions']
        # marginBalance = float(marginAccount['currencies'][0]['margin_balance'])
        # # self.multipule = math.floor(marginBalance / 0.5) + 1
        # # self.threshold = math.floor( float(marginAccount['leverage']) * marginBalance / last_price )

        ######### For test #########
        active_posts = session       


        # if active_posts is None:
        ######### For test ######### 
        if len(active_posts) == 0:
            self.sell_price_prev = last_price + self.stride
            self.buy_price_prev = last_price - self.stride


        else:

            # size_quantity = abs(float(active_posts[0]["quantity"]))
            # price_entry = float(active_posts[0]["price_entry"])

        ######### For test ######### 
            size_quantity = abs(float(active_posts[0].quantity))
            price_entry = float(active_posts[0].price_entry)


        # r = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()

    def updateOrder(self, session,side, price, quantity,index):
        # here is the preparition before the order process

        order_data = {
            'symbol': 'XRPUSDT_PERP',
            'side': side,
            'time_in_force': 'Day',
            'quantity': quantity,
            'price': price,
            'type': 'limit'
        }

        # response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
        # print("============ The order created: ===========\n")
        # print(response)

        ######### For test ######### 
        if len(active_posts) == 0:
            session.append(Position())

        # Create an Order object
        order = Order(order_data)
        order.fill_order(session[0])
        print("============ The order created: ===========\n")
        print(order_data)

        timespot = date_obj = datetime.datetime.fromtimestamp(timestamps[index] / 1000).strftime("%Y-%m-%d %H:%M:%S")
        print("the position info:",  timespot, session[0].price_entry, session[0].quantity )




        if side == "buy":
            self.buy_price_prev = price - self.stride
            self.buy_count += 1
            self.stride *= 1.3
        elif side == "sell":
            self.sell_price_prev = price + self.stride
            self.sell_count += 1
            self.stride *= 1.3
        return 

    def create_orders(self, session, last_price, index):
        # active_posts = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()['positions']
        ######### For test ######### 
        active_posts = session

        # if active_posts[0] is None:
        ######### For test #########


        if len(active_posts) == 0:
            if last_price <= self.buy_price_prev:
                order_data_buy = {
                    'symbol': 'XRPUSDT_PERP',
                    'side': "buy",
                    'time_in_force': 'Day',
                    'quantity': -quantity,
                    'price': self.buy_price_prev,
                    'type': 'limit',
                }   
                
                self.updateOrder(session, "buy", last_price, self.multipule,index)

            elif last_price >= self.sell_price_prev:
                order_data_sell = {
                    'symbol': 'XRPUSDT_PERP',
                    'side': "buy",
                    'time_in_force': 'Day',
                    'quantity': -quantity,
                    'price': self.sell_price_prev,
                    'type': 'limit',
                }
                self.updateOrder(session, "sell", last_price, self.multipule,index)
            else:
                return
        else:

            trap(session, last_price)

            # size_quantity = float(active_posts[0]["quantity"])
            # price_entry = float(active_posts[0]["price_entry"])
            # price_liquidation = float(active_posts[0]["price_liquidation"])
            # quantity = float(active_posts[0]["quantity"])

        self.last_price = last_price    