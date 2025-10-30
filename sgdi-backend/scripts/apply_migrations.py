#!/usr/bin/env python3
"""
SGDI Migration Script
Applies SQL migrations in order with idempotent behavior.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages SQL migrations with idempotent execution"""

    def __init__(self, db_url: str, schema: str = None):
        self.db_url = db_url
        self.schema = schema or settings.db_schema
        self.migrations_dir = Path(__file__).parent.parent / "migrations_sql"
        self.engine = None

    def connect(self):
        """Establish database connection"""
        try:
            self.engine = create_engine(self.db_url, echo=False)
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Disconnected from database")

    def create_schema_if_needed(self):
        """Create schema if it doesn't exist and is not 'public'"""
        if self.schema == "public":
            return

        # Use transaction context manager with engine.begin()
        with self.engine.begin() as conn:
            try:
                # Check if schema exists
                result = conn.execute(text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
                ), {"schema": self.schema})

                if not result.fetchone():
                    logger.info(f"Creating schema '{self.schema}'")
                    conn.execute(text(f"CREATE SCHEMA {self.schema}"))
                    logger.info(f"Schema '{self.schema}' created")
                else:
                    logger.info(f"Schema '{self.schema}' already exists")

                # Set search path
                conn.execute(text(f"SET search_path TO {self.schema}, public"))

            except Exception as e:
                logger.error(f"Error creating/checking schema: {e}")
                raise

    def get_applied_migrations(self) -> set:
        """Get set of already applied migration IDs"""
        applied = set()

        try:
            with self.engine.connect() as conn:
                # Check if migrations table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = :schema
                        AND table_name = 'schema_migrations'
                    )
                """), {"schema": self.schema if self.schema != "public" else "public"})

                table_exists = result.fetchone()[0]

                if not table_exists:
                    logger.info("Migrations table doesn't exist, creating it")
                    self._create_migrations_table()
                    return applied

                # Get applied migrations
                result = conn.execute(text(f"""
                    SELECT migration_id FROM {self.schema}.schema_migrations
                    WHERE applied = true
                """))

                applied = {row[0] for row in result.fetchall()}
                logger.info(f"Found {len(applied)} applied migrations")

        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            raise

        return applied

    def _create_migrations_table(self):
        """Create migrations tracking table"""
        with self.engine.begin() as conn:
            try:
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.schema_migrations (
                        migration_id VARCHAR(255) PRIMARY KEY,
                        applied BOOLEAN NOT NULL DEFAULT false,
                        applied_at TIMESTAMP WITH TIME ZONE,
                        checksum VARCHAR(64),
                        error_message TEXT
                    )
                """))
                logger.info("Migrations table created")
            except Exception as e:
                logger.error(f"Error creating migrations table: {e}")
                raise

    def get_available_migrations(self) -> list:
        """Get list of available migration files sorted by name"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []

        migrations = []
        for file_path in self.migrations_dir.glob("*.sql"):
            if file_path.is_file():
                migration_id = file_path.stem
                migrations.append({
                    "id": migration_id,
                    "path": file_path,
                    "checksum": self._calculate_checksum(file_path)
                })

        # Sort by migration ID
        migrations.sort(key=lambda x: x["id"])
        logger.info(f"Found {len(migrations)} migration files")
        return migrations

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of migration file"""
        import hashlib
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def apply_migration(self, migration: dict, dry_run: bool = False) -> bool:
        """Apply a single migration"""
        migration_id = migration["id"]
        file_path = migration["path"]
        checksum = migration["checksum"]

        logger.info(f"Applying migration: {migration_id}")

        try:
            # Read migration content
            with open(file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            if dry_run:
                logger.info(f"DRY RUN: Would apply migration {migration_id}")
                logger.debug(f"SQL content preview: {sql_content[:200]}...")
                return True

            # Apply migration
            with self.engine.connect() as conn:
                # Start transaction
                trans = conn.begin()

                try:
                    # Execute migration SQL
                    conn.execute(text(sql_content))

                    # Record migration as applied
                    conn.execute(text(f"""
                        INSERT INTO {self.schema}.schema_migrations
                        (migration_id, applied, applied_at, checksum)
                        VALUES (:id, true, NOW(), :checksum)
                        ON CONFLICT (migration_id) DO UPDATE SET
                            applied = true,
                            applied_at = NOW(),
                            checksum = :checksum,
                            error_message = NULL
                    """), {"id": migration_id, "checksum": checksum})

                    logger.info(f"Successfully applied migration: {migration_id}")
                    return True

                except Exception as e:
                    trans.rollback()
                    error_msg = str(e)

                    # Record failed migration (using a new connection)
                    try:
                        with self.engine.begin() as error_conn:
                            error_conn.execute(text(f"""
                                INSERT INTO {self.schema}.schema_migrations
                                (migration_id, applied, applied_at, checksum, error_message)
                                VALUES (:id, false, NOW(), :checksum, :error)
                                ON CONFLICT (migration_id) DO UPDATE SET
                                    applied = false,
                                    applied_at = NOW(),
                                    checksum = :checksum,
                                    error_message = :error
                            """), {"id": migration_id, "checksum": checksum, "error": error_msg})
                    except Exception as record_e:
                        logger.error(f"Failed to record migration error: {record_e}")

                    logger.error(f"Failed to apply migration {migration_id}: {error_msg}")
                    raise

        except Exception as e:
            logger.error(f"Error applying migration {migration_id}: {e}")
            return False

    def apply_all_migrations(self, dry_run: bool = False) -> tuple:
        """Apply all pending migrations"""
        logger.info("Starting migration process" + (" (DRY RUN)" if dry_run else ""))

        applied = self.get_applied_migrations()
        available = self.get_available_migrations()

        pending = [m for m in available if m["id"] not in applied]
        applied_count = 0
        failed_count = 0

        logger.info(f"Found {len(pending)} pending migrations out of {len(available)} total")

        for migration in pending:
            try:
                if self.apply_migration(migration, dry_run):
                    applied_count += 1
                else:
                    failed_count += 1
                    if not dry_run:
                        break  # Stop on first failure
            except Exception as e:
                failed_count += 1
                logger.error(f"Migration {migration['id']} failed: {e}")
                if not dry_run:
                    break

        logger.info(f"Migration process completed: {applied_count} applied, {failed_count} failed")
        return applied_count, failed_count

def main():
    parser = argparse.ArgumentParser(description="Apply SGDI database migrations")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply pending migrations"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what migrations would be applied without executing them"
    )
    parser.add_argument(
        "--dry-run-first",
        type=lambda x: x.lower() == 'true',
        default=True,
        help="Perform dry run before applying (default: true)"
    )
    parser.add_argument(
        "--db-url",
        help="Database URL (overrides config)"
    )
    parser.add_argument(
        "--schema",
        help="Database schema (overrides config)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even if database is not available (for dry-run analysis)"
    )

    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        parser.error("Must specify --apply or --dry-run")

    # Override settings if provided
    db_url = args.db_url or settings.database_url
    schema = args.schema or settings.db_schema

    manager = MigrationManager(db_url, schema)

    # Check if we need database connection
    needs_db = args.apply or (args.dry_run and not args.force)

    db_available = False
    if needs_db:
        try:
            manager.connect()
            db_available = True
            logger.info("Database connection established")
            manager.create_schema_if_needed()
        except Exception as e:
            logger.error(f"Cannot connect to database: {e}")
            if args.force and args.dry_run:
                logger.info("Use --force with --dry-run to analyze migrations without database connection")
            sys.exit(1)

    try:
        if args.dry_run:
            # Dry run only
            if not db_available:
                # Analyze migrations without database
                logger.info("Analyzing available migrations (no database connection)...")
                available = manager.get_available_migrations()
                logger.info(f"Found {len(available)} migration files:")
                for migration in available:
                    logger.info(f"  - {migration['id']}")
                logger.info("Dry run analysis completed (database not required)")
                return

            applied, failed = manager.apply_all_migrations(dry_run=True)
            if failed > 0:
                logger.error(f"Dry run found {failed} migrations that would fail")
                sys.exit(1)

        elif args.apply:
            if not db_available:
                logger.error("Cannot apply migrations: database not available")
                sys.exit(1)

            # Apply migrations
            if args.dry_run_first:
                logger.info("Performing dry run first...")
                applied, failed = manager.apply_all_migrations(dry_run=True)
                if failed > 0:
                    logger.error(f"Dry run found {failed} migrations that would fail. Aborting.")
                    sys.exit(1)
                logger.info("Dry run successful, proceeding with migration...")

            applied, failed = manager.apply_all_migrations(dry_run=False)
            if failed > 0:
                logger.error(f"Migration failed: {failed} migrations could not be applied")
                sys.exit(1)

        logger.info("Migration script completed successfully")

    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)
    finally:
        if db_available:
            manager.disconnect()

if __name__ == "__main__":
    main()
