# Flere brugere (familie)

Appen kan bruges af flere personer. Hver person har sine egne løb, sin egen plan og sin egen Strava-forbindelse.
Andre i familien ser kun det, man selv har valgt at dele.

## Opsætning

1. **Login via Authentik (forward-auth).** Sæt `AUTH_MODE=proxy` og `TRUSTED_PROXIES` til proxyens adresse/netværk.
   Appen stoler *kun* på `X-authentik-*`-headerne fra de adresser. Backend-porten (18000) må ikke kunne nås andre
   steder end via proxyen, ellers kan headerne forfalskes.
2. **Roller via grupper.** `AUTH_ADMIN_GROUPS` (fx `homelab-admins`) giver admin, `AUTH_FAMILY_GROUPS` (fx
   `homelab-family`) giver adgang som familiemedlem. Alle andre afvises (403).
3. **Ejer af de eksisterende data.** Løb og planer fra før flere brugere overtages af den første admin, eller af
   den bruger der står i `AUTH_OWNER_USERNAME`. Den eksisterende Strava-forbindelse fra `.env` flyttes til ejeren
   ved første start.
4. **Strava-app.** `STRAVA_CLIENT_ID`/`STRAVA_CLIENT_SECRET` er fælles for appen. Sæt *Authorization Callback Domain*
   i Strava til appens domæne, og `STRAVA_REDIRECT_URI` (eller `APP_BASE_URL`) til `…/api/strava/callback`.
   Hver person forbinder derefter sin egen Strava under **Mere → Mig**.
5. `APP_SECRET_KEY` bør sættes til en lang tilfældig værdi (underskriver OAuth-state).

## Datakilde: Smashrun

Stravas API kræver nu et Strava-abonnement for appens ejer. Uden det svarer Strava `Application Inactive`, og der
hentes ingen løb. Appen kan derfor hente løb fra [Smashrun](https://api.smashrun.com/v1/documentation) i stedet
(Smashrun får løbene fra fx Garmin). Smashrun-løb gemmes med negativt id og kolonnen `source = 'smashrun'`.
Et løb, der allerede findes fra Strava inden for 2 minutter, tilføjes ikke en gang til.

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
- Gennemførte løb i feeden bruges til at give dine aktiviteter Runnas navn (`Taper 400s`), men kun hvis aktiviteten
  ikke allerede har et navn. Smashrun har ingen løbsnavne.
- Linket gemmes pr. person, vises aldrig igen i appen, og serveren henter kun adresser på `cal.runna.com`.

## Deling

Hver person vælger under **Mere → Mig**:

| Niveau | Familien ser |
|---|---|
| Privat (standard) | Intet. |
| Overblik | Navn, ugens løb, km denne måned, uger i træk. |
| Det hele | Også seneste løb (distance, tid, tempo, rute). Puls og planer deles aldrig. |

Admin har ingen ekstra indsigt i andres løb. `FAMILY_SHARING_ENABLED=false` slår al deling fra for alle.

## Vigtigt: Strava

Stravas API-aftale begrænser, at en tredjepartsapp viser én persons Strava-data til andre. Samtykke i familien
ændrer ikke aftalen. Brug deling med øje for det, hold appen privat, og brug `FAMILY_SHARING_ENABLED=false` som
nødbremse. Strava-appen er desuden som udgangspunkt begrænset til én atlet, til man får udvidet kapaciteten
(typisk op til 10) hos Strava.

## Kendte begrænsninger

- Refresh-tokens ligger i klartekst i SQLite-databasen. Beskyt databasefilen og dens backup.
- Ruter er Stravas forenklede polylines og er ikke afprøvet mod rigtige data.
