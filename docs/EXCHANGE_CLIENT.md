## INHERIT [**BaseClient**](../octopuspy/exchange/base_restapi.py)
For example : [**OkxSpotClient**](../octopuspy/exchange/okx_restapi.py)
```python
class OkxSpotClient(BaseClient):
    def __init__(
        self,
        params: ClientParams,
        logger: Logger = logging.getLogger(__file__)
    ):
    ...
# Parameters for create a new restful client
ClientParams = namedtuple('ClientParams', ['base_url', 'api_key', 'secret', 'passphrase'])
```

### Pre-requirements
When you want to make deal in one exchange, eg. OKX, you will need:

```py
BASE_URL = 'The exchange api url'
API_KEY = "Your api_key"
SECRET = "Your api_secret"
PASSPHRASE = "" # Do not required by Binance, but required by OKX
```

Apply your account on the exchange homepage, you will find these informations in your account if you are given permision to APIs. Find and use them in your program.  

Almost all exchanges need BASE_URL, API_KEY, SECRET. Some exchanges need PASSPHRASE.

### Implements market making interface
1. Get ask1 and bid1 price, Get tickers.  
```python
def top_askbid(self, symbol: str) -> list[AskBid]:
def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
```
Market making strategies need these datas to calculate your order price.  
Call exchange APIs and map return data to OrderID structure, like this:
```python
if okx_res["code"] =='0'and okx_res.get("data"):
    return [AskBid(ap=okx_res["data"][0]["asks"][0][0],
                    aq=okx_res["data"][0]["asks"][0][1],
                    bp=okx_res["data"][0]["bids"][0][0],
                    bq=okx_res["data"][0]["bids"][0][1])]
```
2. Check status of your deals
```python
def open_orders(self, symbol: str) -> list[OrderStatus]:
def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
```
Map APIs return to unified data structure, like this:
```py
if okx_res["code"] =='0'and okx_res.get("data"):
    return [OrderStatus(
        order_id=item["ordId"],
        client_id=self._recover_client_id(item["clOrdId"]),
        side=item["side"],
        price=item["px"],
        state=self._norm_state(item),
        origQty=item["sz"]
    ) for item in okx_res["data"]]
```
3. Control your dealing process
```py
def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:    
```
Use these 3 interfaces to make profit: making orders with proper price, waiting orders to be filled, cancel orders to releas the funds occupied by the exchange. 
## UNIFIED DATA STRUCTURE FOR MARKET MAKING
Market making strategies use these datas to make deals across different exchanges. More exchanges generally bring more profit opportunities.
```py
# parameters for putting a new order
NewOrder = namedtuple('NewOrder', ['symbol', 'client_id', 'side', 'type', 'quantity', 'price', 'biz_type', 'tif', 'reduce_only', 'position_side', 'bait', 'selftrade_enabled'])
# parameters for response of open orders
OrderID = namedtuple('OrderID', ['order_id', 'client_id'])
# parameters for response of order status
OrderStatus = namedtuple('OrderStatus', ['order_id', 'client_id', 'side', 'price', 'state', 'origQty'])
# parameters for realtime dealing. s for symbol, p for price, q for quantity
Ticker = namedtuple('Ticker', ['s', 'p', 'q']) 
# parameters for asks and bids.
# ap for ask price, aq for ask quantity, bp for bid price, bq for bid quantity
AskBid = namedtuple('AskBid', ['ap', 'aq', 'bp', 'bq'])
```