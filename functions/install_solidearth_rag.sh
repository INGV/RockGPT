#!/usr/bin/env bash
# Install or update the SolidEarth RAG pipe on an Open WebUI instance through
# its REST API, then publish it as a Workspace model every user can read.
#
#   functions/install_solidearth_rag.sh [BASE_URL]      (default: production)
#
# Signs in as the local break-glass admin and asks for the password on the
# terminal; nothing is stored. Safe to re-run: an existing function gets its
# code replaced, an existing model record gets its grants reasserted.
#
# Why three steps and not one: Open WebUI stores a function inactive on
# creation (FunctionModel.is_active defaults to False), and a pipe model
# without a Workspace record is visible to admins only. Both facts were
# read from the v0.11.3 source, not from the docs.
set -euo pipefail

readonly BASE_URL="${1:-https://rockgpt.int.ingv.it}"
readonly ADMIN_EMAIL="${ADMIN_EMAIL:-admin@localhost}"
readonly FUNCTION_ID="solidearth_rag"
readonly FUNCTION_NAME="RockGPT SolidEarth"
readonly DESCRIPTION="External RAG on the EarthPrints solid-earth papers (Qdrant collection SolidEarth behind llm.pp.ingv.it)."
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PIPE_FILE="${SCRIPT_DIR}/solidearth_rag_pipe.py"

for TOOL in curl jq; do
    if ! command -v "${TOOL}" >/dev/null 2>&1; then
        echo "missing tool: ${TOOL}" >&2
        exit 1
    fi
done
if [[ ! -r "${PIPE_FILE}" ]]; then
    echo "pipe file not found: ${PIPE_FILE}" >&2
    exit 1
fi

# --- sign in ----------------------------------------------------------------
read -rs -p "Password for ${ADMIN_EMAIL} on ${BASE_URL}: " ADMIN_PASSWORD
echo
SIGNIN_BODY="$(jq -n --arg email "${ADMIN_EMAIL}" --arg password "${ADMIN_PASSWORD}" \
    '{email: $email, password: $password}')"
unset ADMIN_PASSWORD
TOKEN="$(curl -sf -X POST "${BASE_URL}/api/v1/auths/signin" \
    -H "Content-Type: application/json" -d "${SIGNIN_BODY}" | jq -r '.token // empty')"
unset SIGNIN_BODY
if [[ -z "${TOKEN}" ]]; then
    echo "sign-in failed for ${ADMIN_EMAIL}" >&2
    exit 1
fi

# api METHOD PATH [JSON_BODY]: one authenticated call, body on stdout.
# Failures (HTTP >= 400) make curl exit non-zero, which set -e turns into
# an abort, except where the caller tests the result explicitly.
api() {
    local METHOD="$1"
    local API_PATH="$2"
    local BODY="${3:-}"
    if [[ -n "${BODY}" ]]; then
        curl -sf -X "${METHOD}" "${BASE_URL}${API_PATH}" \
            -H "Authorization: Bearer ${TOKEN}" \
            -H "Content-Type: application/json" \
            -d "${BODY}"
    else
        curl -sf -X "${METHOD}" "${BASE_URL}${API_PATH}" \
            -H "Authorization: Bearer ${TOKEN}"
    fi
}

# --- 1. the function ----------------------------------------------------------
FUNCTION_BODY="$(jq -n --arg id "${FUNCTION_ID}" --arg name "${FUNCTION_NAME}" \
    --arg description "${DESCRIPTION}" --rawfile content "${PIPE_FILE}" \
    '{id: $id, name: $name, content: $content, meta: {description: $description}}')"
if api GET "/api/v1/functions/id/${FUNCTION_ID}" | jq -e '.id' >/dev/null 2>&1; then
    api POST "/api/v1/functions/id/${FUNCTION_ID}/update" "${FUNCTION_BODY}" >/dev/null
    echo "function ${FUNCTION_ID}: code updated"
else
    api POST "/api/v1/functions/create" "${FUNCTION_BODY}" >/dev/null
    echo "function ${FUNCTION_ID}: created"
fi

# --- 2. activation -------------------------------------------------------------
IS_ACTIVE="$(api GET "/api/v1/functions/id/${FUNCTION_ID}" | jq -r '.is_active')"
if [[ "${IS_ACTIVE}" != "true" ]]; then
    api POST "/api/v1/functions/id/${FUNCTION_ID}/toggle" >/dev/null
    echo "function ${FUNCTION_ID}: activated"
else
    echo "function ${FUNCTION_ID}: already active"
fi

# --- 3. the Workspace model record --------------------------------------------
# Same id as the function: for a single (non-manifold) pipe the model id is
# the function id. Public read grant = principal "user" "*" (access_grant
# table). No system prompt and no tools: the pipe forwards neither.
# file_upload/vision off because attachments would be silently ignored.
MODEL_BODY="$(jq -n --arg id "${FUNCTION_ID}" --arg name "${FUNCTION_NAME}" \
    --arg description "${DESCRIPTION}" \
    '{
        id: $id,
        base_model_id: null,
        name: $name,
        meta: {
            description: $description,
            capabilities: {citations: true, file_upload: false, vision: false,
                           web_search: false, image_generation: false,
                           code_interpreter: false}
        },
        params: {},
        access_grants: [{principal_type: "user", principal_id: "*", permission: "read"}],
        is_active: true
    }')"
if api GET "/api/v1/models/model?id=${FUNCTION_ID}" | jq -e '.id' >/dev/null 2>&1; then
    api POST "/api/v1/models/model/update?id=${FUNCTION_ID}" "${MODEL_BODY}" >/dev/null
    echo "model ${FUNCTION_ID}: record updated, public read grant reasserted"
else
    api POST "/api/v1/models/create" "${MODEL_BODY}" >/dev/null
    echo "model ${FUNCTION_ID}: record created with public read grant"
fi

echo "done: '${FUNCTION_NAME}' is in the model picker of ${BASE_URL}"
