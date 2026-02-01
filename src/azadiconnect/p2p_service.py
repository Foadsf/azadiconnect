"""
P2PService - Low-level socket operations for peer-to-peer messaging over Tor.
Handles both server (receiving) and client (sending) operations.
Supports text messages and file transfers via Base64 encoding.
"""
import asyncio
import json
import socket
import base64
from typing import Callable, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class P2PMessage:
    """A message received over P2P."""
    msg_type: str  # "text" or "file"
    text: str
    sender: str
    filename: Optional[str] = None
    file_content: Optional[bytes] = None
    raw_data: Optional[dict] = None


class P2PService:
    """
    Handles low-level P2P socket communication.
    
    - Server: Listens on a local port (Tor forwards Hidden Service traffic here)
    - Client: Sends messages through Tor SOCKS proxy to other hidden services
    
    Protocol:
    - Text: {"type": "text", "text": "...", "sender": "..."}
    - File: {"type": "file", "name": "...", "content": "base64...", "sender": "..."}
    """
    
    def __init__(self, local_port: int, socks_port: int, 
                 msg_callback: Callable[[P2PMessage], None],
                 downloads_path: Optional[Path] = None):
        """
        Initialize P2PService.
        
        Args:
            local_port: Local port to listen on (Tor forwards HS traffic here)
            socks_port: Tor SOCKS5 proxy port for outgoing connections
            msg_callback: Function called when a message is received
            downloads_path: Path to save received files
        """
        self._local_port = local_port
        self._socks_port = socks_port
        self._msg_callback = msg_callback
        self._downloads_path = downloads_path
        self._server: Optional[asyncio.Server] = None
        self._running = False
        
        # Create downloads directory if specified
        if self._downloads_path:
            self._downloads_path.mkdir(parents=True, exist_ok=True)
    
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
            # For files, we may need to read more data
            data = await asyncio.wait_for(
                reader.readline(),
                timeout=120.0  # Longer timeout for file transfers
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
            
            # Extract message type
            msg_type = payload.get('type', 'text')
            sender = payload.get('sender', 'unknown')
            
            if msg_type == 'file':
                # Handle file transfer
                filename = payload.get('name', 'unknown_file')
                content_b64 = payload.get('content', '')
                
                try:
                    file_content = base64.b64decode(content_b64)
                except Exception as e:
                    print(f"[P2PService] Failed to decode file: {e}")
                    return
                
                print(f"[P2PService] Received file '{filename}' ({len(file_content)} bytes) from {sender}")
                
                # Save file if downloads path is set
                if self._downloads_path:
                    # Sanitize filename
                    safe_name = "".join(c for c in filename if c.isalnum() or c in '._-')
                    if not safe_name:
                        safe_name = "received_file"
                    
                    save_path = self._downloads_path / safe_name
                    
                    # Avoid overwriting
                    counter = 1
                    original_path = save_path
                    while save_path.exists():
                        stem = original_path.stem
                        suffix = original_path.suffix
                        save_path = original_path.parent / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    save_path.write_bytes(file_content)
                    print(f"[P2PService] Saved file to {save_path}")
                
                message = P2PMessage(
                    msg_type='file',
                    text=f"File received: {filename}",
                    sender=sender,
                    filename=filename,
                    file_content=file_content,
                    raw_data=payload
                )
            else:
                # Handle text message
                text = payload.get('text', '')
                print(f"[P2PService] Received text from {sender}: {text[:50]}...")
                
                message = P2PMessage(
                    msg_type='text',
                    text=text,
                    sender=sender,
                    raw_data=payload
                )
            
            # Call the callback
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
            
            # Clean up address
            address = onion_address.strip()
            if not address.endswith('.onion'):
                address = f"{address}.onion"
            
            print(f"[P2PService] Sending to {address} via SOCKS port {self._socks_port}")
            
            # Create SOCKS socket
            sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            sock.set_proxy(socks.SOCKS5, "127.0.0.1", self._socks_port)
            sock.settimeout(120)  # Longer timeout for file transfers
            
            # Connect to hidden service
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
                sock.settimeout(30)
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
    
    async def send_file(self, onion_address: str, file_path: Path, sender: str) -> bool:
        """
        Send a file to a peer.
        
        Args:
            onion_address: The recipient's .onion address
            file_path: Path to the file to send
            sender: Sender's address
            
        Returns:
            True if file was sent successfully
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"[P2PService] File not found: {file_path}")
                return False
            
            # Read and encode file
            file_content = file_path.read_bytes()
            content_b64 = base64.b64encode(file_content).decode('utf-8')
            
            print(f"[P2PService] Sending file '{file_path.name}' ({len(file_content)} bytes)")
            
            payload = {
                'type': 'file',
                'name': file_path.name,
                'content': content_b64,
                'sender': sender
            }
            
            return await self.send_message(onion_address, payload)
            
        except Exception as e:
            print(f"[P2PService] Send file error: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running
