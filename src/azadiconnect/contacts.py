"""
ContactManager - Manages peer contacts and identity information.
"""
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
import tempfile
import os

ONION_ADDRESS_REGEX = re.compile(r'^[a-z2-7]{56}\.onion$')


@dataclass
class Contact:
    """Represents a peer contact."""
    name: str
    onion_address: str
    public_key: Optional[str] = None
    added_at: str = ""

    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now(timezone.utc).isoformat()
    
    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        short_addr = f"{self.onion_address[:6]}...{self.onion_address[-6:]}"
        return f"{self.name} ({short_addr})"


class ContactManager:
    """Manages storage and retrieval of contacts."""
    
    def __init__(self, data_path: Path):
        """
        Initialize ContactManager.
        
        Args:
            data_path: Path to store contacts.json
        """
        self._data_path = Path(data_path)
        self._contacts_file = self._data_path / "contacts.json"
        self._contacts: Dict[str, Contact] = {}
        
        self._load_contacts()
    
    def _load_contacts(self) -> None:
        """Load contacts from disk."""
        if not self._contacts_file.exists():
            return
            
        try:
            data = json.loads(self._contacts_file.read_text())
            for addr, info in data.items():
                self._contacts[addr] = Contact(**info)
        except Exception as e:
            print(f"[ContactManager] Failed to load contacts: {e}")
            # Keep empty dict if corrupted
    
    def _save_contacts(self) -> None:
        """Save contacts to disk atomically."""
        try:
            data = {addr: asdict(contact) for addr, contact in self._contacts.items()}
            json_str = json.dumps(data, indent=2)
            
            # Atomic write: write to temp file then rename
            # Create temp file in the same directory to ensure same filesystem
            with tempfile.NamedTemporaryFile('w', dir=self._data_path, delete=False) as tf:
                tf.write(json_str)
                temp_path = tf.name
            
            # Set permissions 600
            os.chmod(temp_path, 0o600)
            
            # Atomic replace
            os.replace(temp_path, self._contacts_file)
            
        except Exception as e:
            print(f"[ContactManager] Failed to save contacts: {e}")
            # Try to cleanup temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def add_contact(self, name: str, onion_address: str, public_key: Optional[str] = None) -> bool:
        """
        Add or update a contact.
        
        Args:
            name: Display name
            onion_address: Destination .onion address (v3)
            public_key: Optional identity key
            
        Returns:
            True if validated and added, False otherwise
        """
        # Validate address format
        clean_addr = onion_address.strip().lower()
        
        # Basic cleanup if user didn't type .onion
        if not clean_addr.endswith('.onion'):
            clean_addr += '.onion'
            
        if not ONION_ADDRESS_REGEX.match(clean_addr):
            print(f"[ContactManager] Invalid onion address format: {clean_addr}")
            return False
        
        contact = Contact(
            name=name, 
            onion_address=clean_addr, 
            public_key=public_key
        )
        self._contacts[clean_addr] = contact
        self._save_contacts()
        return True
    
    def delete_contact(self, onion_address: str) -> bool:
        """Delete a contact by address."""
        if onion_address in self._contacts:
            del self._contacts[onion_address]
            self._save_contacts()
            return True
        return False
    
    def get_contact(self, onion_address: str) -> Optional[Contact]:
        """Get contact details."""
        return self._contacts.get(onion_address)
    
    def get_all(self) -> List[Contact]:
        """Get list of all contacts."""
        return list(self._contacts.values())
