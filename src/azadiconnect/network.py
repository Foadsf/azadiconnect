"""
NetworkManager - Handles P2P network communication.
Integrates with TorManager for Tor connectivity and P2PService for messaging.
Supports text messages and file transfers.

SECURITY NOTE:
End-to-end encryption is provided by the Tor Hidden Service protocol (v3 onions).
All traffic between peers is encrypted at the transport layer by Tor.
Application-layer encryption (CryptoManager with ECC/Fernet) is available for
future enhancements such as Perfect Forward Secrecy (PFS) and offline message
signing. For this MVP, we rely on Tor's built-in encryption.
"""
import asyncio
import base64
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from datetime import datetime, timezone

from .tor_manager import TorManager, TorState
from .p2p_service import P2PService, P2PMessage
from .db import DatabaseManager
from .message import Message


class ConnectionState(Enum):
    """Network connection states."""
    DISCONNECTED = auto()
    STARTING_TOR = auto()
    CREATING_SERVICE = auto()
    STARTING_P2P = auto()
    READY = auto()
    ERROR = auto()


class NetworkManager:
    """Manages network communication for P2P messaging and file transfer."""
    
    def __init__(self, app, data_path: Path):
        """
        Initialize NetworkManager.
        
        Args:
            app: Reference to the Toga App instance for background tasks
            data_path: Path to store network data (typically toga.App.paths.data)
        """
        self._app = app
        self._data_path = Path(data_path)
        self._downloads_path = self._data_path / "downloads"
        self._state = ConnectionState.DISCONNECTED
        self._status_message = "Disconnected"
        
        # Database
        self.db = DatabaseManager(self._data_path)
        
        # Managers (injected via setters)
        self._contact_manager = None
        self._crypto_manager = None
        
        # Check platform capability - auto-enable mock mode if Tor unavailable
        if not TorManager.is_available() or not P2PService.is_available():
            self._mock_mode = True
            self._platform_limited = True
            print("[NetworkManager] Platform limited (iOS?) - Mock mode enabled")
        else:
            self._mock_mode = False
            self._platform_limited = False
        
        # Create downloads directory
        self._downloads_path.mkdir(parents=True, exist_ok=True)
        
        # Tor manager
        self._tor_manager = TorManager(self._data_path)
        self._tor_manager.set_state_callback(self._on_tor_state_change)
        self._tor_manager.set_bootstrap_callback(self._on_bootstrap_progress)
        
        # P2P service (initialized when we know the SOCKS port)
        self._p2p_service: Optional[P2PService] = None
        self._p2p_local_port = 8080
        
        # Callbacks
        self._on_message_received: Optional[Callable[[Message], None]] = None
        self._on_status_change: Optional[Callable[[ConnectionState, str], None]] = None
        
        # Message log
        self._message_log: list[Message] = []

    def set_contact_manager(self, contact_manager):
        """Set the contact manager for identity lookups."""
        self._contact_manager = contact_manager

    def set_crypto_manager(self, crypto_manager):
        """Set the crypto manager for encryption."""
        self._crypto_manager = crypto_manager
        
    async def initialize_db(self):
        """Initialize the database."""
        await self.db.init_db()
    
    def get_downloads_path(self) -> Path:
        """Get the downloads directory path."""
        return self._downloads_path
    
    def set_message_callback(self, callback: Callable[[Message], None]) -> None:
        """Set callback to be called when a message is received."""
        self._on_message_received = callback
    
    def set_status_callback(self, callback: Callable[[ConnectionState, str], None]) -> None:
        """Set callback to be called when connection status changes."""
        self._on_status_change = callback
    
    def _set_state(self, state: ConnectionState, message: str) -> None:
        """Update state and notify callback."""
        self._state = state
        self._status_message = message
        print(f"[NetworkManager] {state.name}: {message}")
        if self._on_status_change:
            try:
                self._on_status_change(state, message)
            except Exception as e:
                print(f"[NetworkManager] Callback error: {e}")
    
    def _on_tor_state_change(self, tor_state: TorState, message: str) -> None:
        """Handle TorManager state changes."""
        state_map = {
            TorState.DISCONNECTED: ConnectionState.DISCONNECTED,
            TorState.FINDING_BINARY: ConnectionState.STARTING_TOR,
            TorState.STARTING_TOR: ConnectionState.STARTING_TOR,
            TorState.BOOTSTRAPPING: ConnectionState.STARTING_TOR,
            TorState.CREATING_SERVICE: ConnectionState.CREATING_SERVICE,
            TorState.READY: ConnectionState.STARTING_P2P,
            TorState.ERROR: ConnectionState.ERROR,
        }
        new_state = state_map.get(tor_state, ConnectionState.ERROR)
        
        # If Tor failed, fall back to mock mode
        if tor_state == TorState.ERROR:
            self._mock_mode = True
            self._set_state(
                ConnectionState.READY,
                f"Mock Mode (Tor error: {message})"
            )
            return
        
        self._set_state(new_state, message)
        
        # When Tor is ready, start the P2P service
        if tor_state == TorState.READY:
            async def start_p2p(app):
                await self._start_p2p_service()
            self._app.add_background_task(start_p2p)
    
    async def _start_p2p_service(self) -> None:
        """Initialize and start the P2P service."""
        socks_port = self._tor_manager.get_socks_port()
        if not socks_port:
            self._set_state(ConnectionState.ERROR, "SOCKS port not available")
            self._mock_mode = True
            return
        
        self._set_state(ConnectionState.STARTING_P2P, "Starting P2P service...")
        
        # Create P2P service with downloads path
        self._p2p_service = P2PService(
            local_port=self._p2p_local_port,
            socks_port=socks_port,
            msg_callback=self._on_p2p_message,
            downloads_path=self._downloads_path
        )
        
        # Start the server
        success = await self._p2p_service.start_server()
        if success:
            onion = self._tor_manager.get_onion_address()
            self._set_state(ConnectionState.READY, f"Connected: {onion}")
        else:
            self._set_state(ConnectionState.ERROR, "P2P server failed to start")
            self._mock_mode = True
    
    def _on_p2p_message(self, p2p_msg: P2PMessage) -> None:
        """Handle incoming P2P messages."""
        # Convert to Message object
        is_file = p2p_msg.msg_type == 'file'
        text = p2p_msg.text
        is_encrypted = False
        
        # Handle Encrypted Messages
        if p2p_msg.msg_type == 'encrypted' and self._crypto_manager:
            try:
                import json
                enc_payload = json.loads(text)
                text = self._crypto_manager.decrypt_from_peer(enc_payload)
                is_encrypted = True
                print(f"[NetworkManager] Decrypted message from {p2p_msg.sender}")
            except Exception as e:
                print(f"[NetworkManager] Decryption failed: {e}")
                text = "[Encrypted Message - Key Mismatch]"
        
        message = Message(
            text=text,
            sender_address=p2p_msg.sender,
            is_encrypted=is_encrypted,
            is_file=is_file,
            filename=p2p_msg.filename if is_file else None,
            timestamp=datetime.now(timezone.utc).timestamp(),
            is_outgoing=False
        )
        
        self._message_log.append(message)
        
        # Persist to DB
        asyncio.create_task(self.db.add_message(message, p2p_msg.sender, is_outgoing=False))
        
        # Trigger the UI callback
        if self._on_message_received:
            try:
                self._on_message_received(message)
            except Exception as e:
                print(f"[NetworkManager] Message callback error: {e}")
    
    def _on_bootstrap_progress(self, progress: int) -> None:
        """Handle Tor bootstrap progress."""
        self._set_state(
            ConnectionState.STARTING_TOR,
            f"Bootstrapping Tor: {progress}%"
        )
    
    def connect(self) -> None:
        """Start the network connection."""
        # On platform-limited devices (iOS), go directly to mock mode
        if self._platform_limited:
            self._set_state(
                ConnectionState.READY,
                "Mock Mode (iOS - Tor unavailable)"
            )
            return
        
        self._set_state(ConnectionState.STARTING_TOR, "Initializing Tor...")
        self._tor_manager.start()
    
    def disconnect(self) -> None:
        """Stop the network connection."""
        if self._p2p_service:
            asyncio.create_task(self._p2p_service.stop_server())
            self._p2p_service = None
        
        self._tor_manager.stop()
        self._set_state(ConnectionState.DISCONNECTED, "Disconnected")
    
    def get_my_address(self) -> Optional[str]:
        """Get this node's onion address."""
        if self._tor_manager.is_ready():
            return self._tor_manager.get_onion_address()
        elif self._mock_mode:
            return "mock-address.onion"
        return None
    
    def is_platform_limited(self) -> bool:
        """Check if running on a platform without Tor support (iOS)."""
        return self._platform_limited
    
    def get_connection_status(self) -> str:
        """Get current connection status message."""
        return self._status_message
    
    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    def is_ready(self) -> bool:
        """Check if network is ready for messaging."""
        return self._state == ConnectionState.READY
    
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode
    
    async def _simulate_reply(self, original_message: str, peer_address: str) -> None:
        """Simulate receiving a reply after a delay (mock mode)."""
        await asyncio.sleep(1.0)
        
        reply_text = f"Auto-reply from {peer_address[:20]}..."
        reply_message = Message(
            text=reply_text,
            sender_address=peer_address,
            is_encrypted=False
        )
        
        self._message_log.append(reply_message)
        print(f"[NetworkManager] Received mock reply: {reply_text}")
        
        if self._on_message_received:
            self._on_message_received(reply_message)
    
    async def _send_real_message(self, peer_address: str, message: str) -> bool:
        """Send a message via the real P2P service."""
        if not self._p2p_service:
            print("[NetworkManager] P2P service not available")
            return False
            
        payload_type = 'text'
        content = message
        
        # Check contact for encryption key
        if self._contact_manager and self._crypto_manager:
            contact = self._contact_manager.get_contact(peer_address)
            if contact and contact.public_key:
                try:
                    # Encrypt payload
                    peer_pub_pem = contact.public_key.encode('utf-8')
                    enc_data = self._crypto_manager.encrypt_for_peer(message, peer_pub_pem)
                    
                    # Serialize encryption payload to JSON string for the 'text' field
                    import json
                    content = json.dumps(enc_data)
                    payload_type = 'encrypted'
                    print(f"[NetworkManager] Encrypted message for {contact.name}")
                except Exception as e:
                    print(f"[NetworkManager] Encryption failed: {e}")
        
        payload = {
            'type': payload_type,
            'text': content,
            'sender': self.get_my_address() or 'unknown'
        }
        
        success = await self._p2p_service.send_message(peer_address, payload)
        return success
    
    async def _send_real_file(self, peer_address: str, file_path: Path) -> bool:
        """Send a file via the real P2P service."""
        if not self._p2p_service:
            print("[NetworkManager] P2P service not available")
            return False
        
        sender = self.get_my_address() or 'unknown'
        success = await self._p2p_service.send_file(peer_address, file_path, sender)
        return success
    
    def send_message(self, peer_address: str, message: str) -> bool:
        """
        Send a text message to a peer.
        
        Args:
            peer_address: The peer's onion address
            message: The message text
            
        Returns:
            True if message was sent (or queued)
        """
        outgoing = Message(
            text=message,
            sender_address=self.get_my_address() or "unknown",
            is_encrypted=True, 
            timestamp=datetime.now(timezone.utc).timestamp(),
            is_outgoing=True
        )
        self._message_log.append(outgoing)
        
        # Persist to DB
        asyncio.create_task(self.db.add_message(outgoing, peer_address, is_outgoing=True))
        
        print(f"[NetworkManager] Sending to {peer_address}: {message[:50]}...")
        
        if self._mock_mode or not self._p2p_service:
            async def do_mock_reply(app):
                await self._simulate_reply(message, peer_address)
            self._app.add_background_task(do_mock_reply)
            return True
        else:
            async def do_send(app):
                await self._send_real_message(peer_address, message)
            self._app.add_background_task(do_send)
            return True
    
    def send_file(self, peer_address: str, file_path: Path) -> bool:
        """
        Send a file to a peer.
        
        Args:
            peer_address: The peer's onion address
            file_path: Path to the file to send
            
        Returns:
            True if file send was initiated
        """
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"[NetworkManager] File not found: {file_path}")
            return False
        
        # Log outgoing file message
        outgoing = Message(
            text=f"Sending file: {file_path.name}",
            sender_address=self.get_my_address() or "unknown",
            is_file=True,
            filename=file_path.name,
            timestamp=datetime.now(timezone.utc).timestamp(),
            is_outgoing=True
        )
        self._message_log.append(outgoing)
        
        # Persist
        asyncio.create_task(self.db.add_message(outgoing, peer_address, is_outgoing=True))
        
        print(f"[NetworkManager] Sending file {file_path.name} to {peer_address}")
        
        if self._mock_mode or not self._p2p_service:
            # Mock mode: simulate file send success
            async def do_mock_file_reply(app):
                await asyncio.sleep(1.0)
                reply = Message(
                    text=f"File received: {file_path.name}",
                    sender_address=peer_address,
                    is_file=True,
                    filename=file_path.name,
                    timestamp=datetime.now(timezone.utc).timestamp(),
                    is_outgoing=False
                )
                self._message_log.append(reply)
                # Persist reply
                asyncio.create_task(self.db.add_message(reply, peer_address, is_outgoing=False))
                
                if self._on_message_received:
                    self._on_message_received(reply)
            self._app.add_background_task(do_mock_file_reply)
            return True
        else:
            async def do_send_file(app):
                await self._send_real_file(peer_address, file_path)
            self._app.add_background_task(do_send_file)
            return True
