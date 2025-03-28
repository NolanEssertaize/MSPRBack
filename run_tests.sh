#!/bin/bash
# run_tests.sh - Script pour exécuter les tests avec la base de données réelle

# Activer le mode de test
export TESTING=true
export ENCRYPTION_ENABLED=true
export ENCRYPTION_KEY="test-encryption-key-for-testing"

# Exécuter les tests
echo "Running all tests with actual database..."
pytest app/tests/ -v

# Vérifier si les tests ont réussi
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Tests failed. See output above for details."
fi

# Pour les tests Docker
if [ "$1" == "--docker" ]; then
    echo "Running Docker container tests..."
    docker-compose build
    docker-compose run --rm api pytest app/tests/ -v
    docker-compose down
fi

# Nettoyer après les tests
rm -f test_a_rosa_je.db
find photos -name "test_*" -delete