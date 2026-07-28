from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.config import get_settings

settings = get_settings()

# The engine is the application’s main entry point to the database.
# Conceptually:
    # Application
    #     ↓
    # Engine
    #     ├── Database dialect
    #     ├── Connection pool
    #     └── Database driver
# The engine should be long-lived:
    # One engine per application process
# Engine creation is lazy:
    # The below code - configures the engine but does not necessarily prove that the database is reachable.
    # A real connection is normally obtained only when something such as:
    # engine.connect() or a session first requires connectivity.
engine: Engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
)

# Session
    # A SQLAlchemy Session is the main ORM persistence interface. 
    # It tracks loaded and changed ORM objects and coordinates their database work through the engine.

    # Conceptually:
        # Session
        # ├── Tracks ORM objects
        # ├── Issues queries
        # ├── Adds and deletes records
        # ├── Flushes changes
        # └── Coordinates transactions

    # A session is not the same thing as the engine:
        # Engine
        #     Long-lived database infrastructure

        # Session
        #     Short-lived unit of database work

    # sessionmaker does not create one global session. It creates a factory that can produce sessions when required.
    # Conceptually:
        # SessionFactory
        #     ↓ call
        # Session A

        # SessionFactory
        #     ↓ call again
        # Session B
    # SQLAlchemy documents sessionmaker as the usual factory for creating Session objects bound to an application-level engine.

    # Why not create one global session?
        # Avoid:
            # session = SessionFactory()
            # at module scope and then reuse it for every request.
        # A session represents a unit of work and transaction state. Reusing one session across unrelated requests could cause:
            # Transaction leakage
            # Stale ORM objects
            # One request affecting another
            # Rollback confusion
            # Unsafe concurrent access

    # FastAPI dependency flow:
        # Request begins
        #     ↓
        # Create Session
        #     ↓
        # Repository work
        #     ↓
        # Commit or rollback
        #     ↓
        # Close Session
        #     ↓
        # Request ends

SessionFactory = sessionmaker(
    bind=engine,
    class_=Session,
    # Why autoflush=False?
        # By default, SQLAlchemy can flush pending changes before certain queries.
        # For this learning project, we choose:
            # autoflush=False
            # This makes database writes more explicit:
                # Add object
                #     ↓
                # Explicit flush or commit
        # Trade-off:
            # With autoflush disabled, developers must remember that an unflushed object may not yet appear in database queries.
            # This is not universally “better”; it is a predictability choice for our repository implementation.
    autoflush=False,
    # Why expire_on_commit=False?
        # By default, SQLAlchemy can expire ORM objects after a commit.So they are refreshed from the database when next accessed.
    # Trade-off:
        # The object may no longer automatically reflect a concurrent database update made after the commit.
        # For our short request/repository operations, this is acceptable.
    expire_on_commit=False,
)


# A connection represents one checked-out database connection.
    # Engine
    #     owns/manages pool

    # Connection
    #     temporarily checked out from engine
def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

# Engine.dispose() disposes the existing connection pool and closes checked-in connections; 
# the engine can still create a new pool later if reused.
def dispose_database() -> None:
    engine.dispose()