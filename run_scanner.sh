#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# run_scanner.sh — Bootstrap and run the memecoin scanner.
#
# Usage:
#   ./run_scanner.sh              # normal run
#   ./run_scanner.sh --no-venv    # skip venv creation (CI / system Python)
#
# Cron example (daily at 08:05 UTC):
#   5 8 * * * /path/to/github-slideshow/run_scanner.sh >> /var/log/memecoin.log 2>&1
#
# DISCLAIMER: This script runs an informational tool only. Output is NOT
# financial advice. See memecoin_scanner.py for the full disclaimer.
# -----------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
SCANNER="${SCRIPT_DIR}/memecoin_scanner.py"
REQUIREMENTS=(requests python-dateutil)

USE_VENV=true
if [[ "${1:-}" == "--no-venv" ]]; then
  USE_VENV=false
fi

# --- Logging helper ---
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Memecoin Scanner bootstrap starting ==="
log "Script directory: ${SCRIPT_DIR}"

# --- Check Python ---
PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" &>/dev/null; then
  log "ERROR: python3 not found. Please install Python 3.9+."
  exit 1
fi

PYTHON_VERSION="$("${PYTHON_BIN}" --version 2>&1)"
log "Found: ${PYTHON_VERSION}"

# --- Virtual environment ---
if [[ "${USE_VENV}" == "true" ]]; then
  if [[ ! -d "${VENV_DIR}" ]]; then
    log "Creating virtual environment at ${VENV_DIR} …"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    log "Virtual environment created."
  else
    log "Virtual environment already exists at ${VENV_DIR}."
  fi

  # Activate
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  log "Activated venv: $(which python3)"
  PYTHON_BIN="python3"
fi

# --- Install / upgrade dependencies ---
log "Installing/updating dependencies: ${REQUIREMENTS[*]}"
"${PYTHON_BIN}" -m pip install --quiet --upgrade pip
"${PYTHON_BIN}" -m pip install --quiet --upgrade "${REQUIREMENTS[@]}"
log "Dependencies installed."

# --- Create reports directory if missing ---
mkdir -p "${SCRIPT_DIR}/reports"

# --- Run the scanner ---
log "Running memecoin_scanner.py …"
"${PYTHON_BIN}" "${SCANNER}"
EXIT_CODE=$?

if [[ ${EXIT_CODE} -eq 0 ]]; then
  log "Scanner completed successfully."
else
  log "ERROR: Scanner exited with code ${EXIT_CODE}."
fi

log "=== run_scanner.sh finished (exit ${EXIT_CODE}) ==="
exit "${EXIT_CODE}"
