"""
CryptoManager - Handles E2E encryption key generation and message encryption.
Uses ECC (Elliptic Curve Cryptography) for key exchange and Fernet for message encryption.
"""
import os
import base64
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.fernet import Fernet


class CryptoManager:
    """Manages cryptographic operations for secure messaging."""
    
    def __init__(self, data_path: Path):
        """
        Initialize CryptoManager with key storage path.
        
        Args:
            data_path: Path to store keys (typically toga.App.paths.data)
        """
        self._data_path = Path(data_path)
        self._keys_dir = self._data_path / "keys"
        self._private_key_path = self._keys_dir / "private_key.pem"
        self._public_key_path = self._keys_dir / "public_key.pem"
        
        self._private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self._public_key: Optional[ec.EllipticCurvePublicKey] = None
        
        # Create keys directory if it doesn't exist
        self._keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or generate keys
        self._initialize_keys()
    
    def _initialize_keys(self) -> None:
        """Load existing keys or generate new ones."""
        if self._private_key_path.exists() and self._public_key_path.exists():
            self._load_keys()
        else:
            self._generate_keys()
    
    def _generate_keys(self) -> None:
        """Generate a new ECC key pair and save to disk."""
        # Generate private key using SECP256R1 curve
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()
        
        # Serialize and save private key
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()  # TODO: Add password protection
        )
        self._private_key_path.write_bytes(private_pem)
        
        # Harden permissions (read/write by owner only)
        try:
            import stat
            os.chmod(self._private_key_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            print(f"[CryptoManager] Failed to set private key permissions: {e}")
        
        
        # Serialize and save public key
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self._public_key_path.write_bytes(public_pem)
    
    def _load_keys(self) -> None:
        """Load existing keys from disk."""
        # Load private key
        private_pem = self._private_key_path.read_bytes()
        self._private_key = serialization.load_pem_private_key(
            private_pem,
            password=None
        )
        
        # Load public key
        public_pem = self._public_key_path.read_bytes()
        self._public_key = serialization.load_pem_public_key(public_pem)
    
    def get_public_key_string(self) -> str:
        """
        Get the public key as a base64-encoded string.
        This is the "Connect ID" that users share.
        
        Returns:
            Base64-encoded public key string
        """
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(public_pem).decode('utf-8')
    
    def _derive_shared_key(self, peer_public_key: ec.EllipticCurvePublicKey) -> bytes:
        """
        Derive a shared secret using ECDH key exchange.
        
        Args:
            peer_public_key: The peer's public key
            
        Returns:
            Derived 32-byte key suitable for Fernet
        """
        shared_secret = self._private_key.exchange(ec.ECDH(), peer_public_key)
        
        # Use HKDF to derive a proper key from the shared secret
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'azadiconnect-session-key'
        ).derive(shared_secret)
        
        return base64.urlsafe_b64encode(derived_key)
    
    def encrypt(self, message: str, peer_public_key_b64: str) -> str:
        """
        Encrypt a message for a specific peer.
        
        Args:
            message: The plaintext message
            peer_public_key_b64: Base64-encoded peer public key
            
        Returns:
            Base64-encoded encrypted message
        """
        # Decode peer's public key
        peer_public_pem = base64.b64decode(peer_public_key_b64)
        peer_public_key = serialization.load_pem_public_key(peer_public_pem)
        
        # Derive shared key
        fernet_key = self._derive_shared_key(peer_public_key)
        fernet = Fernet(fernet_key)
        
        # Encrypt
        encrypted = fernet.encrypt(message.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, ciphertext_b64: str, peer_public_key_b64: str) -> str:
        """
        Decrypt a message from a specific peer.
        
        Args:
            ciphertext_b64: Base64-encoded encrypted message
            peer_public_key_b64: Base64-encoded peer public key
            
        Returns:
            Decrypted plaintext message
        """
        # Decode peer's public key
        peer_public_pem = base64.b64decode(peer_public_key_b64)
        peer_public_key = serialization.load_pem_public_key(peer_public_pem)
        
        # Derive shared key
        fernet_key = self._derive_shared_key(peer_public_key)
        fernet = Fernet(fernet_key)
        
        # Decrypt
        encrypted = base64.b64decode(ciphertext_b64)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode('utf-8')
    
    def encrypt_simple(self, message: str) -> Tuple[str, bytes]:
        """
        Simple encryption using a random Fernet key (for mock mode).
        
        Args:
            message: The plaintext message
            
        Returns:
            Tuple of (encrypted message, key used)
        """
        key = Fernet.generate_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(message.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8'), key
    
    def decrypt_simple(self, ciphertext_b64: str, key: bytes) -> str:
        """
        Simple decryption using a provided Fernet key (for mock mode).
        
        Args:
            ciphertext_b64: Base64-encoded encrypted message
            key: The Fernet key used for encryption
            
        Returns:
            Decrypted plaintext message
        """
        fernet = Fernet(key)
        encrypted = base64.b64decode(ciphertext_b64)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode('utf-8')
