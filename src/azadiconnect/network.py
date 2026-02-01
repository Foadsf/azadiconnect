"""
NetworkManager - Handles P2P network communication.
Integrates with TorManager for Tor connectivity and P2PService for messaging.
"""
import asyncio
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from .tor_manager import TorManager, TorState
from .p2p_service import P2PService, P2PMessage


class ConnectionState(Enum):
    """Network connection states."""
    DISCONNECTED = auto()
    STARTING_TOR = auto()
    CREATING_SERVICE = auto()
    STARTING_P2P = auto()
    READY = auto()
    ERROR = auto()


@dataclass
class Message:
    """Represents a chat message."""
    text: str
    sender_address: str
    is_encrypted: bool = False
    timestamp: Optional[float] = None


class NetworkManager:
    """Manages network communication for P2P messaging."""
    
    def __init__(self, app, data_path: Path):
        """
        Initialize NetworkManager.
        
        Args:
            app: Reference to the Toga App instance for background tasks
            data_path: Path to store network data (typically toga.App.paths.data)
        """
        self._app = app
        self._data_path = Path(data_path)
        self._mock_mode = False  # Default to real mode, fallback to mock if Tor fails
        self._state = ConnectionState.DISCONNECTED
        self._status_message = "Disconnected"
        
        # Tor manager
        self._tor_manager = TorManager(self._data_path)
        self._tor_manager.set_state_callback(self._on_tor_state_change)
        self._tor_manager.set_bootstrap_callback(self._on_bootstrap_progress)
        
        # P2P service (initialized when we know the SOCKS port)
        self._p2p_service: Optional[P2PService] = None
        self._p2p_local_port = 8080  # Tor Hidden Service forwards to this
        
        # Callbacks
        self._on_message_received: Optional[Callable[[Message], None]] = None
        self._on_status_change: Optional[Callable[[ConnectionState, str], None]] = None
        
        # Message log
        self._message_log: list[Message] = []
    
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
        
        # Create P2P service
        self._p2p_service = P2PService(
            local_port=self._p2p_local_port,
            socks_port=socks_port,
            msg_callback=self._on_p2p_message
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
        message = Message(
            text=p2p_msg.text,
            sender_address=p2p_msg.sender,
            is_encrypted=False  # TODO: Add encryption handling
        )
        
        self._message_log.append(message)
        
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
        """
        Start the network connection.
        Attempts Tor, falls back to mock mode on failure.
        """
        self._set_state(ConnectionState.STARTING_TOR, "Initializing Tor...")
        self._tor_manager.start()
    
    def disconnect(self) -> None:
        """Stop the network connection."""
        # Stop P2P service
        if self._p2p_service:
            asyncio.create_task(self._p2p_service.stop_server())
            self._p2p_service = None
        
        # Stop Tor
        self._tor_manager.stop()
        self._set_state(ConnectionState.DISCONNECTED, "Disconnected")
    
    def get_my_address(self) -> Optional[str]:
        """Get this node's onion address."""
        if self._tor_manager.is_ready():
            return self._tor_manager.get_onion_address()
        elif self._mock_mode:
            return "mock-address.onion"
        return None
    
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
        
        payload = {
            'text': message,
            'sender': self.get_my_address() or 'unknown'
        }
        
        success = await self._p2p_service.send_message(peer_address, payload)
        return success
    
    def send_message(self, peer_address: str, message: str) -> bool:
        """
        Send a message to a peer.
        
        Args:
            peer_address: The peer's onion address
            message: The message text (should be pre-encrypted)
            
        Returns:
            True if message was sent (or queued)
        """
        outgoing = Message(
            text=message,
            sender_address=self.get_my_address() or "unknown",
            is_encrypted=True
        )
        self._message_log.append(outgoing)
        print(f"[NetworkManager] Sending to {peer_address}: {message[:50]}...")
        
        if self._mock_mode or not self._p2p_service:
            # Mock mode: schedule a simulated reply
            async def do_mock_reply(app):
                await self._simulate_reply(message, peer_address)
            self._app.add_background_task(do_mock_reply)
            return True
        else:
            # Real mode: send via P2P service
            async def do_send(app):
                await self._send_real_message(peer_address, message)
            self._app.add_background_task(do_send)
            return True
