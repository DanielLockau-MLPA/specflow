#!/usr/bin/env bash
# SPDX-FileCopyrightText: (C) 2026 ML!PA Consulting GmbH
# SPDX-License-Identifier: MIT
# Check, list and (optionally) install the dependencies of this project.
#
#   ./setup.sh                      check and list only (exit 1 if a required item is missing)
#   ./setup.sh --install            also install project-level dependencies (uv python, uv sync, npm ci)
#   ./setup.sh --install --syson    additionally pull the SysON docker images
#   ./setup.sh --install-system     additionally install missing system packages via apt (uses sudo)
#   ./setup.sh --yes                do not ask before using sudo
#
# Required: git, uv, Python >= 3.14 (uv can provision it), Node >= 20 + npm,
#           Python packages (pyproject.toml / uv.lock), Node packages (tools/node/package-lock.json),
#           chrome-headless-shell (downloaded via puppeteer) for pre-rendering diagrams
# Optional: Java >= 17 (cross-check with the OMG Pilot Implementation),
#           Docker + compose (SysON for graphical review)

set -u
cd "$(dirname "$0")"

INSTALL=0; SYSTEM=0; SYSON=0; YES=0
for a in "$@"; do
  case "$a" in
    --install) INSTALL=1 ;;
    --install-system) INSTALL=1; SYSTEM=1 ;;
    --syson) SYSON=1 ;;
    --yes|-y) YES=1 ;;
    -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

REQ_PY="3.14"; REQ_NODE="20"; REQ_JAVA="17"
MISSING_REQ=0
declare -a ROWS

have() { command -v "$1" >/dev/null 2>&1; }
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }  # ver_ge have need
row() { ROWS+=("$(printf '%-3s %-9s %-26s %s' "$1" "$2" "$3" "$4")"); }
ok()   { row "OK"  "$1" "$2" "$3"; }
miss() { row "NO"  "$1" "$2" "$3"; [ "$1" = "required" ] && MISSING_REQ=1; }

confirm_sudo() {
  [ "$YES" = 1 ] && return 0
  read -r -p "This will run: $* (sudo). Continue? [y/N] " ans
  [ "$ans" = "y" ] || [ "$ans" = "Y" ]
}

apt_install() {
  have apt-get || { echo "apt-get not available; install manually: $*" >&2; return 1; }
  confirm_sudo apt-get install -y "$@" || return 1
  sudo apt-get install -y "$@"
}

check_system() {
  if have git; then ok required "git" "$(git --version | awk '{print $3}')"; else miss required "git" "install: sudo apt-get install git"; fi

  if have uv; then ok required "uv" "$(uv --version | awk '{print $2}')"
  else miss required "uv" "install: https://docs.astral.sh/uv/getting-started/installation/ (not auto-installed)"; fi

  if have uv && uv python find ">=${REQ_PY}" >/dev/null 2>&1; then
    ok required "python >= ${REQ_PY}" "$(uv python find ">=${REQ_PY}")"
  else
    miss required "python >= ${REQ_PY}" "install: uv python install ${REQ_PY}  (done by --install)"
  fi

  if have node; then
    v="$(node --version | sed 's/^v//')"
    if ver_ge "$v" "$REQ_NODE"; then ok required "node >= ${REQ_NODE}" "$v"; else miss required "node >= ${REQ_NODE}" "found $v; install a newer Node.js"; fi
  else miss required "node >= ${REQ_NODE}" "install: sudo apt-get install nodejs npm (or use nvm)"; fi

  if have npm; then ok required "npm" "$(npm --version)"; else miss required "npm" "install with Node.js"; fi

  if have java; then
    v="$(java -version 2>&1 | head -n1 | sed -E 's/.*"([0-9]+(\.[0-9]+)*).*/\1/')"
    if ver_ge "$v" "$REQ_JAVA"; then ok optional "java >= ${REQ_JAVA}" "$v"; else miss optional "java >= ${REQ_JAVA}" "found $v; needed for the OMG Pilot Implementation cross-check"; fi
  else miss optional "java >= ${REQ_JAVA}" "install: sudo apt-get install openjdk-17-jre-headless"; fi

  if have docker; then
    if docker info >/dev/null 2>&1; then ok optional "docker (daemon)" "$(docker version --format '{{.Server.Version}}' 2>/dev/null)"
    else miss optional "docker (daemon)" "installed but daemon not reachable; start Docker"; fi
    if docker compose version >/dev/null 2>&1; then ok optional "docker compose" "$(docker compose version --short 2>/dev/null)"
    else miss optional "docker compose" "install the compose plugin"; fi
  else
    miss optional "docker (daemon)" "needed for SysON; install Docker"
    miss optional "docker compose" "needed for SysON"
  fi
}

