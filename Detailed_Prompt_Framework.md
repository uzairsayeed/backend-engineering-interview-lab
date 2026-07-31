# AI-Assisted Backend Interview Prompt Framework

## Purpose

This playbook is designed for a **three-hour backend coding interview** where AI assistance—such as GitHub Copilot—is allowed.

The working assumption is:

```text
Total interview time: 180 minutes
Implementation time: 150 minutes
Review and code-review preparation: 30 minutes
```

The objective is not to build a production-complete platform. The objective is to deliver a solution that is:

```text
Complete enough to demonstrate the core requirements
Correct enough to survive review
Simple enough to explain confidently
Structured enough to evolve
```

The framework is written for a Python backend using:

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- SQLite
- Pydantic
- Alembic
- Pytest

The principles remain reusable for other stacks.

---

# 1. Core strategy

Use AI as a **fast implementation partner**, not as an autonomous architect.

```text
Requirements
    ↓
Clarify assumptions
    ↓
Create implementation plan
    ↓
Build a runnable skeleton
    ↓
Implement one vertical slice
    ↓
Complete remaining use cases
    ↓
Add one or two high-value tests
    ↓
Review and prepare explanations
```

Avoid asking AI to generate the complete project in one prompt.

A giant prompt such as:

> Build a production-grade background job scheduler with FastAPI, SQLAlchemy, Alembic, tests, retries, queues, authentication and observability.

commonly produces:

- Too many files
- Unnecessary abstractions
- Inconsistent implementation choices
- Partially connected components
- Code that is difficult to explain
- Features not required by the interviewer

The preferred approach is incremental and checkpoint-driven.

---

# 2. Base Copilot instruction

Paste the following at the beginning of the coding session.

```text
You are assisting me during a three-hour backend coding interview.

I am implementing the solution in Python 3.11 using FastAPI, SQLAlchemy 2.x, SQLite, Pydantic and Alembic.

Important constraints:
- I have 150 minutes for implementation and 30 minutes for review preparation.
- Optimise for a complete, working, explainable solution.
- Do not overengineer.
- Use synchronous SQLAlchemy and synchronous FastAPI routes unless the requirements demand async behaviour.
- Keep domain, service, repository and HTTP responsibilities separated, but avoid unnecessary abstractions.
- Use one SQLAlchemy session per request.
- Repositories may flush but should not own the outer transaction commit.
- Add at most two high-value integration tests.
- Do not add authentication, Docker, queues, caching or distributed infrastructure unless explicitly required.
- Do not generate the entire project at once.
- Work in small stages.
- Before each stage, list the files to create or modify.
- Do not modify unrelated files.
- After generating code, explain the important design decisions and provide commands to run or verify it.
- Flag assumptions explicitly.
- Prefer simple, readable code that I can explain during a code review.
```

This establishes the operating rules for the entire session.

---

# 3. Prompt 1 — Analyse the requirements

As soon as the problem statement is received, paste the exact requirements into this prompt.

```text
Analyse the following interview requirements.

<PASTE THE COMPLETE REQUIREMENTS>

Do not write code yet.

Produce:
1. Functional requirements.
2. Non-functional requirements explicitly stated.
3. Important ambiguities.
4. Assumptions I can reasonably make.
5. Questions worth asking the interviewer.
6. The minimum viable scope that can be completed in 150 minutes.
7. Features that should be discussed but not implemented.
8. Proposed API endpoints and status codes.
9. Core entities and state transitions.
10. The three highest-risk implementation areas.

Keep the design interview-optimised rather than production-complete.
```

## What this prompt should uncover

For a background job scheduler, it may reveal questions such as:

```text
Can jobs be scheduled for the future?
What states are supported?
Can running jobs be cancelled?
Are jobs actually executed or only managed?
How are retries triggered?
Must scheduling survive restarts?
Is concurrent worker execution required?
```

Ask the interviewer only the questions that materially change the implementation.

Do not allow AI to silently decide major product behaviour.

---

# 4. Prompt 2 — Create the implementation plan

After requirements and assumptions are confirmed:

