#!/usr/bin/env bash

set -e

# =========================
# Config
# =========================
BRANCH="feat/scripts-submodules-and-legacy"
DIR="scripts/repos"

COMMIT_MSG="Adiciona scripts de migração e submódulos"

# =========================
# branch
# =========================
echo "Criando branch: $BRANCH"
git checkout -b "$BRANCH"

echo "Criando diretório: $DIR"
mkdir -p "$DIR"

# =========================
# legacy.sh
# =========================
echo "copying legacy.sh"
cp ../legacy.sh "$DIR"

# =========================
# setup-submodules.sh
# =========================
echo "Criando setup-submodules.sh"
cp ../setup-submodules.sh "$DIR"

# =========================
# Git add + commit
# =========================
echo "Adicionando arquivos"
git add "$DIR"

echo "Commitando"
git commit -m "$COMMIT_MSG" -m "
Adiciona scripts para automatizar a migração de repositórios
legados e configuração de submódulos no repositório principal.

Inclui:
- legacy.sh: copia repositórios legados para o novo ambiente
- setup-submodules.sh: adiciona e configura submódulos no repo hub

Objetivo é facilitar a centralização e organização de múltiplos
repositórios em uma estrutura única.
"

# =========================
# Push
# =========================
echo "Enviando branch"
git push -u origin "$BRANCH"

# =========================
# Final
# =========================
gh pr create \
  --base main \
  --head ${BRANCH} \
  --title "Adiciona scripts para de submódulos no s12190-ia-submarina e migração do tnz5" \
  --reviewer \
        breno-krohling-prestserv_petro, \
        suzane-lima-prestserv_petro, \
        matheus-santos16-prestserv_petro \
  --body "$(cat << 'PR'
## Contexto
Este PR adiciona scripts para auxiliar na migração de repositórios
legados e na configuração de submódulos em um repositório central (hub).

## O que foi feito
- Criação do script `legacy.sh` para cópia de repositórios antigos
- Criação do script `setup-submodules.sh` para adicionar submódulos
- Organização dos scripts no diretório `scripts/repos`

## Objetivo
Facilitar o processo de consolidação de múltiplos repositórios em
um único repositório principal, mantendo histórico e separação via
submódulos.

## Como testar
1. Executar `legacy.sh` para migrar um repositório de exemplo
2. Executar `setup-submodules.sh` para adicionar como submódulo
3. Validar se os submódulos foram configurados corretamente

## Observações
- Verificar permissões de execução dos scripts (`chmod +x`)
- Garantir acesso aos repositórios de origem
PR)"
