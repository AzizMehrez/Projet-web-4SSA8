# I1 + I2 — Design détaillé de chaque microservice

Ports / noms / DB **identiques** à `README.md`, `docker-compose.yml` et au code.

---

## 1. ms-candidate — Mohamed Aziz Mehrez — :8081 — MySQL `candidate_db`

### Pourquoi MySQL
Relation 1–1 Candidate↔Address, contraintes UNIQUE email, alignement monolithe pédagogique.

### Modèle (voir `Diagrams/er-candidate.mmd`)

| Entité | Attribut | Type | Contraintes |
|---|---|---|---|
| Address | id | BIGINT | PK |
| | street | VARCHAR(150) | NOT NULL |
| | houseNumber | VARCHAR(10) | NOT NULL |
| | zipCode | VARCHAR(10) | NOT NULL |
| Candidate | id | BIGINT | PK |
| | firstname | VARCHAR(50) | NOT NULL |
| | lastname | VARCHAR(50) | NOT NULL |
| | email | VARCHAR(150) | UNIQUE NOT NULL |
| | addressId | BIGINT | FK **locale** → Address (même DB) |

Relation : Candidate 0..1 — 1 Address (même bounded context).

### API REST

| Resource | URI | Method | Body | Response | Status |
|---|---|---|---|---|---|
| candidates | `/api/candidates` | GET | — | `Candidate[]` (page) | 200 |
| candidates | `/api/candidates/{id}` | GET | — | `Candidate` | 200, 404 |
| candidates | `/api/candidates` | POST | `{firstname,lastname,email,address?}` | `Candidate` + Location | 201, 400, 409 |
| candidates | `/api/candidates/{id}` | PUT | idem | `Candidate` | 200, 400, 404, 409 |
| candidates | `/api/candidates/{id}` | DELETE | — | — | 204, 404, 409 |
| candidates | `/api/candidates/{id}/address/{addressId}` | PUT | — | `Candidate` | 200, 404, 409 |
| candidates | `/api/candidates/{id}/address` | DELETE | — | `Candidate` | 200, 404 |
| addresses | `/api/addresses` | GET | — | `Address[]` | 200 |
| addresses | `/api/addresses/{id}` | GET | — | `Address` | 200, 404 |
| addresses | `/api/addresses` | POST | `{street,houseNumber,zipCode}` | `Address` | 201, 400 |
| addresses | `/api/addresses/{id}` | PUT | idem | `Address` | 200, 400, 404 |
| addresses | `/api/addresses/{id}` | DELETE | — | — | 204, 404 |

**Validation** : Bean Validation (`@Email`, `@NotBlank`, tailles).  
**Pagination** : `GET /api/candidates?page=0&size=20` (prévu).  
**Noms pluriels**, CREATE → 201 + `Location`.

### Interactions (I2)

| Direction | Service | Mode | Données |
|---|---|---|---|
| Appelé par | ms-application | Feign GET `/api/candidates/{id}` | profil résumé |
| Appelle (opt.) | ms-application | Feign | existence candidatures avant delete |
| Publie | RabbitMQ | async | `CandidateDeleted` |

**Si down** : appelant → timeout 2s, retry×3, CB Resilience4j, fallback 503, pas d’écriture métier fantôme.

---

## 2. ms-job — Mohamed Rayen Sboui — :8082 — MySQL `job_db`

### Pourquoi MySQL
Jobs + catégories relationnels, index `available`, même stack que candidate pour simplicité ops, **bases séparées**.

### Modèle (`Diagrams/er-job.mmd`)

| Entité | Attribut | Type | Contraintes |
|---|---|---|---|
| Category | id | BIGINT | PK |
| | name | VARCHAR(100) | UNIQUE NOT NULL |
| | description | VARCHAR(500) | |
| Job | id | BIGINT | PK |
| | name | VARCHAR(100) | NOT NULL |
| | description | VARCHAR(1000) | |
| | available | BOOLEAN | NOT NULL |
| | date | DATE | NOT NULL |
| | categoryId | BIGINT | FK **locale** → Category |

### API REST

