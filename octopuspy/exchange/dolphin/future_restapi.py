import requests
import time
from logging import Logger

from ..base_restapi import ORDER_STATE_CONSTANTS, AskBid, BaseClient, NewOrder, OrderID, OrderStatus, Ticker, ClientParams

DOLPHIN_BASE_URL = "http://localhost:8763"
DOLPHIN_TEST_URL = "http://localhost:8763"

class DOLPHIN_ORDER_STATE_CONSTANTS(ORDER_STATE_CONSTANTS):
    """ UNKNOWN_ORDER_STATUS, PENDING, OPEN, FILLED, CANCELING, CANCELED, UNTRIGGERED, UNRECOGNIZED
    """
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

class DolphinFutureClient(BaseClient):
    """ Restful API Client for Futures Trading of Dolphin
    """
    def __init__(self, params: ClientParams, logger: Logger):
        """ http://localhost:8763 """
        super().__init__(params, logger)
        if not self.base_url:
            self.base_url = DOLPHIN_TEST_URL # default
    
    def _get(self, path, params: dict = None):
        try:
            response = requests.get(f'{self.base_url}{path}', params=params, timeout=5)
            return response.json()
        except requests.exceptions.RequestException:
            self.logger.error('GET request %s failed', path)
            return {}
    
    def _post(self, path, data: dict = None):
        try:
            response = requests.post(f'{self.base_url}{path}', json=data, timeout=5)
            return response.json()
        except requests.exceptions.RequestException:
            self.logger.error('POST request %s failed', path)
            return {}
    
    def _delete(self, path, params: dict = None):
        try:
            response = requests.delete(f'{self.base_url}{path}', params=params, timeout=5)
            return response.json()
        except requests.exceptions.RequestException:
            self.logger.error('DELETE request %s failed', path)
            return {}
    
    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ Get best ask and bid prices """
        if self.mock:
            return super().top_askbid(symbol)   # call mock function if self.mock
        res = self.order_book(symbol, limit=1)
        try:
            top_ask = res['asks'][0]
            top_bid = res['bids'][0]
            return [AskBid(ap=top_ask[0],
                           aq=top_ask[1],
                           bp=top_bid[0],
                           bq=top_bid[1])]
        except Exception:
            self.logger.error('top_askbid response %s', res)
        return []
    
    def order_book(self, symbol: str, limit: int = 30) -> dict:
        """ Get order book depth """
        path = '/fapi/v1/depth'
        params = {
            "symbol": symbol,
            "limit": limit
        }
        res = self._get(path, params)
        if res.get('code') == 200 and res.get('data'):
            return res['data']
        return {'asks': [], 'bids': []}
    
    def ticker(self, symbol: str) -> list[Ticker]:
        """ Get latest ticker """
        if self.mock:
            return super().ticker(symbol)   # call mock function if self.mock
        path = '/fapi/v1/ticker/price'
        params = {"symbol": symbol}
        res = self._get(path, params)
        if res.get('code') == 200 and res.get('data'):
            return [Ticker(s=symbol, p=res['data']['price'], q=res['data']['quantity'])]
        return []
    
    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ Get open orders """
        if self.mock:
            return super().open_orders(symbol)   # call mock function if self.mock
        path = '/fapi/v1/openOrders'
        params = {"symbol": symbol}
        res = self._get(path, params)
        if res.get('code') == 200 and res.get('data'):
            return [OrderStatus(order_id=str(order['orderId']),
                    client_id=order.get('clientOrderId', ''),
                    side=order['side'],
                    price=order['price'],
                    state=DOLPHIN_ORDER_STATE_CONSTANTS.parse(order['status']),
                    origQty=order['origQty']) for order in res['data']]
        return []
    
    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ Make batch orders """
        if self.mock:
            return super().batch_make_orders(orders, symbol)   # call mock function if self.mock
        path = '/fapi/v1/batchOrders'
        batch_orders = []
        for order in orders:
            order_data = {
                "symbol": order.symbol,
                "side": order.side,
                "type": order.type,
                "quantity": order.quantity
            }
            if order.price:
                order_data["price"] = order.price
            if order.client_id:
                order_data["client_order_id"] = order.client_id
            batch_orders.append(order_data)
        
        res = self._post(path, {"batchOrders": batch_orders})
        suc_orders = []
        if res.get('code') == 200 and res.get('data'):
            for item in res['data']:
                order_id = item.get('orderId')
                if order_id:
                    suc_orders.append(OrderID(order_id=str(order_id),
                                      client_id=item.get('clientOrderId', '')))
        return suc_orders
    
    def batch_cancel(self, order_ids: list, symbol: str = '') -> list[OrderID]:
        """ Batch cancel orders """
        if self.mock:
            return super().batch_cancel(order_ids, symbol)   # call mock function if self.mock
        path = '/fapi/v1/order'
        params = {
            "symbol": symbol,
            "orderIds": ",".join(order_ids)
        }
        res = self._delete(path, params)
        results = []
        if res.get('code') == 200 and res.get('data'):
            for item in res['data']:
                order_id = item.get('orderId')
                if order_id:
                    results.append(OrderID(order_id=str(order_id), client_id=''))
        return results
    
    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """ Cancel single order """
        if self.mock:
            return super().cancel_order(order_id, symbol)   # call mock function if self.mock
        res = self.batch_cancel([order_id], symbol)
        if res:
            return res[0]
        return OrderID(order_id='', client_id='')
    
    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ Get order status """
        if self.mock:
            return super().order_status(order_id, symbol)   # call mock function if self.mock
        # Dolphin API doesn't have a direct order status endpoint
        # We'll use open_orders and filter by order_id
        open_orders = self.open_orders(symbol)
        return [order for order in open_orders if order.order_id == order_id]
    
    def self_trade(self, symbol: str, side: str, price: str, qty: str, amt: str = '') -> list[OrderID]:
        """ Self trade by mock """
        if self.mock:
            return super().self_trade(symbol, side, price, qty, amt)   # call mock function if self.mock
        path = '/fapi/v3/mock'
        data = {
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": qty
        }
        res = self._post(path, data)
        if res.get('code') == 200 and res.get('data'):
            return [OrderID(order_id='mock_trade_order', client_id='')]
        return []
    
    # Additional Dolphin Futures-specific methods
    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 10) -> dict:
        """ Get kline data """
        path = '/fapi/v1/klines'
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        res = self._get(path, params)
        if res.get('code') == 200:
            return res
        return {}
    
    def new_order(self, symbol: str, side: str, order_type: str, quantity: str, price: str = None, client_order_id: str = None) -> dict:
        """ Create new order """
        path = '/fapi/v1/order'
        data = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity
        }
        if price:
            data["price"] = price
        if client_order_id:
            data["client_order_id"] = client_order_id
        return self._post(path, data)
