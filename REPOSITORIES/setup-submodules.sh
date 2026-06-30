#!/bin/bash
set -euo pipefail

NC='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'

#############################################
# PARAMETERS
#############################################

ORIGIN_URL="$(git remote get-url origin)"

AUTH_BASE="$(echo "${ORIGIN_URL}" | sed -r 's|/[^/]+$||')"

[[ -n "${AUTH_BASE}" ]] \
  || error 'Unable to determine authenticated Git base URL'

BRANCH_NAME="${BRANCH_NAME:-main}"

REPO_COD="${REPO_COD:-s12190-}"

PROJECT_BASE="${PROJECT_BASE:-${AUTH_BASE}}"

DOMAINS=(${DOMAINS:-})

DRY_RUN="${DRY_RUN:-true}"

BASE_BRANCH="${BASE_BRANCH:-}"

#############################################
# VALIDATION
#############################################

error() {
  echo -e "${RED}ERROR:${NC} $1"
  exit 1
}

info() {
  echo -e "${GREEN}INFO:${NC} $1"
}

run() {
  if [[ "${DRY_RUN}" == 'true' ]]; then
    echo -e "${YELLOW}→ [DRY-RUN]${NC} $*"
  else
    eval "$@"
  fi
}

[[ -n "${BRANCH_NAME}" ]] \
  || error 'BRANCH_NAME is empty'

[[ -n "${REPO_COD}" ]] \
  || error 'REPO_COD is empty'

[[ "${REPO_COD}" == *'-' ]] \
  || error 'REPO_COD must end with "-"'

[[ -n "${PROJECT_BASE}" ]] \
  || error 'PROJECT_BASE is empty'

if [[ ${#DOMAINS[@]} -eq 0 ]]; then
  error 'DOMAINS is empty. Example: DOMAINS="integridade ambiental"'
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

CURRENT_DIR="$(pwd -P)"
[[ "${REPO_ROOT}" == "${CURRENT_DIR}" ]] \
  || error 'This script must be executed from the Git repository root'

[[ "${DRY_RUN}" == 'true' || "${DRY_RUN}" == 'false' ]] \
  || error 'DRY_RUN must be "true" or "false"'

#############################################
# FUNCTIONS
#############################################

submodule_exists() {
  local path="$1"
  git config --file '.gitmodules' --get-regexp path 2>/dev/null \
    | awk '{print $2}' | grep -qx "${path}"
}

validate_repo_url() {
  info "Validating repository accessibility: ${1}"
  git ls-remote "$1" >/dev/null 2>&1 \
    || error "Repository not reachable: $1"
}

#############################################
# PRE-FLIGHT
#############################################

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

[[ "${CURRENT_BRANCH}" != 'HEAD' ]] \
  || error 'Detached HEAD state detected. Checkout a branch first.'

BASE="${BASE_BRANCH:-${CURRENT_BRANCH}}"

info 'Configuration summary:'
info "  Base branch: ${BASE}"
info "  Target branch: ${BRANCH_NAME}"
info "  Repository code: ${REPO_COD}"
info "  Project base URL: ${PROJECT_BASE}"
info "  Dry-run mode: ${YELLOW}${DRY_RUN}${NC}"
info "  Domains:"
for DOMAIN in "${DOMAINS[@]}"; do
  info "    - ${DOMAIN}"
done

for DOMAIN in "${DOMAINS[@]}"; do
  validate_repo_url "${PROJECT_BASE}/${REPO_COD}${DOMAIN}.git"
done

#############################################
# MAIN
#############################################

info 'Fetching base branch'
run "git fetch origin ${BASE}"

info "Creating branch '${BRANCH_NAME}' from '${BASE}'"
run "git checkout -B ${BRANCH_NAME} ${BASE}"

WORKDIR="${BRANCH_NAME}"
WORKDIR='.' #"${BRANCH_NAME}"

if [[ -d "${WORKDIR}" ]]; then
  info "Work directory already exists: ${WORKDIR}"
else
  info "Creating work directory: ${WORKDIR}"
  run "mkdir ${WORKDIR}"
fi

cd "${WORKDIR}"

for DOMAIN in "${DOMAINS[@]}"; do

  info "Processing domain: ${DOMAIN}"

  PROJECT_PATH="${DOMAIN}"
  PROJECT_REPO="${PROJECT_BASE}/${REPO_COD}${DOMAIN}.git"

  if submodule_exists "${WORKDIR}/${PROJECT_PATH}"; then
    info "Submodule already exists: ${WORKDIR}/${PROJECT_PATH}"
  else
    run "git submodule add ${PROJECT_REPO} ${PROJECT_PATH}"
  fi

  info "Configuring reference remote for ${DOMAIN}"
  run "git -C ${PROJECT_PATH} remote add reference ${PROJECT_REPO} || true"
  run "git -C ${PROJECT_PATH} fetch reference"

done

cd "${REPO_ROOT}"

info 'Initializing submodules'
run 'git submodule update --init --recursive'

info 'Staging submodule metadata'
run 'git add .gitmodules'
run "git add ${WORKDIR}"

info 'Committing changes'
run "git commit -m 'PCDD-22227 - ${WORKDIR} - Add project submodules'"

info 'Pushing branch'
run "git push -u origin ${BRANCH_NAME}"
