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
from .contacts import ContactManager


class AzadiConnect(toga.App):
    """Main application class for AzadiConnect."""
    
    def startup(self):
        """Initialize the application UI."""
        self.lang = LanguageManager.get_instance()
        self.lang.register_listener(self._on_language_change)
        
        # Initialize managers
        self.contacts = ContactManager(self.paths.data)
        self.crypto = CryptoManager(self.paths.data)
        self.network = NetworkManager(self, self.paths.data)
        self.network.set_message_callback(self._on_message_received)
        self.network.set_status_callback(self._on_connection_status_change)
        self.network.set_contact_manager(self.contacts)
        
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
        """Build the Chats tab with Contact List and Chat View."""
        self.current_peer = None
        
        # --- 1. Chat View (Message List & Input) ---
        self.message_list = toga.Box(
            style=Pack(direction=COLUMN, padding=10, flex=1)
        )
        
        self.scroll_container = toga.ScrollContainer(
            content=self.message_list,
            style=Pack(flex=1)
        )
        
        # Chat Header (Back button + Peer Name)
        self.back_button = toga.Button(
            self.lang.get("back"),
            on_press=self._on_back_to_contacts,
            style=Pack(padding=5, width=80)
        )
        
        self.chat_header_label = toga.Label(
            "Peer Name",
            style=Pack(padding=5, font_weight='bold', flex=1)
        )
        
        chat_header = toga.Box(
            children=[self.back_button, self.chat_header_label],
            style=Pack(direction=ROW, padding=5, padding_bottom=10)
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
            style=Pack(padding=5, width=50),
            enabled=False  # Disabled until network is ready
        )
        
        input_box = toga.Box(
            children=[self.attach_button, self.message_input, self.send_button],
            style=Pack(direction=ROW, padding=5)
        )
        
        self.chat_view_container = toga.Box(
            children=[chat_header, self.scroll_container, input_box],
            style=Pack(direction=COLUMN, flex=1)
        )
        
        # --- 2. Contact List View ---
        self.add_contact_btn = toga.Button(
            self.lang.get("add_contact"),
            on_press=self._on_add_contact_dialog,
            style=Pack(padding=10, width=200, alignment=CENTER)
        )
        
        # Contact Table
        self.contact_table = toga.Table(
            headings=[self.lang.get("contact_name"), self.lang.get("contact_address")],
            on_activate=self._on_select_contact,
            style=Pack(flex=1, padding_top=10)
        )
        self._refresh_contact_list()
        
        top_bar = toga.Box(
            children=[self.add_contact_btn],
            style=Pack(alignment=CENTER, padding_bottom=10)
        )
        
        self.contact_list_container = toga.Box(
            children=[top_bar, self.contact_table],
            style=Pack(direction=COLUMN, flex=1, padding=10)
        )
        
        # --- 3. Main Container (Starts with Contact List) ---
        self.chats_box = toga.Box(
            children=[self.contact_list_container],
            style=Pack(direction=COLUMN, flex=1)
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
    
    async def _on_add_contact_dialog(self, widget):
        """Open dialog to add a new contact."""
        self.add_contact_window = toga.Window(title=self.lang.get("add_contact"), size=(300, 250))
        
        name_input = toga.TextInput(placeholder="Alice", style=Pack(padding=5, flex=1))
        addr_input = toga.TextInput(placeholder="v3address....onion", style=Pack(padding=5, flex=1))
        
        def save_contact(widget):
            name = name_input.value.strip()
            addr = addr_input.value.strip()
            if name and addr:
                if self.contacts.add_contact(name, addr):
                    self._refresh_contact_list()
                    self.add_contact_window.close()
                else:
                    self.main_window.error_dialog("Error", "Invalid .onion address")
                    
        save_btn = toga.Button(self.lang.get("save"), on_press=save_contact, style=Pack(padding=5, flex=1))
        
        box = toga.Box(
            children=[
                toga.Label(self.lang.get("contact_name"), style=Pack(padding_top=5)),
                name_input,
                toga.Label(self.lang.get("contact_address"), style=Pack(padding_top=5)),
                addr_input,
                toga.Box(children=[save_btn], style=Pack(padding_top=10))
            ],
            style=Pack(direction=COLUMN, padding=10)
        )
        self.add_contact_window.content = box
        self.add_contact_window.show()

    def _refresh_contact_list(self):
        """Reload contacts into the table."""
        if not hasattr(self, 'contact_table'):
            return
            
        data = []
        for contact in self.contacts.get_all():
            data.append((contact.name, contact.onion_address))
        self.contact_table.data = data
        
    def _on_select_contact(self, widget, row):
        """Handle contact selection."""
        # row[1] is the onion address
        addr = row[1]
        contact = self.contacts.get_contact(addr)
        if contact:
            self.current_peer = contact
            self.chat_header_label.text = contact.display_name
            
            # Clear old messages
            if hasattr(self.message_list, 'clear'):
                self.message_list.clear() # Toga main branch has clear()
            else:
                for child in list(self.message_list.children):
                    self.message_list.remove(child)
            self._message_widgets = []
                
            # Switch view
            self.chats_box.remove(self.contact_list_container)
            self.chats_box.add(self.chat_view_container)
            
            # Update status
            conn_status = self.network.get_connection_status()
            self._on_connection_status_change(ConnectionState.READY, conn_status)

    def _on_back_to_contacts(self, widget):
        """Return to contact list."""
        self.current_peer = None
        self.chats_box.remove(self.chat_view_container)
        self.chats_box.add(self.contact_list_container)
        self._refresh_contact_list()

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
            
        if not self.current_peer:
            self.main_window.info_dialog("Info", "No peer selected")
            return
        
        # Clear input
        self.message_input.value = ""
        
        # Add message to UI
        self.add_message_to_ui(text, is_me=True)
        
        # Send via network
        self.network.send_message(self.current_peer.onion_address, text)
    
    async def _on_attach_file(self, widget):
        """Handle attach file button press."""
        if not self.current_peer:
            return

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
                self.network.send_file(self.current_peer.onion_address, file_path)
                
        except Exception as e:
            print(f"[App] File dialog error: {e}")
    
    def _on_message_received(self, message: Message):
        """Callback when a message is received from the network."""
        self.add_message_to_ui(message.text, is_me=False)
    
    def _on_connection_status_change(self, state: ConnectionState, message: str):
        """Callback when connection status changes."""
        # Update status label
        self.status_label.text = message
        
        # Update onion address and enable/disable controls based on state
        if state == ConnectionState.READY:
            address = self.network.get_my_address()
            if address:
                self.onion_address_label.text = address
            else:
                self.onion_address_label.text = self.lang.get("mock_mode")
            
            # Enable file attach button when ready
            self.attach_button.enabled = True
        else:
            # Disable file attach button when not ready
            self.attach_button.enabled = False
    
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
