#!/bin/bash
# setup-observability.sh - Script pour déployer la stack LGTM avec Alloy

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."

    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi

    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi

    # Vérifier que Docker est en marche
    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas en cours d'exécution"
        exit 1
    fi

    log_success "Prérequis vérifiés"
}

# Fonction pour créer la structure des répertoires
create_directories() {
    log_info "Création de la structure des répertoires..."

    mkdir -p observability/{alloy,loki,tempo,mimir,grafana/{provisioning/{datasources,dashboards},dashboards}}
    mkdir -p photos

    log_success "Structure des répertoires créée"
}

# Fonction pour créer le fichier d'environnement
create_env_file() {
    log_info "Création du fichier d'environnement..."

    if [ ! -f .env ]; then
        cat > .env << EOF
# Configuration de base de données
DATABASE_URL=postgresql://plant_user:plant_password@postgres:5432/plant_care_db

# Configuration d'authentification
SECRET_KEY=$(openssl rand -base64 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Configuration du chiffrement
ENCRYPTION_KEY=$(openssl rand -base64 32)
ENCRYPTION_ENABLED=true

# Configuration d'observabilité
ENABLE_OBSERVABILITY=true
OTEL_SERVICE_NAME=plant-care-api
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317
OTEL_RESOURCE_ATTRIBUTES=service.name=plant-care-api,service.version=1.0.0

# Configuration des métriques
ENABLE_METRICS=true

# Configuration de l'environnement
ENVIRONMENT=development
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
        log_success "Fichier .env créé avec des clés sécurisées"
    else
        log_warning "Le fichier .env existe déjà, pas de modification"
    fi
}

# Fonction pour créer les fichiers de configuration manquants
create_missing_configs() {
    log_info "Création des fichiers de configuration..."

    # Configuration Grafana - dashboard provisioning
    cat > observability/grafana/provisioning/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

    # Configuration Grafana - alerting
    mkdir -p observability/grafana/provisioning/alerting
    cat > observability/grafana/provisioning/alerting/alerting.yml << EOF
apiVersion: 1

policies:
  - orgId: 1
    receiver: 'grafana-default-email'
    group_by: ['grafana_folder', 'alertname']

contactPoints:
  - orgId: 1
    name: 'grafana-default-email'
    receivers:
      - uid: 'default-email'
        type: 'email'
        settings:
          addresses: 'admin@localhost'
EOF

    log_success "Fichiers de configuration créés"
}

# Fonction pour démarrer la stack
start_stack() {
    log_info "Démarrage de la stack d'observabilité..."

    # Construire les images si nécessaire
    docker-compose -f docker-compose.observability.yml build

    # Démarrer les services
    docker-compose -f docker-compose.observability.yml up -d

    log_success "Stack démarrée"
}

# Fonction pour vérifier le statut des services
check_services() {
    log_info "Vérification du statut des services..."

    services=("postgres" "api" "alloy" "loki" "tempo" "mimir" "grafana")

    for service in "${services[@]}"; do
        if docker-compose -f docker-compose.observability.yml ps | grep -q "$service.*Up"; then
            log_success "$service est en cours d'exécution"
        else
            log_error "$service n'est pas en cours d'exécution"
        fi
    done
}

# Fonction pour attendre que les services soient prêts
wait_for_services() {
    log_info "Attente de la disponibilité des services..."

    # Attendre PostgreSQL
    log_info "Attente de PostgreSQL..."
    until docker-compose -f docker-compose.observability.yml exec -T postgres pg_isready -U plant_user -d plant_care_db; do
        sleep 2
    done
    log_success "PostgreSQL est prêt"

    # Attendre l'API
    log_info "Attente de l'API..."
    until curl -s http://localhost:8000/health > /dev/null; do
        sleep 2
    done
    log_success "API est prête"

    # Attendre Grafana
    log_info "Attente de Grafana..."
    until curl -s http://localhost:3000/api/health > /dev/null; do
        sleep 2
    done
    log_success "Grafana est prêt"

    # Attendre Alloy
    log_info "Attente d'Alloy..."
    until curl -s http://localhost:12345/-/ready > /dev/null; do
        sleep 2
    done
    log_success "Alloy est prêt"
}

# Fonction pour exécuter les migrations
run_migrations() {
    log_info "Exécution des migrations de base de données..."

    docker-compose -f docker-compose.observability.yml exec api alembic upgrade head

    # Exécuter les fonctions d'optimisation PostgreSQL
    docker-compose -f docker-compose.observability.yml exec postgres psql -U plant_user -d plant_care_db -c "SELECT create_performance_indexes();"

    log_success "Migrations exécutées"
}

# Fonction pour afficher les URLs d'accès
show_access_urls() {
    log_success "Stack d'observabilité déployée avec succès!"
    echo ""
    echo "URLs d'accès:"
    echo "  📊 Grafana: http://localhost:3000 (admin/admin)"
    echo "  🚀 API Plant Care: http://localhost:8000"
    echo "  📖 Documentation API: http://localhost:8000/docs"
    echo "  📈 Métriques: http://localhost:8000/metrics"
    echo "  🔍 Alloy Interface: http://localhost:12345"
    echo "  🗄️  PostgreSQL: localhost:5432 (plant_user/plant_password)"
    echo ""
    echo "Services internes:"
    echo "  📝 Loki (logs): http://localhost:3100"
    echo "  🔗 Tempo (traces): http://localhost:3200"
    echo "  📊 Mimir (métriques): http://localhost:9009"
    echo ""
    echo "Pour arrêter la stack:"
    echo "  docker-compose -f docker-compose.observability.yml down"
    echo ""
    echo "Pour voir les logs:"
    echo "  docker-compose -f docker-compose.observability.yml logs -f [service]"
}

# Fonction pour configurer les alertes Grafana
setup_grafana_alerts() {
    log_info "Configuration des alertes Grafana..."

    # Attendre que Grafana soit complètement initialisé
    sleep 10

    # Exemple d'alerte pour un taux d'erreur élevé
    cat > /tmp/alert-rules.json << EOF
{
  "alert": {
    "condition": "B",
    "data": [
      {
        "refId": "A",
        "queryType": "",
        "relativeTimeRange": {
          "from": 600,
          "to": 0
        },
        "model": {
          "expr": "rate(plant_care_request_duration_seconds_count{status_code=~\"5..\"}[5m])",
          "refId": "A"
        }
      },
      {
        "refId": "B",
        "queryType": "",
        "relativeTimeRange": {
          "from": 0,
          "to": 0
        },
        "model": {
          "conditions": [
            {
              "evaluator": {
                "params": [0.1],
                "type": "gt"
              },
              "operator": {
                "type": "and"
              },
              "query": {
                "params": ["A"]
              },
              "reducer": {
                "params": [],
                "type": "last"
              },
              "type": "query"
            }
          ],
          "refId": "B"
        }
      }
    ],
    "intervalSeconds": 60,
    "maxDataPoints": 43200,
    "noDataState": "NoData",
    "execErrState": "Alerting",
    "for": "5m"
  },
  "annotations": {
    "description": "Le taux d'erreur serveur (5xx) est supérieur à 10%",
    "summary": "Taux d'erreur élevé détecté"
  },
  "labels": {
    "team": "plant-care",
    "severity": "critical"
  },
  "folderUID": "",
  "title": "High Server Error Rate",
  "uid": "",
  "ruleGroup": "plant-care-alerts"
}
EOF

    log_success "Configuration des alertes terminée"
}

# Fonction principale
main() {
    echo "=========================================="
    echo "   SETUP STACK LGTM - PLANT CARE API"
    echo "=========================================="
    echo ""

    check_prerequisites
    create_directories
    create_env_file
    create_missing_configs
    start_stack

    log_info "Attente du démarrage des services (cela peut prendre quelques minutes)..."
    sleep 30

    wait_for_services
    run_migrations
    check_services
    setup_grafana_alerts

    show_access_urls
}

# Fonction de nettoyage en cas d'interruption
cleanup() {
    log_warning "Interruption détectée. Nettoyage..."
    docker-compose -f docker-compose.observability.yml down
    exit 1
}

# Gestion des signaux
trap cleanup SIGINT SIGTERM

# Options de ligne de commande
case "${1:-}" in
    "start")
        main
        ;;
    "stop")
        log_info "Arrêt de la stack..."
        docker-compose -f docker-compose.observability.yml down
        log_success "Stack arrêtée"
        ;;
    "restart")
        log_info "Redémarrage de la stack..."
        docker-compose -f docker-compose.observability.yml down
        sleep 5
        main
        ;;
    "status")
        check_services
        ;;
    "logs")
        service=${2:-}
        if [ -n "$service" ]; then
            docker-compose -f docker-compose.observability.yml logs -f "$service"
        else
            docker-compose -f docker-compose.observability.yml logs -f
        fi
        ;;
    "clean")
        log_warning "Suppression complète de la stack et des données..."
        read -p "Êtes-vous sûr? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f docker-compose.observability.yml down -v --remove-orphans
            docker system prune -f
            log_success "Nettoyage terminé"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]|clean}"
        echo ""
        echo "Commands:"
        echo "  start    - Démarrer la stack complète"
        echo "  stop     - Arrêter la stack"
        echo "  restart  - Redémarrer la stack"
        echo "  status   - Vérifier le statut des services"
        echo "  logs     - Afficher les logs (optionnel: nom du service)"
        echo "  clean    - Supprimer complètement la stack et les données"
        echo ""
        exit 1
        ;;
esac