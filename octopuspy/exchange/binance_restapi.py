import os
import sys
import time
import logging
import requests
from logging import Logger

from binance.spot import Spot as Client
from .base_restapi import (
    AskBid, BaseClient, ClientParams, NewOrder, OrderID, OrderStatus, Ticker, ORDER_STATE_CONSTANTS
)

""" Map bn status to am status:
document: https://developers.binance.com/docs/binance-spot-api-docs/enums

NEW	The order has been accepted by the engine.
PENDING_NEW	The order is in a pending phase until the working order of an order list has been fully filled.
PARTIALLY_FILLED	A part of the order has been filled.
FILLED	The order has been completed.
CANCELED	The order has been canceled by the user.
PENDING_CANCEL	Currently unused
REJECTED	The order was not accepted by the engine and not processed.
EXPIRED	The order was canceled according to the order type's rules (e.g. LIMIT FOK orders with no fill, LIMIT IOC or MARKET orders that partially fill)
or by the exchange, (e.g. orders canceled during liquidation, orders canceled during maintenance)
EXPIRED_IN_MATCH	The order was expired by the exchange due to STP. (e.g. an order with EXPIRE_TAKER will match with existing orders on the book with the same account or same tradeGroupId)
"""
BN_STATUS_MAP = {
    "NEW" : ORDER_STATE_CONSTANTS.NEW,
    "PENDING_NEW" : ORDER_STATE_CONSTANTS.NEW,
    "PARTIALLY_FILLED" : ORDER_STATE_CONSTANTS.PARTIALLY_FILLED,
    "FILLED" : ORDER_STATE_CONSTANTS.FILLED,
    "CANCELED" : ORDER_STATE_CONSTANTS.CANCELED,
    "PENDING_CANCEL" : ORDER_STATE_CONSTANTS.CANCELED,
    "REJECTED" : ORDER_STATE_CONSTANTS.REJECTED,
    "EXPIRED" : ORDER_STATE_CONSTANTS.EXPIRED,
    "EXPIRED_IN_MATCH" : ORDER_STATE_CONSTANTS.EXPIRED
}

"""
Status	Description
GTC:    Good Til Canceled
        An order will be on the book unless the order is canceled.
IOC:    Immediate Or Cancel
        An order will try to fill the order as much as it can before the order expires.
FOK:    Fill or Kill
        An order will expire if the full order cannot be filled upon execution.
"""    

