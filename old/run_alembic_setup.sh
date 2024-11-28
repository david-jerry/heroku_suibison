#!/bin/bash

DB_USERNAME="${DB_USERNAME:-bytestream}"
DB_PASSWORD="${DB_PASSWORD:-Jeloblisvent123.}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-digitopia}"
ALEMBIC_DIRECTORY="migrations"

# Function to kill all background processes and cleanup
cleanup() {
    echo "Stopping alembic migrations and cleaning up..."
    # Kill all background processes started by this script
    kill $(jobs -p) 2>/dev/null || true
    wait
}

# Trap SIGINT (Ctrl+C) and call cleanup function
trap cleanup SIGINT

# Main function to execute the alembic migration process
main() {
    echo "Running alembic migrations..."

    if ! pip show alembic > /dev/null 2>&1; then
        echo "Installing Alembic..."
        pip install alembic
    else
        echo "Alembic is already installed."
    fi

    # Initialize Alembic
    if [ ! -d "$ALEMBIC_DIRECTORY" ]; then
        echo "Initializing Alembic for async PostgreSQL..."
        alembic init -t async $ALEMBIC_DIRECTORY
    else
        echo "Alembic directory already exists."
    fi

    # Update env.py
    ENV_PY="$ALEMBIC_DIRECTORY/env.py"
    if [ -f "$ENV_PY" ]; then
        echo "Updating env.py..."
        if ! grep -q "from sqlmodel import SQLModel" "$ENV_PY"; then
            sed -i "1i from sqlmodel import SQLModel\nfrom src.app.models.activities import *\nfrom src.app.models.users import *\nfrom src.app.models.products import *\nfrom src.app.models.transactions import *\n  # Update with your models" "$ENV_PY"
        fi
        sed -i "s/target_metadata = .*/target_metadata = SQLModel.metadata/" "$ENV_PY"
    else
        echo "env.py not found at $ENV_PY"
    fi

    # Update script.py.mako
    SCRIPT_MAKO="$ALEMBIC_DIRECTORY/script.py.mako"
    if [ -f "$SCRIPT_MAKO" ]; then
        echo "Updating script.py.mako for SQLModel..."
        if ! grep -q "import sqlmodel" "$SCRIPT_MAKO"; then
            sed -i "1i import sqlmodel" "$SCRIPT_MAKO"
        fi
    else
        echo "script.py.mako not found at $SCRIPT_MAKO"
    fi

    # Update alembic.ini
    ALEMBIC_INI="alembic.ini"
    if [ -f "$ALEMBIC_INI" ]; then
        echo "Updating alembic.ini with database URL..."
        sed -i "s#^sqlalchemy.url = .*#sqlalchemy.url = postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}#" "$ALEMBIC_INI"
    else
        echo "alembic.ini not found at $ALEMBIC_INI"
    fi

    echo "Alembic setup complete. You can now use Alembic to manage your database migrations."
}

# Run the main function
main

# Wait for all background processes to finish (if any)
wait