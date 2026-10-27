# ADR 0001: Modular Monolith Architecture

## Status
Accepted

## Context
When building backend foundations, engineering teams frequently face the trade-off between microservices and monoliths. Prematurely adopting microservices introduces network latency, distributed transaction complexity (Sagas), duplicate deployment pipelines, and severe testing friction. Conversely, unstructured monoliths degrade into tangled spaghetti code where modules depend arbitrarily on one another.

## Decision
We adopted a **Feature-Oriented Modular Monolith**. Features live in self-contained directories under `app/modules/<feature>/` containing their own models, schemas, repositories, services, and routers. Shared cross-cutting concerns (logging, configuration, security, database session factories) live in `app/core/`, `app/db/`, and `app/repositories/`.

## Consequences
- **Positive**: Rapid developer velocity, single deployment artifact, atomic cross-entity transactions when required, and straightforward local testing.
- **Positive**: Clear module boundaries allow decomposing a module into an independent microservice in the future if scale requires it.
- **Negative**: Teams must strictly enforce layer boundaries via linting and code reviews to prevent tight coupling between feature modules.
