# ms-notification — Microservice de Notification & Messagerie Événementielle

> **Projet** : JobBoard / TalentConnect — AWD ESPRIT 2026-2027  
> **Responsable** : Dhia Jbali  
> **Technologie** : Python 3.12+, FastAPI, RabbitMQ, SMTP  
> **Port** : `8085`  
> **Architecture** : MVC Modulaire, Microservice Indépendant, Event-Driven

---

## 1. Description du Service

`ms-notification` est le 5ᵉ microservice (« microservice avancé » polyglotte) de la plateforme **TalentConnect**.
Sa mission est de consommer de manière asynchrone les événements métier publiés sur le bus de messages **RabbitMQ** par les services amont (`ms-application`, `ms-interview`, `ms-job`) et d'assurer l'expédition fiable et idempotente de notifications par e-mail au format HTML enrichi aux candidats et utilisateurs.

### Principes Directeurs d'Architecture

1. **Non-bloquant & Asynchrone** : L'envoi de notification (I/O e-mail / SMTP) ne fait jamais partie de la transaction synchrone d'écriture de candidature (`POST /applications`). La cohérence est **éventuelle**.
2. **Pas de base de données partagée** : Aucune dépendance à une base métier externe (`candidate_db`, `job_db`, `application_db`, `interview_db`). Une base locale SQLite dédiée (`data/notifications.db`) assure la persistance isolée de l'idempotence et des journaux d'audit.
3. **Idempotence stricte (`eventId` UUID)** : Tout événement reçu possède un identifiant unique `eventId`. Un événement dupliqué n'est jamais réexpédié deux fois par e-mail.
4. **Résilience RabbitMQ** : Reconnexion automatique, files durables, accusé de réception manuel (ACK/NACK), mécanisme de Dead Letter Queue (DLQ) et retries avec backoff.
5. **Découplage strict** : Le service n'implémente aucune règle métier appartenant à d'autres bounded contexts.

---

## 2. Architecture MVC

Le service est structuré selon le pattern **MVC (Modèle - Vue - Contrôleur)** adapté aux microservices modernes FastAPI :

```
ms-notification/
│
├── app/
│   ├── main.py                     # Point d'entrée FastAPI & gestionnaire de cycle de vie (lifespan)
│   │
│   ├── config/                     # Configuration centralisée & logging
│   │   ├── __init__.py
│   │   ├── settings.py             # Validation des variables d'environnement (pydantic-settings)
│   │   └── logging_config.py       # Journalisation structurée et masquage des secrets
│   │
│   ├── controllers/                # Contrôleurs HTTP (Points d'entrée REST)
│   │   ├── __init__.py
│   │   ├── health_controller.py    # Health check (/health, /health/ready, /actuator/health)
│   │   └── notification_controller.py # Ping, audit logs (/api/notifications), test manuel
│   │
│   ├── models/                     # Modèles internes de données
│   │   ├── __init__.py
│   │   ├── event_model.py          # Modèle d'événement pour l'idempotence
│   │   └── notification_model.py   # Modèle de log d'audit de notification
│   │
│   ├── schemas/                    # Contrats d'événements et schémas Pydantic
│   │   ├── __init__.py
│   │   ├── event_schema.py         # Schéma de base BaseEvent (UUID eventId, occurredAt)
│   │   ├── application_schema.py   # ApplicationCreated, ApplicationStatusChanged
│   │   ├── interview_schema.py     # InterviewScheduled, InterviewCancelled
│   │   └── job_schema.py           # JobAvailabilityChanged
│   │
│   ├── services/                   # Couche Métier (Business Services)
│   │   ├── __init__.py
│   │   ├── notification_service.py # Façade haut-niveau d'orchestration
│   │   ├── event_processor.py      # Traitement, validation et routage des événements AMQP
│   │   ├── email_service.py        # Expédition SMTP (TLS/SSL) & simulation
│   │   └── template_service.py     # Moteur de templates Jinja2 & convertisseur texte
│   │
│   ├── repositories/               # Couche d'Accès aux Données locales (Idempotence)
│   │   ├── __init__.py
│   │   └── event_repository.py     # SQLite thread-safe pour eventId et logs d'audit
│   │
│   ├── messaging/                  # Couche RabbitMQ (AMQP)
│   │   ├── __init__.py
│   │   ├── rabbitmq_config.py      # Topologie (échanges, files, DLX, DLQ, routing keys)
│   │   ├── rabbitmq_connection.py  # Gestion de connexion pika avec health probe
│   │   └── rabbitmq_consumer.py    # Consommateur en arrière-plan (thread daemon avec auto-reconnect)
│   │
│   └── templates/                  # Vues HTML (Templates E-mail Jinja2)
│       ├── base.html               # Layout général TalentConnect responsive
│       ├── application_created.html
│       ├── application_status_changed.html
│       ├── interview_scheduled.html
│       └── interview_cancelled.html
│
├── data/                           # Répertoire de la base SQLite locale isolée
│
├── tests/                          # Suite complète de tests unitaires et d'intégration
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures Pytest (client, base temporaire, mocks)
│   ├── test_health.py              # Tests des sondes de santé et endpoints HTTP
│   ├── test_events.py              # Tests de validation des 5 événements et erreurs
│   ├── test_email.py               # Tests SMTP, templates et conversion texte
│   ├── test_idempotency.py         # Tests anti-doublon, persistance et concurrence
│   └── test_rabbitmq.py            # Tests de ACK / NACK / DLQ et retry
│
├── .env.example                    # Modèle des variables d'environnement
├── .env                            # Configuration locale active
├── .gitignore                      # Exclusions Git
├── requirements.txt                # Dépendances Python déclarées
├── Dockerfile                      # Image Docker de production avec Healthcheck
└── README.md                       # Documentation complète
```