```text
Using the confirmed requirements and assumptions below, create a chronological implementation plan.

<PASTE CONFIRMED REQUIREMENTS AND ASSUMPTIONS>

The solution should use:
- Python 3.11
- FastAPI
- SQLAlchemy 2.x
- SQLite
- Pydantic
- Alembic
- Pytest
- At most two integration tests

Produce:
1. The exact order in which files should be created.
2. The responsibility of each file.
3. Dependencies between the files.
4. Vertical checkpoints where the application should be runnable.
5. A 150-minute implementation time budget.
6. A fallback plan if I start running out of time.

Do not write code yet.
Do not include optional files unless the requirements justify them.
```

## Typical backend file order

A likely sequence is:

```text
pyproject.toml
app/config.py
app/constants.py
app/exceptions.py
app/models.py
app/schemas.py
app/database.py
app/database_models.py
app/repository_protocol.py
app/persistence_mappers.py
app/sql_repository.py
app/service.py
app/dependencies.py
app/routers/<resource>.py
app/exception_handlers.py
app/main.py
tests/integration/test_<resource>.py
migrations/
README.md
```

Reject unnecessary files such as:

- Multiple controller layers
- Factories without a real need
- Generic manager classes
- DTO directories duplicating schemas
- Separate interfaces for every trivial class
- Infrastructure not mentioned in the requirements

---

# 5. Prompt 3 — Generate the minimum project skeleton

```text
Generate the minimum project skeleton for the agreed implementation plan.

Create only:
- pyproject.toml
- package directories
- empty __init__.py files
- app/config.py
- app/main.py with a health endpoint
- .env.example
- .gitignore

Do not implement the business use case yet.
Do not add database models or repositories yet.

Requirements:
- The application must start successfully.
- Configuration must use pydantic-settings.
- Include installation and run commands.
- Show the final directory tree.
```

## Immediate verification

Run:

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
```

Do not proceed until the application starts successfully.

This is the first vertical checkpoint.

---

# 6. Prompt 4 — Define the domain and HTTP contract

```text
Implement the domain definitions and API schemas for the confirmed requirements.

Create or modify only:
- app/constants.py
- app/models.py
- app/schemas.py
- app/exceptions.py

Do not implement SQLAlchemy, repositories, services or routes yet.

Requirements:
- Define supported states explicitly where applicable.
- Represent valid domain data and lifecycle behaviour.
- Keep Pydantic HTTP schemas separate from the domain model.
- Include request and response models only for required endpoints.
- Avoid duplicating constants.
- Use timezone-aware UTC datetimes.
- Clearly identify which validation belongs in Pydantic and which belongs in the service.
- Explain the state-transition rules after the code.
```

## Validation ownership

Use this distinction:

```text
Pydantic / HTTP boundary
    Data shape
    Required fields
    String lengths
    Enum values
    Primitive formatting

Service / business layer
    State transitions
    Cross-field business rules
    Resource ownership
    Retry limits
    Time-based business decisions
```

## Example state machine

For a job scheduler:

```text
PENDING → RUNNING
PENDING → CANCELLED
RUNNING → SUCCEEDED
RUNNING → FAILED
FAILED → PENDING, when retrying
```

Only use transitions confirmed by the requirements.

---

# 7. Prompt 5 — Add the persistence foundation

```text
Add the persistence foundation.

Create or modify only:
- app/database.py
- app/database_models.py
- app/persistence_mappers.py
- app/config.py

Do not create routes or service methods yet.

Requirements:
- Use SQLAlchemy 2.x typed declarative mappings.
- Use one application-level engine.
- Create a session factory, not a global session.
- Keep the domain model separate from the ORM model.
- Add only database constraints required for correctness.
- Use explicit named constraints.
- Support timezone-aware domain datetimes when using SQLite.
- Do not call commit inside mapping code.
- Explain every database constraint and index.
```

## Persistence mental model

```text
Domain model
    ↓ mapper
ORM record
    ↓ SQLAlchemy session
Database row
```

On reads:

```text
Database row
    ↓ ORM record
Persistence mapper
    ↓
Domain model
```

## Database responsibilities

Use database constraints for correctness that must survive concurrent requests:

- Unique business identifiers
- Required values
- Foreign-key relationships
- Valid numeric ranges
- Critical invariants expressible as constraints

Do not duplicate every Pydantic validation rule in the database unless required.

---

# 8. Prompt 6 — Repository and transaction contract

```text
Implement the repository contract and SQLAlchemy repository.

