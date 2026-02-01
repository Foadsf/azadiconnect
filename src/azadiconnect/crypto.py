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
    
    def encrypt_for_peer(self, plaintext: str, peer_public_key_pem: bytes) -> dict:
        """
        Encrypt a message for a peer using Ephemeral ECDH (ECIES).
        
        Args:
            plaintext: The message to encrypt
            peer_public_key_pem: Peer's public key in PEM format (bytes)
            
        Returns:
            Dictionary with 'ephemeral_pub' and 'ciphertext'
        """
        # Load peer public key
        peer_public_key = serialization.load_pem_public_key(peer_public_key_pem)
        
        # 1. Generate ephemeral key pair
        e_priv = ec.generate_private_key(ec.SECP256R1())
        e_pub = e_priv.public_key()
        
        # 2. Derive shared secret (Ephemeral Priv used with Peer Pub)
        shared_secret = e_priv.exchange(ec.ECDH(), peer_public_key)
        
        # 3. Derive symmetric key
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'azadiconnect-ecies'
        ).derive(shared_secret)
        
        fernet_key = base64.urlsafe_b64encode(derived_key)
        fernet = Fernet(fernet_key)
        
        # 4. Encrypt message
        ciphertext = fernet.encrypt(plaintext.encode('utf-8'))
        
        # 5. Serialize ephemeral public key
        e_pub_bytes = e_pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            'ephemeral_pub': base64.b64encode(e_pub_bytes).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }
    
    def decrypt_from_peer(self, payload: dict) -> str:
        """
        Decrypt a message using Ephemeral ECDH.
        
        Args:
            payload: Dictionary containing 'ephemeral_pub' and 'ciphertext'
            
        Returns:
            Decrypted plaintext string
        """
        # Load ephemeral public key
        e_pub_bytes = base64.b64decode(payload['ephemeral_pub'])
        e_pub = serialization.load_pem_public_key(e_pub_bytes)
        
        # 1. Derive shared secret (My Priv used with Ephemeral Pub)
        shared_secret = self._private_key.exchange(ec.ECDH(), e_pub)
        
        # 2. Derive symmetric key
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'azadiconnect-ecies'
        ).derive(shared_secret)
        
        fernet_key = base64.urlsafe_b64encode(derived_key)
        fernet = Fernet(fernet_key)
        
        # 3. Decrypt
        ciphertext = base64.b64decode(payload['ciphertext'])
        decrypted = fernet.decrypt(ciphertext)
        return decrypted.decode('utf-8')
