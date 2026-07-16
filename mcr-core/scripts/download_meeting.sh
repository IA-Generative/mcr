#!/usr/bin/env bash
set -euo pipefail

# download_meeting.sh — Télécharge des fichiers d'une réunion depuis S3 (Scaleway) avec awscli

usage() {
  cat <<'EOF'
download_meeting.sh — Télécharge des fichiers d'une réunion depuis S3 (Scaleway) avec awscli

Découvre ce qui est stocké sur S3 pour une réunion puis propose une sélection
interactive (audio / tous les docs / types de docs choisis) :
     ./download_meeting.sh --id 12345
     ./download_meeting.sh --id 12345 --dest ./out
     ./download_meeting.sh --id 12345 --select audio,docs        # non-interactif
     ./download_meeting.sh --id 12345 --select decision_record.docx,v0.docx
     ./download_meeting.sh --id 12345 --select artifacts,diarization.json

Options :
  --id            ID de la réunion (obligatoire)
  --select        Pré-sélection non-interactive (liste séparée par des virgules) :
                    "audio"        → les fichiers audio
                    "docs"         → tous les documents (transcription + rapports)
                    "artifacts"    → tous les artéfacts intermédiaires du pipeline
                    "<nom.ext>"    → un fichier précis (match sur le nom, docs ou artéfacts)
  --bucket        Nom du bucket (par défaut : mirai-mcr-prod)
  --dest          Dossier local de destination (par défaut : ~/Downloads/<id>)
  --endpoint      Endpoint S3 Scaleway (par défaut : https://s3.fr-par.scw.cloud)
  --region        Région (par défaut : fr-par)
  --profile       Profil AWS CLI (par défaut : scaleway)
  --audio-folder  Dossier audio dans le bucket (par défaut : audio)
  --transcription-folder  Dossier transcriptions (par défaut : transcription)
  --report-folder Dossier rapports (par défaut : report)
  --artifacts-folder      Dossier artéfacts du pipeline (par défaut : artifacts)
  --dry-run       N'exécute pas, affiche uniquement ce qui serait fait
  --quiet         Réduit la verbosité (n'affiche que les erreurs)
  --no-progress   Masque la barre de progression
  --              Tout ce qui suit est passé tel quel à "aws s3 cp" (ex : --exclude / --include)
EOF
}

# Valeurs par défaut
BUCKET="mirai-mcr-prod"
MEETING_ID=""
SELECT=""
DEST=""
ENDPOINT="https://s3.fr-par.scw.cloud"
REGION="fr-par"
PROFILE="scaleway"
AUDIO_FOLDER="audio"
TRANSCRIPTION_FOLDER="transcription"
REPORT_FOLDER="report"
ARTIFACTS_FOLDER="artifacts"
DRY_RUN="false"
QUIET="false"
NO_PROGRESS="false"

# Parse args
PASS_THROUGH=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)               BUCKET="${2:?}"; shift 2 ;;
    --id)                   MEETING_ID="${2:?}"; shift 2 ;;
    --select)               SELECT="${2:?}"; shift 2 ;;
    --dest)                 DEST="${2:?}"; shift 2 ;;
    --endpoint)             ENDPOINT="${2:?}"; shift 2 ;;
    --region)               REGION="${2:?}"; shift 2 ;;
    --profile)              PROFILE="${2:?}"; shift 2 ;;
    --audio-folder)         AUDIO_FOLDER="${2:?}"; shift 2 ;;
    --transcription-folder) TRANSCRIPTION_FOLDER="${2:?}"; shift 2 ;;
    --report-folder)        REPORT_FOLDER="${2:?}"; shift 2 ;;
    --artifacts-folder)     ARTIFACTS_FOLDER="${2:?}"; shift 2 ;;
    --dry-run)              DRY_RUN="true"; shift 1 ;;
    --quiet)                QUIET="true"; shift 1 ;;
    --no-progress)          NO_PROGRESS="true"; shift 1 ;;
    --)                     shift; PASS_THROUGH+=("$@"); break ;;
    -h|--help)
      usage
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
[[ -n "$MEETING_ID" ]] || { echo "--id est requis"; exit 1; }
[[ -n "$DEST" ]] || DEST="$HOME/Downloads/$MEETING_ID"

