Her er en refaktorplan for backend med fokus på services og tydelig domain separation.

Målet er at gøre backend lettere at:

forstå
teste
udvide
vedligeholde uden skjulte sideeffekter
Målbillede

I dag er logikken fordelt nogenlunde funktionelt, men der er stadig kobling mellem:

API-lag
database-adgang
domænelogik
sync/rebuild-flow

Den refaktor, jeg vil sigte mod, er:

app/
├── main.py
├── api/
├── domain/
├── services/
├── repositories/
├── models/
├── db/
└── integrations/

Det behøver ikke laves i ét hug. Det bør ske iterativt.

Principper
1. API-laget skal være tyndt

Endpoints bør kun:

modtage request
validere input
kalde service
returnere response

Ingen reel forretningslogik i main.py.

2. Domænet skal eje reglerne

Regler som:

hvordan en træning evalueres
hvordan et match vælges
hvornår noget er “ikke planlagt”
hvordan ugekonsistens beregnes

skal ligge i domæne- eller servicelag, ikke spredt.

3. Repositories skal eje SQL

SQL bør ikke ligge blandet ind i domænelogik.

4. Services skal orkestrere workflows

Fx:

ingest + metrics + evaluate + rebuild
manuel match
webhook processing
Foreslået target-struktur
api/

HTTP-lag.

api/
├── health.py
├── activities.py
├── planning.py
├── admin.py
└── webhooks.py

Ansvar:

FastAPI routers
request parsing
status codes
response mapping
domain/

Rene domæneregler.

domain/
├── matching.py
├── planning.py
├── consistency.py
└── activities.py

Ansvar:

match-score
statusberegning
consistency-regler
små pure functions

Eksempler:

_compute_status
_candidate_score
“counts_now”
“awaiting”

Det bør være så tæt på pure functions som muligt.

services/

Use cases og orkestrering.

services/
├── planning_service.py
├── activity_service.py
├── sync_service.py
├── metrics_service.py
└── webhook_service.py

Ansvar:

kalde repositories
kalde domænefunktioner
styre transaktionsflow
sikre konsistens

Eksempler:

evaluate_and_sync()
match_activity_to_planned_run()
process_strava_webhook()
run_ingest_workflow()
repositories/

Data access.

repositories/
├── activity_repository.py
├── planned_run_repository.py
├── webhook_event_repository.py
├── sync_state_repository.py
└── metrics_repository.py

Ansvar:

SQL queries
inserts/updates/selects
ingen forretningsregler
models/

Datamodeller og schemas.

models/
├── activity.py
├── planned_run.py
├── webhook_event.py
└── dto.py

Kan være:

Pydantic response/request models
dataclasses til intern brug
db/

Database bootstrap og connection management.

db/
├── connection.py
├── schema.py
└── migrations.py

Ansvar:

get_conn
init_db
migrate_db
integrations/

Eksterne systemer.

integrations/
└── strava/
    ├── client.py
    ├── ingest.py
    └── webhook.py

Ansvar:

Strava API calls
token refresh
payload mapping
Konkrete refaktortrin
Fase 1: Tynd main.py

Lav routers eller i det mindste service-kald.

Nu

main.py importerer mange konkrete funktioner direkte.

Mål

main.py eller routers bør kalde services som:

planning_service.evaluate_planning()
planning_service.match_activity(...)
sync_service.run_ingest()
webhook_service.process_event(...)
Gevinst

Mindsker kobling og gør det lettere at teste use cases uden HTTP.

Fase 2: Flyt workflow-logik til services
Planning service

Opret services/planning_service.py.

Den bør eje:

evaluate_and_sync()
mark_skipped()
mark_rescheduled()
clear_match()
match_activity()
update_planned_run()
delete_planned_run()
Webhook service

Opret services/webhook_service.py.

Den bør eje:

process_event(payload)
Sync service

Opret services/sync_service.py.

Den bør eje:

run_ingest(pages)
run_recent_ingest_window(hours_back)
evt. efterfølgende metrics + plan workflow
Fase 3: Uddrag repositories
PlannedRunRepository

Metoder som:

list_all()
get_by_id(id)
insert(data)
update(id, data)
delete(id)
reset_auto_matches()
update_match(...)
ActivityRepository

Metoder som:

list_runs(limit)
list_candidates(...)
clear_all_matches()
set_match(planned_run_id, activity_id)
rebuild_links_from_planned_runs()
WebhookEventRepository

