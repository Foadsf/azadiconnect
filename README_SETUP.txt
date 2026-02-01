# AzadiConnect - Setup Instructions

## Prerequisites

For the app to work in "Real Mode" (actual Tor connectivity), you need to 
install the Tor binaries. Without these, the app will fall back to "Mock Mode".

## Required Binaries

### 1. Tor Binary

**Linux (Ubuntu/Debian):**
```bash
sudo apt install tor
```

**macOS:**
```bash
brew install tor
```

**Windows:**
Download from https://www.torproject.org/download/

### 2. Snowflake Client (Optional - for censorship circumvention)

Snowflake is a pluggable transport that helps bypass censorship by using 
WebRTC connections through volunteer browser proxies.

**Download from:**
https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/snowflake/-/releases

**Installation:**
1. Download `snowflake-client` for your platform
2. Place the binary in: `src/azadiconnect/resources/snowflake-client`
3. Make it executable: `chmod +x src/azadiconnect/resources/snowflake-client`

If Snowflake binary is not present, the app will connect directly to Tor
(which may be blocked in heavily censored regions).

## Running the App

### Development Mode:
```bash
cd /path/to/toga_file_share
source venv/bin/activate
briefcase dev
```

### Build for Distribution:
```bash
briefcase build
briefcase run
```

## Features

- **Bilingual UI**: English and Farsi (فارسی) with RTL support
- **End-to-End Encryption**: ECC key generation and Fernet symmetric encryption
- **Tor Hidden Services**: Each user gets a unique .onion address
- **File Transfer**: Send files via Base64 over the Tor network
- **Censorship Resistance**: Snowflake transport for bypassing blocks

## Troubleshooting

### "Mock Mode" appears instead of real connection:
- Ensure `tor` is installed and in your PATH
- Check if another Tor instance is running (the app uses dynamic ports)
- Check the console for error messages

### File transfer not working:
- Received files are saved to: `[app data]/downloads/`
- Maximum file size depends on network conditions

### Snowflake not activating:
- Verify the binary exists at `src/azadiconnect/resources/snowflake-client`
- Ensure it has executable permissions
- Check console for "[TorManager] Enabling Snowflake transport"

## License

This project is designed for secure communication in restricted environments.
Use responsibly and in accordance with local laws.