# Flags optionnels communs
EXTRA_FLAGS=()
[[ "$DRY_RUN" == "true" ]] && EXTRA_FLAGS+=(--dryrun)
[[ "$QUIET" == "true" ]] && EXTRA_FLAGS+=(--only-show-errors)
[[ "$NO_PROGRESS" == "true" ]] && EXTRA_FLAGS+=(--no-progress)

mkdir -p "$DEST"

# --- Helpers S3 ---------------------------------------------------------------

# Liste les clés sous un préfixe (une par ligne). Vide si rien.
# Un échec AWS réel (auth, bucket introuvable, réseau) est distingué d'un
# résultat vide : on affiche l'erreur AWS et on sort au lieu de faire croire
# qu'aucun fichier n'existe.
list_keys() {
  local prefix="$1" out err
  err="$(mktemp)"
  if ! out="$(aws --profile "$PROFILE" --region "$REGION" \
      s3api list-objects-v2 \
      --bucket "$BUCKET" \
      --prefix "$prefix" \
      --endpoint-url "$ENDPOINT" \
      --query 'Contents[].Key' \
      --output text 2>"$err")"; then
    echo "Erreur AWS lors de l'inspection de s3://${BUCKET}/${prefix} :" >&2
    cat "$err" >&2
    rm -f "$err"
    exit 1
  fi
  rm -f "$err"
  printf '%s\n' "$out" | tr '\t' '\n' | grep -v '^None$' | grep -v '^$' || true
}

# Télécharge un document, aplati sous DEST en "type-filename.ext"
# (ex : report/12345/decision_record.docx -> report-decision_record.docx).
download_doc() {
  local key="$1"
  local folder="${key%%/*}"
  local filename="${key##*/}"
  local out="$DEST/${folder}-${filename}"
  aws --profile "$PROFILE" --region "$REGION" \
      s3 cp "s3://${BUCKET}/${key}" "$out" \
      --endpoint-url "$ENDPOINT" \
      ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"} \
      ${PASS_THROUGH[@]+"${PASS_THROUGH[@]}"}
}

# Télécharge tous les fichiers audio, aplatis sous DEST en "type-filename.ext"
# (comme les documents). Itère AUDIO_KEYS déjà découvert.
download_audio() {
  local key
  while IFS= read -r key; do
    [[ -z "$key" ]] && continue
    echo "→ Téléchargement de s3://${BUCKET}/${key}"
    download_doc "$key"
  done <<< "$AUDIO_KEYS"
}

# --- Découverte de ce qui est stocké sur S3 ----------------------------------

AUDIO_PREFIX="${AUDIO_FOLDER}/${MEETING_ID}/"
TRANSCRIPTION_PREFIX="${TRANSCRIPTION_FOLDER}/${MEETING_ID}/"
REPORT_PREFIX="${REPORT_FOLDER}/${MEETING_ID}/"
ARTIFACTS_PREFIX="${ARTIFACTS_FOLDER}/${MEETING_ID}/"

echo "→ Réunion ${MEETING_ID} — inspection de s3://${BUCKET}/ ..."
echo "→ Endpoint : ${ENDPOINT} | Région : ${REGION} | Profil : ${PROFILE}"

AUDIO_KEYS="$(list_keys "$AUDIO_PREFIX")"
DOC_KEYS="$(printf '%s\n%s\n' "$(list_keys "$TRANSCRIPTION_PREFIX")" "$(list_keys "$REPORT_PREFIX")" | grep -v '^$' || true)"
ARTIFACT_KEYS="$(list_keys "$ARTIFACTS_PREFIX")"

