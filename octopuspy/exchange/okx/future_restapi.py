""" OKX future API
    online doc: https://www.okx.com/docs-v5/
"""

import os
import sys
import math
from logging import Logger
from collections import namedtuple
from okx import PublicData

PROJ_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_PATH not in sys.path:
    sys.path.insert(0, PROJ_PATH)
    
from ..base_restapi import AskBid, ClientParams, NewOrder, OrderID, OrderStatus, Ticker
from .spot_restapi import OkxSpotClient

# parameters for contract instrument
ContractInfo = namedtuple('ContractInfo', ['symbol', 'biz_type', 'group_id', 'ct_val', 'lever', 'lot_size', 'tick_size'])
"""
Trading Type    SPOT: Spot
                MARGIN: Margin
                SWAP: Perpetual Swap
                FUTURES: Futures
                OPTION: Option
groupId         Perpetual Swap:
                1: Coin-Margined Swap
                2: USDT-Margined Swap
                3: USDC-Margined Swap
                4: Swap Group 1
                5: Swap Group 2
ctVal   String  Contract face value, only applicable to futures/perpetual/option
lever   String  Maximum leverage supported by this instId, not applicable to spot and option
lotSz   String  Order quantity precision, in lots
"""

BATCH_SIZE = 20

class OkxFutureClient(OkxSpotClient):
    def __init__(self, params: ClientParams, logger: Logger):
        """ https://www.okx.com """
        super().__init__(params, logger)
        if not self.base_url:
            self.base_url = "https://www.okx.com" # default
        self.public_api = PublicData.PublicAPI(api_key=self.api_key,
                                               api_secret_key=self.secret,
                                               passphrase=self.passphrase,
                                               use_server_time=False,
                                               flag=self.demo_trading,
                                               domain = self.base_url)
        # Set position mode: long_short_mode - Open/Close mode, net_mode - Buy/Sell mode
        self.account_api.set_position_mode(posMode="net_mode")
        self.account_api.set_leverage(lever="1", mgnMode="isolated")
        self.contract_config={}
        
    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ Place multiple future orders:
        - tdMode: isolated：Isolated ；cross：Cross
        ccy: Margin currency, applicable to isolated margin and cross margin in futures mode, optional parameter
        posSide: Position side, mandatory in open/close mode, only long or short can be selected. Only applicable to futures and perpetual.
        
        - For option orders, only one of px/pxUsd/pxVol can be filled
        px: Order price, only applicable to limit, post_only, fok, ioc, mmp, mmp_and_post_only order types
        pxUsd: Place option order in USD price, only applicable to options
        pxVol: Place option order by implied volatility, e.g., 1 means 100%, only applicable to options
        
        - Operations for dual position direction
        Open long: Buy to open long (side: buy; posSide: long)
        Open short: Sell to open short (side: sell; posSide: short)
        Close long: Sell to close long (side: sell; posSide: long)
        Close short: Buy to close short (side: buy; posSide: short)
        
        - Set position mode
        https://www.okx.com/docs-v5/zh/#trading-account-rest-api-set-position-mode
        
        - 
        
        px
        For option orders, the order price must be an integer multiple of tickSz. Non-integers will be rounded.
        
        """
        norm_symbol = self._norm_symbol(symbol)
        if not self.contract_config.get(norm_symbol):
            _info = self.instrument_info(norm_symbol)
            self.contract_config[norm_symbol] = _info
        ct_val = float(self.contract_config[norm_symbol].ct_val)    # Contract face value
        lot_size = float(self.contract_config[norm_symbol].lot_size)    # Quantity precision
        # tick_size = float(self.contract_config[norm_symbol].tick_size)  # Contract unit, not used for now
        okx_orders = []
        for item in orders:
            okx_order = {
                "instId":norm_symbol,
                "tdMode":"isolated",
                "clOrdId":self._norm_client_id(item.client_id),
                "side":item.side.lower(),
                "ordType":self._norm_type(item),
                "px":item.price,
                "sz":str(round(item.quantity/ct_val, int(-math.log10(lot_size)))),
                "posSide": "net",  # Buy/Sell mode
            }
            okx_orders.append(okx_order)
            self.logger.debug("okx_orders: %s", okx_orders)

        am_res = []
        for i in range(0, len(okx_orders), BATCH_SIZE):
            sub_orders = okx_orders[i:i+BATCH_SIZE]
            okx_res = self.trade_api.place_multiple_orders(sub_orders)
            sub_success = 0
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
        
    def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
        """
        * symbol like: "BTC-USD-SWAP"
        """
        return super().batch_cancel(order_ids, symbol)
    
    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """
        * symbol like: "BTC-USD-SWAP"
        """
        return super().cancel_order(order_id, symbol)
    
    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """
        * symbol like: "BTC-USD-SWAP"
        """
        return super().order_status(order_id, symbol)
    
    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ Ask1 and Bid1 data
        * symbol like: "BTC-USD-SWAP"
        """
        return super().top_askbid(symbol)
    
    def ticker(self, symbol: str) -> list[Ticker]:
        """ Ticker of a single symbol
        * symbol like: "BTC-USD-SWAP"
        """
        return super().ticker(symbol)
    
    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ List open orders
        """
        okx_res = self.trade_api.get_order_list(instType='SWAP', instId=self._norm_symbol(symbol))
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
    
    def get_positions(self):
        """
        GET /api/v5/account/positions
        """
        return self.account_api.get_positions()
    
    def instrument_info(self, symbol:str) -> ContractInfo:
        """
        GET /api/v5/public/instruments
        """
        res = self.public_api.get_instruments(instType="SWAP", instId=self._norm_symbol(symbol))
        if res["code"]=="0" and res.get("data"):
            # 'symbol', 'biz_type', 'group_id', 'ct_val', 'lever', 'lot_size'
            return ContractInfo(symbol=res["data"][0].get("instId", ""),
                                biz_type=res["data"][0].get("instType", ""),
                                ct_val=res["data"][0].get("ctVal", ""),
                                group_id=res["data"][0].get("groupId", ""),
                                lever=res["data"][0].get("lever", ""),
                                lot_size=res["data"][0].get("lotSz"),
                                tick_size=res["data"][0].get("tickSz"))
        return ContractInfo("","","1","","","1","1")
