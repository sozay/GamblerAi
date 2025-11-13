#!/usr/bin/env python3
"""
Database migration script to add the transactions table.

This script creates the transactions table in the database to support
comprehensive trade logging.

Usage:
    python scripts/migrate_add_transactions.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gambler_ai.storage.database import DatabaseManager
from gambler_ai.storage.models import Base, Transaction


def main():
    """Run the migration."""
    print("\n" + "="*80)
    print("DATABASE MIGRATION: Add Transactions Table")
    print("="*80 + "\n")

    # Initialize database manager
    print("Connecting to database...")
    db_manager = DatabaseManager()

    try:
        # Create all tables (will only create missing ones)
        print("Creating transactions table...")
        Base.metadata.create_all(db_manager.engine, tables=[Transaction.__table__])

        print("✓ Migration completed successfully!")
        print("\nThe 'transactions' table has been created.")
        print("All trades will now be logged to:")
        print("  - Database table: transactions")
        print("  - CSV file: logs/transactions.csv")
        print("  - JSON file: logs/transactions.jsonl")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return 1

    print("\n" + "="*80)
    print("Next steps:")
    print("  1. Run backtest with transaction logging enabled")
    print("  2. Check logs/transactions.csv for trade history")
    print("  3. Query database for transaction analysis")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