Create or modify only:
- app/repository_protocol.py
- app/sql_repository.py
- app/persistence_mappers.py

Required operations:
<PASTE THE REQUIRED STORAGE OPERATIONS>

Rules:
- The service must depend on a Protocol, not the concrete SQL repository.
- Inject the SQLAlchemy Session into the repository.
- Repository methods may flush when database errors must be detected.
- Repository methods must not commit the outer transaction.
- Translate only recognised database integrity failures into application exceptions.
- Do not catch broad exceptions.
- Use deterministic ordering for list queries.
- Add pagination only if required.
- Explain transaction ownership and possible concurrency issues.
```

## Prefer domain-specific repository operations

Do not force every problem into generic CRUD.

For a scheduler, useful operations may include:

```text
save_job
get_job
list_jobs
update_status
claim_due_job
cancel_job
increment_attempt_count
```

For a quota manager:

```text
get_quota
reserve_capacity
release_capacity
get_usage
```

For a webhook service:

```text
save_subscription
record_delivery_attempt
list_due_deliveries
mark_delivery_succeeded
mark_delivery_failed
```

## Transaction ownership

```text
FastAPI dependency / unit of work
    Owns commit and rollback

Repository
    Executes queries
    May flush
    Does not commit outer transaction
```

Flush is useful when the repository needs a database error to occur immediately so it can translate a known constraint failure.

---

# 9. Prompt 7 — Build one complete vertical slice

Always implement one end-to-end use case before adding every endpoint.

For example:

```text
POST /jobs
GET /jobs/{job_id}
```

Prompt:

```text
Implement one complete working vertical slice for:
- <CREATE ENDPOINT>
- <GET-BY-ID ENDPOINT>

Create or modify only:
- app/service.py
- app/dependencies.py
- app/routers/<resource>.py
- app/exception_handlers.py
- app/main.py

Use the domain, schemas and SQL repository already present.

Requirements:
- One SQLAlchemy session per request.
- Commit on successful completion.
- Roll back on exception.
- Close the session automatically.
- Route handlers must not contain SQLAlchemy logic.
- Business rules belong in the service.
- Return appropriate HTTP status codes and consistent error responses.
- Do not implement the other endpoints yet.
- After writing the code, provide curl commands for the successful and missing-resource cases.
```

## Vertical checkpoint

```text
POST request
    ↓
Validation
    ↓
Service
    ↓
Repository
    ↓
Database insert
    ↓
Commit
    ↓
GET request
    ↓
Database read
    ↓
Response
```

A working partial system is safer than many unfinished endpoints.

---

# 10. Prompt 8 — Complete remaining requirements incrementally

Use one prompt per logical use case.

## List resources

```text
Add the list-resource use case.

Modify only the files genuinely required.

Requirements:
- Support only the confirmed filters.
- Use deterministic ordering.
- Use pagination only if required.
- Keep filtering logic out of the route where practical.
- Provide curl verification commands.
- Do not refactor unrelated code.
```

## State transition

```text
Add the <STATE TRANSITION> use case.

Requirements:
- Enforce valid lifecycle transitions in the service.
- Make repeated requests explicitly idempotent or non-idempotent.
- Return the agreed status for missing resources and invalid transitions.
- Persist the new state transactionally.
- Do not modify unrelated endpoints.
- Explain the idempotency decision.
```

## Retry behaviour

```text
Add retry behaviour.

Requirements:
- Enforce the maximum retry count.
- Allow retry only from confirmed states.
- Update attempt counters consistently.
- Avoid repository-level commit.
- Explain concurrency risks and what would change in a distributed implementation.
```

## Scheduled or background execution

```text
Implement the minimum required scheduled or background execution behaviour.

Before writing code, state whether this should be:
1. An HTTP-triggered synchronous operation,
2. A simple in-process loop,
3. A background task,
4. Or modelled and discussed only.

Choose the least complex option that satisfies the stated interview requirement.

Do not introduce Celery, Redis, Kafka or a production scheduler unless explicitly required.
```

This prompt prevents unnecessary distributed infrastructure.

---

# 11. Prompt 9 — Ask AI to inspect, not rewrite

Once the core functionality works:

```text
Review the current project for correctness.