class BnSpotClient(BaseClient):
    """ https://api.binance.com """
    def __init__(
            self,
            params: ClientParams,
            logger: Logger=logging.getLogger(__file__)):
        super().__init__(params, logger=logger)
        self.spot_client = Client(api_key=params.api_key, api_secret=params.secret)
        # self.spot_client = Client(base_url=params.base_url, api_key=params.api_key, api_secret=params.secret)

    def tif_map(self, order_type:str, tif:str):
        if order_type == "LIMIT_MAKER":
            return "limit", "gtx"
        return order_type, tif
    
    def type_map(self, order_type:str, tif:str):
        if tif.upper() == "GTX":
            return "LIMIT_MAKER", ""
        return order_type.upper(), tif.upper()
        
    def balance(self, symbol:str=None):
        _params = {"timestamp" : int(time.time()*1000)}
        return self.spot_client.balance(**_params)
    
    def order_book(self, symbol: str) -> dict:
        """ Get order book
        """
        try:
            res = self.spot_client.depth(symbol, limit=20)
            return {
                "timestamp": int(1000 * time.time()),
                "lastUpdateId": res['lastUpdateId'],
                "asks": res['asks'],
                "bids": res['bids']
            }
        except Exception as e:
            self.logger.error("order_book error: %s", e)
            return {}

    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ Raw Response
            {
                'symbol': 'BTCUSDT',
                'bidPrice': '118199.99000000',
                'bidQty': '0.08731000',
                'askPrice': '118200.00000000',
                'askQty': '9.61974000'
            }
        """
        try:
            res = self.spot_client.book_ticker(symbol=symbol)
            return [AskBid(ap=res['askPrice'],
                           aq=res['askQty'],
                           bp=res['bidPrice'],
                           bq=res['bidQty'])]
        except Exception as e:
            self.logger.error(f"top_askbid error: {e}")
            return []

    def ticker(self, symbol: str) -> list[Ticker]:
        """ 
        spot_client.ticker_price(symbols=["BTCUSDT", "BNBUSDT"])
        Raw Response:
        {
            'symbol': 'BTCUSDT',
            'price': '117951.21000000'
        }
        """
        try:
            res = self.spot_client.ticker_price(symbol)
            return [Ticker(s=res['symbol'], p=res['price'], q="0")]
        except Exception as e:
            self.logger.error("ticker error: %s", e)
            return []

    def account_info(self) -> dict:
        """ Response
        """
        _params = {"timestamp" : int(time.time()*1000)}
        try:
            return self.spot_client.account(**_params)
        except Exception as e:
            self.logger.error("account error: %s", e)
            return {}

    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ get open orders
            Response:
            [
                {
                }
            ]
        """
        try:
            res = self.spot_client.get_open_orders(symbol)
            _total_res = []
            for item in res:
                state = BN_STATUS_MAP.get(item["status"], ORDER_STATE_CONSTANTS.UNKNOWN)
                if state == ORDER_STATE_CONSTANTS.UNKNOWN:
                    self.logger.debug("order status unknown: %s", item["status"])
                _total_res.append(OrderStatus(order_id=str(item["orderId"]),
                                              client_id=item["clientOrderId"],
                                              side=item["side"],
                                              price=item["price"],
                                              state=state,
                                              origQty=item["origQty"]))
            return _total_res
        except Exception as e:
            self.logger.error("open_orders fail: %s", e)
            return []
    
    def norm_symbol(self, symbol:str) -> str:
        return symbol.replace("_", "").replace("-", "").upper()

    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ make batch orders by single order api
        """
        norm_symbol = self.norm_symbol(symbol)
        total_results = []
        for order in orders:
            _params = {
                "quantity" : float(order.quantity),
                "price" : float(order.price),
                "newClientOrderId" : order.client_id,
                "timestamp" : int(time.time()*1000)
            }
            _type, _tif = self.type_map(order.type, order.tif)
            if _tif:
                _params["timeInForce"] = _tif
            try:
                res = self.spot_client.new_order(symbol=norm_symbol, side=order.side, type=_type, **_params)
                total_results.append(OrderID(order_id=str(res["orderId"]),
                                    client_id=res["clientOrderId"]))
            except Exception as e:
                self.logger.error("bn make order %s error: %s", order, e)
        return total_results

    def batch_cancel(self, order_ids: list, symbol: str = '') -> list[OrderID]:
        """ cancel multi orders by single cancel api
        Name	Type	Mandatory	Description
        symbol	STRING	YES	
        orderId	LONG	NO	
        origClientOrderId	STRING	NO	
        newClientOrderId	STRING	NO	Used to uniquely identify this cancel. Automatically generated by default.
        cancelRestrictions	ENUM	NO	Supported values:
        ONLY_NEW - Cancel will succeed if the order status is NEW.
        ONLY_PARTIALLY_FILLED - Cancel will succeed if order status is PARTIALLY_FILLED.
        recvWindow	DECIMAL	NO	The value cannot be greater than 60000.
        Supports up to three decimal places of precision (e.g., 6000.346) so that microseconds may be specified.
        timestamp	LONG	YES        
        """
        norm_symbol = self.norm_symbol(symbol)
        total_res = []
        for id in order_ids:
            _params = {"orderId" : int(id), "timestamp" : int(time.time()*1000)}
            try:
                res = self.spot_client.cancel_order(symbol=norm_symbol, **_params)
                total_res.append(OrderID(order_id=str(res["orderId"]), client_id=res["origClientOrderId"]))
            except Exception as e:
                self.logger.error("cancel order [%s] fail: %s", id, e)
        return total_res

    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        norm_symbol = self.norm_symbol(symbol)
        _params = {"orderId" : int(order_id), "timestamp" : int(time.time()*1000)}
        try:
            res = self.spot_client.cancel_order(symbol=norm_symbol, **_params)
            return OrderID(order_id=str(res["orderId"]), client_id=res["origClientOrderId"])
        except Exception as e:
            self.logger.error("cancel order [%s] fail: %s", order_id, e)
            return None

    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ order status
        """
        norm_symbol = self.norm_symbol(symbol)
        _params = {"orderId":int(order_id), "timestamp":int(time.time()*1000)}
        try:     
            res = self.spot_client.get_order(symbol=norm_symbol, **_params)
            state = BN_STATUS_MAP.get(res["status"], ORDER_STATE_CONSTANTS.UNKNOWN)
            if state == ORDER_STATE_CONSTANTS.UNKNOWN:
                self.logger.debug("order status unknown: %s", res["status"])
            return [OrderStatus(order_id = order_id,
                                client_id = res["clientOrderId"],
                                side=res["side"],
                                price=res["price"],
                                state=state,
                                origQty=res["origQty"])]
        except Exception as e:
            self.logger.error("order [%s] status error: %s", order_id, e)
            return []