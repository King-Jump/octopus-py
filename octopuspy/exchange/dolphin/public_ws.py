import asyncio
import websockets
import json
from logging import Logger
from typing import Dict, List, Optional, Callable

class DolphinPublicWSClient:
    """ WebSocket Client for Public Data of Dolphin
    """
    def __init__(self, url: str = "ws://localhost:8765", logger: Optional[Logger] = None):
        """ Initialize WebSocket Client
        
        Args:
            url: WebSocket URL
            logger: Logger instance
        """
        self.url = url
        self.logger = logger
        self.websocket = None
        self.is_connected = False
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.reconnect_interval = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task = None
        self.reconnect_task = None
        self.path = "/spot"  # Default path
    
    async def connect(self, path: str = "/spot"):
        """ Connect to WebSocket server
        
        Args:
            path: WebSocket path ("/spot" or "/future")
        """
        self.path = path
        full_url = f"{self.url}{path}"
        
        try:
            self.websocket = await websockets.connect(full_url)
            self.is_connected = True
            if self.logger:
                self.logger.info(f"Connected to Dolphin WebSocket: {full_url}")
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Start message handler task
            await self._handle_messages()
        except Exception as e:
            if self.logger:
                self.logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
            await self._reconnect()
    
    async def _reconnect(self):
        """ Reconnect to WebSocket server
        """
        if self.logger:
            self.logger.info(f"Attempting to reconnect in {self.reconnect_interval} seconds...")
        await asyncio.sleep(self.reconnect_interval)
        await self.connect(self.path)
    
    async def _heartbeat(self):
        """ Send heartbeat messages to keep connection alive
        """
        while self.is_connected:
            try:
                if self.websocket:
                    # Dolphin WebSocket doesn't require heartbeat
                    # But we'll keep this method for compatibility
                    await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _handle_messages(self):
        """ Handle incoming WebSocket messages
        """
        while self.is_connected:
            try:
                if self.websocket:
                    message = await self.websocket.recv()
                    await self._process_message(message)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Message handling error: {e}")
                break
    
    async def _process_message(self, message: str):
        """ Process incoming message
        
        Args:
            message: Raw JSON message
        """
        try:
            data = json.loads(message)
            
            # Handle subscription messages
            if "e" in data:
                event_type = data["e"]
                if event_type in self.message_handlers:
                    for handler in self.message_handlers[event_type]:
                        await handler(data)
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Message processing error: {e}")
    
    async def subscribe(self, params: List[str], id: int = 1):
        """ Subscribe to WebSocket streams
        
        Args:
            params: Subscription parameters (e.g., ["btcusdt@depth", "btcusdt@trade"])
            id: Subscription ID
        """
        if not self.is_connected:
            if self.logger:
                self.logger.error("Not connected to WebSocket")
            return
        
        # Send subscription message
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": params,
            "id": id
        }
        
        try:
            if self.websocket:
                await self.websocket.send(json.dumps(subscribe_msg))
                if self.logger:
                    self.logger.info(f"Subscribed to streams: {params}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Subscription error: {e}")
    
    async def unsubscribe(self, params: List[str], id: int = 1):
        """ Unsubscribe from WebSocket streams
        
        Args:
            params: Unsubscription parameters (e.g., ["btcusdt@depth", "btcusdt@trade"])
            id: Unsubscription ID
        """
        if not self.is_connected:
            if self.logger:
                self.logger.error("Not connected to WebSocket")
            return
        
        # Send unsubscription message
        unsubscribe_msg = {
            "method": "UNSUBSCRIBE",
            "params": params,
            "id": id
        }
        
        try:
            if self.websocket:
                await self.websocket.send(json.dumps(unsubscribe_msg))
                if self.logger:
                    self.logger.info(f"Unsubscribed from streams: {params}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unsubscription error: {e}")
    
    async def register_callback(self, event_type: str, callback: Callable):
        """ Register callback for WebSocket events
        
        Args:
            event_type: Event type (e.g., "depthUpdate", "trade")
            callback: Message callback function
        """
        if event_type not in self.message_handlers:
            self.message_handlers[event_type] = []
        self.message_handlers[event_type].append(callback)
        if self.logger:
            self.logger.info(f"Registered callback for event: {event_type}")
    
    async def subscribe_depth(self, symbol: str, callback: Callable):
        """ Subscribe to depth channel
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            callback: Depth update callback
        """
        stream = f"{symbol.lower()}@depth"
        await self.subscribe([stream])
        await self.register_callback("depthUpdate", callback)
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """ Subscribe to trades channel
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            callback: Trades update callback
        """
        stream = f"{symbol.lower()}@trade"
        await self.subscribe([stream])
        await self.register_callback("trade", callback)
    
    async def close(self):
        """ Close WebSocket connection
        """
        self.is_connected = False
        
        # Cancel tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.reconnect_task:
            self.reconnect_task.cancel()
        
        # Close websocket
        if self.websocket:
            try:
                await self.websocket.close()
                if self.logger:
                    self.logger.info("WebSocket connection closed")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error closing websocket: {e}")
    
    async def start(self, path: str = "/spot"):
        """ Start WebSocket client
        
        Args:
            path: WebSocket path ("/spot" or "/future")
        """
        await self.connect(path)


# Example usage
async def example():
    """ Example usage of DolphinPublicWSClient
    """
    import logging
    
    # Configure logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("dolphin_ws")
    
    # Create client
    client = DolphinPublicWSClient(logger=logger)
    
    # Define callbacks
    async def depth_callback(data):
        logger.info(f"Depth update: {json.dumps(data, indent=2)}")
    
    async def trade_callback(data):
        logger.info(f"Trade update: {json.dumps(data, indent=2)}")
    
    try:
        # Start client
        await client.start("/spot")
        
        # Subscribe to channels
        await client.subscribe_depth("BTCUSDT", depth_callback)
        await client.subscribe_trades("BTCUSDT", trade_callback)
        
        # Run for 60 seconds
        await asyncio.sleep(60)
    finally:
        # Close client
        await client.close()


if __name__ == "__main__":
    asyncio.run(example())
