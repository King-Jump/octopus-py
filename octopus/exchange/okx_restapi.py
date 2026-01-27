""" OKX spot API
    online doc: https://www.okx.com/docs-v5/
"""
import os
import sys
from logging import Logger, getLogger
from okx import MarketData
from okx import Account
from okx import Trade

PROJ_DIR = os.path.abspath(os.path.abspath(os.path.abspath(__file__)))
if PROJ_DIR not in sys.path:
    sys.path.insert(0, PROJ_DIR)
    
from octopus.exchange.base_restapi import (
    BaseClient, ClientParams, NewOrder, OrderID, Ticker, AskBid,
    OrderStatus, ORDER_STATE_CONSTANTS as order_state
)

BATCH_ORDER_SIZE = 20
BATCH_CANCEL_SIZE = 20

OKX_TYPE_MAP = {
    'GTC': 'limit',
    'IOC': 'ioc',
    'FOK': 'fok',
    'GTX': 'post_only',
}

class OkxSpotClient(BaseClient):
    def __init__(self, params: ClientParams, logger: Logger):
        super().__init__(params, logger)
        self.demo_trading = "0"  # live trading: 0, demo trading: 1
        self.market_data_api = MarketData.MarketAPI(api_key=self.api_key,
                                                    api_secret_key=self.secret,
                                                    passphrase=self.passphrase,
                                                    use_server_time=False,
                                                    flag=self.demo_trading,
                                                    domain = self.base_url)
        self.account_api = Account.AccountAPI(api_key=self.api_key,
                                             api_secret_key=self.secret,
                                             passphrase=self.passphrase,
                                             use_server_time=False,
                                             flag=self.demo_trading,
                                             domain=self.base_url)
        self.trade_api = Trade.TradeAPI(api_key=self.api_key,
                                        api_secret_key=self.secret,
                                        passphrase=self.passphrase,
                                        use_server_time=False,
                                        flag=self.demo_trading,
                                        domain=self.base_url)

    def _norm_symbol(self, symbol:str) -> str:
        return symbol.replace("_","-").upper()

    def _norm_client_id(self, client_id:str) -> str:
        return client_id.replace("_","SlAsH")
    
    def _recover_client_id(self, symbol:str) -> str:
        return symbol.replace("SlAsH","_")
    
    def _norm_order_type(self, order:NewOrder) -> str:
        if order.type == "LIMIT":
            return OKX_TYPE_MAP.get(order.tif, "post_only")
        return  order.type.lower()

    def _norm_state(self, order:dict) -> int:
        """
        state String Order status
        canceled: Order canceled
        live: Order pending
        partially_filled: Partially filled
        filled: Fully filled
        mmp_canceled: Automatically canceled by market maker protection
        """
        if order["state"] == "partially_filled":
            return order_state.PARTIALLY_FILLED
        if order["state"] == "filled":
            return order_state.FILLED
        if order["state"] == "canceled":
            return order_state.CANCELED
        if order["state"] == "live" and order["accFillSz"] == "0":
            return order_state.NEW
        return order_state.UNKNOWN
 
    def _norm_type(self, order:NewOrder) -> str:
        """ Normalize NewOrder state and tif to okx order type
        OKX  ordType:
        market: Market order, only applicable to spot/margin/futures/perpetual
        limit: Limit order
        post_only: Post only order
        fok: Fill or kill
        ioc: Immediate or cancel
        optimal_limit_ioc: Market order immediate or cancel (only for futures and perpetual)
        mmp: Market maker protection (only for option orders under portfolio margin account mode)
        mmp_and_post_only: Market maker protection and post only (only for option orders under portfolio margin account mode)
        elp: Enhanced liquidity program order
        
        am tif: "GTC" "IOC" "FOK" "GTX"
        """
        if order.type.upper() == "LIMIT":
            if order.tif.upper() == "GTX":
                return "post_only"
            elif order.tif.upper() == "GTC":
                return "limit"
            else:
                return order.tif.lower()
        else:
            return "post_only"
        
    def balance(self):
        return self.account_api.get_account_balance()
    
    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ Make batch orders
        OKX parameters:
        [
            {
                "instId":"BTC-USDT",
                "tdMode":"cash",
                "clOrdId":"b15",
                "side":"buy",
                "ordType":"limit",
                "px":"2.15",
                "sz":"2"
            },
            {
                "instId":"BTC-USDT",
                "tdMode":"cash",
                "clOrdId":"b16",
                "side":"buy",
                "ordType":"limit",
                "px":"2.15",
                "sz":"2"
            }
        ]
        
        Okx response:
        {
            "code":"0",
            "msg":"",
            "data":[
                {
                    "clOrdId":"oktswap6",
                    "ordId":"12345689",
                    "tag":"",
                    "ts":"1695190491421",
                    "sCode":"0",
                    "sMsg":""
                },
                {
                    "clOrdId":"oktswap7",
                    "ordId":"12344",
                    "tag":"",
                    "ts":"1695190491421",
                    "sCode":"0",
                    "sMsg":""
                }
            ],
            "inTime": "1695190491421339",
            "outTime": "1695190491423240"
        }        
        """
        okx_orders = [{
            "instId":self._norm_symbol(item.symbol),
            "tdMode":"cash",
            "clOrdId":self._norm_client_id(item.client_id),
            "side":item.side.lower(),
            "ordType":self._norm_type(item),
            "px":item.price,
            "sz":item.quantity
        } for item in orders]
        am_res = []
        for i in range(0, len(okx_orders), BATCH_ORDER_SIZE):
            sub_orders = okx_orders[i:i+BATCH_ORDER_SIZE]
            okx_res = self.trade_api.place_multiple_orders(sub_orders)
            sub_success = 0
            # 'ordId': '3150789784915664896', 'sCode': '0'
            if okx_res.get("data"):
                for item in okx_res["data"]:
                    if item.get("ordId") and item["sCode"] == '0':
                        am_res.append(OrderID(order_id=item["ordId"],
                                            client_id=self._recover_client_id(item["clOrdId"])))
                        sub_success += 1
                    else:
                        self.logger.error("[%s] failed to place order: %s", symbol, item)
            if sub_success < len(sub_orders):
                self.logger.error("%s/%s order succeeded: okx make order return: %s", 
                                  sub_success, len(sub_orders), okx_res)
        return am_res
            
    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ List open orders
        OKX parameter:
        Parameter name Type Required Description
        instType String No Product type
                    SPOT: Spot
                    MARGIN: Margin
                    SWAP: Perpetual Swap
                    FUTURES: Futures
                    OPTION: Option
        instFamily String No Trading pair
                    Applicable to futures/perpetual/option
        instId String No Product ID, e.g., BTC-USDT
        ordType String No Order type
                    market: Market order
                    limit: Limit order
                    post_only: Post only order
                    fok: Fill or kill
                    ioc: Immediate or cancel
                    optimal_limit_ioc: Market order immediate or cancel (only for futures and perpetual)
                    mmp: Market maker protection (only for option orders under portfolio margin account mode)
                    mmp_and_post_only: Market maker protection and post only (only for option orders under portfolio margin account mode)
                    op_fok: Option simple selection (fill or kill)
                    elp: Enhanced liquidity program order
        state String No Order status
                    live: Order pending
                    partially_filled: Partially filled
        after String No Pagination of content before this ID (older data), value is ordId from corresponding interface
        before String No Pagination of content after this ID (newer data), value is ordId from corresponding interface
        limit String No Number of results, maximum 100, default 100
        
        Okx response:
        {
            "code": "0",
            "data": [
                {
                    "ordId": "1752588852617379840",
                    "clOrdId": "",
                    "accFillSz": "0",
                    "state": "live",
                    "px": "13013.5",
                    "side": "buy",
                    "sz": "0.001",
                    "cancelSourceReason": "",
                    ...
                }
            ],
            "msg": ""
        }
        """
        okx_res = self.trade_api.get_order_list(instType='SPOT', instId=self._norm_symbol(symbol))
        if okx_res["code"] =='0'and okx_res.get("data"):
            return [OrderStatus(
                order_id=item["ordId"],
                client_id=self._recover_client_id(item["clOrdId"]),
                side=item["side"],
                price=item["px"],
                state=self._norm_state(item),
                origQty=item["sz"]
            ) for item in okx_res["data"]]
        self.logger.error("[%s] open orders error!: %s", symbol, okx_res)
        return []
       
    def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
        """ batch cancel orders
        Okx parameters:
        instId String Yes Product ID, e.g., BTC-USD-190927
        ordId String Optional Order ID, must provide either ordId or clOrdId, if both provided, ordId takes precedence
        clOrdId String Optional User-defined ID
        
        Okx response:
        {
            "code":"0",
            "msg":"",
            "data":[
                {
                    "clOrdId":"oktswap6",
                    "ordId":"12345689",
                    "ts":"1695190491421",
                    "sCode":"0",
                    "sMsg":""
                },
                {
                    "clOrdId":"oktswap7",
                    "ordId":"12344",
                    "ts":"1695190491421",
                    "sCode":"0",
                    "sMsg":""
                }
            ],
            "inTime": "1695190491421339",
            "outTime": "1695190491423240"
        }
        """
        okx_list = [{
            "instId": self._norm_symbol(symbol),
            "ordId": item
        } for item in order_ids]
        am_res = []
        for i in range(0, len(okx_list), BATCH_CANCEL_SIZE):
            sub_list = okx_list[i: i+BATCH_CANCEL_SIZE]
            okx_res = self.trade_api.cancel_multiple_orders(sub_list)
            cancel_success = 0
            if okx_res.get("data"):
                for item in okx_res["data"]:
                    if item["sCode"] == '0':
                        am_res.append(OrderID(order_id=item["ordId"], client_id=""))
                        cancel_success += 1
                if cancel_success < len(sub_list):
                    self.logger.error("[%s] batch_cancel error! return: %s", symbol, okx_res)            
                    self.logger.error("%s / %s orders canceled", cancel_success, len(sub_list))
        return am_res
        
    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """ cancel single order
        Okx params:
        instId String Yes Product ID, e.g., BTC-USDT
        ordId String Optional Order ID, must provide either ordId or clOrdId, if both provided, ordId takes precedence
        clOrdId String Optional User-defined ID

        Okx response:
        {
            "code":"0",
            "msg":"",
            "data":[
                {
                    "clOrdId":"oktswap6",
                    "ordId":"12345689",
                    "ts":"1695190491421",
                    "sCode":"0",
                    "sMsg":""
                }
            ],
            "inTime": "1695190491421339",
            "outTime": "1695190491423240"
        }
        """
        okx_res = self.trade_api.cancel_order(instId=self._norm_symbol(symbol), ordId=order_id)
        if okx_res["code"] =='0'and okx_res.get("data"):
            return OrderID(order_id=okx_res["data"][0]["ordId"],
                           client_id=self._recover_client_id(okx_res["data"][0]["clOrdId"]))
        self.logger.error("[%s] cancel_order error!: %s", symbol, okx_res)           
        return None

    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ get order status
        Okx response: same as open_orders
        {'code': '0', 'data': [{'accFillSz': '0', 'algoClOrdId': '', 'algoId': '', 'attachAlgoClOrdId': '', 
        'attachAlgoOrds': [], 'avgPx': '', 'cTime': '1766406724251', 'cancelSource': '', 'cancelSourceReason': '', 
        'category': 'normal', 'ccy': 'USDT', 'clOrdId': '10NSlAsH1766406718026S1', 'fee': '0', 'feeCcy': 'BTC', 
        'fillPx': '', 'fillSz': '0', 'fillTime': '', 'instId': 'BTC-USDT', 'instType': 'SPOT', 'isTpLimit': 
        'false', 'lever': '', 'linkedAlgoOrd': {'algoId': ''}, 'ordId': '3150906262616793088', 'ordType': 'post_only', 
        'pnl': '0', 'posSide': 'net', 'px': '60205.9', 'pxType': '', 'pxUsd': '', 'pxVol': '', 'quickMgnType': '', 
        'rebate': '0', 'rebateCcy': 'USDT', 'reduceOnly': 'false', 'side': 'buy', 'slOrdPx': '', 'slTriggerPx': '', 
        'slTriggerPxType': '', 'source': '', 'state': 'live', 'stpId': '', 'stpMode': 'cancel_maker', 'sz': '0.00005', 
        'tag': '', 'tdMode': 'cash', 'tgtCcy': '', 'tpOrdPx': '', 'tpTriggerPx': '', 'tpTriggerPxType': '', 'tradeId': '', 
        'tradeQuoteCcy': 'USDT', 'uTime': '1766406724251'}], 'msg': ''}        
        """
        okx_res = self.trade_api.get_order(self._norm_symbol(symbol), order_id)
        if okx_res["code"] == "0" and okx_res.get("data"):
            return [OrderStatus(
                order_id=okx_res["data"][0]["ordId"],
                client_id=self._recover_client_id(okx_res["data"][0]["clOrdId"]),
                side=okx_res["data"][0]["side"].upper(),
                price=okx_res["data"][0]["px"],
                origQty=okx_res["data"][0]["sz"],
                state=self._norm_state(okx_res["data"][0])
            )]
        self.logger.error("[%s] order_status error!: %s", symbol, okx_res)   
        return []

    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ get best ask and bid
        OKX params:
        instId String Yes Product ID, e.g., BTC-USDT
        sz String No Number of depth levels, maximum 400, i.e., total 800 buy and sell depth levels
        If not provided, returns 1 level of depth data by default
        
        OKX response:
        {'code': '0', 'msg': '', 'data': [{'asks': [['90298.9', '0.01289437', '0', '1']], 'bids': [['90298.8', '1.24886534', '0', '23']], 'ts': '1765456248101'}]}
        """
        okx_res = self.market_data_api.get_orderbook(self._norm_symbol(symbol), "1")
        if okx_res["code"] =='0'and okx_res.get("data"):
            return [AskBid(ap=okx_res["data"][0]["asks"][0][0],
                           aq=okx_res["data"][0]["asks"][0][1],
                           bp=okx_res["data"][0]["bids"][0][0],
                           bq=okx_res["data"][0]["bids"][0][1])]
        self.logger.error("top_askbid error! %s", okx_res)
        return []
    
    def ticker(self, symbol: str) -> list[Ticker]:
        """ Get latest tickers
        Okx response:
        {'code': '0', 'msg': '', 'data': [{'instType': 'SPOT', 'instId': 'BTC-USDT', 'last': '90323.5', 'lastSz': '0.00031774', 'askPx': '90323.5', 'askSz': '0.11424733', 'bidPx': '90323.4', 'bidSz': '1.00466387', 'open24h': '92130.9', 'high24h': '94495.2', 'low24h': '89389.8', 'volCcy24h': '755061593.416869545', 'vol24h': '8257.94439996', 'ts': '1765456321422', 'sodUtc0': '92013.6', 'sodUtc8': '92070'}]}
        """
        okx_res = self.market_data_api.get_ticker(self._norm_symbol(symbol))
        if okx_res["code"] =='0'and okx_res.get("data"):
            return [Ticker(s=symbol, p=okx_res["data"][0]["last"], q=okx_res["data"][0]["lastSz"])]
        self.logger.error("ticker error! %s", okx_res)
        return []