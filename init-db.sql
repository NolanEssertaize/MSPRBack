-- Script d'initialisation de la base de données PostgreSQL
-- pour l'application Plant Care

-- Créer des extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Créer un utilisateur pour l'application si nécessaire
-- (déjà créé via les variables d'environnement Docker)

-- Créer un schéma pour l'application
CREATE SCHEMA IF NOT EXISTS plant_care;

-- Définir le schéma par défaut
SET search_path TO plant_care, public;

-- Créer des index utiles après que les tables soient créées par Alembic
-- Ces commandes seront exécutées après la migration Alembic

-- Fonction pour créer des index après migration
CREATE OR REPLACE FUNCTION create_performance_indexes()
RETURNS void AS $$
BEGIN
    -- Index pour améliorer les performances des requêtes utilisateur
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_email_hash_performance') THEN
        CREATE INDEX CONCURRENTLY idx_users_email_hash_performance ON users(email_hash);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_username_hash_performance') THEN
        CREATE INDEX CONCURRENTLY idx_users_username_hash_performance ON users(username_hash);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_phone_hash_performance') THEN
        CREATE INDEX CONCURRENTLY idx_users_phone_hash_performance ON users(phone_hash);
    END IF;

    -- Index pour améliorer les performances des requêtes de plantes
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_plants_owner_created') THEN
        CREATE INDEX CONCURRENTLY idx_plants_owner_created ON plants(owner_id, created_at DESC);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_plants_in_care') THEN
        CREATE INDEX CONCURRENTLY idx_plants_in_care ON plants(in_care_id) WHERE in_care_id IS NOT NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_plants_name_search') THEN
        CREATE INDEX CONCURRENTLY idx_plants_name_search ON plants USING gin(to_tsvector('english', name));
    END IF;

    -- Index pour améliorer les performances des commentaires
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_commentary_plant_time') THEN
        CREATE INDEX CONCURRENTLY idx_commentary_plant_time ON commentary(plant_id, time_stamp DESC);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_commentary_user_time') THEN
        CREATE INDEX CONCURRENTLY idx_commentary_user_time ON commentary(user_id, time_stamp DESC);
    END IF;

    RAISE NOTICE 'Performance indexes created successfully';
END;
$ LANGUAGE plpgsql;

-- Créer une vue pour les statistiques de l'application
CREATE OR REPLACE VIEW app_statistics AS
SELECT
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM users WHERE is_botanist = true) as total_botanists,
    (SELECT COUNT(*) FROM plants) as total_plants,
    (SELECT COUNT(*) FROM plants WHERE in_care_id IS NOT NULL) as plants_in_care,
    (SELECT COUNT(*) FROM commentary) as total_comments,
    (SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '30 days') as new_users_30d,
    (SELECT COUNT(*) FROM plants WHERE created_at > NOW() - INTERVAL '30 days') as new_plants_30d;

-- Créer une fonction pour nettoyer les anciennes données
CREATE OR REPLACE FUNCTION cleanup_old_data(retention_days INTEGER DEFAULT 365)
RETURNS INTEGER AS $
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Nettoyer les commentaires très anciens (optionnel)
    -- DELETE FROM commentary WHERE time_stamp < NOW() - INTERVAL '%s days', retention_days;
    -- GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Cleanup completed. % rows affected.', deleted_count;
    RETURN deleted_count;
END;
$ LANGUAGE plpgsql;

-- Créer des fonctions utilitaires pour l'observabilité
CREATE OR REPLACE FUNCTION get_table_sizes()
RETURNS TABLE(
    table_name text,
    row_count bigint,
    total_size text,
    index_size text,
    table_size text
) AS $
BEGIN
    RETURN QUERY
    SELECT
        schemaname||'.'||tablename as table_name,
        n_tup_ins - n_tup_del as row_count,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
        pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
    FROM pg_stat_user_tables
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$ LANGUAGE plpgsql;

-- Créer une fonction pour monitorer les performances des requêtes
CREATE OR REPLACE FUNCTION get_slow_queries(threshold_ms INTEGER DEFAULT 1000)
RETURNS TABLE(
    query text,
    calls bigint,
    total_time double precision,
    mean_time double precision,
    rows bigint
) AS $
BEGIN
    -- Cette fonction nécessite l'extension pg_stat_statements
    -- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    RETURN QUERY
    SELECT
        substring(s.query, 1, 100) as query,
        s.calls,
        s.total_exec_time as total_time,
        s.mean_exec_time as mean_time,
        s.rows
    FROM pg_stat_statements s
    WHERE s.mean_exec_time > threshold_ms
    ORDER BY s.mean_exec_time DESC
    LIMIT 20;

    EXCEPTION WHEN undefined_table THEN
        RAISE NOTICE 'pg_stat_statements extension is not available';
        RETURN;
END;
$ LANGUAGE plpgsql;

-- Créer des triggers pour l'audit (optionnel)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Fonction générique d'audit
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, old_values, user_id)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), OLD.id);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, old_values, new_values, user_id)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW), NEW.id);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, new_values, user_id)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW), NEW.id);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$ LANGUAGE plpgsql;

-- Message de confirmation
DO $
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
    RAISE NOTICE 'Remember to run create_performance_indexes() after Alembic migration';
END $;