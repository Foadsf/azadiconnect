"""
Unit tests for AzadiConnect core functionality.
Tests run without requiring real Tor connections or GUI.
"""
import json
import base64
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestLanguageManager:
    """Tests for the LanguageManager singleton and translations."""
    
    def test_singleton_pattern(self):
        """LanguageManager.get_instance() returns the same instance."""
        # Import fresh each time to test singleton
        from azadiconnect.language_manager import LanguageManager
        
        instance1 = LanguageManager.get_instance()
        instance2 = LanguageManager.get_instance()
        
        assert instance1 is instance2
    
    def test_default_language_english(self):
        """Default language should be English."""
        from azadiconnect.language_manager import LanguageManager
        
        lang = LanguageManager.get_instance()
        # Reset to English to ensure clean state
        lang.set_language("en")
        
        assert lang.get("send") == "Send"
        assert lang.get("tab_chats") == "Chats"
    
    def test_switch_to_farsi(self):
        """Switching to Farsi changes translations."""
        from azadiconnect.language_manager import LanguageManager
        
        lang = LanguageManager.get_instance()
        lang.set_language("fa")
        
        assert lang.get("send") == "ارسال"
        assert lang.get("tab_chats") == "گفتگوها"
        
        # Reset to English
        lang.set_language("en")
    
    def test_rtl_flag(self):
        """RTL flag is correct for each language."""
        from azadiconnect.language_manager import LanguageManager
        
        lang = LanguageManager.get_instance()
        
        lang.set_language("en")
        assert lang.is_rtl() is False
        
        lang.set_language("fa")
        assert lang.is_rtl() is True
        
        # Reset
        lang.set_language("en")
    
    def test_missing_key_returns_key(self):
        """Missing translation key returns the key itself."""
        from azadiconnect.language_manager import LanguageManager
        
        lang = LanguageManager.get_instance()
        result = lang.get("nonexistent_key")
        
        assert result == "nonexistent_key"


class TestP2PProtocol:
    """Tests for P2P message protocol construction."""
    
    def test_text_message_payload_structure(self):
        """Text message payload has correct structure."""
        payload = {
            'type': 'text',
            'text': 'Hello, World!',
            'sender': 'abc123.onion'
        }
        
        # Verify JSON serialization works
        json_str = json.dumps(payload)
        parsed = json.loads(json_str)
        
        assert parsed['type'] == 'text'
        assert parsed['text'] == 'Hello, World!'
        assert parsed['sender'] == 'abc123.onion'
    
    def test_file_message_payload_structure(self):
        """File message payload has correct structure with Base64."""
        file_content = b'Test file content here'
        encoded = base64.b64encode(file_content).decode('utf-8')
        
        payload = {
            'type': 'file',
            'name': 'test.txt',
            'content': encoded,
            'sender': 'abc123.onion'
        }
        
        # Verify structure
        assert payload['type'] == 'file'
        assert payload['name'] == 'test.txt'
        
        # Verify Base64 decodes correctly
        decoded = base64.b64decode(payload['content'])
        assert decoded == file_content
    
    def test_base64_encoding_binary_file(self):
        """Binary files encode and decode correctly."""
        # Simulate binary data (like an image)
        binary_data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        
        encoded = base64.b64encode(binary_data).decode('utf-8')
        decoded = base64.b64decode(encoded)
        
        assert decoded == binary_data
    
    def test_large_payload_json_serialization(self):
        """Large payloads serialize correctly."""
        # Create a 1MB "file"
        large_content = b'x' * (1024 * 1024)
        encoded = base64.b64encode(large_content).decode('utf-8')
        
        payload = {
            'type': 'file',
            'name': 'large.bin',
            'content': encoded,
            'sender': 'test.onion'
        }
        
        json_str = json.dumps(payload)
        parsed = json.loads(json_str)
        
        decoded = base64.b64decode(parsed['content'])
        assert len(decoded) == 1024 * 1024


class TestP2PMessage:
    """Tests for P2PMessage dataclass."""
    
    def test_text_message_creation(self):
        """P2PMessage creates correctly for text."""
        from azadiconnect.p2p_service import P2PMessage
        
        msg = P2PMessage(
            msg_type='text',
            text='Hello',
            sender='test.onion'
        )
        
        assert msg.msg_type == 'text'
        assert msg.text == 'Hello'
        assert msg.sender == 'test.onion'
        assert msg.filename is None
        assert msg.file_content is None
    
    def test_file_message_creation(self):
        """P2PMessage creates correctly for files."""
        from azadiconnect.p2p_service import P2PMessage
        
        content = b'file data'
        msg = P2PMessage(
            msg_type='file',
            text='File received: test.txt',
            sender='test.onion',
            filename='test.txt',
            file_content=content
        )
        
        assert msg.msg_type == 'file'
        assert msg.filename == 'test.txt'
        assert msg.file_content == content


