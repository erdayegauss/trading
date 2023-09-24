import csv
import numpy as np
import random
import time
import math
from datetime import datetime
import json
from session import SimulatedSession

from algorithm import TradingAlgorithm, TrapAlgorithm
from SellBuy import TradingAlgorithmSellBuy

def on_open(session, algo):

    ticker_data = next(session.ticker_simulator.simulate_data_stream())['last_price']
    session.ticker_simulator.current_ticker = {
    "last": next(session.ticker_simulator.simulate_data_stream())['last_price'],
    "bid": next(session.ticker_simulator.simulate_data_stream())['best_bid'], 
    "ask": next(session.ticker_simulator.simulate_data_stream())['best_ask']}

    ###### All the  Algorithms has a start function
    algo.start(session)
    print("Subscribe to the XRPUSDT ticker data")


if __name__ == "__main__":
    session = SimulatedSession()


###### -----------  waterpump algo   --------------- #######




    # ## load the algorithm waterpump
    # waterpump = TradingAlgorithm()
    # on_open(session, waterpump)

    # for ticker in session.ticker_simulator.simulate_data_stream():

    #     last_price = float(ticker['last_price'])

    #     ## update orders every ticker
    #     session.updateOrders(last_price)

    #     ###### Algorithm implementation 
    #     waterpump.create_orders(session, last_price)

###### -----------  trap algo   --------------- #######


    ## load the algorithm trap
    # algo = TrapAlgorithm()
    algo = TradingAlgorithmSellBuy()

    on_open(session, algo)

    for ticker in session.ticker_simulator.simulate_data_stream():

        last_price = float(ticker['last_price'])

        ## update orders every ticker
        session.updateOrders(last_price)

        # ###### Algorithm implementation 
        # algo.trap(session, last_price)

        ###### Algorithm implementation 
        algo.updateOrder(session, last_price)
        