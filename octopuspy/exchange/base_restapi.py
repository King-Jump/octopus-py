""" base class of restful API client
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


class BaseClient:
    """ Base Client
    """
    __slots__ = ('base_url', 'api_key', 'secret', 'passphrase', 'logger')
    def __init__(
        self,
        params: ClientParams,
        logger: Logger = logging.getLogger(__file__)
    ):
        self.base_url = params.base_url
        self.api_key = params.api_key
        self.secret = params.secret
        self.passphrase = params.passphrase
        self.logger = logger

    def _timestamp(self) -> int:
        return int(1000 * time.time())

    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ Make batch orders
        """
        raise NotImplementedError('batch_make_orders is not implemented')

    def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
        """ batch cancel orders
        """
        raise NotImplementedError('batch_cancel is not implemented')

    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ List open orders
        """
        raise NotImplementedError('open_orders is not implemented')

    def ticker(self, symbol: str) -> list[Ticker]:
        """ get ticker
        """
        raise NotImplementedError('ticker is not implemented')

    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ get best ask and bid
        """
        raise NotImplementedError('top_askbid is not implemented')

    def self_trade(
        self, symbol: str, side: str, price: str, qty: str, amt: str = ''
    ) -> list[OrderID]:
        """ self trade by mock
        """
        raise NotImplementedError('self_trade is not implemented')

    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """ cancel single order
        """
        raise NotImplementedError('cancel_order is not implemented')

    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ get order status
        """
        raise NotImplementedError('order_status is not implemented')
