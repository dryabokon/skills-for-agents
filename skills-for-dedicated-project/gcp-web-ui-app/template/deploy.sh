#!/usr/bin/env bash
# Deploy this web UI app to Cloud Run behind Google sign-in (IAP), runs kept on a Cloud Storage bucket.
#
#   SERVICE=<name> ./deploy.sh deploy     set up what is missing, build the image, deploy, grant viewers
#   ./deploy.sh grant user:a@x.com ...    let people open the site (revoke: the opposite)
#   ./deploy.sh status                    URL, image, who can open it
#   ./deploy.sh remove                    delete the service (bucket and image stay; add --all to delete them too)
#
# Variables (environment or .env): SERVICE (required, lowercase, e.g. trends-console), PROJECT, REGION, ACCOUNT,
# VIEWERS ("user:a@x.com domain:x.com"), SECRETS ("NAME ..." - .env values put into Secret Manager, given to the app
# as env vars). IAP_CLIENT_ID / IAP_CLIENT_SECRET in .env: OAuth client for IAP (needed outside an organization).
#
# Safety: everything is named after SERVICE and labelled app=gcp-web-ui-app; the script refuses to deploy over a
# service, or use a bucket, that it did not create. It never makes the service public.
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash on Windows would turn /app/runs into a Windows path
ROOT=$(cd "$(dirname "$0")" && { pwd -W 2>/dev/null || pwd; })
envget() { [ -f "$ROOT/.env" ] && sed -n "s/^$1=//p" "$ROOT/.env" | tail -1 | tr -d '\r"'"'"' ' || true; }

SERVICE=${SERVICE:-$(envget SERVICE)}
PROJECT=${PROJECT:-$(envget PROJECT)}; PROJECT=${PROJECT:-$(gcloud config get-value project 2>/dev/null)}
REGION=${REGION:-$(envget REGION)}; REGION=${REGION:-europe-west1}
ACCOUNT=${ACCOUNT:-$(envget ACCOUNT)}; ACCOUNT=${ACCOUNT:-$(gcloud config get-value account 2>/dev/null)}
VIEWERS=${VIEWERS:-$(envget VIEWERS)}; VIEWERS=${VIEWERS:-user:$ACCOUNT}
SECRETS=${SECRETS:-$(envget SECRETS)}
[[ "$SERVICE" =~ ^[a-z][a-z0-9-]{2,40}$ ]] || { echo "set SERVICE (lowercase letters, digits, dashes), e.g. SERVICE=trends-console"; exit 2; }
[ -n "$PROJECT" ] || { echo "set PROJECT (or gcloud config set project ...)"; exit 2; }
REPO=gcp-web-ui-app
BUCKET=$PROJECT-$SERVICE-runs
SA=$SERVICE-site@$PROJECT.iam.gserviceaccount.com
IMAGE=$REGION-docker.pkg.dev/$PROJECT/$REPO/$SERVICE
LABEL=app=gcp-web-ui-app

g() { gcloud --project="$PROJECT" ${ACCOUNT:+--account="$ACCOUNT"} --quiet "$@"; }
say() { printf '\n== %s\n' "$*"; }

guard() {
  local lab
  lab=$(g run services describe "$SERVICE" --region="$REGION" --format='value(metadata.labels.app)' 2>/dev/null || true)
  if g run services describe "$SERVICE" --region="$REGION" >/dev/null 2>&1 && [ "$lab" != gcp-web-ui-app ]; then
    echo "refusing: Cloud Run service $SERVICE exists and is not labelled $LABEL - another app owns it. Pick another SERVICE."; exit 3
  fi
  lab=$(g storage buckets describe "gs://$BUCKET" --format='value(labels.app)' 2>/dev/null || true)
  if g storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 && [ "$lab" != gcp-web-ui-app ]; then
    echo "refusing: bucket gs://$BUCKET exists and is not labelled $LABEL"; exit 3
  fi
}

setup() {
  say "APIs"
  g services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    iap.googleapis.com storage.googleapis.com iam.googleapis.com secretmanager.googleapis.com
  say "Artifact Registry repo $REPO"
  g artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 ||
    g artifacts repositories create "$REPO" --location="$REGION" --repository-format=docker
  say "service account $SA"
  g iam service-accounts describe "$SA" >/dev/null 2>&1 ||
    g iam service-accounts create "${SA%%@*}" --display-name="$SERVICE web UI app"
  say "bucket gs://$BUCKET"
  g storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 ||
    g storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access \
      --public-access-prevention --default-storage-class=STANDARD
  g storage buckets update "gs://$BUCKET" --update-labels="$LABEL" >/dev/null
  g storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA" --role=roles/storage.objectUser >/dev/null
  SECRET_FLAGS=""
  for name in $SECRETS; do
    local sec; sec=$(echo "$SERVICE-$name" | tr 'A-Z_' 'a-z-')
    say "secret $sec (from .env $name, not shown)"
    g secrets describe "$sec" >/dev/null 2>&1 || g secrets create "$sec" --replication-policy=automatic --labels="$LABEL"
    sed -n "s/^$name=//p" "$ROOT/.env" | tail -1 | tr -d '\r"'"'"' ' | tr -d '\n' | g secrets versions add "$sec" --data-file=- >/dev/null
    g secrets add-iam-policy-binding "$sec" --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor >/dev/null
    SECRET_FLAGS="$SECRET_FLAGS${SECRET_FLAGS:+,}$name=$sec:latest"
  done
}

