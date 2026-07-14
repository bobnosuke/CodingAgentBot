import unittest
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from modules.security.encryption import EncryptionManager

class TestEncryption(unittest.TestCase):
    def setUp(self):
        # Use a consistent key for testing
        self.test_key = "Z-h9Ljf2v9vKjNijneFhsoonUwHUJAy5KOfD6BJlS68="
        self.manager = EncryptionManager(self.test_key)

    def test_encrypt_decrypt(self):
        original_text = "sk-or-v1-test-api-key-12345"
        encrypted = self.manager.encrypt(original_text)
        
        self.assertNotEqual(original_text, encrypted)
        
        decrypted = self.manager.decrypt(encrypted)
        self.assertEqual(original_text, decrypted)

    def test_different_encryption(self):
        # Encrypting the same text twice should result in different ciphertexts (due to IV)
        text = "same-text"
        enc1 = self.manager.encrypt(text)
        enc2 = self.manager.encrypt(text)
        
        self.assertNotEqual(enc1, enc2)
        self.assertEqual(self.manager.decrypt(enc1), self.manager.decrypt(enc2))

if __name__ == '__main__':
    unittest.main()