Do not rewrite the architecture.

Inspect specifically for:
- Broken imports.
- Circular dependencies.
- Incorrect SQLAlchemy session lifetime.
- Missing commits or rollbacks.
- Repository methods committing unexpectedly.
- Invalid state transitions.
- Naive versus timezone-aware datetime errors.
- Incorrect HTTP status codes.
- Pydantic/ORM/domain model leakage.
- IntegrityError handling that is too broad.
- Race conditions in claiming, reserving, retrying or updating state.
- Files that are unnecessary.

Return:
1. Critical bugs that must be fixed.
2. Important issues worth fixing.
3. Optional improvements to discuss only.
4. Exact minimal patches for critical issues.

Do not add new features.
```

Avoid asking:

> Improve or refactor the entire project.

That invites large, risky changes late in the interview.

---

# 12. Prompt 10 — Add exactly two integration tests

```text
Add exactly two high-value integration tests for the application.

Use a temporary SQLite database.

Select the two tests that cover the greatest implementation risk.

Possible candidates:
- Complete lifecycle persistence across independent database sessions.
- Invalid or concurrency-sensitive state transition returning the expected API error.
- Retry-limit enforcement.
- Database uniqueness or quota constraint translated into the expected API error.
- Claiming or reserving a resource updates state correctly.

Do not add:
- Unit tests for every method.
- Large fixture hierarchies.
- Factories.
- Mock-heavy tests.
- Tests for trivial Pydantic validation.

Explain why the selected two tests provide the highest value.
```

## Testing strategy

Use the two tests to cover the risk introduced by the project’s most important technical decisions.

Examples:

```text
Persistence-heavy project
    Test persistence across sessions
    Test database constraint translation

State-machine project
    Test one complete lifecycle
    Test invalid transition

Concurrency-sensitive project
    Test atomic reservation or claim
    Test conflict behaviour

External integration project
    Test successful orchestration with a controlled fake
    Test retry/failure state persistence
```

Do not spend interview time recreating a full production test suite.

---

# 13. Prompt 11 — Add Alembic late

Add migrations only after the core application is stable.

```text
Add the smallest correct Alembic setup.

Requirements:
- Use application settings for the database URL.
- Set Base.metadata as target_metadata.
- Generate one initial migration.
- Remove runtime create_all() after the migration exists.
- Document the exact migration commands.
- Do not add migration tests.
- Show what I must manually review in the generated migration.
```

## Time-pressure fallback

When time is limited, using:

```python
Base.metadata.create_all()
```

is acceptable temporarily.

During code review, explain:

> I used `create_all()` to keep the exercise runnable within the time box. The next step would be introducing Alembic, creating a reviewed initial migration, and removing runtime schema creation.

A working application is more valuable than incomplete migration infrastructure.

---

# 14. Final 30-minute review framework

At the 150-minute mark, stop adding features.

The final 30 minutes are for correctness, explanation and code-review preparation.

---

## Review Prompt A — Final code audit

```text
Perform a final interview code review of this project.

Do not modify code yet.

Identify:
1. Any correctness bug.
2. Any request that can leave the database session broken.
3. Any state transition that violates the requirements.
4. Any concurrency issue.
5. Any security concern.
6. Any incomplete requirement.
7. Any unnecessary abstraction.
8. Any code I may struggle to explain.

Classify each item:
- Must fix before submission
- Mention during review
- Future production improvement

Keep the review grounded in the current code.
```

Spend approximately ten minutes fixing only **must-fix** issues.

---

## Review Prompt B — Generate the walkthrough

```text
Using the current project, prepare a code-review walkthrough.

Produce:
1. A 60-second project summary.
2. A five-minute architecture walkthrough.
3. The end-to-end request lifecycle for the main use case.
4. The transaction boundary.
5. The domain state machine, if applicable.
6. The five strongest design decisions.
7. The five most important trade-offs.
8. Current limitations.
9. What I would implement with another day.
10. Likely interviewer questions with concise answers.

Do not claim that unimplemented production features already exist.
```

---

## Review Prompt C — Interview challenge mode

Use this during practice before the real interview.

```text
Act as a strict senior backend interviewer reviewing this implementation.

