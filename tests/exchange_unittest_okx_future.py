import unittest
import os
import sys

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

from octopuspy.utils.log_util import create_logger
LOGGER = create_logger(".", "exchange_unittest.log", "exchange_unittest", 10)

from octopuspy.exchange.base_restapi import ClientParams
from octopuspy.exchange.okx_future_restapi import OkxFutureClient

from test_env import BASE_URL, API_KEY, SECRET, PASSPHRASE

from exchange_unittest import ExchangeTest

class OkxFutureUnitTest(ExchangeTest):
    def setUp(self):
        super().setUp(symbol="BTC-USDT-SWAP", price_decimal=1, qty_decimal=4)
        params = ClientParams(BASE_URL, API_KEY, SECRET, PASSPHRASE)
        self.client = OkxFutureClient(params, LOGGER)

    def test_00_account_info(self):
        ''' check account balance and poisitons
        '''
        print("### test_00_account_balance ###")
        res = self.client.balance()
        print("account balance %s" % res)
        self.assertTrueWithColor(res["code"] == "0" and res["data"], "Account balance inquiry successful")
        res = self.client.get_positions()
        print("account positions %s" % res)
        self.assertTrueWithColor(res["code"] == "0" and res["data"], "Account position inquiry successful")
        res = self.client.instrument_info(self.symbol)
        print("contract info %s" % res)
       
    def test_08_positions(self):
        print("### test_08_account_positions ###")
        res = self.client.get_positions()
        print("account positions %s" % res)
        self.assertTrueWithColor(res["code"] == "0" and not res["data"], "Account position is empty")
        
if __name__ == "__main__":
    suit = unittest.TestSuite()
    suit.addTest(unittest.makeSuite(OkxFutureUnitTest))
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suit)
