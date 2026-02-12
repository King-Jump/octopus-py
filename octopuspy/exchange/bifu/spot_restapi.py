import time
import hmac
import hashlib
import requests
from logging import Logger

from ..base_restapi import ORDER_STATE_CONSTANTS, AskBid, BaseClient, NewOrder, OrderID, OrderStatus, Ticker, ClientParams
BATCH_SIZE = 20

TIF_MAP = {
    'GTC': 'GOOD_TIL_CANCEL',
    'GTX': 'POST_ONLY',
    'FOK': 'FILL_OR_KILL',
    'IOC': 'IMMEDIATE_OR_CANCEL'
}

class BIFU_ORDER_STATE_CONSTANTS(ORDER_STATE_CONSTANTS):
    """ UNKNOWN_ORDER_STATUS, PENDING, OPEN, FILLED, CANCELING, CANCELED, UNTRIGGERED, UNRECOGNIZED
    """
    @classmethod
    def parse(cls, state: str) -> int:
        """ parse state to int
        """
        if state == 'OPEN':
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

BIFU_BASE_URL = "https://api.bifu.co"
BIFU_TEST_URL = "http://api.bifu.internal"

class BifuSpotClient(BaseClient):
    """ Restful API Client for Spot Trading of BiFu
    """
    def __init__(self, params: ClientParams, logger: Logger):
        """ https://api.bifu.co """
        super().__init__(params, logger)
        if not self.base_url:
            self.base_url = BIFU_TEST_URL # default
    
    def _sign(self, path):
        ts = int(1000 * time.time())
        message = f'{path}|{ts}'

        signature = hmac.new(
            self.secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
        return {
            'Decode-MM-Auth-Access-Key': self.api_key,
            'Decode-MM-Auth-Timestamp': str(ts),
            'Decode-MM-Auth-Signature': signature.hexdigest(),
        }

    def _get(self, path, headers: dict = None):
        if headers:
            return requests.get(url=f'{self.base_url}{path}', headers=headers, timeout=5)
        return requests.get(f'{self.base_url}{path}', timeout=5)

    def top_askbid(self, symbol: str) -> list[AskBid]:
        """ limit must be 15 or 200"""
        if self.mock:
            return super().top_askbid(symbol)   # call mock function if self.mock
        res = self.order_book(symbol, limit=15)
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

    def order_book(self, symbol: str, limit: int = 15) -> dict:
        """ Response
        {
            'code': 'SUCCESS',
            'data': [
                {
                    'startVersion': '72150613',
                    'endVersion': '72150633',
                    'level': 15,
                    'instrumentId': '90000001',
                    'asks': [
                        {'price': '118030.3', 'size': '1.070'},
                        {'price': '118032.4', 'size': '4.814'},
                    ],
                    'bids': [
                        {'price': '117807.8', 'size': '1.015'},
                        {'price': '117804.1', 'size': '5.642'},
                    ],
                    'depthType': 'SNAPSHOT'
                }
            ],
            'msg': None,
            'params': None,
            'requestTime': '1753281902961',
            'responseTime': '1753281902981',
            'traceId': 'eb2247f957fc8dea4a88b9a6b42d5570'
        }
        """
        path = f'/api/v1/public/quote/getDepth?instrumentId={symbol}&level={limit}'
        try:
            res = self._get(path).json()
        except requests.exceptions.RequestException:
            self.logger.error('order_book request %s failed', path)
            return {'asks': [], 'bids': []}
        if res.get('code') == 'SUCCESS' and res.get('data'):
            return {
                'asks': [(ask['price'], ask['size']) for ask in res['data'][0]['asks']],
                'bids': [(bid['price'], bid['size']) for bid in res['data'][0]['bids']],
            }
        return {'asks': [], 'bids': []}

    def ticker(self, symbol: str) -> list[Ticker]:
        """ Get latest tickers of given symbols
        {
            'code': 'SUCCESS',
            'data': [
                {'instrumentId': '90000001', 'priceChange': '-1941.54',
                 'priceChangePercent': '-0.020843', 'trades': '268520', 'size': '1640.70124',
                 'value': '151561223.9328885', 'high': '93613.72', 'low': '90890.92',
                 'open': '93147.99', 'close': '91206.45', 'highTime': '1764839357107',
                 'lowTime': '1764876203180', 'startTime': '1764836100000',
                 'endTime': '1764934200000', 'lastPrice': '91206.45', 'markPrice': '0',
                 'indexPrice': '0', 'openInterest': '0'}
            ], 'msg': None, 'params': None, 'requestTime': '1764934994042',
            'responseTime': '1764934994050', 'traceId': 'c68e1c8d66871cebee61ba8b68110009'
        }
        """
        if self.mock:
            return super().ticker(symbol)   # call mock function if self.mock
        path = f'/api/v1/public/quote/getTicker?instrumentId={symbol}'
        try:
            res = requests.get(url=f'{self.base_url}{path}', timeout=5).json()
        except requests.exceptions.RequestException:
            self.logger.error('ticker request %s failed', path)
            return []
        if res.get('code') == 'SUCCESS' and res.get('data'):
            return [Ticker(s=symbol, p=res['data'][0]['lastPrice'], q=res['data'][0]['size'])]
        return []

    def symbol_info(self) -> dict:
        """ Response
            {
                'code': 'SUCCESS',
                'data': {
                    'global': {'leverageStepSize': '1'},
                    'coinList': [
                        {'coinId': '1', 'coinName': 'BTC', 'stepSize': '0.0000001', 'iconUrl': '', 'enableCollateral': False, 'enableSpotDeposit': True, 'enableSpotWithdraw': True},
                        {'coinId': '2', 'coinName': 'USDT', 'stepSize': '0.000000001', 'iconUrl': '', 'enableCollateral': True, 'enableSpotDeposit': True, 'enableSpotWithdraw': True},
                        {'coinId': '3', 'coinName': 'ETH', 'stepSize': '0.00000001', 'iconUrl': '', 'enableCollateral': False, 'enableSpotDeposit': True, 'enableSpotWithdraw': True},
                        {'coinId': '4', 'coinName': 'SOL', 'stepSize': '0.0001', 'iconUrl': '', 'enableCollateral': False, 'enableSpotDeposit': False, 'enableSpotWithdraw': False},
                    ],
                    'contractList': [
                        {'contractId': '10000001', 'contractName': 'BTC/USDT', 'baseCoinId': '1', 'quoteCoinId': '2', 'tickSize': '0.01', 'stepSize': '0.001', 'minOrderSize': '0.002', 'maxOrderSize': '90', 'maxPositionSize': '350',
                        'riskLimitTierList': [
                            {'tier': 1, 'startPositionValue': '0', 'endPositionValue': '200000', 'maxLeverage': '200', 'maintenanceMarginRate': '0.003'},
                            {'tier': 2, 'startPositionValue': '200001', 'endPositionValue': '400000', 'maxLeverage': '100', 'maintenanceMarginRate': '0.005'},
                            {'tier': 3, 'startPositionValue': '400001', 'endPositionValue': '800000', 'maxLeverage': '50', 'maintenanceMarginRate': '0.01'},
                            {'tier': 4, 'startPositionValue': '800001', 'endPositionValue': '1000000', 'maxLeverage': '40', 'maintenanceMarginRate': '0.0125'}
                        ], 'frozenMarginFloatingRatio': '0.01', 'frozenFillFeeFloatingRatio': '0.005', 'takerFeeRate': '0.0005', 'makerFeeRate': '0.0002',
                        'liquidateFeeRate': '0.01', 'defaultLeverage': '20', 'buyLimitPriceRatio': '0.1', 'sellLimitPriceRatio': '0.1',
                        'longLimitLiquidatePrice': '25', 'shortLimitLiquidatePrice': '25000000', 'marketOpenLimitSize': '30', 'marketCloseLimitSize': '30',
                        'isPriceUseFeeRate': False, 'enableTrade': True, 'enableDisplay': True, 'enableOpenPosition': True,
                        'supportMarginModeList': ['SHARED', 'ISOLATED'], 'supportSeparatedModeList': ['COMBINED'], 'supportPositionModeList': [],
                        'isSupportTracing': True, 'isSupportPlanMarket': True, 'fundingInterestRate': '0.0003', 'fundingImpactMarginNotional': '1000',
                        'fundingMaxRate': '0.03', 'fundingMinRate': '-0.03', 'fundingRateIntervalMin': '480',
                        'fundingDailySettleTime': ['00:00:00', '08:00:00', '16:00:00'], 'displayDigitMerge': '0.1,1,10,50,100', 'displayMaxLeverage': '200',
                        'displayMinLeverage': '1', 'displayWebLeverageSettingList': ['1', '40', '80', '120', '160', '200'],
                        'displayAppLeverageSettingList': ['1', '40', '80', '120', '160', '200'], 'displayNew': False, 'displayHot': True,
                        'extraConfig': {'iconUrl': 'https://dcex.exchange/assets/crypto-icon/BTC.png', 'indexDataSource': 'binance, okex, huobi'},
                        'placeConfig': {}
                    }], 'symbolList': [
                        {
                            'symbolId': '90000001',
                            'symbolName': 'BTC-USDT',
                            'baseCoinId': '1',
                            'quoteCoinId': '2',
                            'tickSize': '0.1',      # price decimals
                            'stepSize': '0.001',    # qty decimals
                            'minOrderSize': '0.001', 'maxOrderSize': '100', 'takerFeeRate': '0.0005', 'makerFeeRate': '0.0002', 'buyLimitPriceRatio': '0.1', 'sellLimitPriceRatio': '0.1', 'marketBuyLimitSize': '50', 'marketSellLimitSize': '50', 'marketFallbackPriceRatio': None, 'enableTrade': True, 'enableDisplay': True, 'isSupportTracing': True, 'isSupportPlanMarket': True, 'displayDigitMerge': '0.1,1,10,100', 'displayNew': False, 'displayHot': True, 'extraConfig': {'productCode': 'cmt_btcusdt', 'iconUrl': 'https://dcex.exchange/assets/crypto-icon/BTC.png', 'preValue': '0.001', 'status': '1', 'simulation': 'false', 'symbolSort': '10001'}, 'placeConfig': {'serverCalPlace': '12', 'delegatePricePlace': '4', 'volumePlace': '0', 'pricePlace': '4', 'capitalRatePlace': '8', 'transferInOutPlace': '8', 'propertyPlace': '4', 'propertyHighPlace': '8', 'baseCoinPlace': '1'}},
                        {'symbolId': '90000002', 'symbolName': 'ETH-USDT', 'baseCoinId': '3', 'quoteCoinId': '2', 'tickSize': '0.01', 'stepSize': '0.0001', 'minOrderSize': '0.0001', 'maxOrderSize': '1000', 'takerFeeRate': '0.0005', 'makerFeeRate': '0.0002', 'buyLimitPriceRatio': '0.1', 'sellLimitPriceRatio': '0.1', 'marketBuyLimitSize': '500', 'marketSellLimitSize': '500', 'marketFallbackPriceRatio': None, 'enableTrade': True, 'enableDisplay': True, 'isSupportTracing': True, 'isSupportPlanMarket': True, 'displayDigitMerge': '0.01,0.1,1,10,50,100', 'displayNew': False, 'displayHot': True, 'extraConfig': {'productCode': 'cmt_ethusdt', 'iconUrl': 'https://dcex.exchange/assets/crypto-icon/ETH.png', 'preValue': '0.001', 'status': '1', 'simulation': 'false', 'symbolSort': '10001'}, 'placeConfig': {'serverCalPlace': '12', 'delegatePricePlace': '4', 'volumePlace': '0', 'pricePlace': '4', 'capitalRatePlace': '8', 'transferInOutPlace': '8', 'propertyPlace': '4', 'propertyHighPlace': '8', 'baseCoinPlace': '1'}},
                        {'symbolId': '90000003', 'symbolName': 'PEPE-USDT', 'baseCoinId': '23', 'quoteCoinId': '2', 'tickSize': '0.00000001', 'stepSize': '1', 'minOrderSize': '5000000', 'maxOrderSize': '5000000000', 'takerFeeRate': '0.0005', 'makerFeeRate': '0.0002', 'buyLimitPriceRatio': '0.1', 'sellLimitPriceRatio': '0.1', 'marketBuyLimitSize': '1000000000', 'marketSellLimitSize': '1000000000', 'marketFallbackPriceRatio': None, 'enableTrade': True, 'enableDisplay': True, 'isSupportTracing': True, 'isSupportPlanMarket': True, 'displayDigitMerge': '0.00000001,0.0000001,0.000001', 'displayNew': False, 'displayHot': True, 'extraConfig': {'productCode': 'cmt_ethusdt', 'iconUrl': 'https://dcex.exchange/assets/crypto-icon/PEPE.png', 'preValue': '0.001', 'status': '1', 'simulation': 'false', 'symbolSort': '10001'}, 'placeConfig': {'serverCalPlace': '12', 'delegatePricePlace': '4', 'volumePlace': '0', 'pricePlace': '4', 'capitalRatePlace': '8', 'transferInOutPlace': '8', 'propertyPlace': '4', 'propertyHighPlace': '8', 'baseCoinPlace': '1'}}
                    ]
                }, 'msg': None, 'params': None, 'requestTime': '1754558125947', 'responseTime': '1754558125948', 'traceId': '1165abe361997cf1029bd4d5c1c43eef'
            }
        """
        path = '/api/v1/public/meta/getMetaData'
        res = self._get(path)
        return res.json()

    def balance(self) -> dict:
        """ Response
        """
        path = '/api/v1/private/spot/account/getAccountAsset'
        headers = self._sign(path=path)
        res = self._get(path, headers=headers)
        return res.json()

    def open_orders(self, symbol: str) -> list[OrderStatus]:
        """ get open orders
            Response:
            [
                {
                    'id': '642860486513132526', # order id
                    'accountId': '642135290537837550', 
                    'symbolId': '90000001',     # btc/usdt
                    'baseCoinId': '1', 'quoteCoinId': '2',
                    'orderSide': 'BUY',
                    'price': '112233.3',
                    'size': '0.223',
                    'value': '0',
                    'clientOrderId': '6959282778423',
                    'type': 'LIMIT',
                    'timeInForce': 'GOOD_TIL_CANCEL',
                    'reduceOnly': False,
                    'triggerPrice': '0',
                    'isPositionTpsl': False,
                    'orderSource': 'WEB',
                    'openTpslParentOrderId': '0',
                    'isSetOpenTp': False,
                    'openTpParam': None,
                    'isSetOpenSl': False,
                    'openSlParam': None,
                    'extraType': '',
                    'extraDataJson': '',
                    'takerFeeRate': '0.00000000',
                    'makerFeeRate': '0.00000000',
                    'feeDiscount': '1',
                    'takerFeeDiscount': '1',
                    'makerFeeDiscount': '1',
                    'status': 'OPEN',   # status
                    'matchSequenceId': '72614583',
                    'triggerTime': '0',
                    'triggerPriceTime': '0',
                    'triggerPriceValue': '0',
                    'cancelReason': 'UNKNOWN_ORDER_CANCEL_REASON',
                    'latestFillPrice': '0',
                    'maxFillPrice': '0',
                    'minFillPrice': '0',
                    'cumFillSize': '0',
                    'cumFillValue': '0',
                    'cumFillFee': '0',
                    'createdTime': '1753269883755',
                    'updatedTime': '1753269883763'
                }
            ]
        """
        if self.mock:
            return super().open_orders(symbol)   # call mock function if self.mock
        path = '/api/v1/private/spot/order/getActiveOrderPage2'
        headers = self._sign(path=path)
        open_orders = []
        page_no = 0
        while 1:
            params = {
                'filterSymbolIdList': [symbol],
                'pageNo': page_no,
                'pageSize': 100,
            }
            res = requests.get(
                url=f'{self.base_url}{path}', params=params, headers=headers, timeout=5)
            page = res.json()
            if page.get('data') and page['data'].get('dataList'):
                open_orders.extend([OrderStatus(order_id=str(order['id']),
                    client_id=order['clientOrderId'],
                    side=order['orderSide'],
                    price=order['price'],
                    state=BIFU_ORDER_STATE_CONSTANTS.parse(order['status']),
                    origQty=order['size']) for order in page['data']['dataList'] if order['status'] != 'CANCELING'])
                page_no += 1
                if page['data']['nextFlag']:
                    continue
            break
        return open_orders

    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
        """ Response:
            {
                'code': 'SUCCESS',
                'data': {
                    'list': [
                        {'clientOrderId': '90000001_20307_55441935', 'successOrderId': 648356620849381850, 'errorDetail': {'code': None, 'msg': None}, 'success': True},
                        {'clientOrderId': '90000001_20307_55441948', 'successOrderId': 648356620849382874, 'errorDetail': {'code': None, 'msg': None}, 'success': True}
                    ]
                }, 'msg': None, 'params': None, 'requestTime': '1754580264285', 'responseTime': '1754580264297', 'traceId': '3e941956077878c6f6f87ecf041fa768'
            }
        """
        if self.mock:
            return super().batch_make_orders(orders, symbol)   # call mock function if self.mock
        path='/api/v1/private/spot/order/createOrderBatch'
        if len(orders) <= BATCH_SIZE:
            body = {
                "params": [{
                    "languageType": 0,
                    "sign": '',
                    "timeZone": "UTC+8",
                    "symbolId": order.symbol,
                    "orderSide": order.side,
                    "price": str(order.price),
                    "size": str(order.quantity),
                    "isQuoteSize": False,
                    "clientOrderId": order.client_id,
                    "type": 'LIMIT',
                    "timeInForce": TIF_MAP.get(order.tif, 'GOOD_TIL_CANCEL'),
                    "reduceOnly": False,
                    "triggerPrice": "0.0",
                    "positionTpsl": False,
                    "setOpenTp": False,
                    "setOpenSl": False,
                    "extraType": "",
                    "extraDataJson": ""
                } for order in orders]
            }

            headers = self._sign(path=path)
            try:
                res = requests.post(url=f'{self.base_url}{path}', json=body,
                    headers=headers, timeout=5).json()
                self.logger.debug("Client batch_make_orders response: %s", res)
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed: {e}")
                return []
            suc_orders = []
            if res and res['data'] and res['data']['list']:
                for item in res['data']['list']:
                    order_id = item.get('successOrderId')
                    if order_id:
                        suc_orders.append(OrderID(order_id=str(order_id),
                                          client_id=item.get('clientOrderId', '')))
            return suc_orders

        total_results = []
        for start in range(0, len(orders), BATCH_SIZE):
            body = {
                "params": [{
                    "languageType": 0,
                    "sign": '',
                    "timeZone": "UTC+8",
                    "symbolId": order.symbol,
                    "orderSide": order.side,
                    "price": str(order.price),
                    "size": str(order.quantity),
                    "isQuoteSize": False,
                    "clientOrderId": order.client_id,
                    "type": 'LIMIT',
                    "timeInForce": TIF_MAP.get(order.tif, 'GOOD_TIL_CANCEL'),
                    "reduceOnly": False,
                    "triggerPrice": "0.0",
                    "positionTpsl": False,
                    "setOpenTp": False,
                    "setOpenSl": False,
                    "extraType": "",
                    "extraDataJson": ""
                } for order in orders[start: start+BATCH_SIZE]]
            }

            headers = self._sign(path=path)
            try:
                res = requests.post(url=f'{self.base_url}{path}', json=body,
                    headers=headers, timeout=5).json()
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed: {e}")
                continue
            if res and res['data'] and res['data']['list']:
                for item in res['data']['list']:
                    order_id = item.get('successOrderId')
                    if order_id:
                        total_results.append(OrderID(order_id=str(order_id),
                                            client_id=item.get('clientOrderId', '')))
        return total_results

    def batch_cancel(self, order_ids: list, symbol: str = '') -> list[OrderID]:
        """ Response:
        {
            'code': 'SUCCESS',
            'data': {
                'cancelResultMap': {
                    '642900765957948398': 'SUCCESS',
                    '642860486513132526': 'SUCCESS'
                }
            },
            'msg': None,
            'params': None,
            'requestTime': '1753281239839',
            'responseTime': '1753281239843',
            'traceId': '0e64bc96b739ae8bb72aac63adf1005a'
        }
        """
        if self.mock:
            return super().batch_cancel(order_ids, symbol)   # call mock function if self.mock
        path = '/api/v1/private/spot/order/cancelOrderById'
        if len(order_ids) <= BATCH_SIZE:
            body = {'orderIdList': order_ids}
            headers = self._sign(path=path)
            res = requests.post(url=f'{self.base_url}{path}', json=body,
                headers=headers, timeout=5).json()
            results = []
            if res.get('code') == 'SUCCESS' and res.get('data') and res.get('data').get('cancelResultMap'):
                for cancel_id in res['data']['cancelResultMap']:
                    results.append(OrderID(order_id=cancel_id, client_id=''))
            return results

        total_results = []
        for start in range(0, len(order_ids), BATCH_SIZE):
            body = {'orderIdList': order_ids[start: start+BATCH_SIZE]}
            headers = self._sign(path=path)
            res = requests.post(url=f'{self.base_url}{path}', json=body,
                headers=headers, timeout=5).json()
            if res.get('code') == 'SUCCESS' and res.get('data') and res.get('data').get('cancelResultMap'):
                for cancel_id in res['data']['cancelResultMap']:
                    total_results.append(OrderID(order_id=cancel_id, client_id=''))
        return total_results

    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
        """ Cancel all the orders of given symbol
            {
                'code': 'SUCCESS',
                'data': {
                    'cancelResultMap': {
                        '648344415953234394': 'SUCCESS',
                        '648344489470989786': 'SUCCESS',
                        '648344549596333530': 'SUCCESS'
                    }
                },
                'msg': None, 'params': None, 'requestTime': '1754579969549',
                'responseTime': '1754579970261', 'traceId': '6aaa474859fd5f61a0a0043361475783'
            }
        """
        if self.mock:
            return super().cancel_order(order_id, symbol)   # call mock function if self.mock
        res = self.batch_cancel([order_id], symbol)
        if res:
            return res[0]
        return OrderID(order_id='', client_id='')

    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
        """ Response
        {
            'code': 'SUCCESS',
            'data': [
                {
                    'id': '642860486513132526',
                    'accountId': '642135290537837550',
                    'symbolId': '90000001',
                    'baseCoinId': '1',
                    'quoteCoinId': '2',
                    'orderSide': 'BUY',
                    'price': '112233.3',
                    'size': '0.223',
                    'value': '0',
                    'clientOrderId': '6959282778423',
                    'type': 'LIMIT',
                    'timeInForce': 'GOOD_TIL_CANCEL',
                    'reduceOnly': False,
                    'triggerPrice': '0',
                    'isPositionTpsl': False,
                    'orderSource': 'WEB',
                    'openTpslParentOrderId': '0',
                    'isSetOpenTp': False,
                    'openTpParam': None,
                    'isSetOpenSl': False,
                    'openSlParam': None,
                    'extraType': '',
                    'extraDataJson': '',
                    'takerFeeRate': '0.00000000',
                    'makerFeeRate': '0.00000000',
                    'feeDiscount': '1',
                    'takerFeeDiscount': '1',
                    'makerFeeDiscount': '1',
                    'status': 'OPEN',   # CANCELED
                    'matchSequenceId': '72614583',
                    'triggerTime': '0',
                    'triggerPriceTime': '0',
                    'triggerPriceValue': '0',
                    'cancelReason': 'UNKNOWN_ORDER_CANCEL_REASON',
                    'latestFillPrice': '0',
                    'maxFillPrice': '0',
                    'minFillPrice': '0',
                    'cumFillSize': '0',
                    'cumFillValue': '0',
                    'cumFillFee': '0',
                    'createdTime': '1753269883755',
                    'updatedTime': '1753269883763'
                }
            ],
            'msg': None,
            'params': None,
            'requestTime': '1753277073466',
            'responseTime': '1753277073504',
            'traceId': '835e34b15e345a12107cc3ba330ba2f2'
        }
        """
        if self.mock:
            return super().order_status(order_id, symbol)   # call mock function if self.mock
        path = '/api/v1/private/spot/order/getOrderById'
        query = f"orderIdList={order_id}"
        headers = self._sign(path=path)
        res = requests.get(url=f'{self.base_url}{path}', params=query, headers=headers, timeout=5).json()
        if res.get('code') == 'SUCCESS' and res.get('data'):
            return [OrderStatus(order_id=order['id'],
                    client_id=order['clientOrderId'],
                    side=order['orderSide'],
                    price=order['price'],
                    state=BIFU_ORDER_STATE_CONSTANTS.parse(order['status']),
                    origQty=order['size']) for order in res['data']]
        return []
