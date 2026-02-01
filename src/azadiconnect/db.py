"""
DatabaseManager - Handles local SQLite storage for persistent chat history.
Uses aiosqlite for asynchronous database access.
"""
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

try:
    import aiosqlite
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("[DatabaseManager] aiosqlite not available - persistence disabled")

from .message import Message


class DatabaseManager:
    """Manages SQLite database for message persistence."""
    
    def __init__(self, data_path: Path):
        """
        Initialize DatabaseManager.
        
        Args:
            data_path: Path to store database file
        """
        self._data_path = Path(data_path)
        self._db_path = self._data_path / "messages.db"
        self._ready = False
        
    async def init_db(self) -> None:
        """Initialize the database and create tables."""
        if not DB_AVAILABLE:
            return
            
        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contact_address TEXT,
                        sender_address TEXT,
                        content TEXT,
                        timestamp REAL,
                        is_outgoing BOOLEAN,
                        is_file BOOLEAN DEFAULT 0,
                        file_path TEXT
                    )
                """)
                
                # Index for faster history lookup by contact
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_contact_timestamp 
                    ON messages (contact_address, timestamp)
                """)
                
                await db.commit()
                self._ready = True
                print(f"[DatabaseManager] Database initialized at {self._db_path}")
        except Exception as e:
            print(f"[DatabaseManager] Init error: {e}")
            
    async def add_message(self, message: Message, contact_address: str, is_outgoing: bool) -> None:
        """
        Add a message to the database.
        
        Args:
            message: The Message object
            contact_address: The onion address of the peer (conversation ID)
            is_outgoing: True if sent by me, False if received
        """
        if not self._ready:
            return
            
        try:
            timestamp = message.timestamp or datetime.now(timezone.utc).timestamp()
            
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    INSERT INTO messages (
                        contact_address, sender_address, content, timestamp, 
                        is_outgoing, is_file, file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    contact_address,
                    message.sender_address,
                    message.text,
                    timestamp,
                    is_outgoing,
                    message.is_file,
                    str(message.filename) if message.filename else None
                ))
                await db.commit()
        except Exception as e:
            print(f"[DatabaseManager] Add message error: {e}")
            
    async def get_history(self, contact_address: str, limit: int = 50) -> List[Message]:
        """
        Retrieve chat history for a contact.
        
        Args:
            contact_address: Peer onion address
            limit: Max messages to return
            
        Returns:
            List of Message objects, sorted by timestamp (oldest first)
        """
        if not self._ready:
            return []
            
        try:
            messages = []
            async with aiosqlite.connect(self._db_path) as db:
                # Get latest N messages
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM messages 
                    WHERE contact_address = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (contact_address, limit)) as cursor:
                    rows = await cursor.fetchall()
                    
                    # Process in reverse order (to get chronological)
                    for row in reversed(rows):
                        msg = Message(
                            text=row['content'],
                            sender_address=row['sender_address'],
                            is_encrypted=False, # Stored plaintext
                            is_file=bool(row['is_file']),
                            filename=row['file_path'],
                            timestamp=row['timestamp'],
                            is_outgoing=bool(row['is_outgoing'])
                        )
                        messages.append(msg)
                        
            return messages
        except Exception as e:
            print(f"[DatabaseManager] Get history error: {e}")
            return []
