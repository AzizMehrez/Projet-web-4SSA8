# ms-interview

Service Node.js de planification d’entretiens (Validation 1 : squelette qui démarre).

Port **8084**. Base **MongoDB** `interview_db`. Pas d’entité Application, Job ou Candidate : seulement `applicationId`.

## Lancer

Mongo doit tourner (port hôte **27017**).

```bash
cd Backend
docker compose up -d mongo-interview rabbitmq
cd ms-interview
npm install
npm start
```

Santé : http://localhost:8084/health (alias http://localhost:8084/actuator/health).

`npm start` quitte avec une erreur si Mongo n’est pas joignable. Eureka, le Config Server et RabbitMQ sont optionnels au démarrage local : le service logue un avertissement et continue.

## API (US-12)

Préfixe consommé par la Gateway : `/api/interviews`.

| Méthode | Chemin | Effet |
|---|---|---|
| POST | `/api/interviews` | Planifie (`201`). Corps : `applicationId`, `slot.start`, `slot.end`, `meetingUrl?`, `notes?` |
| GET | `/api/interviews/:id` | Consulte un entretien |
| GET | `/api/interviews?applicationId=` | Liste filtrée |
| PATCH | `/api/interviews/:id` | Annule si `{"status":"CANCELLED"}` |
| PATCH | `/api/interviews/:id/status` | Même annulation |
| DELETE | `/api/interviews/:id` | Annule (`204`), le document reste en `CANCELLED` |

Avant tout `POST`, le service appelle `ms-application` (`GET /api/applications/:id`) avec un timeout de 2 s, 3 tentatives et un circuit breaker (`opossum`). Si la vérification échoue : **503** et **aucune** écriture. Si la candidature n’existe pas : **404** et aucune écriture.

Après enregistrement, publication RabbitMQ de `InterviewScheduled` ou `InterviewCancelled` (échange `jobboard.events`, `eventId` UUID). Le mail n’est pas envoyé ici.

La Gateway valide le JWT Keycloak. Les routes de planification et d’annulation lisent `ROLE_RECRUITER` (en-tête `X-Roles` ou claim du Bearer). Sans rôle fourni, le squelette local accepte l’appel. `ENFORCE_RECRUITER=true` rend le rôle obligatoire.

## Fiche

Capacité : planifier et annuler un entretien lié à une candidature.

Responsabilité : le document Interview (créneau début/fin, `meetingUrl`, notes, statut `SCHEDULED` ou `CANCELLED`) et les events associés.

Interdit : recréer Application, Job ou Candidate, joindre une autre base, envoyer le mail dans la requête.

Pourquoi séparé : le créneau n’existe qu’après une candidature, avec son propre cycle de vie et un modèle document. Le coupler à `ms-application` mélangerait calendrier et dépôt de candidature.
