import unittest
import os
import sys
import time
import logging

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

SYMBOL = "BTC_USDT"
INTERMEDIATE_RESULT = {}

from octopuspy.exchange.base_restapi import BaseClient

from octopuspy.exchange.base_restapi import (
    NewOrder, OrderID, OrderStatus, Ticker, 
    AskBid, ORDER_STATE_CONSTANTS as order_state
)

class Color:
    """ANSI color code"""
    # Base color
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright color
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background color
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # style
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'
    
    # reset
    RESET = '\033[0m'
    
    @classmethod
    def colorize(cls, text, *styles):
        """为文本添加颜色和样式"""
        style_codes = ''.join(getattr(cls, style.upper()) for style in styles)
        return f"{style_codes}{text}{cls.RESET}"

class ColorfulTestCase(unittest.TestCase):
    """Base class for colorful test output"""
    
    def print_color(self, message, *styles):
        """Print colorful message"""
        print(Color.colorize(message, *styles))
    
    def log_info(self, message):
        """Info level log (blue)"""
        self.print_color(f"[INFO] {message}", "BLUE")
    
    def log_success(self, message):
        """Success level log (green)"""
        self.print_color(f"[SUCCESS] {message}", "GREEN", "BOLD")
    
    def log_warning(self, message):
        """Warning level log (yellow)"""
        self.print_color(f"[WARNING] {message}", "YELLOW")
    
    def log_error(self, message):
        """Error level log (red)"""
        self.print_color(f"[ERROR] {message}", "RED", "BOLD")
    
    def log_debug(self, message):
        """Debug level log (cyan)"""
        self.print_color(f"[DEBUG] {message}", "CYAN")
    
    def log_custom(self, message, color="white", style="normal"):
        """Custom color log"""
        color_map = {
            "black": "BLACK",
            "red": "RED",
            "green": "GREEN",
            "yellow": "YELLOW",
            "blue": "BLUE",
            "magenta": "MAGENTA",
            "cyan": "CYAN",
            "white": "WHITE",
        }
        style_map = {
            "normal": "",
            "bold": "BOLD",
            "underline": "UNDERLINE",
            "italic": "ITALIC",
            "bright": "BRIGHT",
        }
        styles = []
        if color in color_map:
            styles.append(color_map[color])
        if style in style_map and style_map[style]:
            styles.append(style_map[style])
        self.print_color(message, *styles)
    
    def assertEqualWithColor(self, first, second, msg="", color="green"):
        """Colored assertEqual"""
        try:
            self.assertEqual(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {first} == {second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {first} != {second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise
    
    def assertTrueWithColor(self, expr, msg="", color="green"):
        """Colored assertTrue"""
        try:
            self.assertTrue(expr, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {expr} is True", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {expr} is not True", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

    def assertIsInstanceWithColor(self, first, second, msg="", color="green"):
        """Colored assertIsInstance"""
        try:
            self.assertIsInstance(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: type({first})=={second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: type({first})!={second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

    def assertInWithColor(self, first, second, msg="", color="green"):
        """Colored assertIsInstance"""
        try:
            self.assertIn(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: type({first})=={second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: type({first})!={second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise
        
class ExchangeFutureTest(ColorfulTestCase):
    """class for exchange unittest"""
    def setUp(self, symbol: str, price_decimal: int = 2, qty_decimal: int = 6, order_pairs: int = 1):
        self.client:BaseClient=None
        # This function runs before each test method
        print("=============== test start ===============")
        self.result = INTERMEDIATE_RESULT
        self.price_decimal = price_decimal
        self.qty_decimal = qty_decimal
        self.symbol = symbol
        self.order_pairs = order_pairs
        self.biz_type = "FUTURE"
        
    def tearDown(self):
        # This runs after each test method
        print("sleep 2 seconds")
        time.sleep(3)
        INTERMEDIATE_RESULT = self.result
        print("RESULT teardown: ", self.result)
        
    def test_01_ask_bid(self):
        ''' expected data scheme : List[AskBid]
        '''
        print("### test_01_ask_bid ###")
        res = self.client.top_askbid(self.symbol)
        print(f"ask_bid test return: {res}")
        self.assertIsInstanceWithColor(res, list, "Return type of top_askbid method is list")
        self.assertIsInstanceWithColor(res[0], AskBid, "List element type is AskBid")
        self.assertIsInstanceWithColor(res[0].ap, str, "ap type is str")
        self.assertIsInstanceWithColor(res[0].aq, str, "aq type is str")
        self.assertIsInstanceWithColor(res[0].bp, str, "bp type is str")
        self.assertIsInstanceWithColor(res[0].bq, str, "bq type is str")


    def test_02_latest_price(self):
        """ expected data scheme : List[Ticker]
        """
        print("### test_02_lastet_price ###")
        res = self.client.ticker(self.symbol)
        print(f"latest price return: {res}")
        self.assertIsInstanceWithColor(res, list, "Return type of ticker method is list")
        for item in res:
            self.assertIsInstanceWithColor(item, Ticker, "List element type is Ticker")
            self.assertIsInstanceWithColor(item.p, str, "p type is str")
            self.assertIsInstanceWithColor(item.q, str, "q type is str")
        self.result["last_price"] = res[0].p

    def test_03_batch_make_orders(self):
        """ expected data scheme: List[OrderID]
        """
        print("### test_03_batch_make_orders ###")
        last_price = float(self.result["last_price"])
        ts = int(time.time()*1000)
        orders = []
        for i in range(self.order_pairs):
            o1 = NewOrder(self.symbol, f'10N_{ts+i*2}S1', 'BUY', 'LIMIT', round(20/last_price*1.2, self.qty_decimal), round(last_price/1.2, self.price_decimal),
                        self.biz_type, 'gtx', '')
            o2 = NewOrder(self.symbol, f'10N_{ts+i*2+1}S2', 'SELL', 'LIMIT', round(20/last_price/1.2, self.qty_decimal), round(last_price*1.2, self.price_decimal),
                        self.biz_type, 'ioc', '')
            orders.extend([o1, o2])
        print("orders: \n%s" % orders)
        res = self.client.batch_make_orders(orders, self.symbol)
        print(f"batch_order_place: {res}")
        self.assertIsInstanceWithColor(res, list, "Return type of batch_make_order method is list")
        self.result["order_ids"] = []
        self.result["clientOrderId"] = []
        if res:
            for item in res:
                self.assertIsInstanceWithColor(item, OrderID, "List element type is OrderID")
                self.assertIsInstanceWithColor(item.order_id, str, "order_id type is str")
                self.assertTrueWithColor(item.order_id, "order_id is not empty")
                self.assertIsInstanceWithColor(item.client_id, str, "client_id type is str")
            self.result["order_ids"].extend([order.order_id for order in res])
            self.result["clientOrderId"].extend([order.client_id for order in res])
        self.assertEqualWithColor(len(res), len(orders), f"Number of orders placed by batch_make_order：{len(orders)}")

    def test_04_open_orders(self):
        """ expected data scheme: List[OrderStatus]
        """
        print("### test_04_open_orders ###")
        res = self.client.open_orders(self.symbol)
        print(f"open orders return: {res}")
        self.assertIsInstanceWithColor(res, list, "Return type of open_orders method is list")
        self.result["open_orders"]=[]
        if res:
            for item in res:
                if item.order_id in self.result["order_ids"]:
                    self.assertIsInstanceWithColor(item, OrderStatus, "List element type is OrderStatus")
                    self.assertTrueWithColor(item.order_id, "order_id is not empty")
                    self.assertIsInstanceWithColor(item.order_id, str, "order_id type is str")
                    self.assertInWithColor(item.state, (order_state.NEW, order_state.CANCELED, order_state.EXPIRED,
                                            order_state.FILLED, order_state.PARTIALLY_FILLED),
                                           "state value is within valid range")
                    self.assertTrueWithColor(item.client_id, "client_id is not empty")
                    self.result["open_orders"].append(item.order_id)
                else:
                    print("id not in order_ids: %s" % item)
        self.assertTrueWithColor(res, "Return result of open_orders method is not empty")

    def test_05_order_status(self):
        """ expected data scheme: List[OrderStatus]
        """
        print("### test_05_order_status ###")
        if self.result["order_ids"]:
            res = self.client.order_status(self.result["order_ids"][0], symbol=self.symbol)
        else:
            res = self.client.order_status(str(int(time.time()*1000)), symbol=self.symbol) # mock test data
        print(f"order status: {res}")
        self.assertIsInstanceWithColor(res, list, "Return type of order_status method is list")
        self.assertTrueWithColor(res, "Return result of order_status is not empty")
        if res:
            for item in res:
                self.assertIsInstanceWithColor(item, OrderStatus,
                                               "List element type is OrderStatus")
                self.assertInWithColor(item.state, (order_state.NEW, order_state.CANCELED, order_state.EXPIRED,
                                                    order_state.FILLED, order_state.PARTIALLY_FILLED),
                                       "state value is within valid range")
        
    def test_06_cancel_order(self):
        """ expected data scheme: OrderID
        """
        print("### test_06_cancel_order ###")
        if self.result["order_ids"]:
            cancel_id = self.result["order_ids"][0]
        else:
            cancel_id = str(int(time.time()*1000))   # mock test data
        res = self.client.cancel_order(symbol=self.symbol, order_id=cancel_id)
        self.assertIsInstanceWithColor(res, OrderID, "Return result type of cancel_order is OrderID")
        self.assertTrueWithColor(res.order_id, "order_id is not empty")

    def test_07_batch_cancel_order(self):
        """ expected data scheme: List[OrderID]
        """
        print("### test_07_batch_cancel_order ###")
        print("prepare to delete %s orders" % len(self.result["order_ids"]))
        if self.result["order_ids"]:
            res = self.client.batch_cancel(self.result["order_ids"], self.symbol)
        else:
            res = self.client.batch_cancel(["1001", "1002"], self.symbol)   # mock test date
        print("sleep 2 seconds after batch cancel")
        self.assertTrueWithColor(res, "Return result of batch_cancel method is not empty")
        self.assertIsInstanceWithColor(res, list, "Return type of batch_cancel method is list")

        time.sleep(2)
        listed_orders = self.client.open_orders(self.symbol)
        for order in listed_orders:
            self.assertTrueWithColor(
                order.order_id not in self.result["order_ids"],
                f"After batch_cancel deletion, {order.order_id} should not be in open_orders")

