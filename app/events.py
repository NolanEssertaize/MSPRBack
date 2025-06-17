import logging

from sqlalchemy import event
from sqlalchemy.orm import mapper, class_mapper
from app.models import User, Plant, Comment
from app.security import security_manager

logger = logging.getLogger(__name__)

def setup_events():
    """Configure les événements SQLAlchemy pour le déchiffrement automatique"""
    
    # Événement pour déchiffrer les données utilisateur après chargement
    @event.listens_for(User, 'load')
    def decrypt_user_data(user, _):
        """Déchiffre les données sensibles d'un utilisateur après chargement depuis la BD"""
        try:
            # On ne déchiffre que si les données sont présentes et n'ont pas déjà été déchiffrées
            if not hasattr(user, '_decrypted') or not user._decrypted:
                if user.email_encrypted:
                    # On accède directement aux attributs pour éviter de déclencher les propriétés
                    user._decrypted_email = security_manager.decrypt_value(user.email_encrypted)
                if user.username_encrypted:
                    user._decrypted_username = security_manager.decrypt_value(user.username_encrypted)
                if user.phone_encrypted:
                    user._decrypted_phone = security_manager.decrypt_value(user.phone_encrypted)
                # Marquer l'utilisateur comme déchiffré pour éviter de répéter l'opération
                user._decrypted = True
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement des données utilisateur: {e}")
    
    # Modifier les propriétés de User pour utiliser les valeurs déchiffrées si disponibles
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
    
    # Remplacer les propriétés existantes par les nouvelles avec cache
    User.email = email_with_cache
    User.username = username_with_cache
    User.phone = phone_with_cache
    
    # Événement pour charger automatiquement le propriétaire d'une plante
    @event.listens_for(Plant, 'load')
    def ensure_owner_loaded(plant, _):
        """S'assure que le propriétaire de la plante est chargé correctement"""
        # Cette fonction préparera la plante pour que son propriétaire soit accessible
        # dans le futur, sans avoir à modifier le modèle de la plante directement
        pass