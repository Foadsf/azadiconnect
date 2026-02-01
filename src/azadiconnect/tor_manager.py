"""
TorManager - Handles Tor process lifecycle and hidden service creation.
Uses stem library to control the Tor daemon.
"""
import os
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional
from enum import Enum, auto


class TorState(Enum):
    """Tor connection states."""
    DISCONNECTED = auto()
    FINDING_BINARY = auto()
    STARTING_TOR = auto()
    BOOTSTRAPPING = auto()
    CREATING_SERVICE = auto()
    READY = auto()
    ERROR = auto()


class TorManager:
    """Manages the Tor process and hidden service."""
    
    def __init__(self, work_path: Path):
        """
        Initialize TorManager.
        
        Args:
            work_path: Path to store Tor data (typically toga.App.paths.data)
        """
        self._work_path = Path(work_path)
        self._tor_data_dir = self._work_path / "tor_data"
        self._state = TorState.DISCONNECTED
        self._bootstrap_progress = 0
        self._error_message: Optional[str] = None
        
        # Tor process and controller
        self._tor_process = None
        self._controller = None
        
        # Hidden service info
        self._onion_address: Optional[str] = None
        self._service_key: Optional[str] = None
        
        # Ports - use 'auto' for dynamic allocation to avoid conflicts
        self._socks_port = 'auto'
        self._control_port = 'auto'
        self._hidden_service_port = 8080
        self._actual_socks_port: Optional[int] = None
        self._actual_control_port: Optional[int] = None
        
        # Callbacks
        self._on_state_change: Optional[Callable[[TorState, str], None]] = None
        self._on_bootstrap_progress: Optional[Callable[[int], None]] = None
        
        # Create data directory
        self._tor_data_dir.mkdir(parents=True, exist_ok=True)
    
    def set_state_callback(self, callback: Callable[[TorState, str], None]) -> None:
        """Set callback for state changes."""
        self._on_state_change = callback
    
    def set_bootstrap_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for bootstrap progress updates."""
        self._on_bootstrap_progress = callback
    
    def _set_state(self, state: TorState, message: str = "") -> None:
        """Update state and notify callback."""
        self._state = state
        if state == TorState.ERROR:
            self._error_message = message
        print(f"[TorManager] State: {state.name} - {message}")
        if self._on_state_change:
            try:
                self._on_state_change(state, message)
            except Exception as e:
                print(f"[TorManager] Callback error: {e}")
    
    def _find_tor_binary(self) -> Optional[str]:
        """
        Find the Tor binary.
        First checks bundled bin/ directory, then system PATH.
        
        Returns:
            Path to tor binary or None if not found
        """
        # Check for bundled binary (for packaged apps)
        bundled_paths = [
            self._work_path.parent / "bin" / "tor",
            self._work_path.parent.parent / "bin" / "tor",
            Path(__file__).parent / "bin" / "tor",
        ]
        
        for bundled in bundled_paths:
            if bundled.exists() and os.access(bundled, os.X_OK):
                return str(bundled)
        
        # Fall back to system tor
        system_tor = shutil.which("tor")
        if system_tor:
            return system_tor
        
        return None
    
    def get_state(self) -> TorState:
        """Get current Tor state."""
        return self._state
    
    def get_onion_address(self) -> Optional[str]:
        """Get the hidden service onion address."""
        return self._onion_address
    
    def get_socks_port(self) -> Optional[int]:
        """Get the SOCKS5 proxy port."""
        return self._actual_socks_port
    
    def get_bootstrap_progress(self) -> int:
        """Get bootstrap progress percentage."""
        return self._bootstrap_progress
    
    def get_error_message(self) -> Optional[str]:
        """Get error message if in ERROR state."""
        return self._error_message
    
    def start(self) -> None:
        """
        Start Tor in a background thread.
        Progress will be reported via callbacks.
        """
        thread = threading.Thread(target=self._start_tor_sync, daemon=True)
        thread.start()
    
    def _start_tor_sync(self) -> None:
        """Synchronous Tor startup (runs in background thread)."""
        try:
            from stem.control import Controller
            from stem.process import launch_tor_with_config
            
            # Find Tor binary
            self._set_state(TorState.FINDING_BINARY, "Looking for Tor binary...")
            tor_binary = self._find_tor_binary()
            
            if not tor_binary:
                self._set_state(
                    TorState.ERROR,
                    "Tor binary not found. Please install Tor: sudo apt install tor"
                )
                return
            
            self._set_state(TorState.STARTING_TOR, f"Found Tor at {tor_binary}")
            
            # Find available ports
            import socket
            def get_free_port():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', 0))
                    return s.getsockname()[1]
            
            self._actual_socks_port = get_free_port()
            self._actual_control_port = get_free_port()
            
            # Tor configuration with dynamic ports
            tor_config = {
                'SocksPort': str(self._actual_socks_port),
                'ControlPort': str(self._actual_control_port),
                'DataDirectory': str(self._tor_data_dir),
                'CookieAuthentication': '1',
                # Reduce logging for cleaner output
                'Log': 'notice stdout',
                
                # ==============================================================
                # SNOWFLAKE PLUGGABLE TRANSPORT (PLACEHOLDER)
                # Uncomment and configure when Snowflake binary is bundled:
                # 
                # 'UseBridges': '1',
                # 'ClientTransportPlugin': 'snowflake exec /path/to/snowflake-client',
                # 'Bridge': 'snowflake 192.0.2.3:80 ...',
                # ==============================================================
            }
            
            # Bootstrap progress callback
            def bootstrap_callback(line: str):
                if "Bootstrapped" in line:
                    try:
                        # Parse "Bootstrapped 45%: ..."
                        percent_str = line.split("Bootstrapped ")[1].split("%")[0]
                        self._bootstrap_progress = int(percent_str)
                        self._set_state(
                            TorState.BOOTSTRAPPING,
                            f"Bootstrapping: {self._bootstrap_progress}%"
                        )
                        if self._on_bootstrap_progress:
                            self._on_bootstrap_progress(self._bootstrap_progress)
                    except (IndexError, ValueError):
                        pass
            
            # Launch Tor
            self._set_state(TorState.BOOTSTRAPPING, "Starting Tor daemon...")
            self._tor_process = launch_tor_with_config(
                config=tor_config,
                tor_cmd=tor_binary,
                init_msg_handler=bootstrap_callback,
                take_ownership=True,  # Kill Tor when Python exits
            )
            
            # Connect controller
            self._set_state(TorState.CREATING_SERVICE, "Connecting to Tor controller...")
            self._controller = Controller.from_port(port=self._actual_control_port)
            self._controller.authenticate()
            
            # Create ephemeral hidden service
            self._set_state(TorState.CREATING_SERVICE, "Creating hidden service...")
            response = self._controller.create_ephemeral_hidden_service(
                ports={80: self._hidden_service_port},
                await_publication=True,
                key_type='NEW',
                key_content='ED25519-V3',
            )
            
            self._onion_address = f"{response.service_id}.onion"
            self._service_key = response.private_key if hasattr(response, 'private_key') else None
            
            self._set_state(TorState.READY, f"Connected: {self._onion_address}")
            
        except ImportError as e:
            self._set_state(TorState.ERROR, f"Missing dependency: {e}")
        except Exception as e:
            self._set_state(TorState.ERROR, f"Tor startup failed: {e}")
    
    def stop(self) -> None:
        """Stop Tor and cleanup."""
        if self._controller:
            try:
                self._controller.close()
            except Exception:
                pass
            self._controller = None
        
        if self._tor_process:
            try:
                self._tor_process.kill()
            except Exception:
                pass
            self._tor_process = None
        
        self._onion_address = None
        self._set_state(TorState.DISCONNECTED, "Stopped")
    
    def is_ready(self) -> bool:
        """Check if Tor is ready for use."""
        return self._state == TorState.READY
