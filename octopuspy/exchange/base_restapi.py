""" base class of restful API client
Implements mock interface for test. Use it by set self.mock=True, and call super class functions.
"""
import time
import logging
from logging import Logger
from collections import namedtuple

# parameters for create a new restful client
ClientParams = namedtuple('ClientParams', ['base_url', 'api_key', 'secret', 'passphrase'])

# parameters for putting a new order
NewOrder = namedtuple('NewOrder', ['symbol', 'client_id', 'side', 'type', 'quantity', 'price',
        'biz_type', 'tif', 'reduce_only', 'position_side', 'bait', 'selftrade_enabled'])


# parameters for response of open orders
OrderID = namedtuple('OrderID', ['order_id', 'client_id'])
OrderStatus = namedtuple('OrderStatus', ['order_id', 'client_id', 'side', 'price', 'state', 'origQty'])
Ticker = namedtuple('Ticker', ['s', 'p', 'q']) # s for symbol, p for price, q for quantity
# ap for ask price, aq for ask quantity, bp for bid price, bq for bid quantity
AskBid = namedtuple('AskBid', ['ap', 'aq', 'bp', 'bq'])

class ORDER_STATE_CONSTANTS:
    UNKNOWN = -1
    NEW = 0
    PARTIALLY_FILLED = 1
    FILLED = 2
    CANCELED = 3
    REJECTED = 4
    EXPIRED = 5
    @classmethod
    def parse(cls, state: str) -> int:
        """ parse state to int
        """
        if state == 'NEW':
            return cls.NEW
        elif state == 'PARTIALLY_FILLED':
            return cls.PARTIALLY_FILLED
        elif state == 'FILLED':
            return cls.FILLED
        elif state == 'CANCELED':
            return cls.CANCELED
        elif state == 'REJECTED':
            return cls.REJECTED
        elif state == 'EXPIRED':
            return cls.EXPIRED
        return cls.UNKNOWN

MOCK_TICKER_RETURN = {
    "BTCUSDT": [Ticker(s='BTCUSDT', p='69987.11', q='1.00')],
    "ETHUSDT": [Ticker(s='ETHUSDT', p='2050.00', q='1.00')],
    "BNBUSDT": [Ticker(s='ETHUSDT', p='629.00', q='1.00')]
}

MOCK_ASKBID_RETURN = {
    "BTCUSDT": [AskBid(ap='69987.11', aq='1.01', bp='69986.11', bq='0.99')],
    "ETHUSDT": [AskBid(ap='2050.00', aq='1.01', bp='2049.00', bq='0.99')],
    "BNBUSDT": [AskBid(ap='629.00', aq='1.01', bp='628.00', bq='0.99')]
}

class BaseClient:
    """ Base Client
    """
    __slots__ = ('base_url', 'api_key', 'secret', 'passphrase', 'logger', 'mock')
    def __init__(
        self,
        params: ClientParams,
        logger: Logger = logging.getLogger(__file__),
        mock: bool = False  # mock response for test
    ):
        self.base_url = params.base_url
        self.api_key = params.api_key
        self.secret = params.secret
        self.passphrase = params.passphrase
        self.logger = logger
        self.mock = mock

    def _timestamp(self) -> int:
        return int(1000 * time.time())

    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ Make batch orders
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return [OrderID(order_id="mock_order_001", client_id="mock_clorder_id_001"),
                    OrderID(order_id="mock_order_002", client_id="mock_clorder_id_002")]
        pass

    def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
        """ batch cancel orders
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return [OrderID(order_id="mock_order_001", client_id="mock_clorder_id_001"),
                    OrderID(order_id="mock_order_002", client_id="mock_clorder_id_002")]
        pass

    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ List open orders
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return [OrderStatus(order_id="mock_order_001", client_id="mock_clorder_id_001",side='BUY',
                                price=1.0, state=ORDER_STATE_CONSTANTS.NEW, origQty=1.0),
                    OrderStatus(order_id="mock_order_001", client_id="mock_clorder_id_001",side='SELL',
                                price=1.0, state=ORDER_STATE_CONSTANTS.NEW, origQty=1.0),]
        pass

    def ticker(self, symbol: str) -> list[Ticker]:
        """ get ticker
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return MOCK_TICKER_RETURN[symbol.upper()]
        pass

    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ get best ask and bid
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return MOCK_ASKBID_RETURN[symbol.upper()]
        pass

    def self_trade(
        self, symbol: str, side: str, price: str, qty: str, amt: str = ''
    ) -> list[OrderID]:
        """ self trade by mock
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return [OrderID(order_id="mock_order_001", client_id="mock_clorder_id_001"),
                    OrderID(order_id="mock_order_002", client_id="mock_clorder_id_002")]
        pass

    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """ cancel single order
        """
        if self.mock:
            time.sleep(0.1)
            return OrderID(order_id="mock_order_001", client_id="mock_clorder_id_001")
        pass

    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ get order status
        """
        # unified for mock test
        if self.mock:
            time.sleep(0.1)
            return [OrderStatus(order_id="mock_order_001", client_id="mock_clorder_id_001",side='BUY',
                                price=1.0, state=ORDER_STATE_CONSTANTS.NEW, origQty=1.0),
                    OrderStatus(order_id="mock_order_001", client_id="mock_clorder_id_001",side='SELL',
                                price=1.0, state=ORDER_STATE_CONSTANTS.NEW, origQty=1.0),]
        pass
