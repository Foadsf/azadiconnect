# ================================================================================
#                           AzadiConnect - Setup Guide
#                    Secure P2P Communication for Restricted Regions
# ================================================================================

AzadiConnect is a censorship-resistant chat application that uses Tor Hidden
Services for anonymous, end-to-end encrypted communication.

## Quick Start (5 minutes)

### Step 1: Install Tor

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install tor
```

**Linux (Fedora):**
```bash
sudo dnf install tor
```

**macOS:**
```bash
brew install tor
```

**Windows:**
1. Download Tor Browser from: https://www.torproject.org/download/
2. Extract to a folder (e.g., C:\Tor)
3. The `tor.exe` binary is in: `Tor Browser\Browser\TorBrowser\Tor\tor.exe`


### Step 2: Install Snowflake (Optional - For Censored Regions)

Snowflake helps bypass censorship using WebRTC connections through volunteer
browser proxies. Skip this step if Tor works directly in your region.

**Download:**
Go to: https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/snowflake/-/releases

Download the appropriate binary:
- Linux: `snowflake-client_linux_amd64`
- macOS: `snowflake-client_darwin_amd64`
- Windows: `snowflake-client_windows_amd64.exe`

**Install:**
```bash
# Create resources directory
mkdir -p src/azadiconnect/resources

# Linux/macOS: Copy and rename
cp ~/Downloads/snowflake-client_linux_amd64 src/azadiconnect/resources/snowflake-client
chmod +x src/azadiconnect/resources/snowflake-client

# Windows: Copy to
# src\azadiconnect\resources\snowflake-client.exe
```


### Step 3: Run the Application

**Development Mode:**
```bash
cd /path/to/toga_file_share
source venv/bin/activate      # Linux/macOS
# OR: venv\Scripts\activate   # Windows

briefcase dev
```

**Build for Distribution:**
```bash
briefcase build
briefcase package
```


## Troubleshooting

### "Mock Mode" appears instead of real Tor connection
- Ensure `tor` is installed and in your PATH
- Try running `tor --version` in terminal to verify installation
- Check if another Tor instance is running (app uses dynamic ports)
- Check console output for specific error messages

### Snowflake not activating
- Verify binary exists at `src/azadiconnect/resources/snowflake-client`
- Ensure it has executable permissions (Linux/macOS: `chmod +x`)
- Check console for: `[TorManager] Enabling Snowflake transport`

### File transfer issues
- Maximum file size: ~7MB (due to Base64 encoding overhead)
- Received files are saved to: `~/.local/share/azadiconnect/downloads/`
- Check console for P2P errors if transfer fails

### Connection timeout
- Tor connections can take 30-60 seconds to establish
- Initial Hidden Service publication may take 1-2 minutes
- Ensure you have stable internet connectivity


## Security Information

### What's Protected
- **Identity**: Your IP address is hidden via Tor
- **Connection**: Traffic is encrypted by Tor Hidden Services (v3 onions)
- **Communication**: Only you and your peer can read messages
- **Files**: Transferred securely through Tor

### What's NOT Protected (yet)
- **Local Data**: Messages are stored in memory only (not persisted)
- **Key Exchange**: No public key verification between peers
- **Forward Secrecy**: Currently relies on Tor's transport encryption

### Best Practices
1. Verify peer's onion address through a secure channel
2. Don't share your onion address publicly
3. Keep Tor and Snowflake binaries updated
4. Use on a trusted device


## Project Structure

```
toga_file_share/
├── README_SETUP.txt              # This file
├── pyproject.toml                # Project configuration
├── venv/                         # Python virtual environment
└── src/azadiconnect/
    ├── app.py                    # Main application UI
    ├── crypto.py                 # ECC key generation (for future PFS)
    ├── language_manager.py       # EN/FA bilingual support
    ├── network.py                # Network connection manager
    ├── p2p_service.py            # P2P message/file transfer
    ├── tor_manager.py            # Tor process management
    ├── locales/
    │   ├── en.json               # English translations
    │   └── fa.json               # Farsi translations (فارسی)
    └── resources/
        └── snowflake-client      # Place Snowflake binary here
```


## Features

✅ Bilingual UI (English + Farsi with RTL support)
✅ Tor Hidden Services for anonymous identity
✅ Real-time chat over Tor network
✅ File transfer (up to ~7MB)
✅ Snowflake transport for censorship circumvention
✅ Automatic fallback to Mock Mode if Tor unavailable


## License & Disclaimer

This software is designed for secure communication in restricted environments.
Use responsibly and in accordance with local laws.

The developers are not responsible for misuse of this software.


## Support

For issues and contributions:
- Report bugs with console output and steps to reproduce
- Include your OS version and Tor version

آزادی به معنای ارتباط بدون سانسور است.
(Azadi means communication without censorship.)
