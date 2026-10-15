#!/usr/bin/env bash
# One-time Google Cloud + Firebase setup for CartPilot.
# Run in Google Cloud Shell (gcloud is preinstalled and already signed in):
#   PROJECT=<your-project-id> REPO=WalterVetrivel/cart_pilot bash infra/setup-gcp.sh
# Safe to re-run: steps that already exist are skipped.
set -euo pipefail

: "${PROJECT:?Set PROJECT to your Google Cloud project id}"
: "${REPO:?Set REPO to owner/repo on GitHub}"
REGION="${REGION:-asia-south1}"

step() { printf '\n==> %s\n' "$*"; }

gcloud config set project "$PROJECT" >/dev/null
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')

step "Enabling APIs (takes a minute or two)"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com firestore.googleapis.com gmail.googleapis.com iamcredentials.googleapis.com \
  sts.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com firebaserules.googleapis.com \
  identitytoolkit.googleapis.com

step "Creating Firestore database (Native mode, $REGION)"
if gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  echo "already exists"
else
  gcloud firestore databases create --location="$REGION" --type=firestore-native
fi

step "Granting the Cloud Run runtime account access to Gemini and Firestore"
RUNTIME_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
for role in roles/aiplatform.user roles/datastore.user; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$RUNTIME_SA" \
    --role="$role" --condition=None >/dev/null
done

step "Creating the GitHub deploy service account"
DEPLOYER="github-deployer@$PROJECT.iam.gserviceaccount.com"
gcloud iam service-accounts describe "$DEPLOYER" >/dev/null 2>&1 \
  || gcloud iam service-accounts create github-deployer --display-name="GitHub deployer"
for role in roles/run.admin roles/iam.serviceAccountUser roles/cloudbuild.builds.editor \
  roles/artifactregistry.admin roles/storage.admin roles/serviceusage.serviceUsageConsumer \
  roles/firebasehosting.admin roles/firebaserules.admin roles/datastore.indexAdmin roles/logging.viewer; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$DEPLOYER" \
    --role="$role" --condition=None >/dev/null
done

step "Letting GitHub Actions in $REPO act as that account (no keys)"
gcloud iam workload-identity-pools describe github --location=global >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools create github --location=global --display-name="GitHub"
gcloud iam workload-identity-pools providers describe github-repo --location=global \
  --workload-identity-pool=github >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools providers create-oidc github-repo --location=global \
    --workload-identity-pool=github --issuer-uri=https://token.actions.githubusercontent.com \
    --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository \
    --attribute-condition="assertion.repository=='$REPO'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO" \
  >/dev/null

step "Adding Firebase to the project and creating the web app"
npx --yes firebase-tools@15 projects:addfirebase "$PROJECT" 2>/dev/null || echo "Firebase already enabled"
APP_ID=$(npx --yes firebase-tools@15 apps:list WEB --project "$PROJECT" --json \
  | python3 -c 'import json,sys; a=json.load(sys.stdin)["result"]; print(a[0]["appId"] if a else "")')
if [ -z "$APP_ID" ]; then
  npx --yes firebase-tools@15 apps:create WEB cartpilot-web --project "$PROJECT" >/dev/null
  APP_ID=$(npx --yes firebase-tools@15 apps:list WEB --project "$PROJECT" --json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"][0]["appId"])')
fi
SDK=$(npx --yes firebase-tools@15 apps:sdkconfig WEB "$APP_ID" --project "$PROJECT" --json)
cfg() { python3 -c "import json,sys; print(json.loads(sys.argv[1])['result']['sdkConfig'].get(sys.argv[2],''))" "$SDK" "$1"; }

cat <<OUT

==> Done. Paste everything below into the thread with Claude (none of it is secret):

GCP_PROJECT_ID=$PROJECT
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-repo
GCP_DEPLOY_SERVICE_ACCOUNT=$DEPLOYER
ALLOWED_ORIGINS=https://$PROJECT.web.app,https://$PROJECT.firebaseapp.com,http://localhost:5173
VITE_FIREBASE_API_KEY=$(cfg apiKey)
VITE_FIREBASE_AUTH_DOMAIN=$(cfg authDomain)
VITE_FIREBASE_PROJECT_ID=$(cfg projectId)
VITE_FIREBASE_STORAGE_BUCKET=$(cfg storageBucket)
VITE_FIREBASE_MESSAGING_SENDER_ID=$(cfg messagingSenderId)
VITE_FIREBASE_APP_ID=$(cfg appId)
OUT
