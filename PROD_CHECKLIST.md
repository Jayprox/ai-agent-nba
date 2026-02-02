# PROD CHECKLIST — AI Agent NBA (Minimal)

Use this after deploys or when “prod feels broken”.

## 1) Backend up?
```bash
curl -sS https://nba-backend.nicesand-609e915a.eastus.azurecontainerapps.io/health | jq
