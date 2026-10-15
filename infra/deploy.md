# Deploying CartPilot

Backend: Cloud Run service `cartpilot-api` in `asia-south1`. Frontend: Firebase Hosting, which
rewrites `/api/**` to the Cloud Run service so the browser only ever talks to one origin.

## One-time Google Cloud setup

```bash
export PROJECT=cartpilot-demo          # your project id
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com firestore.googleapis.com gmail.googleapis.com \
  iamcredentials.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com

# Firestore (Native mode)
gcloud firestore databases create --location=asia-south1

# Let the Cloud Run runtime service account call Gemini and Firestore
PROJECT_NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
RUNTIME_SA=$PROJECT_NUMBER-compute@developer.gserviceaccount.com
for role in roles/aiplatform.user roles/datastore.user; do
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$RUNTIME_SA --role=$role
done
```

Then in the Firebase console: add the GCP project to Firebase, enable **Authentication → Google**, add a
**Web app** (its config goes in `frontend/.env.local` and the GitHub variables below), and put
`infra/.firebaserc`'s `default` to your project id.

## Manual deploy

```bash
cd backend
gcloud run deploy cartpilot-api --source . --region asia-south1 --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=$PROJECT,GOOGLE_CLOUD_LOCATION=asia-south1,GEMINI_MODEL=gemini-2.5-flash

cd ../frontend && npm ci && npm run build
cd ../infra && npx firebase-tools@15 deploy --only hosting,firestore:rules --project $PROJECT
```
`--allow-unauthenticated` is fine: the API verifies Firebase ID tokens itself.

## Continuous deployment (GitHub Actions, keyless)

`.github/workflows/deploy.yml` deploys after CI passes on `main` (or on demand from the Actions tab).
It signs in to Google Cloud with Workload Identity Federation, so no service-account key is stored in GitHub.

```bash
export REPO=<github-user>/<repo>       # e.g. WalterVetrivel/cartpilot

# 1. Deploy service account
gcloud iam service-accounts create github-deployer --display-name="GitHub deployer"
DEPLOYER=github-deployer@$PROJECT.iam.gserviceaccount.com
for role in roles/run.admin roles/iam.serviceAccountUser roles/cloudbuild.builds.editor \
  roles/artifactregistry.admin roles/storage.admin roles/serviceusage.serviceUsageConsumer \
  roles/firebasehosting.admin roles/firebaserules.admin roles/datastore.indexAdmin; do
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$DEPLOYER --role=$role
done

# 2. Workload Identity pool + GitHub provider, restricted to your repo
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc github-repo --location=global \
  --workload-identity-pool=github --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository \
  --attribute-condition="assertion.repository=='$REPO'"
gcloud iam service-accounts add-iam-policy-binding $DEPLOYER --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$REPO"

# Value for the GCP_WORKLOAD_IDENTITY_PROVIDER secret:
echo projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github-repo
```

In the GitHub repo, **Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
|---|---|---|
| Secret | `GCP_WORKLOAD_IDENTITY_PROVIDER` | the `projects/.../providers/github-repo` string above |
| Secret | `GCP_DEPLOY_SERVICE_ACCOUNT` | `github-deployer@<project>.iam.gserviceaccount.com` |
| Variable | `GCP_PROJECT_ID` | your project id |
| Variable | `ALLOWED_ORIGINS` | `https://<project>.web.app,http://localhost:5173` |
| Variable | `GEMINI_MODEL` (optional) | defaults to `gemini-2.5-flash` |
| Variable | `GCP_LOCATION` (optional) | defaults to `asia-south1` |
| Variables | `VITE_FIREBASE_*` (6 of them) | Firebase web app config (public values) |

## OAuth consent screen (Gmail)

Keep the app in **Testing** mode and add the team and judges as test users. Add the
`gmail.readonly` scope. No public verification is needed (SPEC §3 non-goals).
