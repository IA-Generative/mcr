#!/usr/bin/env bash
set -euo pipefail

# upload_chunk.sh — Upload d'un fichier local vers un préfixe S3 (Scaleway) avec awscli
# Usage simple :
#   ./upload_chunk.sh --file ./mon-fichier.weba --prefix audio/42/
#
# Options complètes :
#   --bucket        Nom du bucket (par défaut : mirai-mcr-staging)
#   --prefix        Préfixe S3 de destination (ex : "audio/42/") (obligatoire)
#   --file          Fichier local à uploader (obligatoire)
#   --endpoint      Endpoint S3 Scaleway (par défaut : https://s3.fr-par.scw.cloud)
#   --region        Région (par défaut : fr-par)
#   --profile       Profil AWS CLI (par défaut : scaleway)
#   --dry-run       N'exécute pas, affiche uniquement ce qui serait fait
#   --quiet         Réduit la verbosité (n'affiche que les erreurs)
#   --no-progress   Masque la barre de progression
#
# Exemples :
#   ./upload_chunk.sh --file ./chunk_001.weba --prefix audio/42/
#   ./upload_chunk.sh --file ./output.webm --prefix audio/42/ --bucket mon-bucket

# Valeurs par défaut
BUCKET="mirai-mcr-staging"
PREFIX=""
FILE=""
ENDPOINT="https://s3.fr-par.scw.cloud"
REGION="fr-par"
PROFILE="scaleway"
DRY_RUN="false"
QUIET="false"
NO_PROGRESS="false"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)      BUCKET="${2:?}"; shift 2 ;;
    --prefix)      PREFIX="${2:?}"; shift 2 ;;
    --file)        FILE="${2:?}"; shift 2 ;;
    --endpoint)    ENDPOINT="${2:?}"; shift 2 ;;
    --region)      REGION="${2:?}"; shift 2 ;;
    --profile)     PROFILE="${2:?}"; shift 2 ;;
    --dry-run)     DRY_RUN="true"; shift 1 ;;
    --quiet)       QUIET="true"; shift 1 ;;
    --no-progress) NO_PROGRESS="true"; shift 1 ;;
    -h|--help)
      sed -n '1,200p' "$0" | sed -n '1,80p'
      exit 0
      ;;
    *)
      echo "Argument inconnu : $1" >&2
      exit 1
      ;;
  esac
done

# Vérifications
command -v aws >/dev/null 2>&1 || { echo "awscli introuvable. Installe-le (ex : 'pipx install awscli' ou via un package manager)"; exit 1; }
[[ -n "$BUCKET" ]] || { echo "--bucket est requis"; exit 1; }
[[ -n "$PREFIX" ]] || { echo "--prefix est requis"; exit 1; }
[[ -n "$FILE" ]] || { echo "--file est requis"; exit 1; }
[[ -f "$FILE" ]] || { echo "Le fichier '${FILE}' n'existe pas"; exit 1; }

# Normalisation du préfixe
if [[ "$PREFIX" != */ ]]; then
  PREFIX="${PREFIX}/"
fi

# Construire la clé S3 de destination (préfixe + nom du fichier)
FILENAME=$(basename "$FILE")
S3_KEY="${PREFIX}${FILENAME}"

# Flags optionnels
EXTRA_FLAGS=()
[[ "$DRY_RUN" == "true" ]] && EXTRA_FLAGS+=(--dryrun)
[[ "$QUIET" == "true" ]] && EXTRA_FLAGS+=(--only-show-errors)
[[ "$NO_PROGRESS" == "true" ]] && EXTRA_FLAGS+=(--no-progress)

# Exécution
echo "→ Upload de ${FILE} vers s3://${BUCKET}/${S3_KEY}"
echo "→ Endpoint : ${ENDPOINT} | Région : ${REGION} | Profil : ${PROFILE}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "→ MODE DRY-RUN : aucun fichier ne sera réellement uploadé."
fi

aws --profile "$PROFILE" \
    --region "$REGION" \
    s3 cp "$FILE" "s3://${BUCKET}/${S3_KEY}" \
    --endpoint-url "$ENDPOINT" \
    ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}

echo "✓ Upload terminé : s3://${BUCKET}/${S3_KEY}"
