#!/usr/bin/env bash
set -euo pipefail

# download_prefix.sh — Télécharge récursivement un préfixe S3 (Scaleway) avec awscli
# Usage simple :
#   ./download_prefix.sh --bucket mon-bucket --prefix mon/prefix/ --dest ./local/
#
# Options complètes :
#   --bucket        Nom du bucket (obligatoire)
#   --prefix        Préfixe à télécharger (ex : "data/2025/") (obligatoire)
#   --dest          Dossier local de destination (par défaut : ./download)
#   --endpoint      Endpoint S3 Scaleway (par défaut : https://s3.fr-par.scw.cloud)
#   --region        Région (par défaut : fr-par)
#   --profile       Profil AWS CLI (par défaut : scaleway)
#   --dry-run       N’exécute pas, affiche uniquement ce qui serait fait
#   --quiet         Réduit la verbosité (n’affiche que les erreurs)
#   --no-progress   Masque la barre de progression
#   --              Tout ce qui suit est passé tel quel à "aws s3 cp" (ex : --exclude / --include)
#
# Exemples :
#   ./download_prefix.sh --bucket my-bucket --prefix assets/img/ --dest ./img
#   ./download_prefix.sh --bucket my-bucket --prefix data/ --dest ./data -- --exclude "*tmp*" --include "*.csv"

# Valeurs par défaut
BUCKET="mirai-mcr-prod"
PREFIX=""
DEST="./download"
ENDPOINT="https://s3.fr-par.scw.cloud"
REGION="fr-par"
PROFILE="scaleway"
DRY_RUN="false"
QUIET="false"
NO_PROGRESS="false"

# Parse args
PASS_THROUGH=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)      BUCKET="${2:?}"; shift 2 ;;
    --prefix)      PREFIX="${2:?}"; shift 2 ;;
    --dest)        DEST="${2:?}"; shift 2 ;;
    --endpoint)    ENDPOINT="${2:?}"; shift 2 ;;
    --region)      REGION="${2:?}"; shift 2 ;;
    --profile)     PROFILE="${2:?}"; shift 2 ;;
    --dry-run)     DRY_RUN="true"; shift 1 ;;
    --quiet)       QUIET="true"; shift 1 ;;
    --no-progress) NO_PROGRESS="true"; shift 1 ;;
    --)            shift; PASS_THROUGH+=("$@"); break ;;
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

# Normalisation du préfixe
if [[ "$PREFIX" != */ ]]; then
  PREFIX="${PREFIX}/"
fi

# Création du répertoire de destination
mkdir -p "$DEST"

# Flags optionnels
EXTRA_FLAGS=()
[[ "$DRY_RUN" == "true" ]] && EXTRA_FLAGS+=(--dryrun)
[[ "$QUIET" == "true" ]] && EXTRA_FLAGS+=(--only-show-errors)
[[ "$NO_PROGRESS" == "true" ]] && EXTRA_FLAGS+=(--no-progress)

# Exécution
echo "→ Téléchargement de s3://${BUCKET}/${PREFIX} vers ${DEST}"
echo "→ Endpoint : ${ENDPOINT} | Région : ${REGION} | Profil : ${PROFILE}"

if [[ ${#PASS_THROUGH[@]} -gt 0 ]]; then
  echo "→ Options supplémentaires passées à aws s3 cp : ${PASS_THROUGH[*]}"
fi

if [[ "$DRY_RUN" == "true" ]]; then
  echo "→ MODE DRY-RUN : aucun fichier ne sera réellement téléchargé."
fi

aws --profile "$PROFILE" \
    --region "$REGION" \
    s3 cp "s3://${BUCKET}/${PREFIX}" "$DEST" \
    --recursive \
    --endpoint-url "$ENDPOINT" \
    ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"} \
    ${PASS_THROUGH[@]+"${PASS_THROUGH[@]}"}

echo "✓ Terminé."