AUDIO_COUNT=0
[[ -n "$AUDIO_KEYS" ]] && AUDIO_COUNT=$(printf '%s\n' "$AUDIO_KEYS" | grep -c '^')

# Construit la liste des éléments sélectionnables.
# ITEM_KIND : "audio" | "doc" | "artifact"   ITEM_KEY : préfixe (audio) ou clé
ITEM_KIND=()
ITEM_KEY=()
ITEM_LABEL=()
SELECTED=()

if [[ "$AUDIO_COUNT" -gt 0 ]]; then
  ITEM_KIND+=("audio"); ITEM_KEY+=("$AUDIO_PREFIX")
  ITEM_LABEL+=("Audio (${AUDIO_COUNT} fichier(s)) — ${AUDIO_PREFIX}"); SELECTED+=("0")
fi

if [[ -n "$DOC_KEYS" ]]; then
  while IFS= read -r k; do
    [[ -z "$k" ]] && continue
    ITEM_KIND+=("doc"); ITEM_KEY+=("$k"); ITEM_LABEL+=("$k"); SELECTED+=("0")
  done <<< "$DOC_KEYS"
fi

if [[ -n "$ARTIFACT_KEYS" ]]; then
  while IFS= read -r k; do
    [[ -z "$k" ]] && continue
    ITEM_KIND+=("artifact"); ITEM_KEY+=("$k"); ITEM_LABEL+=("$k"); SELECTED+=("0")
  done <<< "$ARTIFACT_KEYS"
fi

if [[ ${#ITEM_KIND[@]} -eq 0 ]]; then
  echo "Aucun fichier trouvé pour la réunion ${MEETING_ID} (audio/transcription/report/artifacts)." >&2
  exit 1
fi

N=${#ITEM_KIND[@]}

# Indices des documents — pour "tous les docs".
doc_indices() {
  local i
  for ((i=0; i<N; i++)); do
    [[ "${ITEM_KIND[$i]}" == "doc" ]] && echo "$i"
  done
}

# Indices des artéfacts — pour "tous les artéfacts".
artifact_indices() {
  local i
  for ((i=0; i<N; i++)); do
    [[ "${ITEM_KIND[$i]}" == "artifact" ]] && echo "$i"
  done
}

# --- Pré-sélection non-interactive via --select ------------------------------

if [[ -n "$SELECT" ]]; then
  IFS=',' read -r -a TOKENS <<< "$SELECT"
  for tok in "${TOKENS[@]}"; do
    tok="$(echo "$tok" | tr -d '[:space:]')"
    [[ -z "$tok" ]] && continue
    case "$tok" in
      audio)
        for ((i=0; i<N; i++)); do [[ "${ITEM_KIND[$i]}" == "audio" ]] && SELECTED[$i]="1"; done
        ;;
      docs|all-docs|alldocs)
        for i in $(doc_indices); do SELECTED[$i]="1"; done
        ;;
      artifacts|artefacts|all-artifacts)
        for i in $(artifact_indices); do SELECTED[$i]="1"; done
        ;;
      *)
        local_matched="false"
        for ((i=0; i<N; i++)); do
          if [[ "${ITEM_KIND[$i]}" != "audio" && "${ITEM_KEY[$i]}" == *"$tok"* ]]; then
            SELECTED[$i]="1"; local_matched="true"
          fi
        done
        [[ "$local_matched" == "false" ]] && echo "⚠ --select : aucun fichier ne correspond à « ${tok} »" >&2
        ;;
    esac
  done
