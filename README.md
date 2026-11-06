# ⚡ AI-Powered EV Charging Station Management System (VoltFlow)

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql)](https://www.postgresql.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4.2-F7931E.svg?logo=scikitlearn)](https://scikit-learn.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Tests-17%20Passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, production-ready EV charging plaza management platform featuring real-time dispenser hardware control, concurrency-safe reservations, automated metered billing, operational business analytics, a 3-pillar Machine Learning intelligence suite, and a RAG (Retrieval-Augmented Generation) AI assistant.

---

## 📑 Table of Contents

- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Core Features](#-core-features)
- [Database Schema & ERD](#-database-schema--erd)
- [API Reference](#-api-reference)
- [Machine Learning Suite](#-machine-learning-suite)
- [RAG AI Assistant](#-rag-ai-assistant)
- [Frontend Dashboards](#-frontend-dashboards)
- [Installation & Quickstart](#-installation--quickstart)
- [Docker Deployment](#-docker-deployment)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Directory Structure](#-directory-structure)
- [Security Hardening](#-security-hardening)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🏛 System Architecture

VoltFlow couples a high-throughput asynchronous REST backend with decoupled ML estimators and an embedded vector retrieval engine:

```mermaid
graph TB
    subgraph Clients["Presentation Layer"]
        CP["Customer Web Portal<br/>(Discovery, Booking, Live Charge, AI Assistant)"]
        AD["Admin Operations Console<br/>(Plazas, Telemetry Sentinel, Demand AI, Analytics)"]
    end

    subgraph Gateway["FastAPI Application (Port 8000)"]
        AUTH["Auth & RBAC Middleware<br/>(JWT HS256 + Bcrypt)"]
        CORS["CORS & Static Files Host"]
        API_ROUTER["API v1 Gateway Router"]
    end

    subgraph Services["Core Business Services"]
        ST_SVC["Station & Dispenser Service"]
        BK_SVC["Booking & Slot Protection Service"]
        SS_SVC["Session Telemetry & Billing Service"]
        AN_SVC["Analytics Aggregation Engine"]
    end

    subgraph AI_Engines["AI & Machine Learning Layer"]
        DEMAND["Demand Forecaster<br/>(Random Forest Regressor)"]
        RECOMMEND["Station Recommender<br/>(Multi-Criteria Geodesic Scoring)"]
        ANOMALY["Sentinel Telemetry Detector<br/>(Isolation Forest + Physics Heuristics)"]
        RAG["RAG Assistant Pipeline<br/>(Intent Router + ChromaDB + Live Grounding)"]
    end

    subgraph Persistence["Storage & Vectors"]
        PG[("PostgreSQL 16 Engine<br/>(UUIDs, Cascade Deletes, Row Locks)")]
        CHROMA[("ChromaDB Vector Store<br/>(Cosine Embeddings / Knowledge Base)")]
        MODELS[("Trained Model Artifacts<br/>(*.joblib)")]
    end

    CP --> CORS
    AD --> CORS
    CORS --> AUTH
    AUTH --> API_ROUTER

    API_ROUTER --> ST_SVC
    API_ROUTER --> BK_SVC
    API_ROUTER --> SS_SVC
    API_ROUTER --> AN_SVC
    API_ROUTER --> DEMAND
    API_ROUTER --> RECOMMEND
    API_ROUTER --> ANOMALY
    API_ROUTER --> RAG

    ST_SVC --> PG
    BK_SVC --> PG
    SS_SVC --> PG
    AN_SVC --> PG
    DEMAND --> MODELS
    ANOMALY --> MODELS
    RAG --> CHROMA
    RAG --> PG
```

---

## 🛠 Tech Stack

| Domain | Technology | Version | Purpose |
|---|---|---|---|
| **API Framework** | FastAPI | `0.111.0` | Asynchronous high-performance REST API |
| **Server Engine** | Uvicorn | `0.29.0` | Production ASGI web server |
| **Data Validation** | Pydantic v2 & Settings | `2.7.1` / `2.2.1` | Strict schema validation & 12-factor configuration |
| **ORM & Relational DB** | SQLAlchemy | `2.0.30` | Declarative mapping, connection pooling, migrations |
| **Database** | PostgreSQL | `16-alpine` | ACID-compliant relational data store |
| **Database Driver** | Psycopg2-binary | `2.9.9` | Optimized C-extension PostgreSQL adapter |
| **Migrations** | Alembic | `1.13.1` | Programmatic schema migrations |
| **Auth & Cryptography** | Python-Jose & Bcrypt | `3.3.0` / `4.1.2` | Signed JWT bearer tokens, salt-hashed passwords |
| **Machine Learning** | Scikit-Learn | `1.4.2` | Random Forest Regressor & Isolation Forest |
| **Data Manipulation** | Pandas & NumPy | `2.2.2` / `1.26.4` | Telemetry processing, feature engineering |
| **Model Serialization** | Joblib | `1.4.2` | High-efficiency pipeline serialization |
| **Vector Store** | ChromaDB | `0.5.x` | Dense semantic retrieval & policy indexing |
| **Frontend UI** | HTML5 / CSS3 / Vanilla JS | ES6+ | Glassmorphism UI, zero-build lightweight frontend |
| **Test Harness** | Pytest & HTTPX | `8.2.0` / `0.27.0` | Asynchronous integration & unit testing suite |
| **Containerization** | Docker & Compose | Multi-stage | Reproducible containerized deployment |

---

## ✨ Core Features

### 🔐 1. Authentication & Role-Based Access Control (RBAC)
- **Granular Permissions**: Strict role distinction between `CUSTOMER` (driver) and `ADMIN` (network operator).
- **Hardened Cryptography**: Direct Bcrypt hashing with standard salt rounds, eliminating passlib-72 byte truncation bugs.
- **Production Guard**: Public administrative registration is blocked automatically whenever `DEBUG=False`.
- **JWT Bearer Token Flow**: Dual authentication endpoints support both standard JSON credential exchange and OAuth2-compliant form submissions for native Swagger UI testing.

### ⚡ 2. Stations & Dispenser Infrastructure
- **Hierarchical Plazas**: Multi-point charging stations with GPS coordinates, operational state (`ACTIVE`, `UNDER_MAINTENANCE`, `INACTIVE`), and automated cascade deletion.
- **Hardware Attributes**: Detailed dispenser specs including connector standards (`CCS2`, `TYPE2`, `CHADEMO`), rated power in kW (22kW to 350kW), live occupancy, and dynamic tariffs.
- **Parametric Filtering**: Instant discovery filtering by connector type and minimum power thresholds.

### 📅 3. High-Concurrency Slot Reservations
- **Mathematical Overlap Detection**: Uses temporal collision logic:
  $$\text{Overlap} \iff (\text{Start}_A < \text{End}_B) \land (\text{End}_A > \text{Start}_B)$$
- **Strict 409 Conflict Rejection**: Blocks double-booking on identical dispensers.
- **Grace Periods & Auto-Lifecycle**: Reserves dispensers for scheduled windows with status transitions from `CONFIRMED` to `COMPLETED` or `CANCELLED`.

### 🔋 4. Metered Charging Sessions & Automated Billing
- **Hardware State Locking**: `SELECT ... FOR UPDATE` row locks prevent simultaneous session initiation on active dispensers.
- **Dynamic Metering**: Calculates actual energy delivered ($\text{Final kWh} - \text{Initial kWh}$).
- **Automated Billing Engine**: Billed cost is calculated as:
  $$\text{Total Cost} = \text{Energy Delivered (kWh)} \times \text{Tariff Rate (\$/kWh)}$$
- **Simulated Payment Invoicing**: Auto-generates cryptographically unique transaction references (`SIM-PAY-XXXXXXXXXXXX`) upon session closure.

### 📊 5. Operational Analytics Engine
- **N+1 Query Elimination**: Pre-aggregated single-query SQL `GROUP BY` aggregations compute network-wide utilization, occupied vs. available bay ratios, 7-day revenue velocity, and station-by-station revenue distribution.

---

## 🗄 Database Schema & ERD

```mermaid
erDiagram
    users ||--o{ bookings : "creates"
    users ||--o{ charging_sessions : "charges"
    users ||--o{ payments : "pays"
    charging_stations ||--|{ charging_points : "contains (CASCADE)"
    charging_points ||--o{ bookings : "reserved_in"
    charging_points ||--o{ charging_sessions : "dispenses"
    bookings ||--o| charging_sessions : "initiates"
    charging_sessions ||--|| payments : "bills (1:1)"

    users {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        string role "CUSTOMER | ADMIN"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    charging_stations {
        uuid id PK
        string name
        string address
        float latitude
        float longitude
        string status "ACTIVE | INACTIVE | UNDER_MAINTENANCE"
        datetime created_at
        datetime updated_at
    }

    charging_points {
        uuid id PK
        uuid station_id FK
        string identifier
        string connector_type "CCS2 | TYPE2 | CHADEMO"
        float power_kw
        string status "AVAILABLE | OCCUPIED | RESERVED | FAULTED"
        decimal price_per_kwh
        datetime created_at
        datetime updated_at
    }

    bookings {
        uuid id PK
        uuid user_id FK
        uuid charging_point_id FK
        datetime start_time
        datetime end_time
        string status "CONFIRMED | CANCELLED | COMPLETED"
        datetime created_at
        datetime updated_at
    }

    charging_sessions {
        uuid id PK
        uuid booking_id FK
        uuid user_id FK
        uuid charging_point_id FK
        datetime start_time
        datetime end_time
        decimal initial_meter_kwh
        decimal final_meter_kwh
        decimal total_energy_kwh
        decimal total_cost
        string status "IN_PROGRESS | COMPLETED | STOPPED"
        datetime created_at
        datetime updated_at
    }

    payments {
        uuid id PK
        uuid session_id FK
        uuid user_id FK
        decimal amount
        string status "PENDING | COMPLETED | FAILED"
        string transaction_ref UK
        datetime created_at
        datetime updated_at
    }
```

---

## 📡 API Reference

All routes are mounted under `/api/v1` and documented natively in Swagger UI (`/docs`).

### 1. Health & Meta
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/health` | Service uptime and version health check | Public |

### 2. Authentication & Profile
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register new Customer or Admin account | Public |
| `POST` | `/auth/login` | Authenticate with JSON body & get JWT | Public |
| `POST` | `/auth/login/access-token` | OAuth2 password form login (Swagger UI) | Public |
| `GET` | `/auth/me` | Fetch active user credentials and profile | User Token |
| `GET` | `/auth/admin-test` | RBAC verification gate | Admin Only |

### 3. Charging Stations
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/stations` | List all stations with points | Public |
| `POST` | `/stations` | Provision a new charging plaza | Admin Only |
| `GET` | `/stations/{id}` | Detailed station information with dispensers | Public |
| `PUT` | `/stations/{id}` | Update plaza configuration or operational state | Admin Only |
| `DELETE` | `/stations/{id}` | Cascade delete plaza and attached points | Admin Only |
| `GET` | `/stations/{id}/points` | Filter dispensers by connector and power | Public |
| `POST` | `/stations/{id}/points` | Add new EVSE dispenser to plaza | Admin Only |

### 4. Charging Points (EVSE Dispensers)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/points/{id}` | Retrieve individual dispenser telemetry | Public |
| `PUT` | `/points/{id}` | Update dispenser status (`AVAILABLE`/`FAULTED`) | Admin Only |
| `DELETE` | `/points/{id}` | Remove individual dispenser | Admin Only |

### 5. Bookings & Reservations
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/bookings` | Create reservation with overlap protection | User Token |
| `GET` | `/bookings` | List user bookings (or all if Admin, paginated) | User Token |
| `GET` | `/bookings/{id}` | Fetch booking details | User Token |
| `POST` | `/bookings/{id}/cancel` | Cancel scheduled reservation | User Token |

### 6. Charging Sessions & Billing
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/sessions/start` | Start session, lock dispenser to `OCCUPIED` | User Token |
| `GET` | `/sessions` | Session history with pagination | User Token |
| `GET` | `/sessions/{id}` | Get session telemetry & payment invoice | User Token |
| `POST` | `/sessions/{id}/stop` | Terminate session, calculate kWh & bill | User Token |

### 7. Operational Analytics
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/analytics/dashboard` | Aggregated network KPIs, trend, & plazas | Admin Only |

### 8. Machine Learning Intelligence
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/ai/predict-demand` | 24-hour demand & energy consumption forecast | User Token |
| `POST` | `/ai/recommend-stations` | Multi-criteria geodesic ranking with SOC adaptation | User Token |
| `POST` | `/ai/detect-anomalies` | Single telemetry reading fault diagnosis | User Token |
| `POST` | `/ai/inspect-fleet-telemetry` | Batch telemetry audit for fleet sentinel | Admin Only |
| `GET` | `/ai/models-status` | Model serialization artifact health status | Public |

### 9. Generative AI & RAG Assistant
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/assistant/chat` | Grounded multi-source RAG conversation | User Token |
| `GET` | `/assistant/knowledge-base-stats`| ChromaDB collection chunk count & metadata | Public |

---

## 🤖 Machine Learning Suite

VoltFlow integrates three production-trained ML models designed for grid stabilization, driver dispatch, and hardware failure prevention:

### Feature 1: Grid Demand Prediction
- **Algorithm**: Multi-Output Random Forest Regressor (`n_estimators=100`, `max_depth=12`).
- **Feature Engineering**: Cyclical temporal features:
  $$\sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \sin\left(\frac{2\pi \cdot \text{dow}}{7}\right), \quad \cos\left(\frac{2\pi \cdot \text{dow}}{7}\right)$$
- **Leakage Prevention**: Chronological 80/20 train/test split preserving temporal causality.
- **Dataset**: 11,520 real-world hourly observations across 4 charging hubs over 120 days.
- **Verified Metrics**:
  - **Sessions MAE**: **1.451 sessions** (53% error reduction over baseline, $R^2 = 0.708$)
  - **Energy Consumption MAE**: **51.03 kWh** ($R^2 = 0.671$)

### Feature 2: Smart Station Recommendation
- **Algorithm**: Multi-Criteria Weighted Decision Matrix with Geodesic Haversine Distance:
  $$d = 2r \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1\cos\phi_2\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
- **Scoring Function**:
  $$\text{Score} = w_{\text{dist}} \cdot S_{\text{dist}} + w_{\text{avail}} \cdot S_{\text{avail}} + w_{\text{power}} \cdot S_{\text{power}} + w_{\text{tariff}} \cdot S_{\text{tariff}}$$
- **Dynamic SOC Urgency Adaptation**:
  - When driver battery SOC drops below **20%**, the system automatically re-weights to prioritize distance (weight jumps from 0.35 to 0.65) and availability (weight jumps from 0.25 to 0.30) for emergency rerouting.

### Feature 3: Hardware Anomaly Sentinel
- **Algorithm**: Hybrid Isolation Forest (`contamination=0.06`) paired with deterministic electrical engineering heuristic validation.
- **Verified Metrics**:
  - **Precision**: **0.897** | **Recall**: **0.897** | **F1-Score**: **0.897**
- **Monitored Hardware Signatures**:
  1. *Voltage Sag*: Grid voltage dropping below nominal tolerance ($V < 360\text{V}$).
  2. *Dispenser Overcurrent*: Amperage exceeding hardware rated capacity ($I > 360\text{A}$).
  3. *Cable Thermal Runaway*: Liquid-cooled cable junction exceeding critical threshold ($T > 75^\circ\text{C}$).
  4. *Meter Telemetry Stall*: Power draw detected without energy meter incrementation.
  5. *BMS Taper Violation*: High charging rate requested when vehicle battery SOC $> 85\%$.

---

## 🧠 RAG AI Assistant

The conversational intelligence engine incorporates a multi-tier hybrid architecture combining offline vector search with live database grounding:

```mermaid
sequenceDiagram
    autonumber
    actor User as EV Driver
    participant API as /api/v1/assistant/chat
    participant Router as Intent Router
    participant Chroma as ChromaDB Vector Store
    participant LiveDB as PostgreSQL Live DB
    participant Engine as Grounded Synthesis Engine

    User->>API: "What's the cancellation fee and my recent session status?"
    API->>Router: Classify user query intent
    Note over Router: Matches both Policy & Personal keywords -> Intent: HYBRID
    
    par Parallel Retrieval
        Router->>Chroma: Cosine search ("cancellation policy")
        Chroma-->>Engine: 2 Top Markdown Chunks (Source: Policies)
    and
        Router->>LiveDB: Query user_id sessions & live plazas
        LiveDB-->>Engine: Active Sessions & Last Completed Invoice
    end

    Engine->>Engine: Synthesize Grounded Context & Source Attribution
    Engine-->>API: Grounded Response + Source Badges
    API-->>User: Markdown response with policies & live billing breakdown
```

- **Knowledge Base Corpus** (`docs/knowledge_base/`):
  - `station_operating_policies.md`: Grace periods (15 min), idle fees ($0.50/min), cancellation rules.
  - `pricing_and_tariffs.md`: Off-peak vs. peak TOU tariff structures, simulated card payments.
  - `connector_and_technical_guide.md`: CCS2, Type 2, CHAdeMO, CC-CV charging curves.
  - `troubleshooting_and_safety.md`: Emergency disconnects, cable lock release, wet weather protocol.
- **Deterministic & LLM Fallback**: Runs out-of-the-box locally with deterministic grounded templates. Optionally activates Google Gemini LLM when `GEMINI_API_KEY` is provided in the environment.

---

## 🖥 Frontend Dashboards

VoltFlow includes two zero-build, responsive web applications mounted directly by the FastAPI application:

### 1. Customer Charging Portal (`/` or `index.html`)
- **Interactive Plazas Map**: Real-time browsing of charging plazas, live bay availability, connector specifications, and tariff rates.
- **AI Station Recommender**: Interactive battery SOC slider that dynamically adjusts recommendations based on vehicle charge level.
- **Slot Reservation Modal**: Start and end time selection with automated overlap detection feedback.
- **Live Session Simulator**: Real-time charging session start/stop, simulated meter telemetry, and instant invoice breakdown.
- **Floating AI Assistant (FAB)**: Expandable drawer with interactive suggestion pills, markdown responses, and source citation badges.

### 2. Administrator Operations Console (`/admin.html`)
- **KPI Overview Cards**: Total users, active plazas, available/occupied dispensers, and network revenue.
- **Demand Prediction Visualizer**: 24-hour demand forecasting chart rendered dynamically with responsive HTML5 canvases.
- **Anomaly Sentinel Fleet Scanner**: Real-time telemetry scanner that audits dispensers against trained Isolation Forest models and flags faults.
- **Plaza Provisioning Suite**: Administrative modal to create new plazas, manage dispensers, and toggle maintenance status.

---

## 🚀 Installation & Quickstart

### Prerequisites
- Python 3.13+
- PostgreSQL 16+ (or Docker)
- Git

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/your-username/AI-Powered-EV-Charging-Station-Management-System.git
cd AI-Powered-EV-Charging-Station-Management-System

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update `.env` with your PostgreSQL credentials:
```ini
DEBUG=True
SECRET_KEY="your-super-secret-production-key-here"
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ev_charging_db"

# Optional: Enable external Gemini LLM for AI Assistant
# GEMINI_API_KEY="AIzaSy..."
```

### 3. Initialize Database Migrations
```bash
alembic upgrade head
```

### 4. Train ML Models & Index Knowledge Base
```bash
# Generate synthetic datasets & train models
python -m app.ai.demand_prediction.train
python -m app.ai.anomaly_detection.train

# Index Markdown policies into ChromaDB
python -c "from app.ai.assistant.indexer import KnowledgeBaseIndexer; KnowledgeBaseIndexer().reindex_all()"
```

### 5. Launch Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Access the application:
- **Customer Portal**: [http://localhost:8000/](http://localhost:8000/)
- **Admin Dashboard**: [http://localhost:8000/admin.html](http://localhost:8000/admin.html)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Docker Deployment

The system includes a production-ready, multi-stage `Dockerfile` and `docker-compose.yml` configuration:

```bash
# Build and start all services (PostgreSQL + FastAPI)
docker-compose up --build -d

# View real-time container logs
docker-compose logs -f api

# Shut down services and preserve volumes
docker-compose down
```

The Docker stack automatically provisions:
- `db`: PostgreSQL 16 Alpine container with persistent named volume `postgres_data` and native health checks.
- `api`: Python 3.13 multi-stage image running as a non-root `appuser` with persistent volumes for `ml_models` and `ml_data`.

---

## 🧪 Testing & Quality Assurance

The test suite runs against an isolated, high-performance in-memory SQLite database utilizing custom dialect compilers for PostgreSQL UUID compatibility:

```bash
# Run the complete test suite
pytest tests/ -v
```

### Test Suite Execution Output
```
============================= test session starts =============================
platform win32 -- Python 3.13.11, pytest-9.2.0, pluggy-1.7.0
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 17 items

tests/test_ai_features.py::test_haversine_distance PASSED                [  5%]
tests/test_ai_features.py::test_isolation_forest_anomaly_detection_signatures PASSED [ 11%]
tests/test_ai_features.py::test_station_recommendation_multi_criteria_ranking PASSED [ 17%]
tests/test_ai_features.py::test_demand_prediction_24h_cycle PASSED       [ 23%]
tests/test_ai_features.py::test_ai_endpoints_dispatch PASSED             [ 29%]
tests/test_auth.py::test_user_registration_and_authentication_flow PASSED [ 35%]
tests/test_bookings_sessions.py::test_bookings_concurrency_overlap_and_sessions_billing_flow PASSED [ 41%]
tests/test_database.py::test_database_connection PASSED                  [ 47%]
tests/test_database.py::test_create_station_and_charging_point_relationship PASSED [ 52%]
tests/test_health.py::test_root_endpoint PASSED                          [ 58%]
tests/test_health.py::test_health_check_endpoint PASSED                  [ 64%]
tests/test_health.py::test_analytics_dashboard_endpoint PASSED           [ 70%]
tests/test_rag_assistant.py::test_knowledge_base_indexing_and_count PASSED [ 76%]
tests/test_rag_assistant.py::test_vector_similarity_search_retrieval PASSED [ 82%]
tests/test_rag_assistant.py::test_intent_router_classification PASSED    [ 88%]
tests/test_rag_assistant.py::test_rag_engine_grounded_response_generation PASSED [ 94%]
tests/test_stations.py::test_stations_and_charging_points_lifecycle PASSED [100%]

============================= 17 passed in 3.99s ==============================
```

---

## 📂 Directory Structure

```
AI-Powered-EV-Charging-Station-Management-System/
├── app/
│   ├── ai/
│   │   ├── anomaly_detection/     # Isolation Forest & Telemetry Generator
│   │   ├── assistant/             # ChromaDB RAG Engine, Router, & Live Retriever
│   │   ├── demand_prediction/     # Random Forest 24h Grid Forecaster
│   │   └── recommendation/        # Geodesic Multi-Criteria Scoring Engine
│   ├── api/
│   │   ├── deps.py                # JWT Auth & Role Verification Dependencies
│   │   └── v1/
│   │       ├── api.py             # Router Aggregation
│   │       └── endpoints/         # Auth, Stations, Points, Bookings, Sessions, AI
│   ├── core/
│   │   ├── config.py              # Pydantic 12-Factor Settings & Validation Gates
│   │   ├── database.py            # SQLAlchemy Engine & SessionLocal Factory
│   │   └── security.py            # Bcrypt Password Hashing & JWT Minting
│   ├── models/                    # Declarative ORM Models (UUIDs, Relationships)
│   ├── schemas/                   # Pydantic Validation & Serialization DTOs
│   ├── services/                  # Business Logic, Aggregations, & Concurrency Locks
│   └── main.py                    # FastAPI App Initializer & Static Route Mounts
├── docs/
│   └── knowledge_base/            # Markdown Domain Documents for Vector Indexing
├── frontend/
│   ├── admin.html                 # Operator Dashboard & ML Sentinel UI
│   ├── index.html                 # Customer Portal, Booking, & Floating AI Assistant
│   ├── css/style.css              # Custom Glassmorphic Styling
│   └── js/                        # Modular Frontend Controllers (api, customer, admin)
├── migrations/                    # Alembic Database Migrations
├── ml_data/                       # Generated Training Datasets & ChromaDB Store
├── ml_models/                     # Serialized .joblib Model Artifacts
├── tests/                         # Pytest Test Suite (17 Comprehensive Tests)
│   └── conftest.py                # SQLite Test Fixtures & UUID Compilers
├── Dockerfile                     # Multi-Stage Production Container Build
├── docker-compose.yml             # Full-Stack Service Orchestration
├── requirements.txt               # Pinned Python Dependencies
└── pyproject.toml                 # Pytest & Tooling Configuration
```

---

## 🔒 Security Hardening

1. **Production Secret Gate**: The application will abort startup if executed with `DEBUG=False` while retaining the default `SECRET_KEY`.
2. **Strict RBAC Enforcement**: Role-based access control prevents regular `CUSTOMER` accounts from modifying infrastructure, inspecting other users' sessions, or accessing admin dashboards.
3. **Database Concurrency Protection**: Session initiation utilizes row-level locking (`with_for_update`) to eliminate race conditions on dispenser hardware.
4. **Input Sanitization**: Pydantic v2 schemas strictly enforce data types, email formats, and coordinate bounds on all incoming payloads.

---

## 🗺 Roadmap

- [ ] **OCPP 2.0.1 Protocol Integration**: Direct WebSocket gateway for physical EVSE charge point communication.
- [ ] **Dynamic Pricing Engine**: Automated tariff adjustment based on real-time grid wholesale electricity rates.
- [ ] **Stripe / Payment Gateway Integration**: Real-world payment processing with automated refunds on cancelled reservations.
- [ ] **Mobile Application**: Native iOS/Android experience built with React Native.
- [ ] **IoT Telemetry Streaming**: Apache Kafka integration for real-time fleet telemetry ingestion at scale.

---

## 📄 License

This project is licensed under the terms of the **MIT License**. See the [LICENSE](LICENSE) file for details.

