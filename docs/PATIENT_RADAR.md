# DENTAI Armenia Patient Radar

Patient Radar is a tenant-isolated, read-only intent-intelligence module for discovering evidence-linked dental demand signals in Armenia.

It implements the product flow described in the Armenia Patient Radar specification:

`Source Discovery -> Monitoring -> Collection -> Language/Context -> Dental Relevance -> Intent -> Treatment -> Location -> Urgency -> Opportunity Score -> Deduplication -> Intent Timeline -> Dashboard`

## Product boundary

Radar is deliberately separate from the DENTAI clinical X-ray pipeline and from WhatsApp Outreach.

- Radar reads and ranks content supplied from public or otherwise authorized sources.
- Radar never likes, follows, comments, replies, shares, posts, or sends DMs.
- Radar does not bypass CAPTCHAs, login challenges, access controls, or platform security.
- Radar does not automatically contact a discovered person.
- Radar opportunities are not clinic Patients and are not inserted into the `patients` table.
- Author platform identifiers are transformed into a tenant-scoped fingerprint before timeline aggregation.
- Every stored signal keeps its original evidence URL and timestamp for human verification.
- Platform passwords, cookies, and session files are never stored in the DENTAI clinical database or frontend.

## Operational collection

Patient Radar now has two collection modes behind the same source/worker pipeline.

### Built-in public collectors

DENTAI can collect immediately from:

- `WEB`: public HTTP(S) pages. Readable text blocks are normalized, deduplicated, and passed into the intelligence pipeline.
- `TELEGRAM`: public Telegram channels through the public `t.me/s/<channel>` view. Message text, post identifier, source URL, author display when available, and published time are normalized.

The public HTTP collector includes SSRF protections:

- HTTP(S) only;
- no credentials in URLs;
- DNS resolution before the request;
- private, loopback, link-local, multicast, reserved, and unspecified addresses are rejected;
- redirect destinations are validated again;
- response size and readable content types are bounded.

The public page parser also extracts a bounded list of linked public source candidates. These candidates are evidence for future source-graph expansion; they are not silently activated as monitored sources.

### Authorized-session collector

Instagram, Facebook, protected Telegram, and other authenticated sources use a separate authorized-session collector configured with `RADAR_COLLECTOR_URL`.

This follows the product requirement that a clinic-owned account is logged in by the user and that any login, 2FA, verification, or challenge is completed manually by that user. DENTAI does not automate security challenges.

The clinical application calls the collector with a read-only contract:

- clinic identifier;
- registered source metadata;
- collection limits;
- `mode=read_only`.

The collector returns normalized evidence records only. Session/cookie/password material remains outside the clinical API and database.

For a non-loopback collector URL, production requires `RADAR_COLLECTOR_TOKEN`.

## Continuous monitoring worker

Run Patient Radar as a dedicated worker:

```bash
python -m app.radar.worker
```

The worker mirrors DENTAI's tenant-aware background-worker pattern:

1. reads active clinics from the control plane;
2. resolves each clinic tenant database;
3. atomically claims one due source using `FOR UPDATE SKIP LOCKED`;
4. commits the claim lease before network collection;
5. collects source content;
6. performs batch semantic analysis;
7. ingests/deduplicates signals;
8. updates opportunity timelines and scores;
9. records source health and schedules the next poll.

Source runtime states include `IDLE`, `CLAIMED`, `POLLING`, `HEALTHY`, `ERROR`, `ACTION_REQUIRED`, and `PAUSED`.

Retryable failures use bounded exponential backoff. Authentication/session-required failures become `ACTION_REQUIRED` instead of being retried aggressively. A source with new content temporarily receives the high-priority monitoring interval.

## Multilingual intelligence

Patient Radar uses a two-stage intelligence path.

### Deterministic fast path

The existing rules engine provides fast Armenian/Russian/English/mixed-language filtering and a safe fallback when semantic AI is unavailable.

It detects signals related to:

- dental pain;
- dentist recommendations;
- implants;
- veneers;
- crowns;
- root canal treatment;
- fillings;
- braces;
- whitening;
- cleaning;
- wisdom teeth;
- emergency dental care;
- cosmetic dentistry.

### Context-aware semantic refinement

When `RADAR_LLM_ENABLED=true` and `GROQ_API_KEY` is configured, candidate batches are refined using the configured Groq model.

The semantic stage receives only bounded text/context plus deterministic item IDs. It is instructed to understand colloquial Eastern Armenian, Russian, English, transliteration, and mixed Armenian-market text. It can use post/caption context to interpret short comments such as a price question under a veneer post.

The semantic model does not receive platform credentials and is not allowed to identify people, infer protected traits, diagnose disease, or invent facts absent from the supplied text.

The response is strict-schema validated and bound back to the exact input item IDs. Invalid, unavailable, or mismatched responses fall back to the deterministic rules engine.

## Server-owned opportunity score

The language model does not choose the final opportunity score.

DENTAI calculates the score from versioned policy components in `config/patient_radar_rules.json`:

