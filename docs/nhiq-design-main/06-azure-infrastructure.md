# 06 — Azure Infrastructure

> **Claude instructions:** This document covers all Azure resource provisioning using the Azure CLI. Run commands in order. All resources go into the same resource group. Bicep files go in `infra/bicep/`.

---

## Resource Map

| Resource | Name Convention | Purpose |
|---|---|---|
| Resource Group | `neighborhoodiq-rg` | Container for all resources |
| Container Registry | `neighborhoodiqacr` | Docker image storage |
| Container Apps Environment | `niq-env` | Shared networking for all containers |
| Container App — Web | `niq-web` | Next.js frontend |
| Container App — API | `niq-api` | FastAPI backend |
| Container Apps Job — Workers | `niq-worker-*` | Scheduled ingestion jobs |
| PostgreSQL Flexible Server | `niq-postgres` | Primary database |
| Azure Cache for Redis | `niq-redis` | Score cache |
| Blob Storage Account | `niqstorage` | PDF exports |
| Key Vault | `niq-keyvault` | Runtime secrets |
| Front Door | `niq-frontdoor` | CDN, WAF, routing |
| Log Analytics Workspace | `niq-logs` | Centralized logging |

---

## Step 1: Prerequisites

```bash
# Install Azure CLI if not already installed
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"

# Install Container Apps extension
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

---

## Step 2: Resource Group & Core Services

```bash
LOCATION="eastus"
RG="neighborhoodiq-rg"
ACR_NAME="neighborhoodiqacr"

# Resource group
az group create --name $RG --location $LOCATION

# Container Registry (Basic tier — upgrade to Standard for geo-replication later)
az acr create \
  --resource-group $RG \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get ACR credentials (save these as GitHub secrets)
az acr credential show --name $ACR_NAME --resource-group $RG
```

---

## Step 3: Log Analytics (Required for Container Apps)

```bash
LOG_WORKSPACE="niq-logs"

az monitor log-analytics workspace create \
  --resource-group $RG \
  --workspace-name $LOG_WORKSPACE \
  --location $LOCATION

# Get workspace ID and key
LOG_WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group $RG \
  --workspace-name $LOG_WORKSPACE \
  --query customerId -o tsv)

LOG_WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group $RG \
  --workspace-name $LOG_WORKSPACE \
  --query primarySharedKey -o tsv)
```

---

## Step 4: Container Apps Environment

```bash
CA_ENV="niq-env"

az containerapp env create \
  --name $CA_ENV \
  --resource-group $RG \
  --location $LOCATION \
  --logs-workspace-id $LOG_WORKSPACE_ID \
  --logs-workspace-key $LOG_WORKSPACE_KEY
```

---

## Step 5: PostgreSQL Flexible Server

```bash
PG_SERVER="niq-postgres"
PG_ADMIN_USER="niqadmin"
PG_ADMIN_PASSWORD="<STRONG_PASSWORD_HERE>"   # Store in Key Vault after creation
PG_DB="neighborhoodiq"

az postgres flexible-server create \
  --resource-group $RG \
  --name $PG_SERVER \
  --location $LOCATION \
  --admin-user $PG_ADMIN_USER \
  --admin-password $PG_ADMIN_PASSWORD \
  --sku-name Standard_B2ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --yes

# Create the database
az postgres flexible-server db create \
  --resource-group $RG \
  --server-name $PG_SERVER \
  --database-name $PG_DB

# Install PostGIS extension
az postgres flexible-server execute \
  --name $PG_SERVER \
  --resource-group $RG \
  --database-name $PG_DB \
  --admin-user $PG_ADMIN_USER \
  --admin-password $PG_ADMIN_PASSWORD \
  --querytext "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS uuid-ossp;"

# Allow Container Apps environment to connect (firewall rule)
az postgres flexible-server firewall-rule create \
  --resource-group $RG \
  --name $PG_SERVER \
  --rule-name AllowContainerApps \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0    # Replace with actual Container Apps outbound IPs in prod
```

---

## Step 6: Azure Cache for Redis

```bash
REDIS_NAME="niq-redis"

az redis create \
  --resource-group $RG \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Basic \
  --vm-size c0

# Get connection string
REDIS_KEY=$(az redis list-keys \
  --resource-group $RG \
  --name $REDIS_NAME \
  --query primaryKey -o tsv)

REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_NAME}.redis.cache.windows.net:6380"
```

---

## Step 7: Blob Storage (PDF Reports)

```bash
STORAGE_ACCOUNT="niqstorage$(date +%s | tail -c 5)"  # Must be globally unique

az storage account create \
  --resource-group $RG \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

az storage container create \
  --account-name $STORAGE_ACCOUNT \
  --name reports \
  --public-access off

STORAGE_CONNECTION=$(az storage account show-connection-string \
  --resource-group $RG \
  --name $STORAGE_ACCOUNT \
  --query connectionString -o tsv)
```

---

## Step 8: Key Vault

```bash
KV_NAME="niq-keyvault"

az keyvault create \
  --resource-group $RG \
  --name $KV_NAME \
  --location $LOCATION \
  --sku standard

# Store all secrets
az keyvault secret set --vault-name $KV_NAME --name "DATABASE-URL" \
  --value "postgresql://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_SERVER}.postgres.database.azure.com:5432/${PG_DB}?sslmode=require"