deploy() {
  guard
  setup
  local tag; tag=$(date +%Y%m%d-%H%M%S)
  say "build $IMAGE:$tag"
  g builds submit "$ROOT" --tag="$IMAGE:$tag"
  say "deploy $SERVICE (private, IAP)"
  g run deploy "$SERVICE" --image="$IMAGE:$tag" --region="$REGION" --service-account="$SA" --labels="$LABEL" \
    --no-allow-unauthenticated --iap \
    ${SECRET_FLAGS:+--set-secrets="$SECRET_FLAGS"} \
    --execution-environment=gen2 \
    --add-volume=name=runs,type=cloud-storage,bucket="$BUCKET",mount-options=implicit-dirs \
    --add-volume-mount=volume=runs,mount-path=/app/runs \
    --no-cpu-throttling --min-instances=0 --max-instances=1 --cpu=1 --memory=512Mi --timeout=900
  say "IAP may call the service"
  local num; num=$(g projects describe "$PROJECT" --format='value(projectNumber)')
  g beta services identity create --service=iap.googleapis.com >/dev/null 2>&1 || true
  g run services add-iam-policy-binding "$SERVICE" --region="$REGION" \
    --member="serviceAccount:service-$num@gcp-sa-iap.iam.gserviceaccount.com" --role=roles/run.invoker >/dev/null
  iap_client
  grant $VIEWERS
  status
}

# A project outside an organization needs its own OAuth client for IAP: made once in the console
# (Google Auth Platform > Clients, Web application, redirect URI
#  https://iap.googleapis.com/v1/oauth/clientIds/CLIENT_ID:handleRedirect), id and secret in .env.
iap_client() {
  local id sec f
  id=$(envget IAP_CLIENT_ID); sec=$(envget IAP_CLIENT_SECRET)
  [ -n "$id" ] && [ -n "$sec" ] || { echo "IAP_CLIENT_ID / IAP_CLIENT_SECRET not in .env: using the project's IAP settings as they are"; return 0; }
  say "IAP OAuth client from .env (secret not shown)"
  f=$(mktemp); chmod 600 "$f"
  printf 'access_settings:\n  oauth_settings:\n    client_id: %s\n    client_secret: %s\n' "$id" "$sec" > "$f"
  g iap settings set "$(cygpath -w "$f" 2>/dev/null || echo "$f")" >/dev/null; rm -f "$f"
}

# Each Google account must also be a Test user of the OAuth app while it is in Testing (console only).
grant() {
  for v in "$@"; do
    g iap web add-iam-policy-binding --resource-type=cloud-run --service="$SERVICE" --region="$REGION" \
      --member="$v" --role=roles/iap.httpsResourceAccessor >/dev/null && echo "granted $v"
  done
}

revoke() {
  for v in "$@"; do
    g iap web remove-iam-policy-binding --resource-type=cloud-run --service="$SERVICE" --region="$REGION" \
      --member="$v" --role=roles/iap.httpsResourceAccessor >/dev/null && echo "revoked $v"
  done
}

status() {
  say "status"
  g run services describe "$SERVICE" --region="$REGION" \
    --format='value(status.url,spec.template.spec.containers[0].image,status.conditions[0].status)' || return 0
  g iap web get-iam-policy --resource-type=cloud-run --service="$SERVICE" --region="$REGION" \
    --format='value(bindings.members)' 2>/dev/null || true
}

remove() {
  guard
  g run services delete "$SERVICE" --region="$REGION" || true
  if [ "${1:-}" = --all ]; then
    g storage rm --recursive "gs://$BUCKET" || true
    g artifacts docker images delete "$IMAGE" --delete-tags || true
    for name in $SECRETS; do g secrets delete "$(echo "$SERVICE-$name" | tr 'A-Z_' 'a-z-')" || true; done
    g iam service-accounts delete "$SA" || true
  fi
}

case "${1:-}" in
  deploy) deploy ;;
  grant) shift; grant "$@" ;;
  revoke) shift; revoke "$@" ;;
  status) status ;;
  remove) shift; remove "$@" ;;
  *) grep '^#   ' "$0"; exit 1 ;;
esac
