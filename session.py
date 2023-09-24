import csv
import numpy as np
import random
import time
import math
from datetime import datetime
import json
import matplotlib.pyplot as plt


# Define the CSV file name with historical data
class CustomResponse:
    def __init__(self, content):
        self.content = content

    def json(self):
        # Return the content as JSON
        return json.loads(self.content)

# Simulated session class
class SimulatedSession:
    def __init__(self):
        self.proxies = {
            'http': 'http://127.0.0.1:10900',
            'https': 'http://127.0.0.1:10900',
        }
        self.auth = ("", "")
        self.position = None  # Initialize a Position object
        self.ticker_simulator = TickerDataSimulator("ticker_data.csv")  # Initialize a TickerDataSimulator
        self.balance = 0.0
        self.orders = []


    def get(self, url):
        # Simulate a GET request and return position or ticker data
        if "ticker" in url:
            # Simulate ticker data using TickerDataSimulator
            tickers = {
                "XRPUSDT_PERP": self.ticker_simulator.current_ticker
                }
                
            return CustomResponse(json.dumps(tickers))
        elif "account/isolated" in url:
            # Return account data in the specified format
            if self.position == None :
                account_data = {
                    "symbol": "XRPUSDT_PERP",
                    "type": "isolated",
                    "leverage": "20.00",
                    "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "currencies": [
                        {
                            "code": "USDT",
                            "margin_balance": self.balance,
                            "reserved_orders": "0",
                            "reserved_positions": "0.0"
                        }
                    ],
                    "positions": None
                }
            else: 
                account_data = {
                    "symbol": "XRPUSDT_PERP",
                    "type": "isolated",
                    "leverage": "20.00",
                    "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "currencies": [
                        {
                            "code": "USDT",
                            "margin_balance": self.balance,
                            "reserved_orders": "0",
                            "reserved_positions": "0.0"
                        }
                    ],
                    "positions": [
                        {
                            "id": 1234567,
                            "symbol": "XRPUSDT_PERP",
                            "quantity": self.position.quantity,
                            "margin_mode": "isolated",
                            "price_entry": self.position.price_entry,
                            "price_margin_call": "25395.20",
                            "price_liquidation": self.position.price_liquidation,
                            "pnl": self.position.profits,
                            "created_at": "2023-09-17T17:26:10.758Z",
                            "updated_at": "2023-09-17T21:20:03.64Z"
                        }
                    ]
                }    
            return  CustomResponse(json.dumps(account_data))
        elif "futures/order/" in url:

            parts = url.split('/')
            order_id = parts[-1]
            order_data = {}

            for order in self.orders:
                if order.client_order_id == order_id:
                    order.cancel_order()
                    order_data = {
                        "client_order_id": order.client_order_id
                    }
            return CustomResponse(json.dumps(order_data))
        
        else:
            return {}

    def post(self, url, data):
        # Simulate a POST request to create an order using the Order class
        order = Order(data)
        self.orders.append(order)
        # self.position.update_position(order.price, order.quantity)
        return CustomResponse(json.dumps({"message": "Successfully added order", "data": data}))

    def delete(self, url):
        # Simulate a DELETE request and return a JSON response
        if "position/isolated" in url:
            price_query = self.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
            last_price = float(price_query["XRPUSDT_PERP"]["last"])       
            if self.position != None :
                self.position.delete(last_price)
                self.balance += self.position.profits 
                self.position = None
            return CustomResponse(json.dumps({"message": "Successfully deleted"}))
        
        elif "futures/order?&symbol=XRPUSDT_PERP" in url:
            self.orders = []
            return CustomResponse(json.dumps({"message": "Successfully deleted"}))
        elif "futures/order/" in url:
            parts = url.split('/')
            order_id = parts[-1]
            for order in self.orders:
                if order.client_order_id == order_id:
                    order.cancel_order()
                return CustomResponse(json.dumps({"message": "Successfully deleted the order:"+order_id}))
            return CustomResponse(json.dumps({}))

        else: 
            return

    def patch(self, url,data):
        # Simulate a DELETE request and return a JSON response
        if "futures/order/" in url:
            parts = url.split('/')
            order_id = parts[-1]

            for order in self.orders:
                if order.client_order_id == order_id:
                    tmpOrder = {
                    "client_order_id": order.client_order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "status": order.status,
                    "type": order.type,
                    "quantity": order.quantity
                    }
                    order.update_order(tmpOrder)


            return CustomResponse(json.dumps(tmpOrder))

    def updateOrders(self, price):

        for index, order in enumerate(self.orders):
            if (self.orders[index].status == "active") :
                if self.position == None :
                    self.position = Position()
                self.fill_order(self.orders[index], self.position, price)

    def fill_order(self, order, position, current_price):
        if order.type == "limit":
            if (
                (order.side == "buy" and current_price <= order.price and order.status == "active") or
                (order.side == "sell" and current_price >= order.price and order.status == "active")
            ):
                # Execute the limit order when the price meets the order price
                order.price = current_price  # Update the order price
                position.update_position(order.price, order.quantity, order.side)
                order.status = "filled"
            else:
                order.status = "active"
        elif order.type == "stopLimit":
            if (
                (order.side == "buy" and current_price >= order.stop_price and order.status == "active") or
                (order.side == "sell" and current_price <= order.stop_price and order.status == "active")
            ):
                new_order_data = {
                    'client_order_id': order.client_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': order.side,
                    'time_in_force': 'Day',
                    'quantity': order.quantity,
                    'price': order.price,
                    'type': 'limit'
                }

                new_order = Order(new_order_data)
                self.orders.append(new_order)
                order.cancel_order()

            else:
                order.status = "active"
        elif order.type == "takeProfitLimit":
            if (
                (order.side == "buy" and current_price <= order.stop_price and order.status == "active") or
                (order.side == "sell" and current_price >= order.stop_price and order.status == "active")
            ):
                new_order_data = {
                    'client_order_id': order.client_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': order.side,
                    'time_in_force': 'Day',
                    'quantity': order.quantity,
                    'price': order.price,
                    'type': 'limit'
                }

                new_order = Order(new_order_data)
                self.orders.append(new_order)
                order.cancel_order()

            else:
                order.status = "active"  
        elif order.type == "stopMarket":
            if (order.side == "buy" and current_price >= order.stop_price and order.status == "active"): 
                new_order_data = {
                    'client_order_id': order.client_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': order.side,
                    'time_in_force': 'Day',
                    'quantity': order.quantity,
                    'price': order.stop_price*1.0004,
                    'type': 'limit'
                }
            if (order.side == "sell" and current_price <= order.stop_price and order.status == "active"):
                new_order_data = {
                    'client_order_id': order.client_order_id,
                    'symbol': 'XRPUSDT_PERP',
                    'side': order.side,
                    'time_in_force': 'Day',
                    'quantity': order.quantity,
                    'price': order.stop_price*0.9996,
                    'type': 'limit'
                }
                new_order = Order(new_order_data)
                self.orders.append(new_order)
                order.cancel_order()
            else:
                order.status = "active"                
        elif order.type == "market":
            # Execute the market order at the current market price
            order.price = current_price  # Update the order price
            position.update_position(order.price, order.quantity, order.side)
            order.status = "filled"