check_project() {
  if have uv && [ -x .venv/bin/python ] && uv run --no-sync python -c "import mcp, behave, pytest, ruff" >/dev/null 2>&1; then
    ok required "python packages" "mcp, behave, pytest, ruff in .venv"
  else miss required "python packages" "run: ./setup.sh --install  (uv sync)"; fi

  if [ -f tools/node/node_modules/sysml-v2-lsp/dist/server/mcpServer.js ]; then
    ok required "sysml-v2-lsp (npm)" "tools/node/node_modules"
  else miss required "sysml-v2-lsp (npm)" "run: ./setup.sh --install  (npm ci in tools/node)"; fi

  if [ -d tools/node/node_modules/mermaid ] && [ -d tools/node/node_modules/jsdom ]; then
    ok required "mermaid, jsdom (npm)" "tools/node/node_modules"
  else miss required "mermaid, jsdom (npm)" "run: ./setup.sh --install  (npm ci in tools/node)"; fi

  if [ -x tools/node/node_modules/.bin/mmdc ]; then
    ok required "mermaid-cli (npm)" "tools/node/node_modules/.bin/mmdc"
  else miss required "mermaid-cli (npm)" "run: ./setup.sh --install  (npm ci in tools/node)"; fi

  if ls "${PUPPETEER_CACHE_DIR:-$HOME/.cache/puppeteer}"/chrome-headless-shell/*/*/chrome-headless-shell >/dev/null 2>&1; then
    ok required "headless browser" "chrome-headless-shell (puppeteer cache)"
  else miss required "headless browser" "run: ./setup.sh --install  (downloads chrome-headless-shell for diagram rendering)"; fi

  if have docker && docker image inspect eclipsesyson/syson:latest >/dev/null 2>&1; then
    ok optional "SysON image" "eclipsesyson/syson:latest"
  else miss optional "SysON image" "run: ./setup.sh --install --syson"; fi
}

install_system() {
  local pkgs=()
  have git || pkgs+=(git)
  { have node && have npm; } || pkgs+=(nodejs npm)
  have java || pkgs+=(openjdk-17-jre-headless)
  if [ "${#pkgs[@]}" -gt 0 ]; then
    echo ">> installing system packages: ${pkgs[*]}"
    apt_install "${pkgs[@]}" || echo "!! system package installation skipped or failed"
  fi
  have uv || echo "!! uv is not installed automatically; see https://docs.astral.sh/uv/getting-started/installation/"
}

install_project() {
  if have uv; then
    uv python find ">=${REQ_PY}" >/dev/null 2>&1 || { echo ">> uv python install ${REQ_PY}"; uv python install "${REQ_PY}"; }
    echo ">> uv sync --locked"; uv sync --locked || uv sync
  else echo "!! uv missing: skipping python packages"; fi

  if have npm; then
    echo ">> npm ci (tools/node)"
    # --ignore-scripts: the sysml-v2-lsp postinstall only builds its VS Code client, which is not needed here
    if [ -f tools/node/package-lock.json ]; then (cd tools/node && npm ci --ignore-scripts)
    else (cd tools/node && npm install --ignore-scripts); fi
    echo ">> chrome-headless-shell for mermaid-cli (puppeteer)"
    (cd tools/node && npx --no-install puppeteer browsers install chrome-headless-shell) || echo "!! browser download failed; diagram rendering will not work"
  else echo "!! npm missing: skipping node packages"; fi

  if [ "$SYSON" = 1 ]; then
    if have docker && docker info >/dev/null 2>&1; then
      echo ">> docker compose pull (SysON)"; docker compose -f tools/syson/docker-compose.yml pull
    else echo "!! docker not available: skipping SysON images"; fi
  fi
}

print_table() {
  echo
  printf '%-3s %-9s %-26s %s\n' "" "kind" "dependency" "detail"
  printf '%s\n' "--------------------------------------------------------------------------"
  printf '%s\n' "${ROWS[@]}"
  echo
}

[ "$SYSTEM" = 1 ] && install_system
[ "$INSTALL" = 1 ] && install_project

ROWS=(); MISSING_REQ=0
check_system
check_project
print_table

if [ "$MISSING_REQ" = 1 ]; then
  echo "Required dependencies are missing. Re-run with --install (project-level) or --install-system (apt)."
  exit 1
fi
echo "All required dependencies are present."
