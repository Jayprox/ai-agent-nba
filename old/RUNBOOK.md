# RUNBOOK — AI Agent NBA (Production)

## Production URLs
- Frontend (Azure Static Web Apps): https://lemon-bay-0ddcff40f.1.azurestaticapps.net
- Backend (Azure Container Apps): https://nba-backend.nicesand-609e915a.eastus.azurecontainerapps.io

## Required Environment Variables (Backend)
- OPENAI_API_KEY
- ODDS_API_KEY
- API_SPORTS_KEY
- TZ=America/Los_Angeles
- ALLOWED_ORIGINS=https://lemon-bay-0ddcff40f.1.azurestaticapps.net

## Required Environment Variables (Frontend / SWA)
- VITE_API_BASE_URL=https://nba-backend.nicesand-609e915a.eastus.azurecontainerapps.io

## Smoke Tests

### 1) Health
```bash
curl -sS https://nba-backend.nicesand-609e915a.eastus.azurecontainerapps.io/health | jq
