## STANDARD MARKET MAKING INTERFACE
Base class for exchange client : [**BaseClient**](../octopuspy/exchange/base_restapi.py)

### GET MARKET INFO
1. ASK1 AND BID1 PRICE
```python
    def top_askbid(self, symbol: str) -> list[AskBid]:
```
2. TICKERS
```python
    def ticker(self, symbol: str) -> list[Ticker]:
```

### TRADE
1. MAKE MULTIPLE ORDERS
```python
    def batch_make_orders(self, orders: list[NewOrder], symbol: str = '') -> list[OrderID]:
```
2. CANCEL MULTIPLE ORDERS
```python
    def batch_cancel(self, order_ids: list[str], symbol: str) -> list[OrderID]:
```
3. CANCEL ONE ORDER
```python
    def cancel_order(self, order_id: str, symbol: str = '') -> OrderID:
```

### STATUS
1. GET OPEN ORDERS
```python
    def open_orders(self, symbol: str) -> list[OrderStatus]:
```
2. GET ORDER STATUS
```python
    def order_status(self, order_id: str, symbol: str = '') -> list[OrderStatus]:
```

## DATA FLOW TO EXHANGES

```mermaid
graph TD
    %% Modules
    subgraph "Strategy layer"
        A[MARKET MAKING<br/>STRATEGY]
    end
    
    subgraph "Client layer"
        B["ExchangeClient (implements BaseClient)"]
    end
    
    subgraph "Interface layer"
        D[Exchange API]
    end
    
    %% Connections
    A -- "1. market making command" --> B
    B -- "4. result" --> A
    B -- "2. call" --> D
    D -- "3. return" --> B
    
    %% Styles
    style A fill:#c8e6c9,color:#1b5e20
    style B fill:#bbdefb,color:#0d47a1
    style D fill:#ffecb3,color:#e65100
```