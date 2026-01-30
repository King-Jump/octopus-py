## EXCHANGE CLIENT UNIT TEST
Some exchanges provide sandbox environments for testing client code; however, many do not. Therefore, using unit tests to validate the exchange client before launch is crucial. This practice helps prevent financial losses that could result from undetected errors in the code.

## Overview
The OctopusPy Test Framework is a comprehensive unit testing system designed to validate exchange client implementations. It provides a structured approach to testing key exchange functionalities with color-coded output for improved test result visualization.   

Test output:  
![alt text](images/test_output.png)

Where <span style="color:green">green</span> mean passed test cases, <span style="color:red">red</span> mean failed cases. Check program for bugs.

## Class Inheritance Hierarchy

```
unittest.TestCase
    └── ColorfulTestCase
        └── ExchangeTest
            └── OkxUnitTest
```
Example : [**OkxUnitTest**](../tests/exchange_unittest_okx.py)

## Class Details

### 1. `Color` Class

**Purpose**: Provides ANSI color codes and formatting utilities for terminal output.

**Key Features**:
- **Color Constants**: Basic colors (RED, GREEN, BLUE, etc.), bright variants, and background colors
- **Style Constants**: Text formatting (BOLD, UNDERLINE, ITALIC, etc.)
- **Utility Method**: `colorize()` method to apply multiple styles to text

**Implementation Notes**:
- Uses ANSI escape sequences for terminal coloring
- Provides both class-level constants and instance methods
- Supports chaining multiple styles in `colorize()` method

### 2. `ColorfulTestCase` Class

**Purpose**: Extends `unittest.TestCase` with colored output capabilities.

**Inheritance**: `ColorfulTestCase(unittest.TestCase)`

**Key Methods**:

#### Logging Methods:
- `log_info(message)`: Blue-colored informational messages
- `log_success(message)`: Green bold success messages  
- `log_warning(message)`: Yellow warning messages
- `log_error(message)`: Red bold error messages
- `log_debug(message)`: Cyan debug messages
- `log_custom()`: Flexible method for custom color/style combinations

#### Colored Assertion Methods:
- `assertEqualWithColor()`: Colored version of `assertEqual`
- `assertTrueWithColor()`: Colored version of `assertTrue`
- `assertIsInstanceWithColor()`: Colored version of `assertIsInstance`
- `assertInWithColor()`: Colored version of `assertIn`

**Design Pattern**: Uses the Template Method pattern to extend unittest's assertion methods with visual enhancements.

### 3. `ExchangeTest` Class

**Purpose**: Concrete test class for exchange client validation.

**Inheritance**: `ExchangeTest(ColorfulTestCase)`

**Test Configuration**:
- `SYMBOL`: Trading pair symbol (default: "BTC_USDT")
- `INTERMEDIATE_RESULT`: Dictionary for sharing data between test methods
- Test parameters: `price_decimal`, `qty_decimal`, `order_pairs`, `biz_type`

## Test Method Implementation

### Test Sequence Flow

```
setUp() → test_01_ask_bid() → test_02_latest_price() → test_03_batch_make_orders() → 
test_04_open_orders() → test_05_order_status() → test_06_cancel_order() → 
test_07_batch_cancel_order() → tearDown()
```

### Individual Test Methods

#### 1. `test_01_ask_bid()`
- **Purpose**: Tests market depth (order book) retrieval
- **Expected Data**: `List[AskBid]`
- **Validations**: Type checks for `AskBid` structure and its fields

#### 2. `test_02_latest_price()`
- **Purpose**: Tests ticker price retrieval  
- **Expected Data**: `List[Ticker]`
- **Validations**: Type checks and stores last price for subsequent tests

#### 3. `test_03_batch_make_orders()`
- **Purpose**: Tests batch order placement
- **Order Generation**: Creates BUY/SELL order pairs based on last price
- **Expected Data**: `List[OrderID]`
- **Validations**: Order structure, non-empty IDs, count matching

#### 4. `test_04_open_orders()`
- **Purpose**: Tests retrieval of open orders
- **Expected Data**: `List[OrderStatus]`
- **Validations**: Order state, ID matching, structure integrity

#### 5. `test_05_order_status()`
- **Purpose**: Tests individual order status query
- **Expected Data**: `List[OrderStatus]`
- **Validations**: Order state enumeration validation

#### 6. `test_06_cancel_order()`
- **Purpose**: Tests single order cancellation
- **Expected Data**: `OrderID`
- **Validations**: Non-empty order ID in response

#### 7. `test_07_batch_cancel_order()`
- **Purpose**: Tests batch order cancellation
- **Expected Data**: `List[OrderID]`
- **Validations**: Empty open orders after cancellation

## Key Implementation Patterns

### 1. **Test Data Sharing Pattern**
- Uses `INTERMEDIATE_RESULT` dictionary to share data between sequential tests
- Enables dependent tests (e.g., order tests depend on prices from market data tests)

### 2. **Colored Assertion Pattern**
- Wraps standard assertions with color output
- Provides visual feedback without compromising test framework compatibility

### 3. **Graceful Degradation Pattern**
- Tests include fallback mock data when real data is unavailable
- Example: Uses timestamp as mock order ID when no real orders exist

### 4. **Parameterized Testing Pattern**
- Test configuration through `setUp()` parameters
- Supports different symbols, decimal precision, and order quantities

### 5. **State Validation Pattern**
- Validates order states against predefined constants
- Ensures exchange returns standardized state values

## Usage Example
```python
class OkxUnitTest(ExchangeTest):
    def setUp(self):
        super().setUp(symbol="BTC_USDT", price_decimal=1, qty_decimal=6)
        params = ClientParams(BASE_URL, API_KEY, SECRET, PASSPHRASE)
        self.client = OkxSpotClient(params, LOGGER)
    # More customized test case here
    def test_00_account_balance(self):
        ''' check USDT balance
        '''
        print("### test_00_account_balance ###")
        res = self.client.balance()
        print("account balance %s", res)
```

## Best Practices

1. **Test Isolation**: Each test method should be independent, using shared state only through `INTERMEDIATE_RESULT`

2. **Error Handling**: Tests include try-catch blocks with colored error logging

3. **Sleep Management**: Proper delays (`time.sleep()`) between operations to respect API rate limits

4. **Mock Data Support**: Graceful handling of missing real data with mock alternatives

5. **Validation Depth**: Multiple assertion levels (type, value, structure) for comprehensive validation

## Extension Points

1. **Add Custom Tests**: Extend `ExchangeTest` with additional test methods
2. **Custom Assertions**: Add more colored assertion methods in `ColorfulTestCase`
3. **Configuration**: Externalize test parameters via configuration files or environment variables
4. **Async Support**: Extend for asynchronous client implementations
5. **Performance Metrics**: Add timing measurements for performance testing

This framework provides a robust foundation for exchange client testing with visual feedback and comprehensive validation of exchange API implementations.

