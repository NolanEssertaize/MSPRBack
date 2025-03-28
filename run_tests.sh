#!/bin/bash
# run_e2e_tests.sh - Script pour exécuter tous les tests end-to-end pour l'application A_rosa_je

# Définir les couleurs pour une meilleure lisibilité
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages d'information
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Fonction pour afficher les messages de succès
success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Fonction pour afficher les messages d'erreur
error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour afficher les messages d'avertissement
warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Fonction pour afficher la bannière
show_banner() {
    echo "======================================================"
    echo "       TESTS END-TO-END POUR A_ROSA_JE API"
    echo "======================================================"
    echo ""
}

# Fonction pour nettoyer l'environnement de test
cleanup() {
    info "Nettoyage de l'environnement de test..."
    
    # Supprimer la base de données de test si elle existe
    if [ -f "test_a_rosa_je.db" ]; then
        rm -f test_a_rosa_je.db
        success "Base de données de test supprimée."
    fi
    
    # Supprimer les photos de test
    test_photos=$(find photos -name "test_*" 2>/dev/null)
    if [ -n "$test_photos" ]; then
        find photos -name "test_*" -delete
        success "Photos de test supprimées."
    fi
    
    echo ""
}

# Fonction pour exécuter un test spécifique
run_test() {
    local test_name=$1
    local test_file=$2
    
    echo "------------------------------------------------------"
    info "Exécution des tests : $test_name"
    echo "------------------------------------------------------"
    
    python -m pytest $test_file -v
    
    if [ $? -eq 0 ]; then
        success "Tests '$test_name' réussis!"
    else
        error "Tests '$test_name' échoués."
        FAILED_TESTS+=("$test_name")
    fi
    
    echo ""
}

# Fonction pour exécuter les tests dans Docker
run_docker_tests() {
    info "Préparation des tests dans Docker..."
    
    # Vérifier si Docker est installé
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé. Impossible d'exécuter les tests Docker."
        exit 1
    fi
    
    # Vérifier si Docker est en cours d'exécution
    if ! docker info &> /dev/null; then
        error "Docker n'est pas en cours d'exécution. Veuillez démarrer Docker et réessayer."
        exit 1
    fi
    
    echo "------------------------------------------------------"
    info "Construction de l'image Docker..."
    echo "------------------------------------------------------"
    
    docker-compose build
    
    if [ $? -ne 0 ]; then
        error "Échec de la construction de l'image Docker."
        exit 1
    fi
    
    echo "------------------------------------------------------"
    info "Exécution des tests dans le conteneur Docker..."
    echo "------------------------------------------------------"
    
    docker-compose run --rm api pytest app/tests/ -v
    
    if [ $? -eq 0 ]; then
        success "Tous les tests Docker ont réussi!"
    else
        error "Certains tests Docker ont échoué."
    fi
    
    echo "------------------------------------------------------"
    info "Arrêt des conteneurs Docker..."
    echo "------------------------------------------------------"
    
    docker-compose down
}

# Vérifier les dépendances
check_dependencies() {
    info "Vérification des dépendances..."
    
    # Vérifier si pytest est installé
    if ! python -c "import pytest" &> /dev/null; then
        error "pytest n'est pas installé. Veuillez l'installer avec 'pip install pytest'."
        exit 1
    fi
    
    # Vérifier si le répertoire photos existe
    if [ ! -d "photos" ]; then
        warning "Le répertoire 'photos' n'existe pas. Création..."
        mkdir -p photos
    fi
    
    # Vérifier les fichiers de test
    for test_file in "app/tests/test_users.py" "app/tests/test_plants.py" "app/tests/test_comments.py" "app/tests/test_security.py"; do
        if [ ! -f "$test_file" ]; then
            error "Fichier de test manquant: $test_file"
            exit 1
        fi
    done
    
    success "Toutes les dépendances sont satisfaites."
    echo ""
}

# Programme principal
main() {
    # Initialiser les variables
    FAILED_TESTS=()
    
    # Afficher la bannière
    show_banner
    
    # Vérifier les dépendances
    check_dependencies
    
    # Nettoyer l'environnement avant les tests
    cleanup
    
    # Configurer l'environnement pour les tests
    export TESTING=true
    export ENCRYPTION_ENABLED=true
    export ENCRYPTION_KEY="test-encryption-key-for-testing"
    info "Variables d'environnement de test configurées."
    echo ""
    
    # Exécuter les tests
    run_test "Utilisateurs" "app/tests/test_users.py"
    run_test "Plantes" "app/tests/test_plants.py"
    run_test "Commentaires" "app/tests/test_comments.py"
    run_test "Sécurité" "app/tests/test_security.py"
    
    # Exécuter les tests Docker si demandé
    if [ "$1" == "--docker" ]; then
        run_docker_tests
    fi
    
    # Nettoyer l'environnement après les tests
    cleanup
    
    # Afficher le résumé
    echo "======================================================"
    echo "                  RÉSUMÉ DES TESTS"
    echo "======================================================"
    
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        success "Tous les tests end-to-end ont réussi!"
    else
        error "Les tests suivants ont échoué:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
        exit 1
    fi
}

# Exécuter le programme principal avec les arguments
main "$@"