class TickerDataSimulator:
    def __init__(self, csv_file_name):
        self.csv_file_name = csv_file_name
        self.data = self.load_data()
        self.current_ticker = {
                "last": 0.0,
                "bid": 0.0,                
                "ask": 0.0,
                }

    def load_data(self):
        timestamps = []
        best_asks = []
        best_ask_quantities = []
        best_bids = []
        best_bid_quantities = []
        last_prices = []

        with open(self.csv_file_name, mode="r") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader)  # Skip the header row
            for row in reader:
                timestamp, best_ask, best_ask_quantity, best_bid, best_bid_quantity, last_price, *_ = row
                timestamps.append(float(timestamp))
                best_asks.append(float(best_ask))
                best_ask_quantities.append(float(best_ask_quantity))
                best_bids.append(float(best_bid))
                best_bid_quantities.append(float(best_bid_quantity))
                last_prices.append(float(last_price))


                numerical_timeframes = range(len(timeframes))

                # Create a line chart
                plt.figure(figsize=(10, 5))
                plt.plot(numerical_timeframes, last_prices, marker='.', linestyle='-', color='b')

                # Add labels and title
                plt.xlabel("Timeframes")
                plt.ylabel("Last Prices")
                plt.title("Price Trend Over Time")

                # Set x-axis ticks as timeframes
                plt.xticks(numerical_timeframes, timeframes, rotation=45)

                # Show the plot
                plt.grid(True)
                plt.tight_layout()
                # Save the plot to an image file (e.g., PNG)
                plt.savefig("./price_chart.png")

                # Optionally, you can also display the plot
                plt.show()



        return {
            "timestamps": timestamps,
            "best_asks": best_asks,
            "best_ask_quantities": best_ask_quantities,
            "best_bids": best_bids,
            "best_bid_quantities": best_bid_quantities,
            "last_prices": last_prices
        }





    def simulate_data_stream(self):


        for i in range(len(self.data["timestamps"])):
            ticker_data = {
                "timestamp": self.data["timestamps"][i],
                "best_ask": self.data["best_asks"][i],
                "best_ask_quantity": self.data["best_ask_quantities"][i],
                "best_bid": self.data["best_bids"][i],
                "best_bid_quantity": self.data["best_bid_quantities"][i],
                "last_price": self.data["last_prices"][i]
            }
            yield ticker_data

            self.current_ticker  =  {
                "time": self.data["timestamps"][i],
                "last": self.data["last_prices"][i],
                "bid": self.data["best_bids"][i],                
                "ask": self.data["best_asks"][i],
                }


            # time.sleep(0.02)  # Simulate real-time data by waiting 1 second between data points


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

    def update_position(self, new_price_entry, new_quantity, new_side):
        # Update the position with new data
        if self.quantity <= 0 :
            if new_side == "sell":
                if  (self.quantity - new_quantity) != 0.0 :            
                    self.price_entry = (self.price_entry*self.quantity - new_price_entry*new_quantity)/(self.quantity - new_quantity)
                self.margin = - (self.price_entry*self.quantity - new_price_entry*new_quantity)/self.leverage
                self.quantity -= new_quantity

            else:
                if  (self.quantity + new_quantity) != 0.0 :
                    self.price_entry = (self.price_entry*self.quantity + new_price_entry*new_quantity)/(self.quantity + new_quantity)
                self.margin = - (self.price_entry*self.quantity + new_price_entry*new_quantity)/self.leverage
                self.quantity += new_quantity

        else :
            if new_side == "sell":
                if  (self.quantity - new_quantity) != 0.0 :            
                    self.price_entry =  (self.price_entry*self.quantity - new_price_entry*new_quantity)/(self.quantity - new_quantity)
                self.margin =  (self.price_entry*self.quantity - new_price_entry*new_quantity)/self.leverage
                self.quantity -= new_quantity

            else:
                if  (self.quantity + new_quantity) != 0.0 :            
                    self.price_entry =  (self.price_entry*self.quantity + new_price_entry*new_quantity)/(self.quantity + new_quantity)
                self.margin =  (self.price_entry*self.quantity + new_price_entry*new_quantity)/self.leverage
                self.quantity += new_quantity

    def delete(self,current_price):
        self.price_entry = 0.0
        self.quantity = 0.0
        self.margin = 0.0
        self.profits += (current_price - self.price_entry) * self.quantity




