"""
NetworkManager - Handles P2P network communication.
Integrates with TorManager for real Tor connections.
"""
import asyncio
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from .tor_manager import TorManager, TorState


class ConnectionState(Enum):
    """Network connection states."""
    DISCONNECTED = auto()
    STARTING_TOR = auto()
    CREATING_SERVICE = auto()
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
            TorState.READY: ConnectionState.READY,
            TorState.ERROR: ConnectionState.ERROR,
        }
        new_state = state_map.get(tor_state, ConnectionState.ERROR)
        self._set_state(new_state, message)
        
        # If Tor failed, fall back to mock mode
        if tor_state == TorState.ERROR:
            self._mock_mode = True
            self._set_state(
                ConnectionState.READY,
                f"Mock Mode (Tor error: {message})"
            )
    
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
    
    def send_message(self, peer_address: str, message: str) -> bool:
        """
        Send a message to a peer.
        
        Args:
            peer_address: The peer's onion address
            message: The message text (should be pre-encrypted)
            
        Returns:
            True if message was sent (or queued for mock)
        """
        outgoing = Message(
            text=message,
            sender_address=self.get_my_address() or "unknown",
            is_encrypted=True
        )
        self._message_log.append(outgoing)
        print(f"[NetworkManager] Sending to {peer_address}: {message[:50]}...")
        
        if self._mock_mode:
            # In mock mode, schedule a simulated reply
            self._app.add_background_task(
                lambda app: self._simulate_reply(message, peer_address)
            )
            return True
        else:
            # TODO: Send via Tor SOCKS proxy
            # For now, fall back to mock behavior
            self._app.add_background_task(
                lambda app: self._simulate_reply(message, peer_address)
            )
            return True
