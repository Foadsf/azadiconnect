"""
LanguageManager - Singleton for handling bilingual (English/Farsi) localization.
"""
import json
from pathlib import Path
from typing import Callable, Optional


class LanguageManager:
    """Singleton class for managing application localization."""
    
    _instance: Optional['LanguageManager'] = None
    
    def __init__(self):
        if LanguageManager._instance is not None:
            raise RuntimeError("Use LanguageManager.get_instance() instead")
        
        self._current_lang = "en"
        self._translations: dict = {}
        self._listeners: list[Callable[[], None]] = []
        self._locales_dir = Path(__file__).parent / "locales"
        
        # Load default language
        self._load_language("en")
    
    @classmethod
    def get_instance(cls) -> 'LanguageManager':
        """Get the singleton instance of LanguageManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_language(self, lang_code: str) -> None:
        """Load translations from JSON file."""
        lang_file = self._locales_dir / f"{lang_code}.json"
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            self._current_lang = lang_code
        else:
            raise FileNotFoundError(f"Language file not found: {lang_file}")
    
    def set_language(self, lang_code: str) -> None:
        """
        Set the current language and notify all listeners.
        
        Args:
            lang_code: Language code ('en' for English, 'fa' for Farsi)
        """
        if lang_code != self._current_lang:
            self._load_language(lang_code)
            self._notify_listeners()
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        Get translated string for the given key.
        
        Args:
            key: Translation key
            default: Default value if key not found
            
        Returns:
            Translated string or default/key if not found
        """
        return self._translations.get(key, default or key)
    
    def is_rtl(self) -> bool:
        """Check if current language is RTL (Right-to-Left)."""
        return self._translations.get("rtl", False)
    
    def get_current_language(self) -> str:
        """Get the current language code."""
        return self._current_lang
    
    def register_listener(self, callback: Callable[[], None]) -> None:
        """
        Register a callback to be called when language changes.
        
        Args:
            callback: Function to call on language change
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
    
    def unregister_listener(self, callback: Callable[[], None]) -> None:
        """Remove a registered listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        """Notify all registered listeners of language change."""
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                print(f"Error notifying listener: {e}")