class Order:
    def __init__(self, data):
        self.symbol = data.get("symbol")
        self.side = data.get("side")
        self.time_in_force = data.get("time_in_force")  if "time_in_force" in data else "day"
        self.quantity = float(data.get("quantity"))
        self.price = float(data.get("price"))          if "price" in data else None 
        self.type = data.get("type")
        self.status = "active"
        self.client_order_id = data.get("client_order_id") if "client_order_id" in data else "000000"
        self.stop_price = float(data.get("stop_price")) if "stop_price" in data else None


    def cancel_order(self):
        self.status = "cancelled"

    def update_order(self, new_data):
        # Update the order attributes based on new data
        if "symbol" in new_data:
            self.symbol = new_data["symbol"]
        if "side" in new_data:
            self.side = new_data["side"]
        if "time_in_force" in new_data:
            self.time_in_force = new_data["time_in_force"]
        if "quantity" in new_data:
            self.quantity = float(new_data["quantity"])
        if "price" in new_data:
            self.price = float(new_data["price"])
        if "type" in new_data:
            self.type = new_data["type"]
        if "status" in new_data:
            self.status = new_data["status"]
        if "client_order_id" in new_data:
            self.client_order_id = new_data["client_order_id"]
        if "stop_price" in new_data:
            self.stop_price = float(new_data["stop_price"])
