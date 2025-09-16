# generate_encryption_key.py
from cryptography.fernet import Fernet

# Générer une nouvelle clé
key = Fernet.generate_key()
print(f"ENCRYPTION_KEY = {key.decode()}")