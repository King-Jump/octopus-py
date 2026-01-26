import unittest
import os
import sys
import time

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

from utils.log_util import create_logger
LOGGER = create_logger(".", "exchange_unittest.log", "xt_unittest", 10)

SYMBOL = "BTC_USDT"
INTERMEDIATE_RESULT = {}

from exchange.base_restapi import BaseClient

from exchange.base_restapi import (
    NewOrder, OrderID, OrderStatus, Ticker, 
    AskBid, ORDER_STATE_CONSTANTS as order_state
)

class Color:
    """ANSI 颜色代码"""
    # 基础颜色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # 样式
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'
    
    # 重置
    RESET = '\033[0m'
    
    @classmethod
    def colorize(cls, text, *styles):
        """为文本添加颜色和样式"""
        style_codes = ''.join(getattr(cls, style.upper()) for style in styles)
        return f"{style_codes}{text}{cls.RESET}"

class ColorfulTestCase(unittest.TestCase):
    """支持彩色输出的测试用例基类"""
    
    def print_color(self, message, *styles):
        """打印彩色消息"""
        print(Color.colorize(message, *styles))
    
    def log_info(self, message):
        """信息级别日志（蓝色）"""
        self.print_color(f"[INFO] {message}", "BLUE")
    
    def log_success(self, message):
        """成功级别日志（绿色）"""
        self.print_color(f"[SUCCESS] {message}", "GREEN", "BOLD")
    
    def log_warning(self, message):
        """警告级别日志（黄色）"""
        self.print_color(f"[WARNING] {message}", "YELLOW")
    
    def log_error(self, message):
        """错误级别日志（红色）"""
        self.print_color(f"[ERROR] {message}", "RED", "BOLD")
    
    def log_debug(self, message):
        """调试级别日志（青色）"""
        self.print_color(f"[DEBUG] {message}", "CYAN")
    
    def log_custom(self, message, color="white", style="normal"):
        """自定义颜色日志"""
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
        """带颜色的assertEqual"""
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
        """带颜色的assertTrue"""
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
        """带颜色的assertIsInstance"""
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
        """带颜色的assertIsInstance"""
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
        
