"""
NetworkManager - Handles P2P network communication.
Currently implements mock mode for UI testing.
"""
import asyncio
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a chat message."""
    text: str
    sender_address: str
    is_encrypted: bool = False
    timestamp: Optional[float] = None


class NetworkManager:
    """Manages network communication for P2P messaging."""
    
    def __init__(self, app):
        """
        Initialize NetworkManager.
        
        Args:
            app: Reference to the Toga App instance for background tasks
        """
        self._app = app
        self._mock_mode = True  # Always mock until Tor is implemented
        self._my_onion_address = "mock-onion-address.onion"
        self._on_message_received: Optional[Callable[[Message], None]] = None
        self._message_log: list[Message] = []
    
    def set_message_callback(self, callback: Callable[[Message], None]) -> None:
        """
        Set callback to be called when a message is received.
        
        Args:
            callback: Function to call with received Message
        """
        self._on_message_received = callback
    
    def get_my_address(self) -> str:
        """Get this node's onion address."""
        return self._my_onion_address
    
    def set_onion_address(self, address: str) -> None:
        """Set this node's onion address (for Tor integration later)."""
        self._my_onion_address = address
    
    async def _simulate_reply(self, original_message: str, peer_address: str) -> None:
        """
        Simulate receiving a reply after a delay (mock mode).
        
        Args:
            original_message: The message that was sent
            peer_address: The address we sent to
        """
        # Wait 1 second to simulate network delay
        await asyncio.sleep(1.0)
        
        # Generate mock reply
        reply_text = f"Auto-reply from {peer_address[:20]}..."
        
        reply_message = Message(
            text=reply_text,
            sender_address=peer_address,
            is_encrypted=False
        )
        
        # Log the received message
        self._message_log.append(reply_message)
        print(f"[NetworkManager] Received mock reply: {reply_text}")
        
        # Notify via callback
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
        # Log outgoing message
        outgoing = Message(
            text=message,
            sender_address=self._my_onion_address,
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
            # TODO: Implement real Tor/socket sending
            raise NotImplementedError("Real network mode not yet implemented")
    
    def get_connection_status(self) -> str:
        """Get current connection status."""
        if self._mock_mode:
            return "Mock Mode (Simulated)"
        else:
            return "Disconnected"  # TODO: Real status
    
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode
