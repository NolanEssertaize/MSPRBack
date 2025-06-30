

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

check_prerequisites() {
    log_info "Vérification des prérequis..."


    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi


<<<<<<< HEAD
    if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
=======
<<<<<<< HEAD:setup_observability.sh
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
=======
    if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
>>>>>>> a3ba0e1 (Update script and remove useless files):setup_backend.sh
>>>>>>> 437e1e8 (Update script and remove useless files)
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi


    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas en cours d'exécution"
        exit 1
    fi

    log_success "Prérequis vérifiés"
}

create_directories() {
    log_info "Création de la structure des répertoires..."

    mkdir -p observability/{alloy,loki,tempo,grafana/{provisioning/{datasources,dashboards},dashboards}}
    mkdir -p photos

    log_success "Structure des répertoires créée"
}

create_env_file() {
    log_info "Création du fichier d'environnement..."

    if [ ! -f .env ]; then
        cat > .env << EOF
DATABASE_URL=postgresql://plant_user:plant_password@postgres:5432/plant_care_db

SECRET_KEY=$(openssl rand -base64 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

ENCRYPTION_KEY=$(openssl rand -base64 32)
ENCRYPTION_ENABLED=true

ENABLE_OBSERVABILITY=true
OTEL_SERVICE_NAME=plant-care-api
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317
OTEL_RESOURCE_ATTRIBUTES=service.name=plant-care-api,service.version=1.0.0

ENABLE_METRICS=true

ENVIRONMENT=development
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
        log_success "Fichier .env créé avec des clés sécurisées"
    else
        log_warning "Le fichier .env existe déjà, pas de modification"
    fi
}

create_missing_configs() {
    log_info "Création des fichiers de configuration..."


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

start_stack() {
    log_info "Démarrage de la stack d'observabilité..."

<<<<<<< HEAD:setup_observability.sh

    docker compose build


<<<<<<< HEAD
    docker compose up -d
=======
    docker-compose -f docker-compose.observability.yml up -d
=======

    docker compose build


    docker compose up -d
>>>>>>> a3ba0e1 (Update script and remove useless files):setup_backend.sh
>>>>>>> 437e1e8 (Update script and remove useless files)

    log_success "Stack démarrée"
}

check_services() {
    log_info "Vérification du statut des services..."

    services=("postgres" "api" "alloy" "loki" "tempo" "grafana")

    for service in "${services[@]}"; do
        if docker compose ps | grep -q "$service.*Up"; then
            log_success "$service est en cours d'exécution"
        else
            log_error "$service n'est pas en cours d'exécution"
        fi
    done
}

wait_for_services() {
    log_info "Attente de la disponibilité des services..."


    log_info "Attente de PostgreSQL..."
    until docker compose exec -T postgres pg_isready -U plant_user -d plant_care_db; do
        sleep 2
    done
    log_success "PostgreSQL est prêt"


    log_info "Attente de l'API..."
    until curl -s http://localhost:8000/health > /dev/null; do
        sleep 2
    done
    log_success "API est prête"


    log_info "Attente de Grafana..."
    until curl -s http://localhost:3000/api/health > /dev/null; do
        sleep 2
    done
    log_success "Grafana est prêt"


    log_info "Attente d'Alloy..."
    until curl -s http://localhost:12345/-/ready > /dev/null; do
        sleep 2
    done
    log_success "Alloy est prêt"
}

run_migrations() {
    log_info "Exécution des migrations de base de données..."

    docker compose exec api alembic upgrade head

<<<<<<< HEAD:setup_observability.sh

<<<<<<< HEAD
=======
    docker-compose -f docker-compose.observability.yml exec postgres psql -U plant_user -d plant_care_db -c "SELECT create_performance_indexes();"
=======
>>>>>>> a3ba0e1 (Update script and remove useless files):setup_backend.sh

>>>>>>> 437e1e8 (Update script and remove useless files)
    log_success "Migrations exécutées"
}

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
    echo ""
    echo "Pour arrêter la stack:"
    echo "  docker compose down"
    echo ""
    echo "Pour voir les logs:"
    echo "  docker compose -f [service]"
}

setup_grafana_alerts() {
    log_info "Configuration des alertes Grafana..."


    sleep 10


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

cleanup() {
    log_warning "Interruption détectée. Nettoyage..."
    docker compose down
    exit 1
}

trap cleanup SIGINT SIGTERM

case "${1:-}" in
    "start")
        main
        ;;
    "stop")
        log_info "Arrêt de la stack..."
        docker compose down
        log_success "Stack arrêtée"
        ;;
    "restart")
        log_info "Redémarrage de la stack..."
        docker compose down
        sleep 5
        main
        ;;
    "status")
        check_services
        ;;
    "logs")
        service=${2:-}
        if [ -n "$service" ]; then
            docker compose logs "$service" -f
        else
            docker compose logs -f
        fi
        ;;
    "clean")
        log_warning "Suppression complète de la stack et des données..."
        read -p "Êtes-vous sûr? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v --remove-orphans
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