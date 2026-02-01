# AzadiConnect

![Status: Alpha](https://img.shields.io/badge/Status-Alpha-yellow)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-blue)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Censorship-Resistant P2P Chat & File Transfer**

AzadiConnect is a cross-platform application that enables secure, anonymous peer-to-peer communication over the Tor network. Designed for users in restricted environments, it provides end-to-end encrypted messaging with built-in censorship circumvention.

آزادی به معنای ارتباط بدون سانسور است.
*(Azadi means communication without censorship.)*

---

## Features

- 🔒 **End-to-End Encryption** — All traffic encrypted by Tor Hidden Services (v3 onions)
- 🌐 **Anonymous Identity** — Each user gets a unique `.onion` address
- 💬 **Real-Time Chat** — P2P messaging over Tor
- 📎 **File Transfer** — Send files up to 7MB (Base64 encoded)
- 🌨️ **Snowflake Transport** — Bypass censorship using WebRTC proxies
- 🌍 **Bilingual UI** — English and Farsi (فارسی) with RTL support

---

## Quick Start

### Prerequisites

**1. Install Tor:**

```bash
# Linux (Ubuntu/Debian)
sudo apt install tor

# Linux (Fedora)
sudo dnf install tor

# macOS
brew install tor

# Windows: Download from https://www.torproject.org/download/
# Extract, find tor.exe in: Tor Browser\Browser\TorBrowser\Tor\tor.exe
```

# Extract, find tor.exe in: Tor Browser\Browser\TorBrowser\Tor\tor.exe
```

# Extract, find tor.exe in: Tor Browser\Browser\TorBrowser\Tor\tor.exe
```

**2. Linux (.deb):**

Download the latest `.deb` package from Releases.

```bash
# Install with apt (handles dependencies automatically)
sudo apt install ./AzadiConnect-linux-amd64.deb
```

**3. Install Snowflake (Optional — for censored regions):**

Download from: https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/snowflake/-/releases

```bash
# Create resources directory and install
mkdir -p src/azadiconnect/resources
cp ~/Downloads/snowflake-client_linux_amd64 src/azadiconnect/resources/snowflake-client
chmod +x src/azadiconnect/resources/snowflake-client
```

### Running the Application

```bash
# Clone and enter directory
cd toga_file_share

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# OR: venv\Scripts\activate  # Windows

# Install dependencies
pip install briefcase

# Run in development mode
briefcase dev
```

---

## Development

### Project Structure

```
toga_file_share/
├── README.md                     # This file
├── pyproject.toml                # Project config & dependencies
├── tests/                        # Unit tests
│   └── test_core.py
└── src/azadiconnect/
    ├── app.py                    # Main UI (Toga)
    ├── crypto.py                 # ECC key generation
    ├── language_manager.py       # EN/FA localization
    ├── network.py                # Connection state machine
    ├── p2p_service.py            # P2P TCP over SOCKS5
    ├── tor_manager.py            # Tor process & Hidden Service
    ├── locales/                  # Translation files
    │   ├── en.json
    │   └── fa.json
    └── resources/                # Snowflake binary location
```

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run unit tests
pytest tests/ -v
```

### Building for Distribution

```bash
# Build native package
briefcase build

# Package for distribution
briefcase package
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Toga UI (app.py)                        │
│  ┌─────────┐  ┌────────────────────────────┐  ┌──────────┐ │
│  │  Tabs   │  │     Chat Interface         │  │ Settings │ │
│  │ EN | FA │  │ [📎] [Message Input] [Send]│  │ .onion   │ │
│  └─────────┘  └────────────────────────────┘  └──────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  NetworkManager                              │
│  State: DISCONNECTED → STARTING_TOR → READY                 │
│  Routes messages between UI and P2PService                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    P2PService                                │
│  Server: TCP on 127.0.0.1:8080 (receives from Hidden Svc)   │
│  Client: SOCKS5 → Tor → peer.onion:80                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    TorManager                                │
│  Binary detection → Config → Bootstrap → Hidden Service     │
│  Optional: Snowflake pluggable transport                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Mock Mode" appears | Ensure `tor` is installed and in PATH |
| Snowflake not activating | Check binary at `src/azadiconnect/resources/snowflake-client` |
| Connection timeout | Tor can take 30-60 seconds; check internet |
| File transfer fails | Max size ~7MB; check console for errors |

---

## Security

### What's Protected

- **Identity**: IP hidden via Tor onion routing
- **Transport**: Encrypted by Tor Hidden Services (v3)
- **Communication**: Only peers can read messages

### What's NOT Protected (MVP Limitations)

- Local data is memory-only (not persisted)
- No public key verification between peers
- Forward secrecy relies on Tor transport

### Best Practices

1. Verify peer's `.onion` address through a secure channel
2. Don't share your `.onion` address publicly
3. Keep Tor and Snowflake binaries updated

---

## License

MIT License. See [LICENSE](LICENSE) file.

---

## Disclaimer

This software is provided for educational and research purposes. It is designed to enable secure communication in restricted environments. The developers are not responsible for misuse of this software. Use responsibly and in accordance with applicable laws.

---

**Made with ❤️ for freedom of communication**