| Resource | URI | Method | Body | Response | Status |
|---|---|---|---|---|---|
| jobs | `/api/jobs` | GET | query `available`,`categoryId`,`page`,`size` | `Job[]` | 200, 404 si category inconnue |
| jobs | `/api/jobs/{id}` | GET | — | `Job` | 200, 404 |
| jobs | `/api/jobs` | POST | `{name,description,available,date,categoryId}` | `Job` | 201, 400, 404 |
| jobs | `/api/jobs/{id}` | PUT | idem | `Job` | 200, 400, 404 |
| jobs | `/api/jobs/{id}/availability` | PATCH | query `available` | `Job` | 200, 404 |
| jobs | `/api/jobs/{id}` | DELETE | — | — | 204, 404, 409 |
| categories | `/api/categories` | GET/POST | … | … | 200/201, 400, 409 |
| categories | `/api/categories/{id}` | GET/PUT/DELETE | … | … | 200/204, 400, 404, 409 |
| categories | `/api/categories/{id}/jobs` | GET | — | `Job[]` | 200, 404 |

### Interactions (I2)

| Direction | Service | Mode | Données |
|---|---|---|---|
| Appelé par | ms-application | Feign | job + `available` |
| Publie | RabbitMQ | async | `JobAvailabilityChanged` |

**Failure** : idem timeout / retry / CB / 503 fail-fast côté candidature.

---

## 3. ms-application — Maryem Slatni — :8083 — PostgreSQL `application_db`

### Pourquoi PostgreSQL
Montrer *polyglot persistence* ; UNIQUE `(candidate_id, job_id)` robuste ; **pas** de FK vers MySQL distant — seulement des Long IDs.

### Modèle (`Diagrams/er-application.mmd`)

| Attribut | Type | Notes |
|---|---|---|
| id | BIGINT | PK |
| applicationDate | DATE | NOT NULL |
| motivation | VARCHAR(2000) | |
| status | VARCHAR(30) | SUBMITTED, UNDER_REVIEW, INTERVIEW, … |
| candidateId | BIGINT | **référence logique** (pas de FK cross-DB) |
| jobId | BIGINT | **référence logique** |

### API REST

| Resource | URI | Method | Body | Response | Status |
|---|---|---|---|---|---|
| applications | `/api/applications` | GET | `candidateId?`,`jobId?`,`page`,`size` | `Application[]` | 200, 404 si filtre ID inconnu (via Feign) |
| applications | `/api/applications/{id}` | GET | — | `Application` | 200, 404 |
| applications | `/api/applications` | POST | `{candidateId,jobId,motivation,applicationDate?}` | `Application` | 201, 400, 404, 409 |
| applications | `/api/applications/{id}` | PUT | `{motivation,applicationDate}` | `Application` | 200, 400, 404 |
| applications | `/api/applications/{id}` | PATCH | `{status}` | `Application` | 200, 400, 404 |
| applications | `/api/applications/{id}` | DELETE | — | — | 204, 404 |

**Règles 409** : job non disponible ; double candidature.  
**Pas** d’URI `/api/candidates/.../applications` hébergée ici sans reverse-proxy clair — le filtre query respecte REST et évite de « posséder » la ressource candidate.

### Interactions (I2)

| Direction | Service | Mode | Données |
|---|---|---|---|
| Appelle | ms-candidate, ms-job | **Feign sync** | validation existence / available |
| Appelé par | ms-interview (HTTP sync), (opt.) ms-candidate (Feign) | sync | `applicationId` |
| Publie | RabbitMQ | async | `ApplicationCreated`, `ApplicationStatusChanged` |
| Consomme | RabbitMQ | async | `JobAvailabilityChanged` (cohérence éventuelle) |

**Failure plan** :  
1. Feign timeout 2s  
2. Retry ×3 (transitoire)  
3. Circuit breaker open → fallback 503 ProblemDetail  
4. **Jamais** de candidature sauvegardée si validation sync échoue  
5. Si RabbitMQ down après commit : log + retry publish → notif éventuellement cohérente  
6. Consumers notif **idempotents** (`eventId`)

---

## 4. ms-interview — Mohamed Ezzedine Zouiten — :8084 — Node.js — MongoDB `interview_db`