Ask me one question at a time about:
- Architecture
- SQLAlchemy sessions and transactions
- State transitions
- Concurrency
- Idempotency
- Failure recovery
- Database constraints
- Testing choices
- Scaling beyond one process
- External integrations, if present

After each answer, critique it and ask a deeper follow-up.
Do not provide the answer before I respond.
```

---

# 15. Recommended 180-minute timeline

## 0–15 minutes — Understand and scope

```text
Read requirements
Ask interviewer questions
Record assumptions
Define API contract
Define state transitions
Identify high-risk areas
```

Use Prompt 1 and Prompt 2.

---

## 15–30 minutes — Create the runnable skeleton

```text
Project setup
Configuration
Health endpoint
Application starts
```

Use Prompt 3.

---

## 30–55 minutes — Domain and database foundation

```text
Domain model
Pydantic schemas
Exceptions
ORM model
Database engine and session factory
Persistence mappers
```

Use Prompt 4 and Prompt 5.

---

## 55–85 minutes — Repository and first vertical slice

```text
Repository protocol
SQL repository
Service
Create endpoint
Get-by-ID endpoint
```

Use Prompt 6 and Prompt 7.

---

## 85–125 minutes — Complete core functionality

```text
List
Update or transition state
Cancel or delete
Retry or reserve
Required filters
Scheduled behaviour if explicitly required
```

Use focused Prompt 8 variants.

---

## 125–140 minutes — Manual validation

Verify:

```text
Happy path
Missing resource
Invalid transition
Duplicate or constraint conflict
Restart persistence
Time-based behaviour
```

Use curl, Swagger UI or a short script.

---

## 140–150 minutes — Lean tests or migration

Priority order:

```text
1. One or two high-value integration tests
2. Alembic, only if the application is stable
3. README run commands
```

---

## 150–180 minutes — Stop building

```text
10 minutes
    Correctness audit and critical fixes

10 minutes
    Architecture and trade-off notes

10 minutes
    Rehearse code-review questions
```

Do not add optional features during this period.

---

# 16. Prompting rules during the interview

## Rule 1 — Ask for minimal diffs

Prefer:

```text
Modify only app/service.py and app/sql_repository.py.
Show the minimal patch.
```

Avoid:

```text
Rewrite the application cleanly.
```

---

## Rule 2 — State the invariant explicitly

Weak prompt:

```text
Fix cancellation.
```

Strong prompt:

```text
A job may be cancelled only from PENDING.
Cancellation of an already-cancelled job should be idempotent.
A RUNNING job must return 409.
Implement this without changing unrelated endpoints.
```

---

## Rule 3 — Give AI the exact failure

```text
POST /jobs succeeds, but GET from a second request returns 404.
Here is the traceback and the relevant session dependency.
Identify the root cause before proposing a patch.
```

Ask for the root cause before asking for code changes.

---

## Rule 4 — Force explanation after generation

```text
Explain this implementation as though I must defend it in a senior-engineer code review.

Focus on:
- Why this layer owns the behaviour.
- Transaction implications.
- Concurrency implications.
- Alternatives considered.
```

---

## Rule 5 — Do not accept code you cannot narrate

Before moving to the next step, answer:

```text
What calls this function?
What data enters it?
What transaction is active?
What database operations can occur?
What can fail?
Who catches the failure?
Who commits or rolls back?
What response does the client receive?
```

---

## Rule 6 — Reject unrelated refactoring

When AI changes unrelated files, respond:

```text
Revert the unrelated refactoring.
Keep the existing architecture.
Apply only the minimal change needed for the stated requirement.
```

---

## Rule 7 — Keep production extensions as discussion items

Unless explicitly required, discuss rather than implement:

- Redis
- Celery
- Kafka
- Distributed locks
- Kubernetes
- Authentication
- Rate limiting
- Caching
- Multi-region replication
- Advanced observability
- Complex CI/CD

These are valuable review topics but often poor uses of a three-hour implementation window.

---

# 17. Reusable compact prompt

Use this for most incremental implementation tasks.

```text
Implement the next requirement:

<REQUIREMENT>

Current architecture:
<BRIEF CURRENT STRUCTURE>

Modify only:
<FILES>

