import hashlib
import base64
from cryptography.fernet import Fernet
from app.config import settings

class SecurityManager:
    def __init__(self):

        self.fernet = Fernet(self._prepare_key(settings.ENCRYPTION_KEY))
    
    def _prepare_key(self, key_string):
        
        if len(key_string) == 44 and key_string[-2:] == '==':

            return key_string.encode()

        key_bytes = hashlib.sha256(key_string.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)
    
    def hash_value(self, value):
        
        if value is None:
            return None
        return hashlib.sha256(value.encode()).hexdigest()
    
    def encrypt_value(self, value):
        
        if value is None:
            return None
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value):
        
        if encrypted_value is None:
            return None
        return self.fernet.decrypt(encrypted_value.encode()).decode()

    def find_by_email(self, db_session, email):
        
        from app.models import User  # Import ici pour éviter l'importation circulaire
        email_hash = self.hash_value(email)
        return db_session.query(User).filter(User.email_hash == email_hash).first()
    
    def find_by_username(self, db_session, username):
        
        from app.models import User
        username_hash = self.hash_value(username)
        return db_session.query(User).filter(User.username_hash == username_hash).first()
    
    def find_by_phone(self, db_session, phone):
        
        from app.models import User
        phone_hash = self.hash_value(phone)
        return db_session.query(User).filter(User.phone_hash == phone_hash).first()

security_manager = SecurityManager()