az keyvault secret set --vault-name $KV_NAME --name "REDIS-URL" --value $REDIS_URL
az keyvault secret set --vault-name $KV_NAME --name "ANTHROPIC-API-KEY" --value "<YOUR_KEY>"
az keyvault secret set --vault-name $KV_NAME --name "MAPBOX-TOKEN" --value "<YOUR_KEY>"
az keyvault secret set --vault-name $KV_NAME --name "NEXTAUTH-SECRET" --value "$(openssl rand -hex 32)"
az keyvault secret set --vault-name $KV_NAME --name "AZURE-STORAGE-CONNECTION-STRING" --value $STORAGE_CONNECTION
```

---

## Step 9: Deploy API Container App

```bash
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RG --query loginServer -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --resource-group $RG --query passwords[0].value -o tsv)

az containerapp create \
  --name niq-api \
  --resource-group $RG \
  --environment $CA_ENV \
  --image "${ACR_LOGIN_SERVER}/neighborhoodiq-api:latest" \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 5 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars \
    "DATABASE_URL=secretref:database-url" \
    "REDIS_URL=secretref:redis-url" \
    "ANTHROPIC_API_KEY=secretref:anthropic-api-key" \
    "MAPBOX_TOKEN=secretref:mapbox-token" \
    "ENVIRONMENT=production" \
    "LOG_LEVEL=WARNING" \
  --secrets \
    "database-url=$(az keyvault secret show --vault-name $KV_NAME --name DATABASE-URL --query value -o tsv)" \
    "redis-url=$(az keyvault secret show --vault-name $KV_NAME --name REDIS-URL --query value -o tsv)" \
    "anthropic-api-key=$(az keyvault secret show --vault-name $KV_NAME --name ANTHROPIC-API-KEY --query value -o tsv)" \
    "mapbox-token=$(az keyvault secret show --vault-name $KV_NAME --name MAPBOX-TOKEN --query value -o tsv)"
```

---

## Step 10: Deploy Web Container App

```bash
API_FQDN=$(az containerapp show \
  --name niq-api \
  --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

az containerapp create \
  --name niq-web \
  --resource-group $RG \
  --environment $CA_ENV \
  --image "${ACR_LOGIN_SERVER}/neighborhoodiq-web:latest" \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port 3000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 5 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars \
    "NEXT_PUBLIC_API_URL=https://${API_FQDN}" \
    "NEXTAUTH_URL=https://nh-iq.com" \
    "NEXTAUTH_SECRET=secretref:nextauth-secret" \
  --secrets \
    "nextauth-secret=$(az keyvault secret show --vault-name $KV_NAME --name NEXTAUTH-SECRET --query value -o tsv)"
```

---

## Step 11: Worker Container Apps Jobs

```bash
# One job per data source — runs on schedule
az containerapp job create \
  --name niq-worker-epa \
  --resource-group $RG \
  --environment $CA_ENV \
  --image "${ACR_LOGIN_SERVER}/neighborhoodiq-worker:latest" \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --trigger-type Schedule \
  --cron-expression "0 2 * * *" \
  --replica-timeout 3600 \
  --replica-retry-limit 2 \
  --cpu 1 \
  --memory 2Gi \
  --command "python" "-m" "ingest.epa.run" \
  --env-vars \
    "DATABASE_URL=secretref:database-url" \
    "EPA_AQS_EMAIL=<email>" \
    "EPA_AQS_KEY=secretref:epa-key" \
  --secrets \
    "database-url=$(az keyvault secret show --vault-name $KV_NAME --name DATABASE-URL --query value -o tsv)"
```

---

## Step 12: Azure Front Door

```bash
FD_PROFILE="niq-frontdoor"

az afd profile create \
  --profile-name $FD_PROFILE \
  --resource-group $RG \
  --sku Standard_AzureFrontDoor

# Add origin groups and routes for web and API
# (Full Bicep template recommended for this — see infra/bicep/frontdoor.bicep)
```

For routing rules:
- `/api/v1/*` → forwards to `niq-api` Container App
- `/*` → forwards to `niq-web` Container App

---

## Scaling Configuration

| Container App | Min Replicas | Max Replicas | Scale Trigger |
|---|---|---|---|
| `niq-web` | 0 | 5 | HTTP concurrency > 10 |
| `niq-api` | 0 | 10 | HTTP concurrency > 20 |
| `niq-worker-*` | N/A | 1 | Schedule / manual |

Scale to zero means **$0 cost when idle** — critical for early stage.

---

## Cost Estimate (Early Stage, Low Traffic)

| Resource | Monthly Cost |
|---|---|
| Container Apps (scale to zero, <1M req) | ~$5–20 |
| PostgreSQL Flexible (Burstable B2ms) | ~$35 |
| Azure Cache for Redis (Basic C0) | ~$16 |
| Blob Storage | ~$1 |
| Container Registry (Basic) | ~$5 |
| Front Door (Standard) | ~$35 |
| Log Analytics | ~$0–5 |
| **Total** | **~$100–120/month** |

Upgrade PostgreSQL to General Purpose and Redis to Standard when MRR > $5K.

---

## Checklist

- [ ] Resource group created
- [ ] ACR created, credentials saved as GitHub secrets
- [ ] Container Apps environment created
- [ ] PostgreSQL created with PostGIS extension
- [ ] Redis created
- [ ] Blob storage created with `reports` container
- [ ] Key Vault created with all secrets
- [ ] API Container App deployed and healthy
- [ ] Web Container App deployed and healthy
- [ ] At least one worker job created
- [ ] Front Door routing `/api/v1/*` and `/*` correctly
- [ ] Custom domain configured (optional at launch)