Rules:
- Keep routes thin.
- Put business rules in the service.
- Put persistence queries in the repository.
- Do not commit inside repository methods.
- Preserve one session per request.
- Use explicit application exceptions.
- Do not refactor unrelated code.
- Do not add optional infrastructure.
- State assumptions.
- Show the minimal code changes.
- Give commands to verify the behaviour.
- Explain the key design and transaction decisions.
```

---

# 18. Debugging prompt

Use this when the application fails.

```text
Diagnose the following failure before changing code.

Expected behaviour:
<EXPECTED>

Actual behaviour:
<ACTUAL>

Error or traceback:
<PASTE ERROR>

Relevant files:
<PASTE OR REFERENCE FILES>

Return:
1. The most likely root cause.
2. Evidence from the code or traceback.
3. The smallest safe fix.
4. A command or request that verifies the fix.
5. Any regression risk introduced by the patch.

Do not refactor unrelated code.
```

---

# 19. API design review prompt

```text
Review the proposed API contract before implementation.

Requirements:
<PASTE REQUIREMENTS>

Proposed endpoints:
<PASTE ENDPOINTS>

Check:
- Resource naming
- HTTP methods
- Status codes
- Idempotency
- Error behaviour
- Pagination
- Filtering
- State-transition endpoints
- Whether any endpoint leaks persistence details

Return only changes that materially improve correctness or clarity.
Do not expand the scope.
```

---

# 20. Database design review prompt

```text
Review the proposed SQLAlchemy model before implementation.

Requirements:
<PASTE REQUIREMENTS>

Proposed model:
<PASTE MODEL>

Check:
- Primary key choice
- Business-key uniqueness
- Nullability
- Foreign keys
- Check constraints
- Indexes needed by actual queries
- Timestamp handling
- State representation
- Concurrency-sensitive fields
- Fields that should not be persisted

Classify recommendations as:
- Required for correctness
- Useful but optional
- Production-only
```

---

# 21. State-machine review prompt

```text
Review this state machine against the requirements.

Requirements:
<PASTE REQUIREMENTS>

States:
<PASTE STATES>

Transitions:
<PASTE TRANSITIONS>

For every transition, identify:
- Source state
- Target state
- Preconditions
- Idempotency behaviour
- Invalid-transition response
- Persistence changes
- Concurrency concern

Do not invent states or transitions not justified by the requirements.
```

---

# 22. Concurrency review prompt

```text
Review the following use case for concurrency problems.

Use case:
<PASTE FLOW OR CODE>

Analyse:
- Check-then-write races
- Lost updates
- Duplicate processing
- Double reservation or double claiming
- Transaction isolation assumptions
- Database constraints
- Whether an atomic UPDATE can replace read-modify-write
- Whether optimistic or pessimistic locking is necessary

Recommend the simplest solution appropriate for a three-hour interview.
Separate implemented fixes from production-scale improvements.
```

---

# 23. README generation prompt

```text
Create a concise interview-project README based on the current repository.

Include only:
- Project purpose
- Implemented features
- Architecture summary
- Setup commands
- Database migration commands
- Run command
- Two or three example API requests
- Test command
- Key assumptions
- Known limitations
- What I would add with more time

