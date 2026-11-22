#!/usr/bin/env bash
# Comprobación de sintaxis y suite de pruebas locales.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo 'Falta python3' >&2; exit 2; }
command -v curl >/dev/null || { echo 'Falta curl' >&2; exit 2; }
command -v timeout >/dev/null || { echo 'Falta GNU timeout' >&2; exit 2; }
printf 'Sintaxis Bash... '
bash -n scripts/check.sh
bash -n scripts/validar.sh
printf 'OK\nPruebas funcionales...\n'
python3 tests/test_check.py
