import csv
import numpy as np
import random
import time
import math
from datetime import datetime
import json
from session import SimulatedSession

from algorithm import TradingAlgorithm, TrapAlgorithm

def on_open(session):

    ticker_data = next(session.ticker_simulator.simulate_data_stream())['last_price']
    session.ticker_simulator.current_ticker = {
    "last": next(session.ticker_simulator.simulate_data_stream())['last_price'],
    "bid": next(session.ticker_simulator.simulate_data_stream())['best_bid'], 
    "ask": next(session.ticker_simulator.simulate_data_stream())['best_ask']}

    trading_algo.start(session)
    print("Subscribe to the XRPUSDT ticker data")





if __name__ == "__main__":
    session = SimulatedSession()
    trading_algo = TradingAlgorithm()

    on_open(session)


    for ticker in session.ticker_simulator.simulate_data_stream():
        # Simulate a GET request for account data
        # marginAccount = session.get('https://api.hitbtc.com/api/3/futures/account/isolated/XRPUSDT_PERP').json()
        # active_posts = marginAccount['positions']
        # marginBalance = float(marginAccount['currencies'][0]['margin_balance'])

        # print("Simulated Account Data:")
        # print(json.dumps(active_posts, indent=4),marginBalance)

        # # Simulate a GET request for ticker data
        # tickers = session.get('https://api.hitbtc.com/api/3/public/ticker?symbols=XRPUSDT_PERP').json()
        # print("\nSimulated Ticker Data:")
        # print(float(tickers["XRPUSDT_PERP"]["last"]))

        # # Simulate a DELETE request
        # # delete_response = session.delete("https://api.hitbtc.com/api/3/futures/order?&symbol=XRPUSDT_PERP").json()
        # # print("\nSimulated DELETE Response:")
        # # print(json.dumps(delete_response, indent=4))

        # # Simulate a POST request (you can provide order_data as needed)
        # order_data = {
        #     'symbol': 'XRPUSDT_PERP',
        #     'side': 'buy',
        #     'quantity': 1,
        #     'price': 105.0,
        #     'type': 'limit',
        #     'stop_price': 105.0
        # }
        # post_response = session.post('https://api.hitbtc.com/api/3/futures/order/', data=order_data).json()
        # print("\nSimulated POST Response:")
        # print(json.dumps(post_response, indent=4))
        # print("The updated position info is:")
        # print(session.position.quantity)
        # tick_data = data["data"]["XRPUSDT_PERP"]
        # print("The XRP ticker ask bid, last, sell buy prices, buy sell counts are:",ticker['best_ask'],float(ticker['last_price']), trading_algo.sell_price_prev, trading_algo.buy_price_prev, trading_algo.buy_count, trading_algo.sell_count)
        last_price = float(ticker['last_price'])
        # Call the create_orders method from the trading algorithm
        trading_algo.create_orders(session, last_price)