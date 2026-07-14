"""
Encryption utilities for CoderAgent
Handles secure storage and retrieval of sensitive data (API keys, etc.)
"""
import base64
from cryptography.fernet import Fernet
from logger import setup_logger

logger = setup_logger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, master_key: str = None):
        """
        Initialize encryption manager
        
        Args:
            master_key: Master encryption key (base64 encoded). If None, generates new key.
        """
        if master_key:
            self.cipher = Fernet(master_key.encode())
        else:
            # Generate new key
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            logger.warning(f"Generated new encryption key: {key.decode()}")
            logger.warning("Store this key in ENCRYPTION_KEY environment variable!")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Encrypted string (base64 encoded)
        """
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        
        Args:
            ciphertext: Encrypted string (base64 encoded)
        
        Returns:
            Decrypted plaintext string
        """
        try:
            encrypted = base64.b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key
        
        Returns:
            Base64 encoded encryption key
        """
        key = Fernet.generate_key()
        return key.decode()


# Global encryption manager instance
_encryption_manager = None


def get_encryption_manager(master_key: str = None) -> EncryptionManager:
    """
    Get or create global encryption manager instance
    
    Args:
        master_key: Master encryption key (base64 encoded)
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(master_key)
    
    return _encryption_manager
