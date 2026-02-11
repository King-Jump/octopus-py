import os
import sys

PROJ_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_PATH not in sys.path:
    sys.path.insert(0, PROJ_PATH)

from octopuspy.utils.log_util import create_logger
from octopuspy import ClientParams, OkxSpotClient, NewOrder
from test_env import BASE_URL, API_KEY, SECRET, PASSPHRASE

LOGGER = create_logger(".", "exchange_unittest.log", "exchange_unittest", 10)
symbol = "BTC_USDT"

params = ClientParams(BASE_URL, API_KEY, SECRET, PASSPHRASE)
client = OkxSpotClient(params, LOGGER)

o1 = NewOrder(symbol=symbol, client_id='001', side='BUY', type='LIMIT', quantity=0.000010,
              price=65432.1, biz_type='spot', tif='gtx', position_side='')
o2 = NewOrder(symbol=symbol, client_id='002', side='SELL', type='LIMIT', quantity=0.000010,
              price=70000.1, biz_type='spot', tif='ioc', position_side='')
orders=[o1, o2]
print(client.batch_make_orders(orders))