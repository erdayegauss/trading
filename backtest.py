import csv
import numpy as np
import random
import time
import math
import datetime

# Define the CSV file name with historical data
csv_file_name = "ticker_data.csv"

# Load historical trading data into a list of dictionaries
timestamps = []
best_asks = []
best_ask_quantities = []
best_bids = []
best_bid_quantities = []
last_prices = []


with open(csv_file_name, mode="r") as csv_file:
    reader = csv.reader(csv_file)
    header = next(reader)  # Skip the header row
    for row in reader:
        # Extract data from each row
        timestamp, best_ask, best_ask_quantity, best_bid, best_bid_quantity, last_price,*_ = row

        # Append data to respective lists (you can create lists for other fields as needed)
        timestamps.append(float(timestamp))
        best_asks.append(float(best_ask))
        best_ask_quantities.append(float(best_ask_quantity))
        best_bids.append(float(best_bid))
        best_bid_quantities.append(float(best_bid_quantity))
        last_prices.append(float(last_price))



# Here is typical postion example

# [
#   {
#   "symbol":"XRPUSDT_PERP","type":"isolated","leverage":"20.00","created_at":"2023-09-13T12:31:31.366Z","updated_at":"2023-09-15T02:46:13.431Z",
#   "currencies":[{"code":"USDT","margin_balance":"1.847347812014","reserved_orders":"0","reserved_positions":"2.052639960455"}],
# 
#   "positions":[{"id":175609786,"symbol":"XRPUSDT_PERP","margin_mode":"Isolated","quantity":"-51",
#   "price_entry":"0.4853","price_margin_call":"0.4992","price_liquidation":"0.5073","pnl":"0.002454545454",
#   "created_at":"2023-09-13T12:31:31.366Z","updated_at":"2023-09-15T02:46:13.431Z"}]
#   },
#  
#  {
#   "symbol":"","type":"cross","leverage":"","created_at":"","updated_at":"",
#   "currencies":[{"code":"USDT","margin_balance":"0.010258413438","reserved_orders":"","reserved_positions":"0"}],
#   "positions":null
#   }
# ]


# Define your Position class (as shown in previous responses)
class Position:
    def __init__(self, symbol="XRPUSDT_PERP", price_entry=0.0, quantity=0, leverage=20, margin=0.0, price_liquidation=0.0, profits=0.0, rate=0.0):
        self.symbol = symbol  # Trading symbol (e.g., BTCUSD, ETHUSD)
        self.price_entry = price_entry  # Entry price of the position
        self.quantity = quantity  # Position size (number of contracts, tokens, etc.)
        self.leverage = leverage  # Leverage used for the position
        self.margin = margin  # Available capital for trading
        self.price_liquidation = self.calculate_price_liquidation()
        self.profits = profits
        self.rate = rate

    def calculate_margin_required(self):
        # Calculate the margin required for the position
        notional_value = self.price_entry * self.quantity
        margin_required = notional_value / self.leverage
        return margin_required

    def calculate_price_liquidation(self):
        # Calculate the liquidation price based on position type and margin requirements
        # Liquidation price for a long position
        if self.quantity != 0 : 
            price_liquidation = self.price_entry - 0.99*(self.margin / self.quantity)
            return price_liquidation
        else: 
            return 0.0

    def calculate_profit_loss(self, current_price):
        # Calculate the profit or loss based on the current price
        if self.is_long:
            profit_loss = (current_price - self.price_entry) * self.quantity
        else:
            profit_loss = (self.price_entry - current_price) * self.quantity
        return profit_loss

    def update_position(self, new_price_entry, new_quantity):
        # Update the position with new data
        self.price_entry = (new_price_entry*new_quantity+self.price_entry*self.quantity)/(new_quantity+self.quantity)
        self.quantity = self.quantity + new_quantity
        self.margin = (new_price_entry*new_quantity+self.price_entry*self.quantity)/self.leverage
    def delete(self,current_price):
        self.price_entry = 0.0
        self.quantity = 0.0
        self.margin = 0.0

        self.profits += (current_price - self.price_entry) * self.quantity





# here is the example of order for the platform, the rest of could actully be in default value
        # order_data = {
        #     'symbol': 'XRPUSDT_PERP',
        #     'side': side,
        #     'time_in_force': 'Day',
        #     'quantity': quantity,
        #     'price': price,
        #     'type': 'limit'
        # }



