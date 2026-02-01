from dataclasses import dataclass
from typing import Optional

@dataclass
class Message:
    """Represents a chat message."""
    text: str
    sender_address: str
    is_encrypted: bool = False
    is_file: bool = False
    filename: Optional[str] = None
    timestamp: Optional[float] = None
    is_outgoing: bool = False
