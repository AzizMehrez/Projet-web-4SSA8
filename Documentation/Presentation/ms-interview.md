# Slide 8 — ms-interview (Ezzedine, ~40 s)

## À dire

Je porte **ms-interview**, port **8084**, en **Node.js**. La capacité, c’est planifier ou annuler un entretien **après** une candidature (US-12).

Le service ne possède qu’un document Mongo `Interview` dans `interview_db` : `applicationId` (identifiant distant, pas une entité Application), le créneau début/fin, `meetingUrl`, les notes, et le statut `SCHEDULED` ou `CANCELLED`. Je ne recrée ni Candidate, ni Job, ni Application.

Avant d’écrire, un appel HTTP vers `ms-application` vérifie que la candidature existe : timeout 2 s, 3 tentatives, circuit breaker. S’il échoue, **503** et rien n’est persisté. Le mail part ensuite en asynchrone : `InterviewScheduled` et `InterviewCancelled` sur RabbitMQ, avec un `eventId`, consommés par `ms-notification`. Le mail n’est jamais dans la transaction.

La Gateway valide le JWT. La planification est prévue pour `ROLE_RECRUITER`.

Démarrage : `cd Backend/ms-interview && npm install && npm start`, avec Mongo sur le port 27017. Santé : `GET /health`.

## Pourquoi ce service existe

Le créneau a son propre cycle de vie et un modèle document. Le laisser dans `ms-application` couplerait le calendrier au dépôt de candidature et empêcherait l’équipe Node d’avancer seule.

## Schéma dessiné

`InterviewScheduled` et `InterviewCancelled` partent de **ms-interview** vers RabbitMQ, pas de `ms-candidate`. `CandidateDeleted` est le seul event de `ms-candidate`.