class ExchangeTest(ColorfulTestCase):
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
        self.biz_type = "SPOT"
        
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
        self.assertIsInstanceWithColor(res, list, "top_askbid方法返回类型list")
        self.assertIsInstanceWithColor(res[0], AskBid, "list成员类型AskBid")
        self.assertIsInstanceWithColor(res[0].ap, str, "ap类型str")
        self.assertIsInstanceWithColor(res[0].aq, str, "aq类型str")
        self.assertIsInstanceWithColor(res[0].bp, str, "bp类型str")
        self.assertIsInstanceWithColor(res[0].bq, str, "bq类型str")

    def test_02_latest_price(self):
        """ expected data scheme : List[Ticker]
        """
        print("### test_02_lastet_price ###")
        res = self.client.ticker(self.symbol)
        print(f"latest price return: {res}")
        self.assertIsInstanceWithColor(res, list, "ticker方法返回类型list")
        for item in res:
            self.assertIsInstanceWithColor(item, Ticker, "list成员Ticker")
            self.assertIsInstanceWithColor(item.p, str, "p类型str")
            self.assertIsInstanceWithColor(item.q, str, "q类型str")
        self.result["last_price"] = res[0].p

    def test_03_batch_make_orders(self):
        """ expected data scheme: List[OrderID]
        """
        print("### test_03_batch_make_orders ###")
        last_price = float(self.result["last_price"])
        ts = int(time.time()*1000)
        orders = []
        for i in range(self.order_pairs):
            o1 = NewOrder(self.symbol, f'10N_{ts+i*2}S1', 'BUY', 'LIMIT', round(20/last_price*1.5, self.qty_decimal), round(last_price/1.5, self.price_decimal),
                        self.biz_type, 'gtx', reduce_only=False, position_side='', bait=False, selftrade_enabled=False)
            o2 = NewOrder(self.symbol, f'10N_{ts+i*2+1}S2', 'SELL', 'LIMIT', round(20/last_price/1.5, self.qty_decimal), round(last_price*1.5, self.price_decimal),
                        self.biz_type, 'ioc', reduce_only=False, position_side='', bait=False, selftrade_enabled=False)
            orders.extend([o1, o2])
        LOGGER.debug("orders: \n%s", orders)
        res = self.client.batch_make_orders(orders, self.symbol)
        print(f"batch_order_place: {res}")
        self.assertIsInstanceWithColor(res, list, "batch_make_order方法返回类型list")
        self.result["order_ids"] = []
        self.result["clientOrderId"] = []
        if res:
            for item in res:
                self.assertIsInstanceWithColor(item, OrderID, "list成员类型OrderID")
                self.assertIsInstanceWithColor(item.order_id, str, "order_id类型str")
                self.assertTrueWithColor(item.order_id, "order_id非空")
                self.assertIsInstanceWithColor(item.client_id, str, "client_id类型str")
            self.result["order_ids"].extend([order.order_id for order in res])
            self.result["clientOrderId"].extend([order.client_id for order in res])
        self.assertEqualWithColor(len(res), len(orders), f"batch_make_order下单数量：{len(orders)}")

    def test_04_open_orders(self):
        """ expected data scheme: List[OrderStatus]
        """
        print("### test_04_open_orders ###")
        res = self.client.open_orders(self.symbol)
        print(f"open orders return: {res}")
        self.assertIsInstanceWithColor(res, list, "open_orders方法返回类型list")
        self.result["open_orders"]=[]
        if res:
            for item in res:
                if item.order_id in self.result["order_ids"]:
                    self.assertIsInstanceWithColor(item, OrderStatus, "list成员类型OrderStatus")
                    self.assertTrueWithColor(item.order_id, "order_id非空")
                    self.assertIsInstanceWithColor(item.order_id, str, "order_id类型str")
                    self.assertInWithColor(item.state, (order_state.NEW, order_state.CANCELED, order_state.EXPIRED,
                                            order_state.FILLED, order_state.PARTIALLY_FILLED), "state取值在有效范围内")
                    self.assertTrueWithColor(item.client_id, "client_id非空")
                    self.result["open_orders"].append(item.order_id)
                else:
                    LOGGER.debug("id not in order_ids: %s", item)
        self.assertTrueWithColor(res, "open_orders方法返回结果非空")

    def test_05_order_status(self):
        """ expected data scheme: List[OrderStatus]
        """
        print("### test_05_order_status ###")
        if self.result["order_ids"]:
            res = self.client.order_status(self.result["order_ids"][0], symbol=self.symbol)
        else:
            res = self.client.order_status(str(int(time.time()*1000)), symbol=self.symbol) # mock test data
        print(f"order status: {res}")
        self.assertIsInstanceWithColor(res, list, "order_status方法返回类型list")
        self.assertTrueWithColor(res, "order_status返回结果非空")
        if res:
            for item in res:
                self.assertIsInstanceWithColor(item, OrderStatus, "list成员类型OrderStatus")
                self.assertInWithColor(item.state, (order_state.NEW, order_state.CANCELED, order_state.EXPIRED,
                                           order_state.FILLED, order_state.PARTIALLY_FILLED), "state取值在有效范围内")
        
    def test_06_cancel_order(self):
        """ expected data scheme: OrderID
        """
        print("### test_06_cancel_order ###")
        if self.result["order_ids"]:
            cancel_id = self.result["order_ids"][0]
        else:
            cancel_id = str(int(time.time()*1000))   # mock test data
        res = self.client.cancel_order(symbol=self.symbol, order_id=cancel_id)
        print(f"cancel order: {res}")
        self.assertIsInstanceWithColor(res, OrderID, "cancel_order返回结果类型OrderID")
        self.assertTrueWithColor(res.order_id, "order_id非空")

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
        self.assertTrueWithColor(res, "batch_cancel方法返回结果非空")
        self.assertIsInstanceWithColor(res, list, "batch_cancel方法返回类型list")

        time.sleep(2)
        listed_orders = self.client.open_orders(self.symbol)
        for order in listed_orders:
            self.assertTrueWithColor(
                order.order_id not in self.result["order_ids"], f"batch_cancel删除后{order.order_id}不应在open_orders")