Metoder som:

insert_event(payload)
mark_processed(id)
Gevinst

SQL bliver samlet ét sted og kan ændres uden at rode i domænelogik.

Fase 4: Gør matching-domænet rent

Din nuværende matching.py indeholder både:

domænelogik
DB-opslag
mutations

Det bør deles.

Behold i domænet
_compute_actual_value
_compute_ratio
_compute_status
_candidate_score
Flyt ud i service/repository
select af planned rows
select af activity rows
update af matched fields
reset af DB-state
Gevinst

Match-logikken bliver testbar uden database.

Fase 5: Gør aktivitets-API til et egentligt read model endpoint

Aktivitetssiden er et godt eksempel på, at frontend i dag samler for meget selv.

Lav en read model i service/repository:

list_activity_overview(limit)
med joined planinfo og afledt status

Det er et klassisk “query model”-problem og bør løses backend-side.

Foreslået domain split
Domæne: Planning

Ansvar:

planned run status
override semantics
match lifecycle

Kernebegreber:

planned run
status
manual override
optional/mandatory
Domæne: Activities

Ansvar:

løb som fakta
afbrudt / ikke planlagt / matchet
read-model til UI
Domæne: Matching

Ansvar:

kandidatvurdering
scoring
statusudledning fra actual vs target
Domæne: Consistency

Ansvar:

ugeopgørelse
counts_now
score grøn/gul/rød
Domæne: Sync/Webhooks

Ansvar:

eksterne hændelser
ingest orchestration
idempotent behandling
Konkrete filer at skabe først

Jeg ville starte sådan her:

services/
  planning_service.py
  webhook_service.py

repositories/
  planned_run_repository.py
  activity_repository.py

domain/
  matching_rules.py
  consistency_rules.py

Det er den mindste men meningsfulde opdeling.

Forslag til ansvar pr. ny fil
services/planning_service.py

Indeholder:

evaluate_and_sync()
rebuild_activity_links()
match_activity_to_planned_run()
clear_planned_run_match()
mark_planned_run_skipped()
mark_planned_run_rescheduled()
update_planned_run()
delete_planned_run()

Dette er det vigtigste første skridt.

domain/matching_rules.py

Indeholder:

compute_actual_value(...)
compute_ratio(...)
compute_status(...)
candidate_score(...)
repositories/planned_run_repository.py

Indeholder SQL til:

hente planned runs
opdatere matchfelter
resette auto-matches
repositories/activity_repository.py

Indeholder SQL til:

hente aktiviteter
hente kandidater
rebuild links
opdatere matched_planned_run_id
Teststrategi efter refaktor
Unit tests på domæneregler

Test uden DB:

scoreberegning
statusberegning
ugekonsistens
Service tests

Test med testdatabase:

evaluate_and_sync
manual match
delete
webhook activity flow
API tests

Kun få smoke tests:

endpoints returnerer korrekt
integration fra request til response
Risici ved refaktor
1. For stor refaktor på én gang

Undgå det. Tag use case for use case.

2. Midlertidig dobbeltlogik

I en periode kan du have både gamle funktioner og nye services. Det er okay, men vær bevidst om det.

3. Navneforvirring

Brug klare navne:

planning_service
planned_run_repository
matching_rules

ikke generiske navne som utils.

Anbefalet iterativ plan
Sprint A
udtræk planning_service
lad main.py bruge den
behold eksisterende SQL i planning.py hvis nødvendigt
Sprint B
udtræk activity_repository og planned_run_repository
flyt SQL ud af service
Sprint C
udtræk matching_rules
gør matching mere testbar
Sprint D
udtræk webhook_service
ensret ingest/webhook/admin flows
Sprint E
læg read-models bag /api/activities og /api/planning
Hvad jeg ville gøre først i praksis

Hvis du vil have størst værdi først, så start her:

opret services/planning_service.py
flyt evaluate_and_sync() og match-/override-flow derover
lad main.py kun kalde planning service
flyt derefter rebuild_activity_links() med

Det vil straks gøre backend mere forståelig.

Slutmål

Det backend-design, jeg ville sigte mod, er:

routers håndterer HTTP
services styrer workflows
repositories håndterer data
domain håndterer regler
integrations håndterer Strava

Det vil passe godt til appens nuværende kompleksitet uden at blive over-engineered.