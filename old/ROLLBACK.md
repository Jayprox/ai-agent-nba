# ROLLBACK — AI Agent NBA

## 🔥 90-second Production Sanity Checks (copy/paste)

## Goal
Return production to a known-good state quickly if a deploy breaks prod.

## Known-good reference
- Tag: prod-gold-2026-02-02

## Rollback options

### Option 1 (fastest): revert Git commit(s) and let CI redeploy
1) Find the bad commit(s):
```bash
git log --oneline --decorate -n 20