### Capacité, responsabilités, interdits, pourquoi séparé
**Capacité** : planifier et annuler un entretien lié à une candidature (US-12).  
**Responsabilités** : document `Interview` (créneau début/fin, `meetingUrl`, notes, statut), vérification synchrone que la candidature existe, publication de `InterviewScheduled` / `InterviewCancelled`.  
**Interdits** : aucune entité `Application`, `Job` ou `Candidate` ; pas de jointure cross-DB ; le mail n’est pas envoyé dans la requête.  
**Pourquoi séparé** : le créneau apparaît après la candidature, avec un cycle de vie et un modèle document propres. Le coupler à `ms-application` mélangerait calendrier et dépôt de candidature.

### Pourquoi MongoDB
Document Interview avec champs optionnels variables (lien visio, notes) ; pas de schéma relationnel critique. Stack **Node.js** (Express, Mongoose).

### Modèle (`Diagrams/er-interview.mmd`)

| Champ | Type | Notes |
|---|---|---|
| id | String/ObjectId | PK |
| applicationId | String | identifiant distant uniquement |
| slot.start / slot.end | DateTime | créneau |
| status | String | `SCHEDULED`, `CANCELLED` |
| meetingUrl | String | optionnel |
| notes | String | optionnel |

### API REST

| Resource | URI | Method | Body | Response | Status |
|---|---|---|---|---|---|
| interviews | `/api/interviews` | GET | `applicationId?`,`page`,`size` | `Interview[]` | 200 |
| interviews | `/api/interviews/{id}` | GET | — | `Interview` | 200, 404 |
| interviews | `/api/interviews` | POST | `{applicationId, slot:{start,end}, meetingUrl?, notes?}` | `Interview` | 201, 400, 404, 503 |
| interviews | `/api/interviews/{id}/status` | PATCH | `{status:CANCELLED, reason?}` | `Interview` | 200, 400, 404 |
| interviews | `/api/interviews/{id}` | PATCH | idem | `Interview` | 200, 400, 404 |
| interviews | `/api/interviews/{id}` | DELETE | — | — | 204, 404 |

DELETE et PATCH **annulent** (statut `CANCELLED`) : le document reste consultable. PUT hors squelette V1.

### Interactions (I2)

| Direction | Service | Mode |
|---|---|---|
| Appelle | ms-application | HTTP sync (axios, timeout 2 s, 3 tentatives, circuit breaker opossum) |
| Publie | RabbitMQ | `InterviewScheduled`, `InterviewCancelled` (`eventId` UUID) |

**Failure** : vérification en échec → **503** et **aucune** écriture. Candidature absente → **404**, aucune écriture. Le mail est publié après l’enregistrement (cohérence éventuelle). La Gateway valide le JWT ; planification / annulation ciblent `ROLE_RECRUITER`.

---

## 5. ms-notification — Dhia Jbali — :8085 — Python FastAPI (avancé)

### Pourquoi avancé / pas de DB métier
Polyglotte (Python) ; messaging RabbitMQ comme cœur ; I/O e-mail (+ LLM optionnel) hors chemin critique. Pas de vérité métier → pas de DB partagée.

### Modèle logique
`NotificationLog` optionnel : `{id, eventId, channel, recipient, status, sentAt}` — local uniquement.

### API REST

| Resource | URI | Method | Body | Response | Status |
|---|---|---|---|---|---|
| health | `/actuator/health` | GET | — | `{status}` | 200 |
| notifications | `/api/notifications/ping` | GET | — | `{status,service}` | 200 |
| notifications | `/api/notifications` | GET | — | historique (futur) | 200 |

### Interactions (I2)

| Direction | Mode | Events |
|---|---|---|
| Consomme | async RabbitMQ | ApplicationCreated, ApplicationStatusChanged, InterviewScheduled, InterviewCancelled, (opt.) JobAvailabilityChanged |
| N’appelle **pas** les MS métier en sync | — | évite monolithe distribué |

**Failure** : si service down → messages en queue ; au redémarrage, consommation idempotente. Si LLM down → template texte fixe.
