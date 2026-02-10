"""
binance_umfuture_restapi, USD-M futures
Documentation: https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info

BnUMFutureClient inheritated from BaseClient, impliments stand exhange interface for BaseClient.
In addition to some account interface for management or testing.
"""
import time
import os
import sys
import time
import logging
from logging import Logger
from urllib.parse import urlencode

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

from binance.um_futures import UMFutures as Client
from ..base_restapi import (
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

BATCH_MAKE_SIZE = 5
BATCH_CANCEL_SIZE = 10

class BnUMFutureClient(BaseClient):
    """ https://fapi.binance.com """
    def __init__(
            self,
            params: ClientParams,
            logger: Logger=logging.getLogger(__file__)):
        super().__init__(params, logger=logger)
        self.future_client = Client(key=params.api_key, secret=params.secret)

    def tif_map(self, order_type:str, tif:str):
        if order_type == "LIMIT_MAKER":
            return "limit", "gtx"
        return order_type, tif
    
    def type_map(self, order_type:str, tif:str):
        if tif.upper() == "GTX":
            return "LIMIT", "GTC"
        return order_type.upper(), tif.upper()
        
    def norm_symbol(self, symbol:str) -> str:
        return symbol.replace("_", "").replace("-", "").upper()
    
    def balance(self):
        try:
            params = {"timestamp" : int(time.time()*1000)}
            return self.future_client.balance(**params)
        except Exception as e:
            self.logger.error("um_balance error: %s", e)
            return []
        
    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ Raw Response
            {
                "symbol": "BTCUSDT",
                "bidPrice": "4.00000000",
                "bidQty": "431.00000000",
                "askPrice": "4.00000200",
                "askQty": "9.00000000",
                "time": 1589437530011   // Transaction time
            }            
        """
        if self.mock:
            return super().top_askbid(symbol)   # call mock function if self.mock
        try:
            res = self.future_client.book_ticker(symbol=symbol)
            return [AskBid(ap=res['askPrice'],
                           aq=res['askQty'],
                           bp=res['bidPrice'],
                           bq=res['bidQty'])]
        except Exception as e:
            self.logger.error(f"top_askbid error: {e}")
            return []

    def ticker(self, symbol: str) -> list[Ticker]:
        """ 
        Raw Response:
        {
            "symbol": "BTCUSDT",
            "price": "6000.01",
            "time": 1589437530011   // Transaction time
        }
        """
        if self.mock:
            return super().ticker(symbol)   # call mock function if self.mock
        try:
            res = self.future_client.ticker_price(symbol)
            return [Ticker(s=res['symbol'], p=res['price'], q="0")]
        except Exception as e:
            self.logger.error("ticker error: %s", e)
            return []
    
    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ Portfolio get open orders
            Response:
        {
            "avgPrice": "0.00000",				
            "clientOrderId": "abc",				
            "cumQuote": "0",						
            "executedQty": "0",					
            "orderId": 1917641,					
            "origQty": "0.40",						
            "origType": "TRAILING_STOP_MARKET",
            "price": "0",
            "reduceOnly": false,
            "side": "BUY",
            "positionSide": "SHORT",
            "status": "NEW",
            "stopPrice": "9300",				// please ignore when order type is TRAILING_STOP_MARKET
            "closePosition": false,   			// if Close-All
            "symbol": "BTCUSDT",
            "time": 1579276756075,				// order time
            "timeInForce": "GTC",
            "type": "TRAILING_STOP_MARKET",
            "activatePrice": "9020",			// activation price, only return with TRAILING_STOP_MARKET order
            "priceRate": "0.3",					// callback rate, only return with TRAILING_STOP_MARKET order						
            "updateTime": 1579276756075,		
            "workingType": "CONTRACT_PRICE",
            "priceProtect": false,            // if conditional order trigger is protected	
            "priceMatch": "NONE",              //price match mode
            "selfTradePreventionMode": "NONE", //self trading preventation mode
            "goodTillDate": 0      //order pre-set auot cancel time for TIF GTD order
        }
        """
        if self.mock:
            return super().open_orders(symbol)   # call mock function if self.mock
        try:
            res = self.future_client.get_open_orders(symbol)
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
            
    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ make batch orders
        Name	Type	Mandatory	Description
        symbol	STRING	YES	
        side	ENUM	YES	
        positionSide	ENUM	NO	Default BOTH for One-way Mode ; LONG or SHORT for Hedge Mode. It must be sent with Hedge Mode.
        type	ENUM	YES	
        timeInForce	ENUM	NO	
        quantity	DECIMAL	YES	
        reduceOnly	STRING	NO	"true" or "false". default "false".
        price	DECIMAL	NO	
        newClientOrderId	STRING	NO	A unique id among open orders. Automatically generated if not sent. Can only be string following the rule: ^[\.A-Z\:/a-z0-9_-]{1,36}$
        newOrderRespType	ENUM	NO	"ACK", "RESULT", default "ACK"
        priceMatch	ENUM	NO	only avaliable for LIMIT/STOP/TAKE_PROFIT order; can be set to OPPONENT/ OPPONENT_5/ OPPONENT_10/ OPPONENT_20: /QUEUE/ QUEUE_5/ QUEUE_10/ QUEUE_20; Can't be passed together with price
        selfTradePreventionMode	ENUM	NO	EXPIRE_TAKER:expire taker order when STP triggers/ EXPIRE_MAKER:expire taker order when STP triggers/ EXPIRE_BOTH:expire both orders when STP triggers; default NONE
        goodTillDate	LONG	NO	order cancel time for timeInForce GTD, mandatory when timeInforce set to GTD; order the timestamp only retains second-level precision, ms part will be ignored; The goodTillDate timestamp must be greater than the current time plus 600 seconds and smaller than 253402300799000        
        """
        if self.mock:
            return super().batch_make_orders(orders, symbol)   # call mock function if self.mock
        norm_symbol = self.norm_symbol(symbol)
        total_results = []
        for i in range(0, len(orders), BATCH_MAKE_SIZE):
            _sub_orders = orders[i : i+BATCH_MAKE_SIZE]
            _bn_list = []
            for order in _sub_orders:
                _type, _tif = self.type_map(order.type, order.tif)
                _bn_order = {
                    "symbol" : norm_symbol,
                    "side" : order.side,
                    "type" : _type,
                    "quantity" : float(order.quantity),
                    "price" : float(order.price),
                    "newClientOrderId" : order.client_id,
                    "positionSide" : "BOTH",    # One-way Mode
                }
                if _tif:
                    _bn_order["timeInForce"] = _tif
                _bn_list.append(_bn_order)
                try:
                    res = self.future_client.new_batch_order(_bn_list)
                    for item in res:
                        total_results.append(OrderID(order_id=str(item["orderId"]),
                                            client_id=item["clientOrderId"]))
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
        if self.mock:
            return super().batch_cancel(order_ids, symbol)   # call mock function if self.mock
        norm_symbol = self.norm_symbol(symbol)
        total_res = []
        for i in range(0, len(order_ids), BATCH_CANCEL_SIZE):
            _sub_ids = order_ids[i : i+BATCH_CANCEL_SIZE]
            _bn_list = [int(id) for id in _sub_ids]
            try:
                res = self.future_client.cancel_batch_order(norm_symbol, _bn_list, [])
                total_res = total_res.extend(
                    [OrderID(order_id=str(item["orderId"]), client_id=item["origClientOrderId"]) for item in res]
                )
            except Exception as e:
                self.logger.error("cancel order [%s] fail: %s", id, e)
        return total_res

    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """ cancel order by order id
        """
        if self.mock:
            return super().cancel_order(order_id, symbol)   # call mock function if self.mock
        norm_symbol = self.norm_symbol(symbol)
        _params = {"orderId" : int(order_id), "timestamp" : int(time.time()*1000)}
        try:
            res = self.future_client.cancel_order(symbol=norm_symbol, orderId=int(order_id))
            return OrderID(order_id=str(res["orderId"]), client_id=res["origClientOrderId"])
        except Exception as e:
            self.logger.error("cancel order [%s] fail: %s", order_id, e)
            return None

    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ order status
        """
        if self.mock:
            return super().order_status(order_id, symbol)   # call mock function if self.mock
        _params = {"orderId":int(order_id)}
        try:     
            res = self.future_client.order_status(**_params)
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
