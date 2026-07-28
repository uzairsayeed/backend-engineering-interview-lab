# V3 Concept Notes

An interactive glossary of the database, SQLAlchemy, transaction, dependency,
and migration concepts introduced in TinyURL V3.

## Quick navigation

- [Database foundations](#database-foundations)
- [SQLAlchemy infrastructure](#sqlalchemy-infrastructure)
- [Models, mapping, and constraints](#models-mapping-and-constraints)
- [Repository and dependency boundaries](#repository-and-dependency-boundaries)
- [Transactions and persistence operations](#transactions-and-persistence-operations)
- [Alembic and schema evolution](#alembic-and-schema-evolution)

---

## Database foundations

<details open>
<summary><strong>Relational database</strong></summary>

Stores data in structured tables consisting of rows and columns.

</details>

<details>
<summary><strong>Primary key</strong></summary>

A non-null unique identifier for a database row.

```text
short_urls.id
```

</details>

<details>
<summary><strong>Surrogate key</strong></summary>

An internal identifier with no direct business meaning.

```text
id = 42
```

</details>

<details>
<summary><strong>Natural or business key</strong></summary>

A meaningful identifier from the application domain.

```text
short_code = "python"
```

</details>

<details>
<summary><strong>Unique constraint</strong></summary>

A database rule preventing duplicate values.

</details>

<details>
<summary><strong>Check constraint</strong></summary>

A database rule requiring a condition to remain true.

```text
redirect_count >= 0
```

</details>

<details>
<summary><strong>Nullability</strong></summary>

Whether a database column may contain `NULL`.

</details>

<details>
<summary><strong>Integrity error</strong></summary>

A database-reported violation of a relational constraint.

</details>

## SQLAlchemy infrastructure

<details open>
<summary><strong>ORM</strong></summary>

Maps Python classes and objects to relational database tables and rows.

```text
Python class → table
Python object → row
Attribute → column
```

</details>

<details>
<summary><strong>Engine</strong></summary>

Long-lived SQLAlchemy object managing database connectivity, dialect behaviour,
and connection pooling.

</details>

<details>
<summary><strong>Connection</strong></summary>

One active communication channel checked out from the engine.

</details>

<details>
<summary><strong>Session</strong></summary>

ORM unit of work that tracks objects and coordinates queries and database
changes.

</details>

<details>
<summary><strong>Session factory</strong></summary>

Callable configuration used to create independent session objects.

</details>

<details>
<summary><strong>Dialect</strong></summary>

SQLAlchemy component that understands a particular database’s SQL and
behaviour.

Examples:

- SQLite dialect
- PostgreSQL dialect
- MySQL dialect

</details>

<details>
<summary><strong>Connection pool</strong></summary>

A collection of reusable database connections managed by the engine.

</details>

<details>
<summary><strong>Connection-pool disposal</strong></summary>

Closing checked-in pooled connections and replacing the current pool.

</details>

<details>
<summary><strong>Declarative mapping</strong></summary>

Defining an ORM class and its table structure together using Python class
declarations.

</details>

<details>
<summary><strong>Database metadata</strong></summary>

SQLAlchemy’s collection of table, column, and constraint definitions.

```python
Base.metadata
```

</details>

<details>
<summary><strong>ORM identity map</strong></summary>

The session mechanism that associates a database row’s primary key with one ORM
object instance.

</details>

<details>
<summary><strong>Scalar result</strong></summary>

A query result containing one selected value or one ORM entity rather than a
full row tuple.

</details>

## Models, mapping, and constraints

<details open>
<summary><strong>Persistence model</strong></summary>

A class representing how application data is stored in a database.

</details>

<details>
<summary><strong>Persistence mapper</strong></summary>

Converts domain objects into ORM records and reconstructs domain objects from
ORM records.

</details>

<details>
<summary><strong>Detached domain object</strong></summary>

A normal domain object reconstructed from persistence but not automatically
tracked by the ORM.

</details>

<details>
<summary><strong>Structural typing</strong></summary>

A class satisfies an interface by implementing the required methods, without
explicitly inheriting from it.

</details>

## Repository and dependency boundaries

<details open>
<summary><strong>Structural repository contract</strong></summary>

The set of operations that any storage implementation must provide to the
service.

</details>

<details>
<summary><strong>Request-scoped dependency</strong></summary>

A dependency created for one request and released when that request’s work
finishes.

</details>

<details>
<summary><strong>Dependency scope</strong></summary>

Controls when a FastAPI yield dependency enters and exits.

```text
function scope:
    exits before response is sent

request scope:
    exits after response is sent
```

</details>

## Transactions and persistence operations

<details open>
<summary><strong>Transaction</strong></summary>

A group of database operations that succeed or fail together.

```text
Begin
    ↓
Database operations
    ↓
Commit

or:

Begin
    ↓
Failure
    ↓
Rollback
```

</details>

<details>
<summary><strong>Transaction boundary</strong></summary>

The point defining which operations commit or roll back together.

</details>

<details>
<summary><strong>Flush</strong></summary>

Sends pending SQL changes to the database within the current transaction.

</details>

<details>
<summary><strong>Commit</strong></summary>

Permanently completes the current transaction.

</details>

<details>
<summary><strong>Rollback</strong></summary>

Discards the current transaction’s changes.

</details>

<details>
<summary><strong>Savepoint</strong></summary>

A recoverable checkpoint inside a larger transaction.

```text
Transaction
    ├── Savepoint
    │      └── Failed INSERT
    │
    └── Continue transaction
```

</details>

<details>
<summary><strong>Atomic update</strong></summary>

A change performed by the database as one indivisible statement.

```sql
redirect_count = redirect_count + 1
```

</details>

## Alembic and schema evolution

<details open>
<summary><strong>Database migration</strong></summary>

A versioned operation that changes a database schema.

</details>

<details>
<summary><strong>Revision</strong></summary>

One migration file identified by a unique revision ID.

</details>

<details>
<summary><strong>Head</strong></summary>

The latest revision in a migration branch.

</details>

<details>
<summary><strong>Upgrade</strong></summary>

Moves a database forward to a newer revision.

```bash
alembic upgrade head
```

</details>

<details>
<summary><strong>Downgrade</strong></summary>

Moves a database backwards to an older revision.

```bash
alembic downgrade -1
```

</details>

<details>
<summary><strong>Autogenerate</strong></summary>

Compares SQLAlchemy metadata with the current database and generates candidate
migration operations.

</details>

<details>
<summary><strong>Migration history</strong></summary>

The ordered chain of schema revisions.

```text
base
  ↓
revision 1
  ↓
revision 2
  ↓
head
```

</details>

<details open>
<summary><strong>Schema ownership in V3</strong></summary>

Schema ownership is the component responsible for creating and evolving
database structure.

For V3:

- Alembic owns schema evolution.
- FastAPI owns request processing.
- SQLAlchemy ORM describes the intended schema.

</details>
