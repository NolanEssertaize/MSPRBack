# Plant Care Application - Stack LGTM avec Alloy

Cette documentation décrit l'implémentation de la stack d'observabilité LGTM (Loki, Grafana, Tempo, Mimir) avec Grafana Alloy pour l'application Plant Care.

##  Démarrage Rapide

### Prérequis
- Docker et Docker Compose
- 8 GB de RAM minimum
- Ports disponibles: 3000, 3100, 3200, 4317, 4318, 5432, 8000, 9009, 12345

### Installation et Démarrage

```bash
# Cloner le projet et naviguer dans le répertoire
cd plant-care-app

# Rendre le script exécutable
chmod +x setup-observability.sh

# Démarrer la stack complète
./setup-observability.sh start
```

Le script va automatiquement :
- Créer la structure des répertoires
- Générer un fichier `.env` avec des clés sécurisées
- Démarrer tous les services
- Exécuter les migrations de base de données
- Configurer les dashboards Grafana

##  Architecture

### Services Déployés

| Service | Port | Description | Interface |
|---------|------|-------------|-----------|
| **PostgreSQL** | 5432 | Base de données principale | - |
| **Plant Care API** | 8000 | Application FastAPI | http://localhost:8000/docs |
| **Grafana Alloy** | 12345 | Collecteur de télémétrie | http://localhost:12345 |
| **Loki** | 3100 | Stockage des logs | - |
| **Tempo** | 3200 | Stockage des traces | - |
| **Mimir** | 9009 | Stockage des métriques | - |
| **Grafana** | 3000 | Visualisation | http://localhost:3000 |

### Flux de Données

```
Application FastAPI → Alloy → LGTM Stack → Grafana
                     ↓
              [Logs, Traces, Métriques]
```

##  Observabilité

### Métriques Collectées

#### Métriques de l'Application
- `plant_care_user_registrations_total` - Nombre total d'inscriptions
- `plant_care_plant_creations_total` - Nombre total de plantes créées
- `plant_care_care_requests_total` - Nombre total de demandes de soin
- `plant_care_comments_created_total` - Nombre total de commentaires
- `plant_care_active_users` - Nombre d'utilisateurs actifs
- `plant_care_plants_in_care` - Nombre de plantes en soin

#### Métriques de Performance
- `plant_care_request_duration_seconds` - Durée des requêtes HTTP
- `plant_care_database_query_duration_seconds` - Durée des requêtes DB
- Métriques système (CPU, mémoire, disque)

### Logs Structurés

Tous les logs sont au format JSON avec les champs suivants :
- `timestamp` - Horodatage ISO 8601
- `level` - Niveau de log (DEBUG, INFO, WARNING, ERROR)
- `service` - Nom du service
- `trace_id` - ID de trace pour corrélation
- `span_id` - ID de span pour corrélation
- `user_id` - ID utilisateur si authentifié
- `message` - Message du log
- Champs contextuels spécifiques

### Traces Distribuées

OpenTelemetry auto-instrumente :
- Requêtes HTTP FastAPI
- Requêtes base de données SQLAlchemy/PostgreSQL
- Requêtes HTTP sortantes
- Opérations personnalisées avec `@trace_function`

##  Dashboards Grafana

### Dashboard Principal : "Plant Care - Application Overview"

**Panneaux disponibles :**
1. **Request Rate** - Taux de requêtes par seconde
2. **Total User Registrations** - Nombre total d'inscriptions
3. **Response Time** - Temps de réponse (P50, P95)
4. **Request Methods Distribution** - Distribution des méthodes HTTP
5. **Plant Statistics** - Statistiques des plantes
6. **Database Query Performance** - Performance des requêtes DB
7. **Application Errors and Warnings** - Logs d'erreurs et avertissements

### Accès Grafana
- URL: http://localhost:3000
- Login: `admin`
- Password: `admin`

##  Configuration

### Variables d'Environnement

```bash
# Base de données
DATABASE_URL=postgresql://plant_user:plant_password@postgres:5432/plant_care_db

# Observabilité
ENABLE_OBSERVABILITY=true
OTEL_SERVICE_NAME=plant-care-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317

# Sécurité
SECRET_KEY=<généré automatiquement>
ENCRYPTION_KEY=<généré automatiquement>
```

### Configuration Alloy

Le fichier `observability/alloy/config.alloy` configure :
- Découverte des services Docker
- Collecte des logs (conteneurs + système)
- Collecte des métriques (Prometheus + custom)
- Réception des traces OTLP
- Export vers Loki, Tempo, et Mimir

### Configuration PostgreSQL

Optimisations incluses :
- Pool de connexions configuré
- Index de performance automatiques
- Fonctions d'analyse et monitoring
- Audit trail optionnel

