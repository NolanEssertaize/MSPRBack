# Plant Care Application

## Description
Cette application est un système complet de gestion de soins pour plantes, développé avec FastAPI. Elle permet aux utilisateurs d'enregistrer leurs plantes, de demander des services de soins auprès de botanistes, et de gérer les instructions d'entretien des plantes.

## Fonctionnalités
- 🌱 **Gestion des plantes**
  - Enregistrement de nouvelles plantes
  - Téléchargement de photos de plantes
  - Ajout d'instructions d'entretien
  - Suivi des emplacements des plantes

- 👤 **Gestion des utilisateurs**
  - Inscription et authentification des utilisateurs
  - Sécurité basée sur les jetons JWT
  - Chiffrement des données personnelles
  - Accès basé sur les rôles (utilisateurs réguliers et botanistes)

- 🤝 **Système de demande de soins**
  - Gestion directe des soins par les botanistes
  - Suivi des plantes en cours d'entretien
  - Système de notification des statuts

- 💬 **Système de commentaires**
  - Ajout de commentaires sur les plantes
  - Échange d'informations entre utilisateurs et botanistes
  - Historique de communication

## Stack Technique
- **Framework Backend**: FastAPI
- **Base de données**: SQLite avec SQLAlchemy ORM
- **Authentification**: Jetons JWT
- **Chiffrement**: Fernet (cryptography)
- **Migrations**: Alembic
- **Documentation API**: Swagger/OpenAPI
- **Conteneurisation**: Docker et Docker Compose
- **Tests**: Pytest avec base de données réelle

## Prérequis
- Docker et Docker Compose (pour le déploiement conteneurisé)
- Python 3.10 ou supérieur (pour le développement local)
- pip (gestionnaire de paquets Python)
- virtualenv (recommandé pour le développement local)

## Installation et déploiement

### Utilisation de Docker (Recommandé)

1. Clonez le dépôt:
```bash
git clone [url-du-dépôt]
cd plant-care-app
```

2. Configurez les variables d'environnement:
   La configuration par défaut se trouve dans `docker-compose.yml`. Pour la production, vous devriez changer les clés `SECRET_KEY` et `ENCRYPTION_KEY`.

3. Construisez et démarrez les conteneurs Docker:
```bash
docker-compose up -d
```

4. Initialisez la base de données (première fois uniquement):
```bash
docker-compose exec api alembic upgrade head
```

5. Accédez à l'application:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Documentation alternative: http://localhost:8000/redoc

6. Commandes Docker supplémentaires:

   - Afficher les logs:
   ```bash
   docker-compose logs -f
   ```

   - Arrêter l'application:
   ```bash
   docker-compose down
   ```

   - Reconstruire après des modifications:
   ```bash
   docker-compose up --build -d
   ```

### Configuration du développement local

1. Clonez le dépôt:
```bash
git clone [url-du-dépôt]
cd plant-care-app
```

2. Créez et activez un environnement virtuel:
```bash
python -m venv .venv
source .\.venv/bin/activate  # Sur Windows: .venv\Scripts\activate
```

3. Installez les dépendances:
```bash
pip install -r requirements.txt
```

4. Créez le fichier d'environnement:
Créez un fichier `.env` dans le répertoire racine avec:
```env
DATABASE_URL=sqlite:///a_rosa_je.db
SECRET_KEY=votre-clé-très-secrète-à-changer
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=votre-clé-de-chiffrement-à-changer
ENCRYPTION_ENABLED=true
```

5. Initialisez la base de données:
```bash
alembic upgrade head
```

6. Démarrez l'application:
```bash
uvicorn app.main:app --reload
```

## Points d'API

### Authentification
- `POST /token` - Obtenir un jeton d'accès
- `POST /users/` - Créer un nouvel utilisateur

### Utilisateurs
- `PUT /users/{user_id}` - Mettre à jour un utilisateur
- `GET /users/me/` - Obtenir les informations de l'utilisateur actuel
- `DELETE /users/` - Supprimer un utilisateur

### Plantes
- `POST /plants/` - Créer une nouvelle plante
- `GET /my_plants/` - Lister les plantes de l'utilisateur
- `GET /all_plants/` - Lister toutes les plantes sauf celles de l'utilisateur
- `PUT /plants/{id}` - Mettre à jour une plante
- `DELETE /plants/` - Supprimer une plante

### Soins des plantes
- `PUT /plants/{plant_id}/start-care` - Commencer à prendre soin d'une plante
- `PUT /plants/{plant_id}/end-care` - Terminer les soins d'une plante
- `GET /care-requests/` - Lister les demandes de soins