Do not claim unimplemented features.
Keep it short enough to review quickly.
```

---

# 24. Submission readiness checklist

## Requirements

```text
□ Every required use case is implemented or explicitly documented as out of scope
□ Important assumptions are written down
□ API behaviour matches the agreed contract
□ State transitions match the requirements
```

## Runtime

```text
□ Application installs successfully
□ Application starts with one documented command
□ Health endpoint works
□ Database initialisation steps are documented
□ Core happy path works end to end
□ Data survives independent requests or restart when persistence is required
```

## Architecture

```text
□ Routes are thin
□ Service owns business rules
□ Repository owns persistence queries
□ Domain model does not depend on FastAPI
□ Service does not depend on SQLAlchemy ORM classes
□ One session exists per request
□ Repository does not commit the outer transaction
```

## Errors

```text
□ Missing resource returns the expected status
□ Invalid transition returns a clear conflict or validation response
□ Database conflicts are translated deliberately
□ Unknown errors do not expose sensitive internals
```

## Database

```text
□ Business-key uniqueness is database-enforced where required
□ Critical invariants use constraints where practical
□ Queries used by endpoints are deterministic
□ Read-modify-write operations have been reviewed for lost updates
```

## Tests

```text
□ One or two high-value integration tests pass
□ Tests use an isolated temporary database
□ Tests cover the project’s primary risk areas
□ Test setup is not disproportionately complex
```

## Review preparation

```text
□ 60-second summary prepared
□ Main request lifecycle understood
□ Transaction boundary understood
□ Five design decisions prepared
□ Five trade-offs prepared
□ Limitations stated honestly
□ Next production improvements prioritised
```

---

# 25. Time-pressure fallback plan

## Level 1 — Full interview-optimised solution

```text
FastAPI
Domain model
Pydantic schemas
SQLAlchemy persistence
Repository
Service
Request-scoped transaction
Core endpoints
Two tests
Alembic
README
```

## Level 2 — Complete working core

Skip or simplify:

```text
Alembic
Second test
Advanced filtering
Optional endpoint
```

Keep:

```text
Working API
Persistence
Clear layering
Manual verification
One meaningful test
```

## Level 3 — Minimum viable submission

```text
FastAPI
SQLAlchemy
One vertical slice
Core required endpoints
Manual verification
README assumptions and limitations
```

Temporarily use `create_all()` if necessary.

## Level 4 — Emergency stabilisation

Stop feature work and ensure:

```text
Application starts
One happy path works
No syntax/import failures
Database commits correctly
Known limitations are documented
```

A smaller working project is stronger than a larger broken one.

---

# 26. Behaviour to avoid

Do not:

- Ask AI to build the entire system in one pass
- Accept abstractions you cannot explain
- Add infrastructure not required by the prompt
- Let routes contain direct database queries
- Commit independently inside every repository method
- Rely only on an application-level existence check for uniqueness
- Add a large test suite under interview time pressure
- Spend the final 30 minutes adding features
- Claim production readiness
- Hide incomplete requirements during review
- Refactor working code without a concrete reason

---

# 27. Mental model for AI usage

```text
AI should accelerate:
    Syntax
    Boilerplate
    Repetitive mappings
    SQLAlchemy statements
    Pydantic models
    Test setup
    Documentation
    Error diagnosis

You must own:
    Requirement interpretation
    Scope
    API contract
    State machine
    File boundaries
    Transaction ownership
    Concurrency decisions
    Idempotency
    Trade-offs
    Final explanation
```

The central principle is:

```text
Use AI to accelerate typing
        ≠
Delegate architectural ownership to AI
```

---

# 28. One-page interview sequence

```text
1. Paste base Copilot instruction

2. Analyse requirements
   - Functional scope
   - Ambiguities
   - Questions
   - API contract
   - State machine

3. Create implementation plan
   - File order
   - Dependencies
   - Time budget
   - Fallback plan

4. Create skeleton
   - pyproject
   - config
   - main
   - health
   - run successfully

5. Define domain and schemas
   - constants
   - models
   - exceptions
   - request/response schemas

6. Add persistence
   - engine
   - session factory
   - ORM models
   - constraints
   - mappers

7. Add repository
   - protocol
   - SQL implementation
   - flush, no commit

8. Build one vertical slice
   - create
   - get
   - commit/rollback
   - verify manually

9. Add remaining use cases one by one
   - list
   - transitions
   - retry
   - cancellation
   - scheduling

10. Run correctness review
    - minimal patches only

11. Add two high-value integration tests

12. Add Alembic only when stable

13. Stop at 150 minutes

14. Final 30 minutes
    - critical fixes
    - walkthrough
    - trade-offs
    - limitations
    - likely questions
```

---

# 29. Final interview explanation

A concise explanation of this development method:

> I use AI incrementally rather than asking it to generate the complete project. I first clarify requirements and define the API and state model. I then create a runnable skeleton, establish domain and persistence boundaries, and build one complete vertical slice before expanding functionality. I constrain each AI prompt to specific files and invariants, verify every stage, and use the last 30 minutes exclusively for correctness review and preparing the architecture walkthrough. AI accelerates implementation, but I retain ownership of scope, transactions, concurrency, idempotency and design trade-offs.

---

# 30. Framework summary

```text
Understand before coding
Build vertically
Prompt narrowly
Verify continuously
Keep tests lean
Delay optional infrastructure
Stop feature work on time
Prepare to explain every decision
```
