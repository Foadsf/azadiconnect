"""
AzadiConnect - Secure P2P Chat Application
Main application module with bilingual (English/Farsi) UI, chat interface, and Tor integration.
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER, LEFT, RIGHT

from .language_manager import LanguageManager
from .crypto import CryptoManager
from .network import NetworkManager, Message, ConnectionState


class AzadiConnect(toga.App):
    """Main application class for AzadiConnect."""
    
    def startup(self):
        """Initialize the application UI."""
        self.lang = LanguageManager.get_instance()
        self.lang.register_listener(self._on_language_change)
        
        # Initialize managers
        self.crypto = CryptoManager(self.paths.data)
        self.network = NetworkManager(self, self.paths.data)
        self.network.set_message_callback(self._on_message_received)
        self.network.set_status_callback(self._on_connection_status_change)
        
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
        
        # Start network connection in background
        self.add_background_task(self._start_network)
    
    async def _start_network(self, app):
        """Start network connection in background."""
        self.network.connect()
    
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
        
        self.attach_button = toga.Button(
            self.lang.get("attach_file"),
            on_press=self._on_attach_file,
            style=Pack(padding=5, width=50)
        )
        
        input_box = toga.Box(
            children=[self.attach_button, self.message_input, self.send_button],
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
        # === Connection Status Section ===
        self.status_header = toga.Label(
            self.lang.get("connection_status"),
            style=Pack(
                padding_bottom=5,
                font_weight='bold',
                font_size=14
            )
        )
        
        self.status_label = toga.Label(
            self.lang.get("disconnected"),
            style=Pack(padding_bottom=15)
        )
        
        # === My Identity Section ===
        self.identity_header = toga.Label(
            self.lang.get("my_identity"),
            style=Pack(
                padding_top=10,
                padding_bottom=5,
                font_weight='bold',
                font_size=14
            )
        )
        
        self.onion_address_label = toga.Label(
            "...",
            style=Pack(padding_bottom=5)
        )
        
        self.copy_button = toga.Button(
            self.lang.get("copy_address"),
            on_press=self._on_copy_address,
            style=Pack(padding=5, width=100)
        )
        
        identity_box = toga.Box(
            children=[self.onion_address_label, self.copy_button],
            style=Pack(direction=ROW, padding_bottom=20)
        )
        
        # === Language Section ===
        self.lang_header = toga.Label(
            self.lang.get("settings_language"),
            style=Pack(
                padding_top=20,
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
        
        # === Assemble Settings ===
        self.settings_box = toga.Box(
            children=[
                self.status_header,
                self.status_label,
                self.identity_header,
                identity_box,
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
    
    def add_message_to_ui(self, text: str, is_me: bool = True) -> None:
        """
        Add a message bubble to the chat UI.
        
        Args:
            text: The message text
            is_me: True if this is my message, False if received
        """
        is_rtl = self.lang.is_rtl()
        
        # Determine alignment based on sender and RTL mode
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
            spacer = toga.Box(style=Pack(flex=1))
            bubble_box.insert(0, spacer)
        elif (not is_me and not is_rtl) or (is_me and is_rtl):
            spacer = toga.Box(style=Pack(flex=1))
            bubble_box.add(spacer)
        
        # Add to message list
        self.message_list.add(bubble_box)
        self._message_widgets.append(bubble_box)
        
        # Try to scroll to bottom
        try:
            self.scroll_container.vertical_position = self.scroll_container.max_vertical_position
        except Exception:
            pass
    
    def _on_send_message(self, widget):
        """Handle send button press."""
        text = self.message_input.value.strip()
        if not text:
            return
        
        # Clear input
        self.message_input.value = ""
        
        # Add message to UI
        self.add_message_to_ui(text, is_me=True)
        
        # Send via network
        self.network.send_message(self._mock_peer_address, text)
    
    async def _on_attach_file(self, widget):
        """Handle attach file button press."""
        try:
            file_path = await self.main_window.open_file_dialog(
                title="Select file to send",
                multiple_select=False
            )
            
            if file_path:
                # Add feedback message to UI
                filename = file_path.name if hasattr(file_path, 'name') else str(file_path).split('/')[-1]
                self.add_message_to_ui(f"{self.lang.get('sending_file')}{filename}", is_me=True)
                
                # Send file via network
                self.network.send_file(self._mock_peer_address, file_path)
                
        except Exception as e:
            print(f"[App] File dialog error: {e}")
    
    def _on_message_received(self, message: Message):
        """Callback when a message is received from the network."""
        self.add_message_to_ui(message.text, is_me=False)
    
    def _on_connection_status_change(self, state: ConnectionState, message: str):
        """Callback when connection status changes."""
        # Update status label
        self.status_label.text = message
        
        # Update onion address if ready
        if state == ConnectionState.READY:
            address = self.network.get_my_address()
            if address:
                self.onion_address_label.text = address
            else:
                self.onion_address_label.text = self.lang.get("mock_mode")
    
    def _on_copy_address(self, widget):
        """Copy onion address to clipboard."""
        address = self.network.get_my_address()
        if address:
            try:
                # Use Toga's clipboard API
                import toga.platform
                # Note: Clipboard access varies by platform
                # For GTK, we can use the system clipboard
                import subprocess
                subprocess.run(['xclip', '-selection', 'clipboard'], 
                             input=address.encode(), check=True)
                self.copy_button.text = self.lang.get("copied")
                
                # Reset button text after delay
                async def reset_button(app):
                    import asyncio
                    await asyncio.sleep(2)
                    self.copy_button.text = self.lang.get("copy_address")
                
                self.add_background_task(reset_button)
            except Exception as e:
                print(f"Clipboard error: {e}")
                # Fallback: just show the address was selected
                self.copy_button.text = address[:10] + "..."
    
    def _update_ui_texts(self):
        """Update all UI text elements with current language."""
        # Update window title
        self.main_window.title = self.lang.get("app_name")
        
        # Update Chat input
        self.message_input.placeholder = self.lang.get("type_message")
        self.send_button.text = self.lang.get("send")
        
        # Update Settings tab
        self.status_header.text = self.lang.get("connection_status")
        self.identity_header.text = self.lang.get("my_identity")
        self.copy_button.text = self.lang.get("copy_address")
        self.lang_header.text = self.lang.get("settings_language")
        self.lang_desc.text = self.lang.get("settings_language_desc")
        self.btn_english.text = self.lang.get("english")
        self.btn_farsi.text = self.lang.get("farsi")
        
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