### Commentaires
- `POST /comments/` - Créer un commentaire
- `GET /plants/{plant_id}/comments/` - Obtenir les commentaires d'une plante
- `PUT /comments/{comment_id}` - Mettre à jour un commentaire
- `DELETE /comments/{comment_id}` - Supprimer un commentaire
- `GET /users/{user_id}/comments/` - Obtenir les commentaires d'un utilisateur

## Structure du projet
```
plant_care_app/
├── alembic/                  # Migrations de base de données
│   ├── versions/
│   └── env.py
├── app/                      # Code source de l'application
│   ├── __init__.py
│   ├── main.py              # Application FastAPI
│   ├── config.py            # Paramètres de configuration
│   ├── database.py          # Connexion à la base de données
│   ├── models.py            # Modèles SQLAlchemy
│   ├── schemas.py           # Modèles Pydantic
│   ├── auth.py              # Logique d'authentification
│   ├── encryption.py        # Module de chiffrement
│   └── tests/               # Tests avec base de données réelle
├── photos/                   # Photos des plantes téléchargées
├── requirements.txt          # Dépendances du projet
├── alembic.ini              # Configuration Alembic
├── Dockerfile               # Configuration d'image Docker
├── docker-compose.yml       # Configuration Docker Compose
├── run_tests.sh             # Script d'exécution des tests
├── .dockerignore            # Exclusions pour la construction Docker
└── .env                     # Variables d'environnement (dev local uniquement)
```

## Sécurité des données

### Chiffrement des données personnelles
Cette application utilise le chiffrement Fernet pour protéger les informations personnelles des utilisateurs:

- Les données chiffrées incluent:
  - Adresses email
  - Numéros de téléphone
  - Noms d'utilisateur

- Avantages du chiffrement:
  - Protection contre les accès non autorisés à la base de données
  - Conformité améliorée avec les réglementations sur la protection des données (RGPD)
  - Risque réduit en cas de violation de données

### Configuration du chiffrement
Le chiffrement est configuré via les variables d'environnement:
```env
ENCRYPTION_KEY=votre-clé-de-chiffrement-sécurisée
ENCRYPTION_ENABLED=true
```

## Tests

L'application utilise Pytest avec une base de données réelle pour des tests complets:

```bash
# Exécuter tous les tests
./run_tests.sh

# Exécuter les tests dans Docker
./run_tests.sh --docker
```

Les tests couvrent:
- Authentification des utilisateurs
- Opérations CRUD sur les plantes
- Système de commentaires
- Chiffrement et déchiffrement des données

## Notes de sécurité
- Changez les clés `SECRET_KEY` et `ENCRYPTION_KEY` par défaut en production
- Utilisez HTTPS en production
- Implémentez la limitation de débit pour une utilisation en production
- Mettez régulièrement à jour les dépendances

## Sauvegarde et maintenance

### Sauvegarde des données
L'application utilise des volumes pour conserver les données en dehors du conteneur:
- Fichier de base de données (`a_rosa_je.db`)
- Répertoire des photos de plantes (`photos/`)

Pour sauvegarder vos données, copiez simplement ces fichiers depuis la machine hôte.

### Migrations de base de données
Après avoir modifié les modèles, créez et appliquez les migrations:

Avec Docker:
```bash
docker-compose exec api alembic revision --autogenerate -m "Description des changements"
docker-compose exec api alembic upgrade head
```

## Dépannage

### Problèmes courants
- **Problèmes de connexion à la base de données**: Vérifiez que le fichier de base de données existe et a les permissions appropriées
- **Échecs de téléchargement de photos**: Vérifiez que le répertoire photos existe et a les permissions d'écriture
- **Erreurs d'authentification**: Vérifiez que votre jeton n'a pas expiré (par défaut 30 minutes)
- **Problèmes de chiffrement**: Assurez-vous que la clé de chiffrement est cohérente et correctement configurée

### Spécifique à Docker
- **Le conteneur ne démarre pas**: Vérifiez les logs avec `docker-compose logs -f api`
- **Problèmes de montage de volume**: Vérifiez le chemin dans docker-compose.yml et les permissions du répertoire

### Réinitialisation de la base de données
Si vous rencontrez des problèmes de migration complexes, vous pouvez réinitialiser complètement la base de données:

```bash
# Arrêtez l'application
docker-compose down

# Supprimez la base de données
rm a_rosa_je.db

# Redémarrez et recréez la base de données
docker-compose up -d
docker-compose exec api alembic upgrade head
```

## Contact
Nolan Essertaize