class TestNetworkManagerMocked:
    """Tests for NetworkManager with mocked dependencies."""
    
    def test_message_dataclass(self):
        """Message dataclass has correct fields."""
        from azadiconnect.network import Message
        
        msg = Message(
            text='Test',
            sender_address='x.onion',
            is_encrypted=False,
            is_file=False
        )
        
        assert msg.text == 'Test'
        assert msg.sender_address == 'x.onion'
        assert msg.is_encrypted is False
        assert msg.is_file is False
    
    def test_file_message_dataclass(self):
        """Message dataclass handles file flags."""
        from azadiconnect.network import Message
        
        msg = Message(
            text='Sending file: doc.pdf',
            sender_address='x.onion',
            is_file=True,
            filename='doc.pdf'
        )
        
        assert msg.is_file is True
        assert msg.filename == 'doc.pdf'
    
    def test_connection_states_exist(self):
        """ConnectionState enum has expected values."""
        from azadiconnect.network import ConnectionState
        
        assert hasattr(ConnectionState, 'DISCONNECTED')
        assert hasattr(ConnectionState, 'STARTING_TOR')
        assert hasattr(ConnectionState, 'CREATING_SERVICE')
        assert hasattr(ConnectionState, 'STARTING_P2P')
        assert hasattr(ConnectionState, 'READY')
        assert hasattr(ConnectionState, 'ERROR')


class TestProjectSetup:
    """Tests for project configuration integrity."""
    
    def test_pyproject_has_stem_dependency(self):
        """pyproject.toml includes stem for Tor control."""
        pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
        
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            assert 'stem' in content
    
    def test_pyproject_has_pysocks_dependency(self):
        """pyproject.toml includes pysocks for SOCKS5."""
        pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
        
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            assert 'pysocks' in content
    
    def test_pyproject_has_cryptography_dependency(self):
        """pyproject.toml includes cryptography for ECC."""
        pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
        
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            assert 'cryptography' in content
    
    def test_locale_files_exist(self):
        """Locale JSON files exist for both languages."""
        locales_path = Path(__file__).parent.parent / 'src' / 'azadiconnect' / 'locales'
        
        assert (locales_path / 'en.json').exists()
        assert (locales_path / 'fa.json').exists()
    
    def test_locale_files_valid_json(self):
        """Locale files contain valid JSON."""
        locales_path = Path(__file__).parent.parent / 'src' / 'azadiconnect' / 'locales'
        
        en_content = (locales_path / 'en.json').read_text()
        fa_content = (locales_path / 'fa.json').read_text()
        
        # Should not raise
        en_data = json.loads(en_content)
        fa_data = json.loads(fa_content)
        
        # Both should have 'send' key
        assert 'send' in en_data
        assert 'send' in fa_data


class TestCryptoManager:
    """Tests for CryptoManager (if available)."""
    
    def test_key_generation(self):
        """CryptoManager generates ECC keys."""
        from azadiconnect.crypto import CryptoManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crypto = CryptoManager(Path(tmpdir))
            
            # Should have generated keys
            assert crypto._private_key is not None
            assert crypto._public_key is not None
    
    def test_get_public_key_string(self):
        """get_public_key_string returns base64 encoded key."""
        from azadiconnect.crypto import CryptoManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crypto = CryptoManager(Path(tmpdir))
            key_str = crypto.get_public_key_string()
            
            # Should be base64 encoded (decodable)
            import base64
            decoded = base64.b64decode(key_str)
            assert b'-----BEGIN PUBLIC KEY-----' in decoded
    
    def test_simple_encrypt_decrypt(self):
        """Simple encryption roundtrip works."""
        from azadiconnect.crypto import CryptoManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crypto = CryptoManager(Path(tmpdir))
            
            plaintext = "Secret message"
            encrypted, key = crypto.encrypt_simple(plaintext)
            decrypted = crypto.decrypt_simple(encrypted, key)
            
            assert decrypted == plaintext
    
    def test_simple_encryption_different_each_time(self):
        """Simple encryption produces different ciphertext each time."""
        from azadiconnect.crypto import CryptoManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            crypto = CryptoManager(Path(tmpdir))
            
            plaintext = "Same message"
            encrypted1, _ = crypto.encrypt_simple(plaintext)
            encrypted2, _ = crypto.encrypt_simple(plaintext)
            
            # Due to random key, these should differ
            assert encrypted1 != encrypted2