##  Utilisation

### Recherche dans les Logs (Loki)

```logql
# Logs d'erreur de l'application
{service="plant-care-api"} |= "ERROR"

# Logs d'un utilisateur spécifique
{service="plant-care-api"} | json | user_id="123"

# Logs de requêtes lentes
{service="plant-care-api"} | json | duration_ms > 1000
```

### Requêtes de Métriques (Mimir/Prometheus)

```promql
# Taux de requêtes par seconde
rate(plant_care_request_duration_seconds_count[5m])

# P95 du temps de réponse
histogram_quantile(0.95, rate(plant_care_request_duration_seconds_bucket[5m]))

# Taux d'erreur
rate(plant_care_request_duration_seconds_count{status_code=~"5.."}[5m]) / 
rate(plant_care_request_duration_seconds_count[5m])
```

### Recherche de Traces (Tempo)

- Recherche par service : `service.name="plant-care-api"`
- Recherche par utilisateur : `user.id="123"`
- Recherche par durée : `duration > 1s`

##  Alertes

### Alertes Configurées

1. **High Error Rate** - Taux d'erreur > 10%
2. **Slow Response Time** - P95 > 2s
3. **Database Connection Issues** - Échecs de connexion DB
4. **High Memory Usage** - Utilisation mémoire > 80%

### Configuration des Notifications

Modifier `observability/grafana/provisioning/alerting/alerting.yml` pour configurer :
- Email
- Slack
- Webhook
- PagerDuty

## 🛠️ Maintenance

### Commandes Utiles

```bash
# Démarrer la stack
./setup-observability.sh start

# Arrêter la stack
./setup-observability.sh stop

# Redémarrer la stack
./setup-observability.sh restart

# Voir le statut des services
./setup-observability.sh status

# Voir les logs d'un service
./setup-observability.sh logs [service_name]

# Nettoyage complet
./setup-observability.sh clean
```

### Monitoring de la Stack

```bash
# Vérifier les métriques d'Alloy
curl http://localhost:12345/metrics

# Vérifier la santé de Loki
curl http://localhost:3100/ready

# Vérifier la santé de Tempo
curl http://localhost:3200/ready

# Vérifier la santé de Mimir
curl http://localhost:9009/ready
```

### Sauvegarde

```bash
# Sauvegarder la base de données
docker-compose -f docker-compose.observability.yml exec postgres \
  pg_dump -U plant_user plant_care_db > backup.sql

# Sauvegarder les données Grafana
docker cp plant_care_grafana:/var/lib/grafana ./grafana-backup
```

##  Sécurité

### Bonnes Pratiques Implémentées

- Utilisateurs non-root dans les conteneurs
- Secrets générés automatiquement
- Chiffrement des données sensibles
- Isolation réseau avec Docker Compose
- Health checks pour tous les services

### Configuration Production

Pour la production, modifier :

```bash
# Variables d'environnement
ENVIRONMENT=production
SECRET_KEY=<votre-clé-forte>
ENCRYPTION_KEY=<votre-clé-de-chiffrement>

# Base de données
DATABASE_URL=postgresql://user:pass@prod-db:5432/plant_care

# Grafana
GF_SECURITY_ADMIN_PASSWORD=<mot-de-passe-fort>
```

## 🐛 Dépannage

### Problèmes Courants

1. **Services qui ne démarrent pas**
   ```bash
   # Vérifier les logs
   ./setup-observability.sh logs
   
   # Vérifier l'espace disque
   df -h
   ```

2. **Grafana inaccessible**
   ```bash
   # Redémarrer Grafana
   docker-compose -f docker-compose.observability.yml restart grafana
   ```

3. **Métriques manquantes**
   ```bash
   # Vérifier Alloy
   curl http://localhost:12345/-/config
   ```

4. **Problèmes de base de données**
   ```bash
   # Vérifier PostgreSQL
   docker-compose -f docker-compose.observability.yml exec postgres \
     pg_isready -U plant_user
   ```

### Logs de Debug

```bash
# Activer le debug pour un service
docker-compose -f docker-compose.observability.yml exec api \
  python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
```

##  Ressources

- [Documentation Grafana Alloy](https://grafana.com/docs/alloy/)
- [Documentation OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation PostgreSQL](https://www.postgresql.org/docs/)

##  Contribution

Pour contribuer à l'amélioration de la stack d'observabilité :

1. Fork le projet
2. Créer une branche feature
3. Tester les modifications avec la stack complète
4. Soumettre une pull request

##  Support

En cas de problème avec la stack d'observabilité :

1. Vérifier les logs : `./setup-observability.sh logs`
2. Vérifier le statut : `./setup-observability.sh status`
3. Consulter cette documentation
4. Créer une issue GitHub avec les logs d'erreur
