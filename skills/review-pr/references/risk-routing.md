# Risk Routing

Select specialist reviewers only from concrete evidence in the patch or recon.

## Contract and compatibility

Trigger examples:

- routes, controllers, API schemas, GraphQL, protobuf, OpenAPI
- shared DTOs or exported types
- event producers/consumers, webhooks, SDKs
- cookie, token, OAuth, session, feature-flag contracts
- cross-repository interface changes

## Data and migration

Trigger examples:

- SQL/schema migrations, backfills, reconciliation
- transaction boundaries, queues, retries, deduplication
- deletion, archival, encryption, key rotation
- persistence model or old/new data compatibility

## Operations and release

Trigger examples:

- Dockerfile, CI workflow, Helm, Kustomize, Kubernetes
- runtime environment or feature flags
- health/readiness probes
- architecture-specific binaries or image build changes

## UI and product contract

Trigger only when an authoritative design, specification, prototype, screenshot baseline, or existing contract is available.

Examples:

- visible copy, layout, navigation, animation, accessibility
- loading, empty, error, permission, and recovery states
- mobile/web platform divergence

## Routing rules

- Quality and security remain the baseline for non-trivial reviews.
- Add at most the specialists supported by evidence; do not run every category by default.
- If one specialist spans multiple triggers, give it one coherent brief rather than spawning duplicate reviewers.
- Every specialist uses the normalized finding schema and read-only access.
- Reviewer absence means only that no trigger was found, not that the risk category is proven safe.