---

## 3. Catalogue des Événements Consommés

| Événement | Producteur | File RabbitMQ | Routing Key | Action Notification |
|---|---|---|---|---|
| `ApplicationCreated` | `ms-application` | `notification.application.created` | `application.created` | E-mail de confirmation au candidat avec numéro de dossier et référence offre |
| `ApplicationStatusChanged` | `ms-application` | `notification.application.status_changed` | `application.status.changed` | E-mail informant le candidat de la mise à jour de son statut (ex: DÉPOSÉE → EN ATTENTE / ACCEPTÉE) |
| `InterviewScheduled` | `ms-interview` | `notification.interview.scheduled` | `interview.scheduled` | Convocation par e-mail avec date/heure, lien visio (Meet/Teams) et consignes |
| `InterviewCancelled` | `ms-interview` | `notification.interview.cancelled` | `interview.cancelled` | Avis d'annulation avec motif au candidat |
| `JobAvailabilityChanged` | `ms-job` | `notification.job.availability_changed` | `job.availability.changed` | Enregistrement de l'état du catalogue dans le journal d'audit (aucun e-mail non sollicité) |

### Format des Payloads

Tous les payloads doivent inclure un `eventId` au format UUID valide :

```json
{
  "eventId": "e9b28b6d-a34f-4d6f-9988-123456789abc",
  "applicationId": 42,
  "candidateId": 105,
  "jobId": 12,
  "email": "candidat@esprit.tn",
  "candidateName": "Mohamed Aziz",
  "jobTitle": "Développeur Backend Python",
  "occurredAt": "2026-11-15T10:30:00Z"
}
```

---

## 4. Stratégie de Résilience & RabbitMQ

- **Échange principal** : `jobboard.exchange` (type `topic`, durable).
- **Dead Letter Exchange (DLX)** : `jobboard.dlx` (type `direct`, durable).
- **Dead Letter Queue (DLQ)** : `notification.dlq` (liée avec la clé `notification.dead_letter`).
- **Politique de traitement** :
  - **Succès ou Doublon** : `basic_ack` immédiat.
  - **Erreur permanente** (JSON invalide, UUID manquant, violation de contrat) : rejet avec `basic_nack(requeue=False)` pour transfert direct vers la DLQ, évitant tout blocage de la file d'attente.
  - **Erreur temporaire** (ex. coupure SMTP, indisponibilité réseau) : réexpédition avec incrément du header `x-retry-count`. Après 3 échecs (`RABBITMQ_MAX_RETRIES`), le message est acheminé vers la DLQ.
- **Reconnexion transparente** : Le consommateur s'exécute dans un thread d'arrière-plan autonome appliquant un backoff exponentiel en cas de déconnexion du courtier RabbitMQ.

---

## 5. Idempotence & Stockage Local

Le microservice applique le principe de dédoublonnage strict via la table SQLite locale `processed_events` :
- Chaque `eventId` reçu est vérifié avant exécution.
- Si l'ID a déjà été traité avec succès, l'opération est sautée avec accusé de réception (`ACK`), garantissant qu'un candidat ne recevra jamais deux fois le même e-mail lors d'un réacheminement de message.
- La persistance locale survit aux redémarrages du conteneur sans faire appel à une base de données partagée.

---

## 6. Endpoints REST (FastAPI)

| Méthode | URL | Description | Statut |
|---|---|---|---|
| `GET` | `/health` | Sonde de vivacité (Liveness) | 200 OK |
| `GET` | `/health/ready` | Sonde d'état complet (Readiness) vérifiant RabbitMQ et SQLite | 200 OK / 503 |
| `GET` | `/actuator/health` | Compatibilité Spring Boot Actuator pour API Gateway et Eureka | 200 OK |
| `GET` | `/api/notifications/ping` | Endpoint ping d'origine pour compatibilité | 200 OK |
| `GET` | `/api/notifications` | Consultation de l'historique d'audit des notifications | 200 OK |
| `POST` | `/api/notifications/test` | Émission d'une notification de test (protégée hors dev) | 200 OK |
| `GET` | `/docs` | Documentation interactive Swagger OpenAPI | 200 OK |

