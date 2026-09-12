# Where the data lives

Accounts, execution results, tester verdicts, defects and the session-signing
secret all live in one database. Which database depends on one environment
variable:

| `DATABASE_URL` | Backend | Survives a redeploy? |
|---|---|---|
| unset | SQLite file at `QTCAP_DB_PATH` (default `data/lab.sqlite3`) | On your laptop, yes. On a free hosting tier, **no** |
| `postgres://…` | PostgreSQL | Yes |

## Why a file is not enough when hosted

A Render free web service has **no persistent disk** — the filesystem is part of
the container, and a redeploy, a crash or a spin-down replaces the container.
The SQLite file goes with it, and so does every account, every result and every
defect the class raised. That is a property of the hosting rather than a bug
here, but "re-register after every deploy" is not something to ask a class to
live with.

Set `DATABASE_URL` and the same code writes to Postgres instead. Nothing else
changes: no migration step, no ORM, no second code path to test — the schema is
created on first use against whichever backend is configured, and
`tests/test_lab.py` runs its whole suite against both.

## Which Postgres

**Neon free tier** is the recommendation: it is permanent, needs no card, and
gives 0.5 GB per project — several orders of magnitude more than a class of
forty produces in a term.

**Render's own free Postgres expires 30 days after it is created** and is then
deleted. It works, and it is one click from the service, but put a reminder in
your calendar or the class loses its data on day 31. Supabase, Railway and any
other Postgres connection string work equally well.

## Setting it up (Neon, about three minutes)

1. Sign up at **neon.tech** and create a project. Pick the region nearest the
   service — Singapore for the Render config in this repo.
2. On the project dashboard, copy the **connection string**. It looks like:

   ```
   postgresql://user:password@ep-something-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

3. In **Render → your service → Environment**, add:

   ```
   DATABASE_URL = <the connection string>
   ```

4. **Save** — Render redeploys automatically. The schema is created on the first
   request that touches it.

Verify from anywhere:

```
curl -s https://capitalmarket.genaitesting.online/api/health | python -m json.tool
```

```json
{
  "storage": {"backend": "postgres", "location": "ep-….neon.tech", "persistent": true},
  "storage_durable": true
}
```

`"backend": "sqlite"` means the variable did not reach the process — check for a
typo in the key name, and that the deploy that followed the change actually
finished.

## The session secret

Session cookies are signed with a secret. In order of preference the app uses:

1. `QTCAP_SESSION_SECRET`, if you set one.
2. A secret generated once and stored in the database. With Postgres configured
   this is durable, so **a redeploy no longer signs the class out** and you do
   not need to set anything.
3. A per-process random secret, when there is no durable store. Correct but
   forgetful — sessions end with the process.

`/api/auth/config` reports which of these is in force as
`sessions_survive_restart`.

## Local development

Do nothing. With `DATABASE_URL` unset you get the SQLite file, which is the
right answer on a laptop — no server to run, and `rm data/lab.sqlite3` is a
clean slate.

To exercise the Postgres path locally:

```bash
export DATABASE_URL=postgresql://localhost:5432/qtcap
pytest tests/test_lab.py -q
```

`tests/test_lab.py` also runs every case against both backends in one go when
`QTCAP_TEST_POSTGRES` points at a database:

```bash
QTCAP_TEST_POSTGRES=postgresql://localhost:5432/qtcap pytest tests/test_lab.py -q
```

Without it the Postgres half is skipped rather than failing, so CI on a machine
with no database still passes honestly.

## What the dialect layer does

`app/db.py` is small on purpose — four tables do not need an ORM. It handles
exactly three differences and nothing else:

* **Placeholders.** Queries are written in SQLite's style (`?`, `:name`) and
  rewritten to psycopg's (`%s`, `%(name)s`) on the way out.
* **Types.** `REAL` in the schema becomes `DOUBLE PRECISION` on Postgres.
  SQLite's `REAL` is 64-bit; Postgres's is 32-bit, which rounds a Unix timestamp
  to the nearest few minutes and produces a defect that surfaces a month later
  as "why is everything timestamped the same?".
* **Rows.** Both backends hand back mappings, so calling code never learns which
  one it is talking to.

`sslmode=require` is appended to any URL that does not already carry it, because
managed Postgres needs TLS and the common copy-paste mistake is a URL without
it.

## Backups

There are none, deliberately. The lab's export buttons — **Report (markdown)**
and **Results (CSV)** in My Account — are the retention story, and a class
should download theirs before the session ends. If you want more than that,
`pg_dump` against the same `DATABASE_URL` is the whole answer.
