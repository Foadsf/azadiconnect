"""
AzadiConnect - Secure P2P Chat Application
Main application module with bilingual (English/Farsi) UI and chat interface.
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER, LEFT, RIGHT

from .language_manager import LanguageManager
from .crypto import CryptoManager
from .network import NetworkManager, Message


class AzadiConnect(toga.App):
    """Main application class for AzadiConnect."""
    
    def startup(self):
        """Initialize the application UI."""
        self.lang = LanguageManager.get_instance()
        self.lang.register_listener(self._on_language_change)
        
        # Initialize managers
        self.crypto = CryptoManager(self.paths.data)
        self.network = NetworkManager(self)
        self.network.set_message_callback(self._on_message_received)
        
        # Mock peer address for testing
        self._mock_peer_address = "mock-peer-12345.onion"
        
        # Track message widgets for potential updates
        self._message_widgets: list[toga.Box] = []
        
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
        """Build the Chats tab with actual chat interface."""
        # Message list container (scrollable)
        self.message_list = toga.Box(
            style=Pack(
                direction=COLUMN,
                padding=10,
                flex=1
            )
        )
        
        self.scroll_container = toga.ScrollContainer(
            content=self.message_list,
            style=Pack(flex=1)
        )
        
        # Input area
        self.message_input = toga.TextInput(
            placeholder=self.lang.get("type_message"),
            style=Pack(flex=1, padding=5)
        )
        
        self.send_button = toga.Button(
            self.lang.get("send"),
            on_press=self._on_send_message,
            style=Pack(padding=5, width=80)
        )
        
        input_box = toga.Box(
            children=[self.message_input, self.send_button],
            style=Pack(direction=ROW, padding=5)
        )
        
        # Main chat layout
        self.chats_box = toga.Box(
            children=[
                self.scroll_container,
                input_box
            ],
            style=Pack(
                direction=COLUMN,
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
        
        # Connection status section
        self.status_header = toga.Label(
            self.lang.get("connection_status"),
            style=Pack(
                padding_top=20,
                padding_bottom=5,
                font_weight='bold',
                font_size=14
            )
        )
        
        self.status_label = toga.Label(
            self.network.get_connection_status() if hasattr(self, 'network') else self.lang.get("mock_mode"),
            style=Pack(padding_bottom=10)
        )
        
        self.settings_box = toga.Box(
            children=[
                self.lang_header,
                self.lang_desc,
                lang_buttons_box,
                self.status_header,
                self.status_label
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
    
    def add_message_to_ui(self, text: str, is_me: bool = True) -> None:
        """
        Add a message bubble to the chat UI.
        
        Args:
            text: The message text
            is_me: True if this is my message, False if received
        """
        is_rtl = self.lang.is_rtl()
        
        # Determine alignment based on sender and RTL mode
        # In LTR: my messages right, theirs left
        # In RTL: my messages left, theirs right
        if is_me:
            align = LEFT if is_rtl else RIGHT
            bg_color = "#DCF8C6"  # Light green for sent
        else:
            align = RIGHT if is_rtl else LEFT
            bg_color = "#FFFFFF"  # White for received
        
        # Create message label
        message_label = toga.Label(
            text,
            style=Pack(
                padding=10,
                background_color=bg_color,
                flex=0
            )
        )
        
        # Create bubble container with alignment
        bubble_box = toga.Box(
            children=[message_label],
            style=Pack(
                direction=ROW,
                padding=5,
                alignment=align
            )
        )
        
        # Add spacer for alignment
        if (is_me and not is_rtl) or (not is_me and is_rtl):
            # Push to right: add spacer on left
            spacer = toga.Box(style=Pack(flex=1))
            bubble_box.insert(0, spacer)
        elif (not is_me and not is_rtl) or (is_me and is_rtl):
            # Push to left: add spacer on right
            spacer = toga.Box(style=Pack(flex=1))
            bubble_box.add(spacer)
        
        # Add to message list
        self.message_list.add(bubble_box)
        self._message_widgets.append(bubble_box)
        
        # Try to scroll to bottom (best effort)
        try:
            self.scroll_container.vertical_position = self.scroll_container.max_vertical_position
        except Exception:
            pass  # Scrolling may not be supported on all platforms
    
    def _on_send_message(self, widget):
        """Handle send button press."""
        text = self.message_input.value.strip()
        if not text:
            return
        
        # Clear input
        self.message_input.value = ""
        
        # Add message to UI
        self.add_message_to_ui(text, is_me=True)
        
        # Send via network (mock mode will trigger auto-reply)
        # In real mode, we'd encrypt first with peer's public key
        self.network.send_message(self._mock_peer_address, text)
    
    def _on_message_received(self, message: Message):
        """
        Callback when a message is received from the network.
        
        Args:
            message: The received Message object
        """
        # Add to UI (decryption would happen here in real mode)
        self.add_message_to_ui(message.text, is_me=False)
    
    def _update_ui_texts(self):
        """Update all UI text elements with current language."""
        # Update window title
        self.main_window.title = self.lang.get("app_name")
        
        # Update Chat input
        self.message_input.placeholder = self.lang.get("type_message")
        self.send_button.text = self.lang.get("send")
        
        # Update Settings tab
        self.lang_header.text = self.lang.get("settings_language")
        self.lang_desc.text = self.lang.get("settings_language_desc")
        self.btn_english.text = self.lang.get("english")
        self.btn_farsi.text = self.lang.get("farsi")
        self.status_header.text = self.lang.get("connection_status")
        
        # Update tab labels
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


def main():
    """Application entry point."""
    return AzadiConnect(
        "AzadiConnect",
        "org.azadiconnect.azadiconnect"
    )


if __name__ == "__main__":
    main().main_loop()
