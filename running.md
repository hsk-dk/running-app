🏗️ Running – Systemdokumentation
🎯 Formål

Running er en personlig træningsapp til:

synkronisering af løb fra Strava
planlægning af træning
automatisk og manuel match mellem plan og faktiske løb
evaluering af træningskonsistens
🗄️ Database
🧱 Overordnet model

Der er to centrale entiteter:

activities → faktiske løb (fra Strava)
planned_runs → planlagte træninger

Relation:

activities.matched_planned_run_id → planned_runs.id
planned_runs.matched_activity_id → activities.id

👉 planned_runs er source of truth
👉 activities er derived state

📊 Tabel: activities
Felt	Type	Beskrivelse
id	INTEGER	Strava activity id
name	TEXT	Navn
sport_type	TEXT	fx Run
start_date	TEXT	ISO timestamp
distance_m	REAL	distance
moving_time_s	INTEGER	tid
average_heartrate	REAL	puls
is_extra	INTEGER	1 = ikke planlagt
is_aborted	INTEGER	afbrudt
matched_planned_run_id	INTEGER	FK til plan
📊 Tabel: planned_runs
Felt	Type	Beskrivelse
id	INTEGER	PK
planned_date	TEXT	dato
session_type	TEXT	easy / long / intervals
target_type	TEXT	time / distance
target_value	REAL	mål
mandatory	INTEGER	obligatorisk
status	TEXT	gennemført / forkortet / planlagt osv.
matched_activity_id	INTEGER	FK
actual_value	REAL	faktisk
manual_override	INTEGER	manuel ændring
override_reason	TEXT	hvorfor
match_score	REAL	auto-match score
match_reason	TEXT	forklaring
📊 Øvrige tabeller
derived_metrics
precomputed statistik (tempo, puls osv.)
webhook_events
log af Strava webhook events
sync_state
system state (fx sidste sync)
⚙️ Backend
🧩 Arkitektur
FastAPI
├── main.py (API endpoints)
├── db.py (schema + migration)
├── ingest.py (Strava fetch)
├── strava.py (API client)
├── matching.py (auto-match algoritme)
├── planning.py (business logic)
├── metrics.py (statistik)
├── webhooks.py (Strava events)
🔄 Dataflow
1. Sync (manual eller webhook)
Strava → ingest → activities
2. Metrics
activities → derived_metrics
3. Plan matching
planned_runs ←→ activities

via:

evaluate_and_sync()
🧠 Matching-algoritme
Grundprincipper
ét løb → én plan
tolerance: ±1 dag
greedy matching
Score
(day_diff, value_diff, long_penalty, start_date, id)

Der gemmes også:

match_score
match_reason
🔁 Konsistensstrategi
Kritisk regel
planned_runs = source of truth
activities = derived
Rebuild
rebuild_activity_links()
Central funktion
evaluate_and_sync()

Bruges i:

manual match
plan ændringer
webhook flow
admin endpoints
🔌 API endpoints (udvalg)
Core
GET /api/activities
GET /api/planning
POST /api/planning
PUT /api/planning/{id}
DELETE /api/planning/{id}
Matching
POST /api/planning/evaluate
POST /api/planning/{id}/match-activity
POST /api/planning/{id}/clear-match
Admin
POST /api/admin/ingest
POST /api/admin/recalculate-plan
POST /api/admin/rebuild-links
GET /api/admin/health
Webhook
POST /api/webhooks/strava
🎨 Frontend
🧩 Struktur
App.tsx
├── OverviewPage
├── PlanPage
├── ActivitiesPage
├── AdminPage
🧠 State (App.tsx)
summary
monthlyVolume
activities
plannedRuns
weeklyConsistency
adminStatus
📄 Pages
Overblik
uge status
næste træning
trends
Plan
CRUD
manuel match
evaluering
match_reason vises
Løb
filtrering
status (matchet / ikke planlagt / afbrudt)
relation til plan
Admin
systemstatus
sync
debug
🧱 UI-principper
cards
badges
modaler via portal
sticky headers
compact actions
🧪 Systemregler
Match
ét løb → én plan
plan er styrende
manual override vinder altid
Status
gennemført ≥ 90%
forkortet ≥ 50%
ellers sprunget over
Konsistens
fremtidige træninger tæller ikke negativt
uge evalueres dynamisk
🧾 Kendte begrænsninger
Backend
greedy matching (ikke optimal globalt)
session_type bruges kun delvist
sport_type filter = "Run"
Frontend
noget logik stadig i UI (plan lookup)
ikke fuldt komponentiseret
Data
afhængig af Strava kvalitet
historisk import edge cases
📌 Backlog
🔥 Høj prioritet
1. Backend: enrich /api/activities
inkluder planned_run
inkluder activity_status
fjerne behov for frontend mapping
2. Match-kvalitet
bedre scoring
evt. session-type heuristik
undgå dårlige matches
3. UI: match kandidater
vis:
± dage
± mål
bedre beslutningsstøtte
4. Admin forbedringer
vis mismatch count
vis last webhook
vis sync health
5. Overblik v2
“kræver handling”
trends
tydelig næste træning
🟡 Medium
aktivitetsside → drilldown
audit trail (ændringer)
plan templates
bedre labels (fx "ikke planlagt")
🟢 Lav
styling refinements
komponentbibliotek
eksport / import
multi-user support
🚀 Næste arkitekturretning

Den vigtigste næste udvikling er:

👉 flyt mere logik til backend

Specifikt:

activities API skal være “færdig”
frontend skal være “dumb renderer”
🧠 Samlet vurdering

Systemet er nu:

stabilt
konsistent (med rebuild-strategi)
funktionelt som produkt

Det næste skridt er:

👉 bedre forklarlighed og beslutningsstøtte
👉 mindre frontend-logik
👉 mere robuste backend-kontrakter