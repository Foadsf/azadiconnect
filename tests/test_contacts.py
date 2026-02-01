
import json
import pytest
from pathlib import Path
from azadiconnect.contacts import ContactManager, Contact

class TestContactManager:
    @pytest.fixture
    def contact_manager(self, tmp_path):
        return ContactManager(tmp_path)

    def get_valid_onion(self):
        # 56 chars of base32 (a-z, 2-7)
        return "abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstwvxy.onion"

    def test_add_contact(self, contact_manager):
        onion = self.get_valid_onion()
        # Test case insensitivity (mixed case input)
        input_onion = onion.upper()
        
        assert contact_manager.add_contact("Alice", input_onion)
        
        # Should be stored as lowercase
        contact = contact_manager.get_contact(onion)
        assert contact is not None
        assert contact.name == "Alice"
        assert contact.onion_address == onion
        
    def test_add_contact_invalid_onion(self, contact_manager):
        assert not contact_manager.add_contact("Bob", "invalid")
        assert not contact_manager.add_contact("Bob", "short.onion")
        # Too long
        assert not contact_manager.add_contact("Bob", "a" * 57 + ".onion")

    def test_persistence(self, tmp_path):
        cm = ContactManager(tmp_path)
        onion = "abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstwvxy.onion"
        cm.add_contact("Alice", onion)
        
        # New instance should load it
        cm2 = ContactManager(tmp_path)
        contact = cm2.get_contact(onion)
        assert contact is not None
        assert contact.name == "Alice"

    def test_delete_contact(self, contact_manager):
        onion = self.get_valid_onion()
        contact_manager.add_contact("Alice", onion)
        assert contact_manager.delete_contact(onion)
        assert contact_manager.get_contact(onion) is None

    def test_get_all(self, contact_manager):
        onion1 = "abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstwvxy.onion"
        onion2 = "bbcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstwvxy.onion"
        contact_manager.add_contact("Alice", onion1)
        contact_manager.add_contact("Bob", onion2)
        
        all_contacts = contact_manager.get_all()
        assert len(all_contacts) == 2
