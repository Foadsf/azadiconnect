"""
P2PService - Low-level socket operations for peer-to-peer messaging over Tor.
Handles both server (receiving) and client (sending) operations.
"""
import asyncio
import json
import socket
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class P2PMessage:
    """A message received over P2P."""
    text: str
    sender: str
    raw_data: Optional[dict] = None


class P2PService:
    """
    Handles low-level P2P socket communication.
    
    - Server: Listens on a local port (Tor forwards Hidden Service traffic here)
    - Client: Sends messages through Tor SOCKS proxy to other hidden services
    """
    
    def __init__(self, local_port: int, socks_port: int, 
                 msg_callback: Callable[[P2PMessage], None]):
        """
        Initialize P2PService.
        
        Args:
            local_port: Local port to listen on (Tor forwards HS traffic here)
            socks_port: Tor SOCKS5 proxy port for outgoing connections
            msg_callback: Function called when a message is received
        """
        self._local_port = local_port
        self._socks_port = socks_port
        self._msg_callback = msg_callback
        self._server: Optional[asyncio.Server] = None
        self._running = False
    
    async def start_server(self) -> bool:
        """
        Start the TCP server to receive incoming P2P messages.
        
        Returns:
            True if server started successfully
        """
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                '127.0.0.1',
                self._local_port
            )
            self._running = True
            print(f"[P2PService] Server listening on 127.0.0.1:{self._local_port}")
            
            # Start serving in background
            asyncio.create_task(self._server.serve_forever())
            return True
            
        except Exception as e:
            print(f"[P2PService] Failed to start server: {e}")
            return False
    
    async def stop_server(self) -> None:
        """Stop the TCP server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            print("[P2PService] Server stopped")
    
    async def _handle_client(self, reader: asyncio.StreamReader, 
                             writer: asyncio.StreamWriter) -> None:
        """
        Handle an incoming client connection.
        
        Args:
            reader: Stream reader for incoming data
            writer: Stream writer for responses
        """
        peer_addr = writer.get_extra_info('peername')
        print(f"[P2PService] Connection from {peer_addr}")
        
        try:
            # Read data (expect JSON terminated by newline)
            data = await asyncio.wait_for(
                reader.readline(),
                timeout=30.0
            )
            
            if not data:
                print("[P2PService] Empty data received")
                return
            
            # Parse JSON
            try:
                payload = json.loads(data.decode('utf-8').strip())
            except json.JSONDecodeError as e:
                print(f"[P2PService] Invalid JSON: {e}")
                return
            
            # Extract message fields
            text = payload.get('text', '')
            sender = payload.get('sender', 'unknown')
            
            print(f"[P2PService] Received from {sender}: {text[:50]}...")
            
            # Create message object and trigger callback
            message = P2PMessage(
                text=text,
                sender=sender,
                raw_data=payload
            )
            
            # Call the callback (schedule on main thread for GUI safety)
            try:
                self._msg_callback(message)
            except Exception as e:
                print(f"[P2PService] Callback error: {e}")
            
            # Send acknowledgment
            writer.write(b'OK\n')
            await writer.drain()
            
        except asyncio.TimeoutError:
            print("[P2PService] Client timeout")
        except Exception as e:
            print(f"[P2PService] Error handling client: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    
    async def send_message(self, onion_address: str, payload: dict) -> bool:
        """
        Send a message to a peer via Tor SOCKS proxy.
        
        Args:
            onion_address: The recipient's .onion address
            payload: Dictionary to send as JSON
            
        Returns:
            True if message was sent successfully
        """
        try:
            import socks
            
            # Clean up address (remove .onion if needed for parsing)
            address = onion_address.strip()
            if not address.endswith('.onion'):
                address = f"{address}.onion"
            
            print(f"[P2PService] Sending to {address} via SOCKS port {self._socks_port}")
            
            # Create SOCKS socket
            sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            sock.set_proxy(socks.SOCKS5, "127.0.0.1", self._socks_port)
            sock.settimeout(60)  # Tor connections can be slow
            
            # Connect to hidden service (port 80 is the virtual port)
            try:
                sock.connect((address, 80))
            except Exception as e:
                print(f"[P2PService] Connection failed: {e}")
                sock.close()
                return False
            
            # Send JSON payload with newline
            data = json.dumps(payload) + '\n'
            sock.sendall(data.encode('utf-8'))
            
            # Wait for acknowledgment
            try:
                sock.settimeout(10)
                response = sock.recv(1024)
                if b'OK' in response:
                    print(f"[P2PService] Message acknowledged")
            except socket.timeout:
                print("[P2PService] No acknowledgment received (timeout)")
            
            sock.close()
            print(f"[P2PService] Message sent successfully")
            return True
            
        except ImportError:
            print("[P2PService] pysocks not installed")
            return False
        except Exception as e:
            print(f"[P2PService] Send error: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running