- Dental relevance: 25%
- Treatment intent: 20%
- Armenia/location match: 20%
- Urgency: 15%
- Recency: 10%
- Recommendation intent: 5%
- Classifier confidence: 5%

Tiers are:

- `HOT`: 90-100
- `WARM`: 75-89
- `RESEARCH`: 50-74
- `IGNORE`: below 50

This is an **Opportunity score**, not a calibrated probability that a person will become a clinic patient.

## Deduplication and intent timeline

Signals are deduplicated using stable platform/source/author/signal/text evidence keys.

When a stable platform author identifier is available, it is converted to a tenant-scoped fingerprint. Multiple signals from the same platform identity aggregate into one opportunity timeline instead of becoming unrelated leads.

Opportunity metadata keeps:

- latest score;
- peak score;
- score trend;
- a bounded score history;
- latest source/evidence URL;
- score components;
- semantic classifier provenance.

This enables the product behavior described in the specification: a person can move from an early pain signal to a recommendation request and later to active price/treatment research while remaining one reviewable opportunity.

## Source graph and adaptive monitoring

Each source records:

- Armenia relevance;
- engagement score;
- dental-signal probability;
- overall source score;
- priority;
- adaptive monitoring interval;
- last poll/content times;
- next check time;
- safe runtime state and error metadata.

Default policy intervals are configured in `config/patient_radar_rules.json`:

- High priority: 5 minutes
- Medium priority: 45 minutes
- Low priority: 180 minutes
- Inactive: 1440 minutes

## API

Read access is available to authenticated clinic users. Source management, manual collection, ingestion, and opportunity state changes require Director or Manager role.

Core endpoints:

- `GET /api/v1/radar/dashboard`
- `GET /api/v1/radar/runtime`
- `GET /api/v1/radar/sources`
- `POST /api/v1/radar/sources`
- `PATCH /api/v1/radar/sources/{source_id}`
- `POST /api/v1/radar/sources/{source_id}/run`
- `GET /api/v1/radar/sources/due`
- `POST /api/v1/radar/sources/{source_id}/polled`
- `POST /api/v1/radar/ingest`
- `POST /api/v1/radar/classify-preview`
- `GET /api/v1/radar/opportunities`
- `GET /api/v1/radar/opportunities/{opportunity_id}`
- `PATCH /api/v1/radar/opportunities/{opportunity_id}`

## Frontend product

`Patient Radar` is a first-class DENTAI navigation section with operational controls rather than a static concept screen.

It includes:

- collector readiness for Instagram, Facebook, Telegram, and Web;
- active/due/unhealthy/action-required source counts;
- semantic AI mode status;
- source score, priority, cadence, health, last success, and safe error state;
- Add Source;
- Run Now;
- pause/resume;
- Hot/Warm/Research KPIs;
- filters for platform, tier, language, treatment, and score;
- prioritized opportunity queue;
- score-trend indicator;
- evidence detail drawer;
- multi-signal intent timeline;
- original evidence links;
- review/archive actions;
- explicit read-only and non-probabilistic-score explanations.

Public Web and public Telegram sources can be added and run immediately. Instagram/Facebook correctly show action-required/not-ready until an authorized-session collector is configured and healthy.

## Deployment

Before enabling the product for a clinic, run the clinic-plane migration:

```bash
MIGRATION_PLANE=clinic alembic upgrade head
```

Deploy a dedicated Radar worker using the same DENTAI application image/code:

```bash
python -m app.radar.worker
```

Important environment variables:

```text
RADAR_WORKER_POLL_SECONDS=5
RADAR_CLAIM_SECONDS=180
RADAR_HTTP_TIMEOUT_SECONDS=20
RADAR_HTTP_MAX_BYTES=2097152
RADAR_MAX_ITEMS_PER_POLL=300
RADAR_LLM_ENABLED=true
RADAR_LLM_BATCH_SIZE=32
```

The existing `GROQ_API_KEY`, `GROQ_MODEL`, and `GROQ_TIMEOUT_SECONDS` settings are reused for semantic refinement.

For Instagram/Facebook or protected sources, additionally configure:

```text
RADAR_COLLECTOR_URL=<private authorized-session collector URL>
RADAR_COLLECTOR_TOKEN=<shared internal token>
RADAR_COLLECTOR_TIMEOUT_SECONDS=30
```

Never commit either the collector token or platform session data.

## Operational verification

The scoped `Patient Radar` GitHub Actions workflow validates:

- multilingual/scoring behavior;
- public Web parsing;
- public Telegram parsing;
- server-owned semantic scoring;
- runtime imports;
- scoped Ruff checks;
- frontend tests;
- frontend production build.

Production smoke verification should additionally confirm:

1. clinic migration is at `0005_patient_radar`;
2. Radar worker is running;
3. a public Web source can be added and `Run now` completes;
4. a public Telegram source can be added and collected;
5. new candidate signals create evidence-linked opportunities;
6. the same stable identity aggregates into one timeline;
7. source health/cadence updates in the UI;
8. authorized-session collector health is visible before enabling Instagram/Facebook sources.
