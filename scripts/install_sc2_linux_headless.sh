#!/usr/bin/env bash
# Install StarCraft II headless Linux binary to $SCRATCH/sc2
# Blizzard's "SC2 Linux packages" are provided free for AI research.
# See: https://github.com/Blizzard/s2client-proto#downloads
#
# Usage:
#   bash scripts/install_sc2_linux_headless.sh
#   bash scripts/install_sc2_linux_headless.sh --version 4.10
#
# Sets SC2PATH=$SCRATCH/sc2 in ~/.bashrc.
# Maps are downloaded to $SC2PATH/Maps/Melee/.
#
# Author: Anonymous Authors

set -euo pipefail

SC2_VERSION="${SC2_VERSION:-4.10}"
SC2_BASE_URL="https://blzdistsc2-a.akamaihd.net/Linux"
SC2_ARCHIVE="SC2.${SC2_VERSION}.zip"
MAPS_ARCHIVE="Ladder2019Season3.zip"

INSTALL_DIR="${SCRATCH:-$HOME}/sc2"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "Installing SC2 ${SC2_VERSION} headless to ${INSTALL_DIR}"

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

# ── Download SC2 binary ────────────────────────────────────────────────────
if [ ! -d "${INSTALL_DIR}/SC2" ]; then
    log "Downloading ${SC2_ARCHIVE} ..."
    wget -q --show-progress \
        "${SC2_BASE_URL}/${SC2_ARCHIVE}" \
        -O "${SC2_ARCHIVE}"
    log "Extracting ..."
    unzip -q "${SC2_ARCHIVE}" -d "${INSTALL_DIR}"
    rm -f "${SC2_ARCHIVE}"
    log "SC2 binary extracted to ${INSTALL_DIR}/SC2"
else
    log "SC2 binary already present at ${INSTALL_DIR}/SC2, skipping download."
fi

# ── Download map pack ────────────────────────────────────────────────────────
MAPS_DIR="${INSTALL_DIR}/SC2/Maps"
mkdir -p "${MAPS_DIR}/Melee"
if [ ! -f "${MAPS_DIR}/Melee/Simple64.SC2Map" ]; then
    log "Downloading map pack ${MAPS_ARCHIVE} ..."
    wget -q --show-progress \
        "${SC2_BASE_URL}/Maps/${MAPS_ARCHIVE}" \
        -O "${MAPS_ARCHIVE}"
    unzip -q "${MAPS_ARCHIVE}" -d "${MAPS_DIR}"
    rm -f "${MAPS_ARCHIVE}"
    log "Maps extracted to ${MAPS_DIR}"
else
    log "Maps already present at ${MAPS_DIR}, skipping download."
fi

# ── Write EULA acceptance file ───────────────────────────────────────────────
# Blizzard's AI research license is accepted by creating this file.
EULA_FILE="${INSTALL_DIR}/SC2/.eula_accepted"
if [ ! -f "${EULA_FILE}" ]; then
    echo "SC2 AI Research License accepted $(date)" > "${EULA_FILE}"
    log "EULA acceptance file written."
fi

# ── Export SC2PATH ────────────────────────────────────────────────────────────
SC2PATH_LINE="export SC2PATH=${INSTALL_DIR}/SC2"
if ! grep -qF "SC2PATH" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# StarCraft II headless for DeFAb sc2live" >> ~/.bashrc
    echo "${SC2PATH_LINE}" >> ~/.bashrc
    log "Added SC2PATH to ~/.bashrc"
fi
export SC2PATH="${INSTALL_DIR}/SC2"

log "Installation complete."
log "SC2PATH=${SC2PATH}"
log "Next: pip install blanc[sc2live] && python scripts/sc2live_extract_traces.py"
