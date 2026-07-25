# Backend Engineering Interview Lab

A collection of production-oriented backend systems built from scratch
using Python, FastAPI, SQLAlchemy and PostgreSQL.

The repository documents not only the final implementations, but also:

- requirements
- architecture
- design decisions
- mistakes and lessons learned
- tests
- production trade-offs
- interview-optimised decisions

## Projects

| Project | Current Stage | Concepts |
|---|---|---|
| TinyURL | V1 complete | Domain models, repository pattern, service layer, dependency injection, CLI, pytest |
| Food Ordering | Planned | State transitions, transactions, inventory |
| Background Jobs | Planned | Queues, retries, idempotency |
| Rate Limiter | Planned | Sliding windows, concurrency, Redis |

## TinyURL Roadmap

- [x] Plain Python domain model
- [x] In-memory repository
- [x] Service layer
- [x] Interactive CLI
- [x] Unit tests
- [ ] FastAPI boundary
- [ ] SQLAlchemy persistence
- [ ] Docker
- [ ] Logging and observability
