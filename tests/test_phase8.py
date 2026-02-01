
import pytest
import asyncio
import base64
from pathlib import Path
from azadiconnect.db import DatabaseManager
from azadiconnect.crypto import CryptoManager
from azadiconnect.message import Message
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_db_persistence(tmp_path):
    mgr = DatabaseManager(tmp_path)
    await mgr.init_db()
    
    msg = Message(
        text="Hello Persistence", 
        sender_address="my-address", 
        is_encrypted=False, 
        timestamp=1234567890.0
    )
    
    # Add Outgoing
    await mgr.add_message(msg, "peer.onion", is_outgoing=True)
    
    # Add Incoming
    msg_in = Message(
        text="Hello back", 
        sender_address="peer.onion", 
        timestamp=1234567895.0
    )
    await mgr.add_message(msg_in, "peer.onion", is_outgoing=False)
    
    # Retrieve
    history = await mgr.get_history("peer.onion")
    assert len(history) == 2
    assert history[0].text == "Hello Persistence"  # Oldest first? 
    # get_history logic: SELECT ... ORDER BY timestamp DESC LIMIT ?. reversed(rows).
    # So oldest first.
    assert history[0].is_outgoing == True
    assert history[1].text == "Hello back"
    assert history[1].is_outgoing == False

def test_crypto_ecies(tmp_path):
    sender = CryptoManager(tmp_path / "sender")
    receiver = CryptoManager(tmp_path / "receiver")
    
    # Get Receiver Public Key (PEM bytes)
    # get_public_key_string returns base64 string
    peer_pub_b64 = receiver.get_public_key_string()
    peer_pub_pem = base64.b64decode(peer_pub_b64)
    
    # Encrypt (Sender -> Receiver)
    plaintext = "Top Secret Hybrid Message"
    payload = sender.encrypt_for_peer(plaintext, peer_pub_pem)
    
    assert 'ephemeral_pub' in payload
    assert 'ciphertext' in payload
    
    # Decrypt (Receiver)
    decrypted = receiver.decrypt_from_peer(payload)
    assert decrypted == plaintext

