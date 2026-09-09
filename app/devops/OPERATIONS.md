# Operations

## Install order

1. Run `python3 scripts/check-dependency-admission.py` and archive its reviewed inventory digest.
   For a release review, also run `scripts/security-gate.sh` with the admitted scanner snapshot.
2. Create namespace and referenced Secrets through the bank's approved secret workflow. Populate
   the backend Secret from the prefixed runtime-key inventory in `app/backend/.env.example`; never
   copy the example values. Run `python3 scripts/check-config-sync.py` before rendering.
3. Promote every reviewed OCI index from the offline bundle to the internal registry without
   changing its digest, then fill one environment overlay with those digests and the exact full
   lowercase source revision being promoted.
4. Run `scripts/render-charts.sh --environment-ready <environment>` and archive its evidence.
5. Install PostgreSQL and Redis.
6. Run the immutable migration Job for the source revision.
7. Install backend, frontend and workers.
8. Install optional observability.

Rollback application releases without rolling schema backward. Restore PostgreSQL into an isolated
claim, validate it, then perform a separately approved cutover. Rotate Secrets by creating a new
version, rolling consumers and removing the old version only after verification.
