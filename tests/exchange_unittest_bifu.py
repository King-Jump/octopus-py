import unittest
import os
import sys
import json

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

from octopuspy.utils.log_util import create_logger
LOGGER = create_logger(".", "exchange_unittest.log", "BN_SPOT_TEST", 1)

from octopuspy import BifuSpotClient, ClientParams
from test_env import BASE_URL, API_KEY, SECRET
from tests.exchange_unittest import ExchangeTest

SYMBOL = "TRUMPUSDT"

class BifuExchangeTest(ExchangeTest):
    def setUp(self):
        super().setUp(symbol=SYMBOL, price_decimal=2, qty_decimal=3)
        params = ClientParams(base_url=BASE_URL, api_key=API_KEY, secret=SECRET, passphrase="")
        self.client = BifuSpotClient(params, LOGGER)
        
if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(BifuExchangeTest)
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)
