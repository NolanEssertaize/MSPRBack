import logging

from sqlalchemy import event
from sqlalchemy.orm import mapper, class_mapper
from app.models import User, Plant, Comment
from app.security import security_manager

logger = logging.getLogger(__name__)

def setup_events():

    @event.listens_for(User, 'load')
    def decrypt_user_data(user, _):
        
        try:

            if not hasattr(user, '_decrypted') or not user._decrypted:
                if user.email_encrypted:

                    user._decrypted_email = security_manager.decrypt_value(user.email_encrypted)
                if user.username_encrypted:
                    user._decrypted_username = security_manager.decrypt_value(user.username_encrypted)
                if user.phone_encrypted:
                    user._decrypted_phone = security_manager.decrypt_value(user.phone_encrypted)

                user._decrypted = True
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement des données utilisateur: {e}")

    @property
    def email_with_cache(self):
        if hasattr(self, '_decrypted_email'):
            return self._decrypted_email
        return security_manager.decrypt_value(self.email_encrypted) if self.email_encrypted else None
    
    @property
    def username_with_cache(self):
        if hasattr(self, '_decrypted_username'):
            return self._decrypted_username
        return security_manager.decrypt_value(self.username_encrypted) if self.username_encrypted else None
    
    @property
    def phone_with_cache(self):
        if hasattr(self, '_decrypted_phone'):
            return self._decrypted_phone
        return security_manager.decrypt_value(self.phone_encrypted) if self.phone_encrypted else None

    User.email = email_with_cache
    User.username = username_with_cache
    User.phone = phone_with_cache

    @event.listens_for(Plant, 'load')
    def ensure_owner_loaded(plant, _):


        pass
