"""
AzadiConnect - Secure P2P Chat Application
Main application module with bilingual (English/Farsi) UI.
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER, LEFT, RIGHT

from .language_manager import LanguageManager


class AzadiConnect(toga.App):
    """Main application class for AzadiConnect."""
    
    def startup(self):
        """Initialize the application UI."""
        self.lang = LanguageManager.get_instance()
        self.lang.register_listener(self._on_language_change)
        
        # Create the main tabbed container
        self.tab_container = toga.OptionContainer(
            style=Pack(flex=1)
        )
        
        # Build the tabs
        self._build_chats_tab()
        self._build_settings_tab()
        
        # Add tabs to container
        self._update_tabs()
        
        # Create main window
        self.main_window = toga.MainWindow(title=self.lang.get("app_name"))
        self.main_window.content = self.tab_container
        self.main_window.show()
    
    def _build_chats_tab(self):
        """Build the Chats tab content."""
        self.no_chats_label = toga.Label(
            self.lang.get("no_chats"),
            style=Pack(
                padding=20,
                text_align=CENTER,
                flex=1
            )
        )
        
        self.add_contact_button = toga.Button(
            self.lang.get("add_contact"),
            on_press=self._on_add_contact,
            style=Pack(padding=10)
        )
        
        self.chats_box = toga.Box(
            children=[
                self.no_chats_label,
                self.add_contact_button
            ],
            style=Pack(
                direction=COLUMN,
                alignment=CENTER,
                padding=20,
                flex=1
            )
        )
    
    def _build_settings_tab(self):
        """Build the Settings tab content."""
        # Language section header
        self.lang_header = toga.Label(
            self.lang.get("settings_language"),
            style=Pack(
                padding_bottom=5,
                font_weight='bold',
                font_size=14
            )
        )
        
        self.lang_desc = toga.Label(
            self.lang.get("settings_language_desc"),
            style=Pack(padding_bottom=15)
        )
        
        # Language toggle buttons
        self.btn_english = toga.Button(
            self.lang.get("english"),
            on_press=self._on_select_english,
            style=Pack(padding=5, width=120)
        )
        
        self.btn_farsi = toga.Button(
            self.lang.get("farsi"),
            on_press=self._on_select_farsi,
            style=Pack(padding=5, width=120)
        )
        
        lang_buttons_box = toga.Box(
            children=[self.btn_english, self.btn_farsi],
            style=Pack(direction=ROW, padding_bottom=20)
        )
        
        self.settings_box = toga.Box(
            children=[
                self.lang_header,
                self.lang_desc,
                lang_buttons_box
            ],
            style=Pack(
                direction=COLUMN,
                alignment=CENTER,
                padding=20,
                flex=1
            )
        )
    
    def _update_tabs(self):
        """Update tab container with current language labels."""
        # On first call, create the tabs and store references
        if not hasattr(self, '_chats_tab'):
            self._chats_tab = toga.OptionItem(
                self.lang.get("tab_chats"),
                self.chats_box
            )
            self._settings_tab = toga.OptionItem(
                self.lang.get("tab_settings"),
                self.settings_box
            )
            self.tab_container.content.append(self._chats_tab)
            self.tab_container.content.append(self._settings_tab)
        else:
            # Update existing tab labels
            self._chats_tab.text = self.lang.get("tab_chats")
            self._settings_tab.text = self.lang.get("tab_settings")
    
    def _update_ui_texts(self):
        """Update all UI text elements with current language."""
        # Update window title
        self.main_window.title = self.lang.get("app_name")
        
        # Update Chats tab
        self.no_chats_label.text = self.lang.get("no_chats")
        self.add_contact_button.text = self.lang.get("add_contact")
        
        # Update Settings tab
        self.lang_header.text = self.lang.get("settings_language")
        self.lang_desc.text = self.lang.get("settings_language_desc")
        self.btn_english.text = self.lang.get("english")
        self.btn_farsi.text = self.lang.get("farsi")
        
        # Update tab labels (recreate tabs)
        self._update_tabs()
    
    def _on_language_change(self):
        """Callback when language changes."""
        self._update_ui_texts()
    
    def _on_select_english(self, widget):
        """Switch to English."""
        self.lang.set_language("en")
    
    def _on_select_farsi(self, widget):
        """Switch to Farsi."""
        self.lang.set_language("fa")
    
    def _on_add_contact(self, widget):
        """Handle add contact button press (placeholder)."""
        # To be implemented in Phase 2
        pass


def main():
    """Application entry point."""
    return AzadiConnect(
        "AzadiConnect",
        "org.azadiconnect.azadiconnect"
    )


if __name__ == "__main__":
    main().main_loop()