class Order:
    def __init__(self, data):
        self.symbol = data.get("symbol")
        self.side = data.get("side")
        self.time_in_force = data.get("time_in_force")
        self.quantity = float(data.get("quantity"))
        self.price = float(data.get("price"))        
        self.type = data.get("type")
        self.status = "active"

    def fill_order(self,position):
        # Simulate filling an order by updating the position
        position.update_position(self.price, self.quantity)
        self.status = "filled"


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
        self.last_price = 0.0


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

    def bunny(self):
        # The primary idea is to measure the current price and the last price, make sure the speed of increase is large enough to trigger the high position trade.
        
        if self.buy_count > 5:
            self.buy_price_prev = min(self.buy_price_prev, self.last_price * 0.98)

        if self.sell_count > 5:
            self.sell_price_prev = max(self.sell_price_prev, self.last_price * 1.02)
        

    def start(self, session):

        # price_query = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        # last_price = float(price_query["XRPUSDT_PERP"]["last"])

        # marginAccount = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()
        # active_posts = marginAccount['positions']
        # marginBalance = float(marginAccount['currencies'][0]['margin_balance'])
        # # self.multipule = math.floor(marginBalance / 0.5) + 1
        # # self.threshold = math.floor( float(marginAccount['leverage']) * marginBalance / last_price )

        ######### For test #########
        last_price = random.uniform(0.45, 0.5)
        active_posts = session       


        # if active_posts is None:
        ######### For test ######### 
        if len(active_posts) == 0:
            self.stride = last_price * 0.0012
            self.sell_price_prev = last_price + self.stride
            self.buy_price_prev = last_price - self.stride
            self.buy_count = 1
            self.sell_count = 1
        else:

            # size_quantity = abs(float(active_posts[0]["quantity"]))
            # price_entry = float(active_posts[0]["price_entry"])

        ######### For test ######### 
            size_quantity = abs(float(active_posts[0].quantity))
            price_entry = float(active_posts[0].price_entry)


            self.stride = last_price * 0.0012 * 1.3 ** (self.orderCounts(size_quantity))
            self.sell_price_prev = price_entry + self.stride
            self.buy_price_prev = price_entry - self.stride
            self.buy_count = self.orderCounts(size_quantity / self.multipule) + 1
            self.sell_count = self.orderCounts(size_quantity / self.multipule) + 1

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
                self.updateOrder(session, "buy", last_price, self.multipule,index)
            elif last_price >= self.sell_price_prev:
                self.updateOrder(session, "sell", last_price, self.multipule,index)
            else:
                return
        else:

            # size_quantity = float(active_posts[0]["quantity"])
            # price_entry = float(active_posts[0]["price_entry"])
            # price_liquidation = float(active_posts[0]["price_liquidation"])
            # quantity = float(active_posts[0]["quantity"])


        ######### For test #########

            size_quantity = float(active_posts[0].quantity)
            price_entry = float(active_posts[0].price_entry)
            price_liquidation = float(active_posts[0].price_liquidation)
            quantity = float(active_posts[0].quantity)


            #  here is the logic for the non-empty positon
            # This time we should unify the buy and sell order together
            if (last_price - price_entry) * np.sign(quantity) >= 0.0025 * price_entry:

                # delete = session.delete('https://api.hitbtc.com/api/3/futures/position/isolated/XRPUSDT_PERP',
                #                         json={"price": last_price}).json()

        ######### For test #########
                active_posts[0].delete(last_price)

                self.start(session)
                return
            else:

                self.bunny()

                side = "sell"
                if np.sign(quantity) < 0:
                    side = "buy"

                if (last_price <= min(self.buy_price_prev, (price_entry * 0.999))) or (last_price >= max(self.sell_price_prev, (price_entry * 1.001))) and (size_quantity < self.threshold):
                    
                    buy = self.updateOrder(session, side, last_price, self.orderSize(self.buy_count) * self.multipule,index)
                    return buy
                else:
                    return   

        self.last_price = last_price             


if __name__ == "__main__":
    active_posts=[]
    trading_algo = TradingAlgorithm() 
    trading_algo.start(active_posts)

    print(len(last_prices))

    for index, price in enumerate(last_prices):
        trading_algo.create_orders(active_posts, float(price),index)
