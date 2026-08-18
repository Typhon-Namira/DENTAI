# DENTAI Armenia Patient Radar

Patient Radar is a tenant-isolated, read-only intent-intelligence module for discovering evidence-linked dental demand signals in Armenia.

## Product boundary

Radar is deliberately separate from the DENTAI clinical X-ray pipeline and from WhatsApp Outreach.

- Radar reads and ranks content supplied from public or otherwise authorized sources.
- Radar never likes, follows, comments, replies, shares, posts, or sends DMs.
- Radar does not bypass CAPTCHAs, login challenges, access controls, or platform security.
- Radar does not automatically contact a discovered person.
- Radar opportunities are not clinic Patients and are not inserted into the `patients` table.
- Author platform identifiers are transformed into a tenant-scoped fingerprint before timeline aggregation.
- The product stores the original evidence URL and timestamp so a human can verify each opportunity.

## Backend architecture

The tenant database contains three dedicated tables:

- `radar_sources`: the Armenian source graph and adaptive monitoring metadata.
- `radar_signals`: normalized evidence, contextual classification, scoring components, and dedupe keys.
- `radar_opportunities`: a timeline-level aggregation of candidate signals from the same platform identity.

The intelligence pipeline is:

1. Source registration / discovery candidate
2. Adaptive source ranking
3. Collector ingestion
4. Duplicate detection
5. Language detection
6. Fast dental relevance
7. Context-aware treatment and intent detection
8. Location detection
9. Urgency detection
10. Recency calculation
11. Opportunity scoring
12. Timeline aggregation
13. Dashboard and human review

The scoring policy is versioned in `config/patient_radar_rules.json`. The default weighting follows the product design:

- Dental relevance: 25%
- Treatment intent: 20%
- Armenia/location match: 20%
- Urgency: 15%
- Recency: 10%
- Recommendation intent: 5%
- Classifier confidence: 5%

Tiers are `HOT` (90-100), `WARM` (75-89), `RESEARCH` (50-74), and `IGNORE` (<50).

The number is intentionally called an **Opportunity score**, not a conversion probability. The current policy is a ranking mechanism and is not statistically calibrated to predict whether a person will become a clinic patient.

## Multilingual engine

The first operational classifier supports Armenian, Russian, English, and mixed-language content. It evaluates the signal together with available post/caption/context text, which allows short comments such as a price question to inherit dental context from a veneer or implant post.

The treatment ontology currently includes dental pain, dentist recommendation, implant, veneer, crown, root canal, filling, braces, whitening, cleaning, wisdom tooth, emergency dental care, and cosmetic dentistry. The ontology and scoring rules are versioned so they can be expanded without changing historical interpretation silently.

## Source graph and monitoring

Each source records Armenia relevance, engagement, dental-signal probability, an overall source score, priority, and the next check time.

Default intervals:

- High priority: 5 minutes
- Medium priority: 45 minutes
- Low priority: 180 minutes
- Inactive: 1440 minutes

When new content is observed, the source temporarily receives the high-priority interval. A collector can request due sources from `GET /api/v1/radar/sources/due` and report an empty successful poll using `POST /api/v1/radar/sources/{source_id}/polled`.

## Collector contract

Platform collection is intentionally isolated from the FastAPI product. An authorized collector process should:

1. authenticate using a clinic-owned account/session where the platform permits it;
2. read only content visible to that account;
3. never solve or bypass security challenges automatically;
4. send normalized batches to `POST /api/v1/radar/ingest`;
5. include stable platform signal/author identifiers when available;
6. include the original evidence URL, observed time, publication time, and post/caption context;
7. avoid unnecessary private or sensitive attributes.

This separation keeps platform session state out of the clinical API process and lets each platform connector be replaced independently as platform behavior changes.

## API

Read access is available to authenticated clinic users. Source management, ingestion, and opportunity state changes require Director or Manager role.

- `GET /api/v1/radar/dashboard`
- `GET /api/v1/radar/sources`
- `POST /api/v1/radar/sources`
- `PATCH /api/v1/radar/sources/{source_id}`
- `GET /api/v1/radar/sources/due`
- `POST /api/v1/radar/sources/{source_id}/polled`
- `POST /api/v1/radar/ingest`
- `POST /api/v1/radar/classify-preview`
- `GET /api/v1/radar/opportunities`
- `GET /api/v1/radar/opportunities/{opportunity_id}`
- `PATCH /api/v1/radar/opportunities/{opportunity_id}`

## Frontend

`Patient Radar` is a first-class product navigation section. It contains:

- Hot / Warm / Research KPI cards
- monitored-source and 24-hour signal counts
- filters for platform, tier, language, treatment, and minimum score
- prioritized opportunity queue
- source graph highlights and adaptive monitoring cadence
- evidence detail drawer
- intent timeline across multiple signals
- original evidence links
- review/archive actions for Director and Manager
- an explicit read-only safety boundary
- a score explanation that avoids presenting ranking as a calibrated conversion probability

## Deployment

Run the clinic-plane Alembic migration before enabling the UI:

```bash
MIGRATION_PLANE=clinic alembic upgrade head
```

The migration is skipped on the control plane and is designed to tolerate a fresh schema where the target tables already exist.

A production platform collector should be deployed as a separate service with its own persistent encrypted session storage and minimal network access. Do not place Facebook, Instagram, or Telegram session files in Git, application logs, frontend storage, or the control database.
