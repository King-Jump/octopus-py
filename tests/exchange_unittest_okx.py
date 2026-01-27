import unittest
import os
import sys
import time

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

from octopus.utils.log_util import create_logger
LOGGER = create_logger(".", "exchange_unittest.log", "exchange_unittest", 10)

from octopus import ClientParams, OkxSpotClient

from tests.exchange_unittest import ExchangeTest

from test_env import BASE_URL, API_KEY, SECRET, PASSPHRASE
class OkxUnitTest(ExchangeTest):
    def setUp(self):
        super().setUp(symbol="BTC_USDT", price_decimal=1, qty_decimal=6)
        params = ClientParams(BASE_URL, API_KEY, SECRET, PASSPHRASE)
        self.client = OkxSpotClient(params, LOGGER)

    def test_00_account_balance(self):
        ''' check USDT balance
        '''
        print("### test_00_account_balance ###")
        res = self.client.balance()
        print("account balance %s", res)
        self.assertTrueWithColor(res["code"] == "0" and res["data"], "账户余额查询成功")
        
if __name__ == "__main__":
    suit = unittest.TestSuite()
    suit.addTest(unittest.makeSuite(OkxUnitTest))
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suit)