---

## 7. Variables d'Environnement

Le fichier `.env` contrôle la configuration :

| Variable | Défaut | Description |
|---|---|---|
| `APP_NAME` | `ms-notification` | Nom du service |
| `APP_ENV` | `development` | Environnement (`development`, `production`, `test`) |
| `APP_PORT` | `8085` | Port HTTP d'écoute |
| `APP_HOST` | `0.0.0.0` | Adresse d'écoute réseau |
| `DEBUG` | `false` | Mode debug FastAPI |
| `RABBITMQ_HOST` | `localhost` | Hôte du broker RabbitMQ (`rabbitmq` sous Docker) |
| `RABBITMQ_PORT` | `5672` | Port AMQP |
| `RABBITMQ_USER` | `guest` | Nom d'utilisateur RabbitMQ |
| `RABBITMQ_PASSWORD` | `guest` | Mot de passe RabbitMQ |
| `RABBITMQ_EXCHANGE` | `jobboard.exchange` | Nom de l'échange topic |
| `RABBITMQ_CONSUMER_ENABLED` | `true` | Active/désactive le thread de consommation AMQP |
| `SMTP_ENABLED` | `false` | `true` pour envoi réel via SMTP, `false` pour mode simulation |
| `SMTP_HOST` | `localhost` | Serveur SMTP (ex. `smtp.gmail.com` ou MailHog) |
| `SMTP_PORT` | `1025` | Port SMTP (587 pour TLS, 465 pour SSL, 1025 pour MailHog) |
| `SMTP_USER` | `""` | Identifiant SMTP |
| `SMTP_PASSWORD` | `""` | Mot de passe d'application SMTP |
| `SMTP_USE_TLS` | `false` | Activer STARTTLS |
| `DATABASE_PATH` | `data/notifications.db` | Chemin du fichier SQLite local |

---

## 8. Commandes d'Exécution Locale (Windows PowerShell)

### Étape 1 : Créer et activer un environnement virtuel Python

```powershell
# Se positionner dans le dossier du microservice
cd "c:\Users\dhiaj_onolvpc\Downloads\web (3)\web\Backend\ms-notification"

# Créer l'environnement virtuel (Python 3.12+)
python -m venv venv

# Activer l'environnement virtuel
.\venv\Scripts\Activate.ps1
```

### Étape 2 : Installer les dépendances

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Étape 3 : Configurer l'environnement

```powershell
# Copier le modèle si .env n'existe pas
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### Étape 4 : Lancer les tests unitaires et d'intégration

```powershell
$env:PYTHONPATH = "."
pytest tests -v
```

### Étape 5 : Démarrer le microservice FastAPI sur le port 8085

```powershell
$env:PYTHONPATH = "."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8085 --reload
```

Le service est accessible sur :
- **Swagger UI** : [http://localhost:8085/docs](http://localhost:8085/docs)
- **Health Liveness** : [http://localhost:8085/health](http://localhost:8085/health)
- **Health Readiness** : [http://localhost:8085/health/ready](http://localhost:8085/health/ready)
- **Actuator Health** : [http://localhost:8085/actuator/health](http://localhost:8085/actuator/health)
- **Ping** : [http://localhost:8085/api/notifications/ping](http://localhost:8085/api/notifications/ping)

### Étape 6 : Tester une notification manuelle

```powershell
Invoke-RestMethod -Uri "http://localhost:8085/api/notifications/test" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"to_email": "candidat@esprit.tn", "template_name": "application_created.html"}'
```

---

## 9. Déploiement avec Docker & Docker Compose

### Construction de l'image Docker seule

```powershell
cd "c:\Users\dhiaj_onolvpc\Downloads\web (3)\web\Backend\ms-notification"
docker build -t ms-notification:latest .
```

### Exécution complète avec la stack backend

```powershell
cd "c:\Users\dhiaj_onolvpc\Downloads\web (3)\web\Backend"
docker compose up -d rabbitmq ms-notification
```

Vérifier les logs du conteneur :
```powershell
docker compose logs -f ms-notification
```

---

## 10. Dépannage & FAQ

**Q1. Pourquoi uvicorn échoue avec `command not found` ?**  
Utilisez `python -m uvicorn app.main:app --port 8085` car l'exécutable uvicorn n'est pas toujours ajouté au PATH de Windows.

**Q2. Que faire si RabbitMQ n'est pas démarré lors des tests locaux ?**  
Le service est résilient : il continue d'écouter les requêtes HTTP, marque la sonde `/health/ready` comme `DEGRADED`, et retente automatiquement la connexion RabbitMQ avec backoff sans crasher l'application.

**Q3. Comment tester l'envoi d'e-mails réels ?**  
Renseignez vos identifiants SMTP dans `.env` :
```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre.email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe_application
SMTP_USE_TLS=true
```
Lorsque `SMTP_ENABLED=false`, les e-mails sont simulés et tracés dans la base SQLite locale sans générer d'erreur réseau.
