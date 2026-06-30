#!/usr/bin/env bash
# Remove all legacy* branches (remote and local)

set -Eeuo pipefail

LEGACY_PREFIX="${1:-legacy}"

# =============================
# Delete remote legacy* branches
# =============================
echo -e "\e[33mDeleting remote branches matching '${LEGACY_PREFIX}*'...\e[0m"
for br in $(git ls-remote --heads origin "${LEGACY_PREFIX}*" \
           | cut -f2 | sed 's|refs/heads/||'); do
  echo "Deleting remote branch: $br"
  git push origin --delete "$br"
done

# =============================
# Delete local legacy* branches
# =============================
echo -e "\e[33mDeleting local branches matching '${LEGACY_PREFIX}*'...\e[0m"
for br in $(git branch --list "${LEGACY_PREFIX}*"); do
  echo "Deleting local branch: $br"
  git branch -D "$br"
done

echo -e "\e[32mAll '${LEGACY_PREFIX}*' branches removed successfully!\e[0m"
