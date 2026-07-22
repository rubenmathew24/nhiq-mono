#!/usr/bin/env bash
# Verify / bind Container App env vars listed in infra/deploy/app-env.manifest.json.
# Does not change Redis/Postgres SKU or firewall. Never prints secret values.
set -euo pipefail

MANIFEST="${1:?manifest path}"
APP_NAME="${2:?container app name}"
RESOURCE_GROUP="${3:?resource group}"
SECTION="${4:?api|web}"

if ! command -v jq >/dev/null; then
  echo "error: jq required" >&2
  exit 1
fi

mapfile -t REQUIRED < <(jq -r --arg s "$SECTION" '.[$s][]' "$MANIFEST")

# Known ACA secret names (kebab) for secretref binding — values already on the app.
declare -A SECRETREF_MAP=(
  [DATABASE_URL]=database-url
  [REDIS_URL]=redis-url
  [SECRET_KEY]=secret-key
  [MAPBOX_TOKEN]=mapbox-token
  [ANTHROPIC_API_KEY]=anthropic-api-key
  [AUTH_SECRET]=auth-secret
)

echo "app_config: checking $APP_NAME section=$SECTION"

EXISTING_JSON=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.template.containers[0].env" -o json)

EXISTING_SECRETS=$(az containerapp secret list \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[].name" -o tsv || true)

MISSING=()
TO_BIND=()

for NAME in "${REQUIRED[@]}"; do
  # Build-time public web vars: documented in manifest; skip runtime ACA for NEXT_PUBLIC_*
  if [[ "$NAME" == NEXT_PUBLIC_* ]]; then
    echo "skip runtime bind (build-arg): $NAME"
    continue
  fi
  if echo "$EXISTING_JSON" | jq -e --arg n "$NAME" 'map(.name) | index($n) != null' >/dev/null; then
    echo "present: $NAME"
    continue
  fi
  # Try to bind secretref if we know the ACA secret name and it exists
  REF="${SECRETREF_MAP[$NAME]:-}"
  if [[ -n "$REF" ]] && echo "$EXISTING_SECRETS" | grep -qx "$REF"; then
    echo "will bind: $NAME=secretref:$REF"
    TO_BIND+=("${NAME}=secretref:${REF}")
    continue
  fi
  MISSING+=("$NAME")
done

if ((${#TO_BIND[@]})); then
  echo "app_config: binding ${#TO_BIND[@]} env vars on $APP_NAME"
  az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --set-env-vars "${TO_BIND[@]}" \
    --output none
fi

if ((${#MISSING[@]})); then
  echo "error: missing required env on $APP_NAME: ${MISSING[*]}" >&2
  echo "Add Container App secrets/env (or GitHub/Key Vault wiring) for these names, then re-run." >&2
  exit 1
fi

echo "app_config: $APP_NAME ok"
