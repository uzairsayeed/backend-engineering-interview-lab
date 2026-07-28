# TinyURL V3 Design Decisions

An interactive record of the trade-offs behind TinyURL V3’s persistence,
transaction, dependency, testing, and migration design.

## Quick navigation

- [Database infrastructure](#database-infrastructure)
- [Persistence modelling](#persistence-modelling)
- [Repository implementation](#repository-implementation)
- [Request transactions](#request-transactions)
- [Database migrations](#database-migrations)

> Expand any decision to compare its naïve, production-grade, and
> interview-optimised approaches.

---

<a id="database-infrastructure"></a>

## Database infrastructure (Decisions 1–6)

<details open>
<summary><strong>V3 Decision 1: Use SQLAlchemy directly</strong></summary>

- **Naïve:** Use raw SQLite statements throughout the application.
- **Production-grade:** Choose SQLAlchemy Core, ORM, or another persistence
  approach based on workload and team standards.
- **Interview-optimised:** Use SQLAlchemy ORM directly.
- **Why:** It exposes the important persistence concepts while preserving
  repository boundaries.

</details>

<details>
<summary><strong>V3 Decision 2: Begin with SQLite</strong></summary>

- **Naïve:** Hardcode a local SQLite path everywhere.
- **Production-grade:** Use PostgreSQL or another production database with
  managed credentials and tuned pooling.
- **Interview-optimised:** Use configured SQLite locally.
- **Why:** It requires no external server and keeps attention on ORM and
  transaction concepts.
- **Revisit:** The database URL can later point to PostgreSQL.

</details>

<details>
<summary><strong>V3 Decision 3: One engine per process</strong></summary>

- **Naïve:** Create an engine for each operation.
- **Production-grade:** Configure application-level engines and connection
  pools with observability and lifecycle management.
- **Interview-optimised:** Create one module-level engine.
- **Why:** The engine represents long-lived database infrastructure.

</details>

<details>
<summary><strong>V3 Decision 4: Use a session factory, not a global session</strong></summary>

- **Naïve:** Reuse one session for all requests.
- **Production-grade:** Manage request or use-case-scoped sessions through a
  dependency container or unit-of-work abstraction.
- **Interview-optimised:** Create one `SessionFactory` and later create one
  session per request.
- **Why:** Transaction state must not leak between requests.

</details>

<details>
<summary><strong>V3 Decision 5: Do not connect the repository yet</strong></summary>

- **Naïve:** Replace every storage operation in one large change.
- **Production-grade:** Use controlled migrations, feature flags, and gradual
  rollout.
- **Interview-optimised:** Establish and verify database infrastructure before
  adding mappings and repository logic.
- **Why:** Smaller changes are easier to understand and debug.

</details>

<details>
<summary><strong>V3 Decision 6: No new tests in Module 1</strong></summary>

- **Naïve:** Skip all verification.
- **Production-grade:** Add configuration, connectivity, pool, and failure
  integration tests.
- **Interview-optimised:** Run a direct connection smoke check.
- **Why:** The V3 test budget is intentionally reserved for two high-value
  integration tests after persistence is implemented.

> “I kept the SQLAlchemy entity separate from the domain dataclass.
> The ORM entity reflects storage structure, including its internal primary
> key, while the domain object owns expiration and redirect behaviour.”

```text
ShortUrlRecord
    ↓ mapper
ShortUrl
    ↓ domain behaviour
ShortUrlRecord
    ↓ persistence
```

</details>

<a id="persistence-modelling"></a>

## Persistence modelling (Decisions 7–13)

<details open>
<summary><strong>V3 Decision 7: Separate domain and persistence models</strong></summary>

- **Naïve:** Reuse one class for API, domain, and database.
- **Production-grade:** Maintain explicit boundary models and mapping rules.
- **Interview-optimised:** Keep `ShortUrl` and `ShortUrlRecord` separate.
- **Why:** The database has an internal ID and persistence concerns that should
  not leak into the domain or API.

</details>

<details>
<summary><strong>V3 Decision 8: Use a surrogate integer primary key</strong></summary>

- **Naïve:** Make `short_code` the primary key without discussing the trade-off.
- **Production-grade:** Select natural or surrogate keys based on lifecycle and
  relationships.
- **Interview-optimised:** Use `id` as the database primary key and `short_code`
  as a unique business key.
- **Why:** It separates internal row identity from the public alias.

</details>

<details>
<summary><strong>V3 Decision 9: Enforce short-code uniqueness in the database</strong></summary>

- **Naïve:** Depend only on `repository.exists()`.
- **Production-grade:** Use a named database constraint and translate database
  conflicts.
- **Interview-optimised:** Add:

  ```python
  UniqueConstraint("short_code")
  ```

- **Why:** The database provides the final concurrency-safe guarantee.

</details>

<details>
<summary><strong>V3 Decision 10: Application-generated timestamps</strong></summary>

- **Naïve:** Mix application and database timestamps.
- **Production-grade:** Establish an organisation-wide timestamp and clock
  policy.
- **Interview-optimised:** Let the service generate both `created_at` and
  `expires_at`.
- **Why:** Existing injected-clock behaviour remains deterministic.

</details>

<details>
<summary><strong>V3 Decision 11: Keep redirect count non-negative</strong></summary>

- **Naïve:** Trust every application caller.
- **Production-grade:** Use constraints and atomic updates.
- **Interview-optimised:** Add a database check constraint.
- **Why:** Invalid negative analytics state is rejected at the persistence
  boundary.

</details>

<details>
<summary><strong>V3 Decision 12: Use Text for the destination</strong></summary>

- **Naïve:** Pick an arbitrary small string size.
- **Production-grade:** Define limits based on product and infrastructure
  requirements.
- **Interview-optimised:** Validate the URL in Pydantic and store it as `Text`.
- **Why:** Avoid accidental truncation while keeping validation at the HTTP
  boundary.

</details>

<details>
<summary><strong>V3 Decision 13: No persistence tests yet</strong></summary>

- **Chosen approach:** Manually create and inspect the table.
- **Why:** The two lean integration tests remain reserved for the completed
  database-backed workflow.

</details>

<a id="repository-implementation"></a>

## Repository implementation (Decisions 14–20)

<details open>
<summary><strong>V3 Decision 14: Introduce a repository protocol</strong></summary>

- **Naïve:** Type the service against the concrete dictionary repository.
- **Production-grade:** Define repository interfaces per bounded context.
- **Interview-optimised:** Use a Python `Protocol`.
- **Why:** Both in-memory and SQL repositories can satisfy the same service
  dependency.

</details>

<details>
<summary><strong>V3 Decision 15: Map domain and persistence objects explicitly</strong></summary>

- **Naïve:** Return ORM objects directly.
- **Production-grade:** Use dedicated mapping layers and possibly richer
  aggregate reconstruction.
- **Interview-optimised:** Add two small mapping functions.
- **Why:** ORM-specific fields and state do not leak into the service.

</details>

<details>
<summary><strong>V3 Decision 16: Inject sessions into SQL repositories</strong></summary>

- **Naïve:** Create a session inside every repository method.
- **Production-grade:** Use request-scoped units of work or transaction
  managers.
- **Interview-optimised:** Pass one request session into the repository
  constructor.
- **Why:** Session lifetime and transaction ownership remain visible.

</details>

<details>
<summary><strong>V3 Decision 17: Repositories flush but do not commit</strong></summary>

- **Naïve:** Commit in every repository method.
- **Production-grade:** Coordinate transactions around complete use cases.
- **Interview-optimised:** Repository methods call `flush()`; the request
  dependency will commit.
- **Why:** Several repository operations can eventually participate in one
  transaction.

</details>

<details>
<summary><strong>V3 Decision 18: Use a savepoint for retryable insertion</strong></summary>

- **Naïve:** Allow a duplicate flush to make the session unusable.
- **Production-grade:** Use a unit-of-work strategy, database-native upserts, or
  carefully scoped savepoints.
- **Interview-optimised:** Wrap each insert attempt in `begin_nested()`.
- **Why:** Generated aliases can retry after a unique conflict without losing
  the outer transaction.

</details>

<details>
<summary><strong>V3 Decision 19: Translate only the short-code uniqueness conflict</strong></summary>

- **Naïve:** Treat every `IntegrityError` as a duplicate alias.
- **Production-grade:** Inspect portable database diagnostics and repository
  error categories.
- **Interview-optimised:** Check the named constraint or SQLite’s
  column-specific message.
- **Why:** Other integrity failures should remain unexpected errors.

</details>

<details>
<summary><strong>V3 Decision 20: Keep testing manual in this module</strong></summary>

No new automated tests are added.

The manual checks prove:

- Persistence across sessions.
- Duplicate conflict translation.

The final two integration tests will be added after the API uses SQL storage.

</details>

<a id="request-transactions"></a>

## Request transactions (Decisions 21–27)

<details open>
<summary><strong>V3 Decision 21: One session per request</strong></summary>

- **Naïve:** Reuse a global session.
- **Production-grade:** Use explicit unit-of-work scopes based on use-case
  boundaries.
- **Interview-optimised:** Create one SQLAlchemy session per HTTP request.
- **Why:** Transaction and ORM state do not leak across concurrent requests.

</details>

<details>
<summary><strong>V3 Decision 22: Dependency owns the transaction</strong></summary>

- **Naïve:** Every repository method commits itself.
- **Production-grade:** Use a unit-of-work abstraction around complete business
  operations.
- **Interview-optimised:** The FastAPI session dependency commits or rolls back.
- **Why:** Repository operations can participate in the same transaction.

</details>

<details>
<summary><strong>V3 Decision 23: Commit before sending the response</strong></summary>

- **Naïve:** Commit after the client has already received success.
- **Production-grade:** Complete the transaction before acknowledging success.
- **Interview-optimised:** Use `Depends(..., scope="function")`.
- **Why:** Commit failures can still become proper `500` responses.

</details>

<details>
<summary><strong>V3 Decision 24: Create the service per request</strong></summary>

- **Naïve:** Keep one global service holding one global session.
- **Production-grade:** Build request/use-case scoped dependency graphs.
- **Interview-optimised:** Construct the service and SQL repository from the
  request session.
- **Why:** The service remains stateless while persistence state is
  request-scoped.

</details>

<details>
<summary><strong>V3 Decision 25: Persist redirect count through the repository</strong></summary>

- **Naïve:** Mutate a detached domain object and assume SQLAlchemy notices.
- **Production-grade:** Record analytics asynchronously or perform atomic
  database updates.
- **Interview-optimised:** Add an atomic repository increment operation.
- **Why:** The database—not a temporary Python object—must own the durable
  count.

</details>

<details>
<summary><strong>V3 Decision 26: Automatically create tables temporarily</strong></summary>

- **Naïve:** Require undocumented manual SQL.
- **Production-grade:** Run versioned migrations during deployment.
- **Interview-optimised:** Call `create_all()` during application startup for
  now.
- **Why:** The local application is immediately runnable.
- **Revisit:** Remove after Alembic becomes responsible for the schema.

</details>

<details>
<summary><strong>V3 Decision 27: Existing API tests remain in-memory</strong></summary>

**Why:** They already verify the HTTP contract.

The two future SQL integration tests will verify only the new risks:

- Persistence across sessions/restarts.
- Database uniqueness translation.

</details>

<a id="database-migrations"></a>

## Database migrations (Decisions 29–33)

<details open>
<summary><strong>V3 Decision 29: Use versioned migrations</strong></summary>

- **Naïve:** Depend on `create_all()` forever.
- **Production-grade:** Use controlled, reviewed, deployment-managed
  migrations.
- **Interview-optimised:** Add Alembic with one initial migration.
- **Why:** Schema changes become explicit, ordered, and reviewable.

</details>

<details>
<summary><strong>V3 Decision 30: Use the same database configuration</strong></summary>

- **Naïve:** Hardcode a separate URL in `alembic.ini`.
- **Production-grade:** Integrate with deployment configuration and secret
  management.
- **Interview-optimised:** Load `Settings.database_url` inside
  `migrations/env.py`.
- **Why:** The application and migration command target the same configured
  database.

</details>

<details>
<summary><strong>V3 Decision 31: Autogenerate, then review</strong></summary>

- **Naïve:** Apply generated migrations without inspection.
- **Production-grade:** Review, test, and validate migration scripts in CI and
  staging.
- **Interview-optimised:** Use `--autogenerate`, manually inspect `upgrade()`
  and `downgrade()`, then apply.
- **Why:** Autogeneration accelerates authoring but does not replace design
  judgement.

</details>

<details>
<summary><strong>V3 Decision 32: Alembic owns schema creation</strong></summary>

- **Naïve:** Run migrations and also retain startup `create_all()`.
- **Problem:** Two separate mechanisms appear responsible for the schema.
- **Chosen:** Remove `create_all()` from application startup.
- **Why:** Database evolution has one clear owner.

</details>

<details>
<summary><strong>V3 Decision 33: Tests may still use create_all()</strong></summary>

- **Why:** The two lean integration tests validate persistence behaviour, not
  the migration chain.
- **Trade-off:** They will not detect an incorrect Alembic script.
- **Future option:** Add one blank-database-to-head migration smoke test when
  deployment readiness matters.

</details>
