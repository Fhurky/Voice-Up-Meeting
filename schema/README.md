# Persistence

schema/profile.yml records the fixed authority and migration adapter. PostgreSQL is the only storage
engine; SQLAlchemy models own desired state and Alembic owns migration history.

PGVector is available only as an accepted-PRD capability inside that same PostgreSQL database. The
platform image supplies the admitted extension binary and a reviewed Alembic migration enables SQL
extension `vector`; application startup never installs or enables it. Embedding generation stays
behind an application port and approved infrastructure adapter. See
`rules/46-vector-embedding-boundary.md` for the data, tenant, model-version and retrieval contract.

~~~sh
scripts/db.sh generate <migration-name>
scripts/db.sh apply
scripts/db.sh status
scripts/db.sh validate
~~~

Never hand-author a migration as a substitute for changing the recorded schema authority. Review
generated migrations before applying them.
