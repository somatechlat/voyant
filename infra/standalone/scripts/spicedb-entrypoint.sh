#!/bin/sh
set -e
SPICEDB_KEY=$(cat /run/secrets/spicedb_grpc_preshared_key)
exec spicedb serve --grpc-preshared-key "$SPICEDB_KEY" "$@"
