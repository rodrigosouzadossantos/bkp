#!/usr/bin/env bash
# vim: set ts=2 sts=2 sw=2 et:

set -Eeuo pipefail

# =============================
# Capture all script output
# =============================
LOG_FILE="$(mktemp)"
trap 'rm -f "$LOG_FILE"' EXIT

exec 3>&1 4>&2
exec >"$LOG_FILE" 2>&1

# =============================
# Parameters
# =============================
# $1 = legacy repo name
# $2 = destination repo name
# $3 = optional legacy prefix (default: legacy)
if [ $# -lt 2 ] || [ $# -gt 3 ];
then
  echo -e "\e[31mUsage: $0 <legacy-repo> <dest-repo> [legacy-prefix]\e[0m" >&3
  exit 1
fi

LEGACY_REPO="$1"
DEST_REPO="$2"
LEGACY_PREFIX="${3:-legacy}"

OWNER="petrobrasbr"
GITHUB="https://github.com/${OWNER}"
SRC_REPO="${GITHUB}/${LEGACY_REPO}.git"
DEST_REPO_URL="${GITHUB}/${DEST_REPO}.git"

# =============================
# Check required commands
# =============================
for cmd in git git-filter-repo;
do
  if ! command -v "$cmd" >/dev/null;
  then
    echo -e "\e[31mERROR: $cmd not found\e[0m" >&3
    exit 1
  fi
done

# =============================
# Workspace
# =============================
WORKDIR="$(mktemp -d)"
DEST_DIR="${WORKDIR}/dest"
LEGACY_DIR="${WORKDIR}/legacy"

cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

rollback() {
  exec 1>&3 2>&4
  echo -e "\e[31mERROR occurred. Script output:\e[0m"
  cat "$LOG_FILE"

  echo -e "\n\e[33mRolling back pushed legacy refs...\e[0m"
  cd "$DEST_DIR" || return
  for ref in "${PUSHED_REFS[@]:-}";
  do
    echo -e "\e[31mDeleting remote ref: $ref\e[0m"
    git push origin ":$ref" || true
  done
}
trap rollback ERR

# =============================
# Clone destination repo
# =============================
echo -e "\e[34mCloning destination repo...\e[0m" >&3
git clone --no-tags "$DEST_REPO_URL" "$DEST_DIR"
cd "$DEST_DIR"

# =============================
# Remove old legacy branches/tags
# =============================
echo -e "\e[33mRemoving old ${LEGACY_PREFIX}/* branches and tags...\e[0m" >&3
for br in $(git ls-remote --heads origin "${LEGACY_PREFIX}/*" \
           | cut -f2 | sed 's|refs/heads/||');
do
  git push origin --delete "$br"
done

for tg in $(git ls-remote --tags origin "${LEGACY_PREFIX}/*" \
           | cut -f2 | sed 's|refs/tags/||');
do
  git push origin --delete "refs/tags/$tg"
done

# =============================
# Clone legacy repo bare
# =============================
echo -e "\e[34mCloning legacy repo...\e[0m" >&3
git clone --bare "$SRC_REPO" "$LEGACY_DIR"

# =============================
# Import legacy branches as orphan
# =============================
cd "$DEST_DIR"
PUSHED_REFS=()

for br in $(git -C "$LEGACY_DIR" for-each-ref \
           --format='%(refname:short)' refs/heads/);
do
  TARGET="${LEGACY_PREFIX}/${br}"
  echo -e "\e[36mProcessing legacy branch:\e[0m $br  \e[31m\xE2\x9E\xA4\e[0m  $TARGET\e[0m" >&3

  # Create temporary orphan root
  git checkout --orphan tmp-root
  git rm -rf . >/dev/null 2>&1

  git commit --allow-empty -m "Orphan root for legacy branch $TARGET"

  # Create legacy branch on top of orphan
  git checkout -b "$TARGET"
  git remote add legacy-temp "$LEGACY_DIR"
  git fetch legacy-temp "$br"
  git merge --allow-unrelated-histories -m \
    "Import legacy branch $br" FETCH_HEAD

  # Prepend legacy info to README.md if it exists
  if [ -f README.md ];
  then
    cat <<EOF | sed -r 's/^ +//' | cat - README.md > README.tmp
      # Legacy Branch

      **Original Branch:** $br  
      **Imported As:** $TARGET  
      **Origin Repo:** $SRC_REPO  
      **Imported Date:** $(date -u +"%Y-%m-%d %H:%M UTC")  

      This file represents the root commit for the legacy branch.  
      All historical commits from the legacy branch are imported  
      on top of this orphan root.

      <br>

      ---

      <br>

EOF

    mv README.tmp README.md

    git add README.md
    git commit -m "Add legacy branch info for '$br' as '$TARGET'"
  fi

  # Push to remote
  git push origin "$TARGET"
  PUSHED_REFS+=("refs/heads/$TARGET")

  # Cleanup temp orphan
  git branch -D tmp-root
  git remote remove legacy-temp
done

# =============================
# Import tags with prefix
# =============================
echo -e "\e[36mProcessing legacy tags...\e[0m" >&3
for tg in $(git -C "$LEGACY_DIR" tag);
do
  NEW_TAG="${LEGACY_PREFIX}/${tg}"
  git tag "$NEW_TAG" "$tg"
  git push origin "$NEW_TAG"
done

# =============================
# Done
# =============================
echo -e "\n\e[32m=====================================\e[0m" >&3
echo -e "\e[32mLegacy import completed successfully!\e[0m" >&3
echo -e "\e[32m=====================================\e[0m" >&3
echo -e "\e[36mImported branches:\e[0m" >&3
for r in "${PUSHED_REFS[@]}";
do
  echo "  $r" >&3
done

exec 1>&3 2>&4
