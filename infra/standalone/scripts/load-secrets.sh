#!/bin/sh
# =============================================================================
# Docker Secrets Loader
# =============================================================================
# Reads environment variables ending in _FILE, loads their contents, and
# exports the base variable name. Example:
#   REDIS_PASSWORD_FILE=/run/secrets/redis_password
#   -> exports REDIS_PASSWORD=<contents of file>
# =============================================================================

for var in $(env | grep '_FILE=' | cut -d= -f1); do
    secret_path=$(eval echo "\$$var")
    if [ -r "$secret_path" ]; then
        secret_val=$(cat "$secret_path")
        base_var=$(echo "$var" | sed 's/_FILE$//')
        export "$base_var"="$secret_val"
    fi
done

exec "$@"
