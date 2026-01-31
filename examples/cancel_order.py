import os
import sys

PROJ_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_PATH not in sys.path:
    sys.path.insert(0, PROJ_PATH)

from octopuspy.utils.log_util import create_logger
from octopuspy import ClientParams, OkxSpotClient
from test_env import BASE_URL, API_KEY, SECRET, PASSPHRASE

LOGGER = create_logger(".", "exchange_unittest.log", "exchange_unittest", 10)
symbol = "BTC_USDT"

params = ClientParams(BASE_URL, API_KEY, SECRET, PASSPHRASE)
client = OkxSpotClient(params, LOGGER)
print(client.cancel_order(order_id='001', symbol=symbol))