else
  # --- Sélection interactive (checkboxes) ------------------------------------
  if [[ ! -t 0 && ! -e /dev/tty ]]; then
    echo "Pas de terminal interactif disponible. Utilise --select pour choisir en non-interactif." >&2
    exit 1
  fi

  # Un seul fichier : pré-sélectionné, Entrée le télécharge directement.
  [[ "$N" -eq 1 ]] && SELECTED[0]="1"

  all_docs_selected() {
    local i has=0
    for i in $(doc_indices); do
      has=1
      [[ "${SELECTED[$i]}" == "1" ]] || return 1
    done
    [[ "$has" -eq 1 ]]
  }

  all_artifacts_selected() {
    local i has=0
    for i in $(artifact_indices); do
      has=1
      [[ "${SELECTED[$i]}" == "1" ]] || return 1
    done
    [[ "$has" -eq 1 ]]
  }

  render() {
    echo ""
    if [[ "$N" -eq 1 ]]; then
      echo "Réunion ${MEETING_ID} — un seul fichier disponible :"
    else
      echo "Réunion ${MEETING_ID} — sélectionne ce qu'il faut télécharger :"
    fi
    local i n=1
    # Lignes "tous les docs"/"tous les artéfacts" seulement s'il y en a,
    # et uniquement quand il y a plus d'un fichier au total.
    if [[ "$N" -gt 1 && -n "$(doc_indices)" ]]; then
      if all_docs_selected; then echo "   d) [x] Tous les documents"; else echo "   d) [ ] Tous les documents"; fi
    fi
    if [[ "$N" -gt 1 && -n "$(artifact_indices)" ]]; then
      if all_artifacts_selected; then echo "   t) [x] Tous les artéfacts"; else echo "   t) [ ] Tous les artéfacts"; fi
    fi
    for ((i=0; i<N; i++)); do
      local mark="[ ]"
      [[ "${SELECTED[$i]}" == "1" ]] && mark="[x]"
      printf "  %2d) %s %s\n" "$n" "$mark" "${ITEM_LABEL[$i]}"
      n=$((n+1))
    done
    echo ""
    if [[ "$N" -eq 1 ]]; then
      echo "Commandes : 1 bascule · Entrée=télécharger · q=quitter"
    else
      echo "Commandes : <n°> bascule · a=tout · x=rien · d=tous les docs · t=tous les artéfacts · Entrée=télécharger · q=quitter"
    fi
  }

  while true; do
    render
    printf "> "
    read -r choice </dev/tty || choice="q"
    case "$choice" in
      ""|ok|go|download)
        break ;;
      q|quit|exit)
        echo "Annulé."; exit 0 ;;
      a|all)
        for ((i=0; i<N; i++)); do SELECTED[$i]="1"; done ;;
      x|none)
        for ((i=0; i<N; i++)); do SELECTED[$i]="0"; done ;;
      d|docs)
        if all_docs_selected; then
          for i in $(doc_indices); do SELECTED[$i]="0"; done
        else
          for i in $(doc_indices); do SELECTED[$i]="1"; done
        fi ;;
      t|artifacts|artefacts)
        if all_artifacts_selected; then
          for i in $(artifact_indices); do SELECTED[$i]="0"; done
        else
          for i in $(artifact_indices); do SELECTED[$i]="1"; done
        fi ;;
      *)
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= N )); then
          idx=$((choice-1))
          [[ "${SELECTED[$idx]}" == "1" ]] && SELECTED[$idx]="0" || SELECTED[$idx]="1"
        else
          echo "Entrée invalide : ${choice}"
        fi ;;
    esac
  done
fi

# --- Téléchargement des éléments sélectionnés --------------------------------

any=0
for ((i=0; i<N; i++)); do
  [[ "${SELECTED[$i]}" != "1" ]] && continue
  any=1
  if [[ "${ITEM_KIND[$i]}" == "audio" ]]; then
    download_audio
  else
    echo "→ Téléchargement de s3://${BUCKET}/${ITEM_KEY[$i]}"
    download_doc "${ITEM_KEY[$i]}"
  fi
done

if [[ "$any" -eq 0 ]]; then
  echo "Aucun élément sélectionné, rien à télécharger."
  exit 0
fi

echo "✓ Terminé. Fichiers dans : ${DEST}/"
