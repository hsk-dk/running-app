# Flere brugere (familie)

Appen kan bruges af flere personer. Hver person har sine egne løb, sin egen plan og sin egen kilde (Garmin Connect, Smashrun).
Andre i familien ser kun det, man selv har valgt at dele.

## Opsætning

1. **Login via Authentik (forward-auth).** Sæt `AUTH_MODE=proxy` og `TRUSTED_PROXIES` til proxyens adresse/netværk.
   Appen stoler *kun* på `X-authentik-*`-headerne fra de adresser. Backend-porten (18000) må ikke kunne nås andre
   steder end via proxyen, ellers kan headerne forfalskes.
2. **Roller via grupper.** `AUTH_ADMIN_GROUPS` (fx `homelab-admins`) giver admin, `AUTH_FAMILY_GROUPS` (fx
   `homelab-family`) giver adgang som familiemedlem. Alle andre afvises (403).
3. **Ejer af de eksisterende data.** Løb og planer fra før flere brugere overtages af den første admin, eller af
   den bruger der står i `AUTH_OWNER_USERNAME`.
4. `APP_SECRET_KEY` bør sættes til en lang tilfældig værdi (underskriver OAuth-state).

## Datakilde: Garmin Connect (anbefalet)

Garmin har et officielt **personligt API** til dine egne data
([oversigt](https://developer.garmin.com/gc-developer-program/overview)). Det er gratis, kræver ingen ansøgning og
ingen adgangskode i appen. Appen henter dine løb direkte fra Garmin, også de løb der ikke har GPS.

1. Log ind på [Garmin Connect → Personlige API-nøgler](https://connect.garmin.com/app/settings/personalApiToken) og
   opret en nøgle. Den vises **kun én gang**. Nøglen udløber efter den periode, du vælger (højst et år).
2. Indsæt den under **Mere → Mig → Garmin Connect**. Appen tjekker nøglen, gemmer den (vises aldrig igen) og henter
   hele historikken i baggrunden. Bagefter henter **Synkronisér** (Admin) nye løb.
3. Serveren skal kunne nå `https://personal.connectapi.garmin.com`.

Hvad du får, som Smashrun ikke giver:
- **Urets egen fil (FIT)** for hvert løb: tempo og puls gennem løbet, **runderne** (intervallernes trin), kilometertider
  med puls, og GPS-rute for løb udendørs. Løb på løbebånd har ingen rute, men fuld profil.
- Udendørsløb læses ved synkronisering; øvrige løb læses første gang du åbner dem (ét kald pr. løb).
- Et løb, der allerede findes fra Smashrun eller fra Strava-tiden (samme starttid inden for to minutter), tilføjes ikke igen,
  men knyttes til sin Garmin-aktivitet, så det får profil og splits.
- Familien ser aldrig din puls: hverken i profilen, rundetabellen eller pr. kilometer.
- **Udforsk (under År)** bruger det: *Dine ruter* som kontaktark, områdekort og afspilning, og *Dine løb som bjergkæde* (tempoet for de
  seneste løb, ét bjerg pr. løb). Til bjergkæden skal urets filer være læst. Det sker, når et løb åbnes, eller med knappen
  **Læs flere løb ind fra Garmin** (25 ad gangen, ét kald pr. løb, nyeste først). Animationerne slås fra ved reduceret bevægelse.

Garmin skriver, at personlig adgang ikke er til kommercielle apps med mange brugere. Hver person bruger sin egen nøgle.

## Datakilde: Smashrun (valgfri)

Garmin er hovedkilden. Smashrun kan bruges ved siden af eller i stedet
([API](https://api.smashrun.com/v1/documentation)). Smashrun-løb gemmes med negativt id og kolonnen
`source = 'smashrun'`. Et løb, der allerede findes fra en anden kilde inden for 2 minutter, tilføjes ikke en gang til.

To måder at forbinde på (under **Mere → Mig**):

1. **Personligt token (hurtigst).** Åbn API Explorer i Smashruns dokumentation, skriv `client`, tryk Connect, og
   kopiér tokenet ind i appen. Det virker ca. 12 uger og kan ikke fornyes af sig selv. Appen viser udløbsdatoen
   og advarer de sidste 14 dage. Smashrun (`api@smashrun.com`) kan forlænge det i hånden.
2. **App-nøgle (fornyer sig selv).** Bed Smashrun om en nøgle, og sæt `SMASHRUN_CLIENT_ID`,
   `SMASHRUN_CLIENT_SECRET` og evt. `SMASHRUN_REDIRECT_URI` i `.env`. Redirect-adressen hos Smashrun skal være
   `https://<dit-domæne>/api/smashrun/callback`. Nøglen må kun bruges til én applikation.

Der er ingen webhook fra Smashrun: løb hentes med knappen **Synkronisér** under Mere → Admin.

## Planen fra Runna

Hver person kan indsætte sit **Runna-kalenderlink** under Mere → Mig (i Runna-appen: *Connected Apps & Devices* →
kalender → iCalendar-link, `https://cal.runna.com/….ics`). Appen læser feeden, når du trykker **Synkronisér** under
Admin eller **Hent planen nu** under Mig.

- Kommende Runna-løb bliver planlagte løb (dato, type af navnet, mål: distance fra titlen, ellers varighed).
  Et flyttet løb opdateres, et aflyst fremtidigt løb fjernes. Løb du har rettet i hånden, løb der allerede er matchet
  med en aktivitet, og dage hvor du selv har planlagt, røres ikke.
- **Historik:** Plan-løb, som Runna lister som gennemført, bliver også til planlagte løb, så Plan-siden viser, hvad der var
  planlagt i fortiden, og hvordan det gik. Målet er distancen i løbets navn ("5km Easy Run"); et løb, der kun hedder
  det, det er (fx "Taper 400s"), har ingen planlagt distance i feeden, og så står det, du løb, i stedet. Et gennemført løb
  får kun et planlagt løb, hvis der findes et løb at matche med (ellers ville planen fejlagtigt stå som sprunget over),
  og aldrig et ekstra på en dag, der allerede har en plan. **Runna lister ikke løb, du sprang over**, så historikken viser
  kun gennemførte sessioner.
- Gennemførte løb i feeden bruges også til at give dine aktiviteter Runnas navn (`Taper 400s`), men kun hvis aktiviteten
  ikke allerede har et navn.
- Linket gemmes pr. person, vises aldrig igen i appen, og serveren henter kun adresser på `cal.runna.com`.

## Deling

Hver person vælger under **Mere → Mig**:

| Niveau | Familien ser |
|---|---|
| Privat (standard) | Intet. |
| Overblik | Navn, ugens løb, km denne måned, uger i træk. |
| Det hele | Også seneste løb (distance, tid, tempo, rute). Puls og planer deles aldrig. |

Admin har ingen ekstra indsigt i andres løb. `FAMILY_SHARING_ENABLED=false` slår al deling fra for alle.

## Opbygning og første gange (støtte, ikke konkurrence)

- **Din opbygning** og **Dine første gange** (Udforsk) måler kun dig mod din egen start: uger i gang, længste løb måned for måned, første 3/5/8/10 km, første uge med 3 løb, 10/25/50/100 løb, 4/8/12 uger i træk. Er man ny (under 20 løb eller højst 12 uger inde), vises de øverst i stedet for rekorderne.
- **Nyt i familien** (Familie) viser kun milepæle fra de seneste 21 dage ("Mads: første løb på 5 km"), fra delingsniveauet "overblik" og op. Ingen kilometer, tider eller puls, og ingen rangliste.
- Familiesiden har ikke længere en kilometerfordeling mellem personer. Samlet kilometertal pr. måned står stadig øverst.

## Anden træning (roning, gang, cykling)

Garmin-synkroniseringen gemmer også det, der ikke er løb: gang, cykling, roning, padling, svømning og styrketræning. De gemmes under deres gruppe som sportstype, så alle løbetal, rekorder, planmatch og ruter er uændrede. De vises som små prikker på årsringen og på delekortet, og de nævnes i årsfilmen og under Belastning. `GET /api/activities/other` giver kun hvad og hvornår, aldrig puls eller rute.

- Første synkronisering efter opdateringen læser hele historikken igen, én gang, for at hente det ældre (markeret med `garmin_others_read`).
- Løb under 1 km (opvarmning eller et afbrudt løb) tæller ikke i rekorder, uger i træk, belastning eller filmen.

## Strava er fjernet

Stravas API er lukket for appen (kræver abonnement), så Strava-forbindelsen, webhooken og synkroniseringen er fjernet.
Migration 12 sletter de gemte Strava-tokens og webhook-loggen. **Løbene fra Strava-tiden bliver liggende** med deres
ruter (`source = 'strava'`). Strava-variablerne i `.env` bruges ikke længere og kan fjernes.

## Flyvetur-kortet

Udforsk viser et stiliseret kort, hvor kameraet flyver mellem de steder, du har løbet. Kortet tegnes helt i browseren:

- Landegrænser kommer fra Natural Earth (public domain) og ligger som statiske filer: `europe-land.json` (ca. 113 KB, hele Europa) og `denmark-coast.json` (ca. 47 KB, detaljeret kyst om Danmark, som tones ind, når kameraet er over Danmark). Der hentes ingen kortfliser, og ingen positioner sendes til tredjepart.
- Stednavne tages fra dine løbs navne ("Horsens - …", "Horsens Løb"). Mangler de, bruges "nær <by>" ud fra `europe-towns.json`: alle danske byer over 1000 indbyggere fra GeoNames (CC BY 4.0, via github.com/lutangar/cities.json) plus et udvalg af svenske, norske og tyske byer fra Natural Earth.
- Filerne genereres med `python tools/build_map_data.py ne_50m_admin_0_countries.geojson ne_10m_populated_places_simple.geojson ne_10m_admin_0_countries.geojson cities.json` (de to sidste er valgfrie).
- Uden for Danmark er kysten grov og tones ud, når du er tæt på. Med "reducer bevægelse" vises et stillbillede i stedet for animation.

## Kendte begrænsninger

- Refresh-tokens ligger i klartekst i SQLite-databasen. Beskyt databasefilen og dens backup.
- Ruter fra Strava-tiden er Stravas forenklede polylines; nye ruter kommer fra Garmins FIT-fil. Ingen af delene er afprøvet mod rigtige data.
