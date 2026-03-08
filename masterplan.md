# LogiSense — Master Plan

> **Unified Warehouse & Cold Chain Intelligence Platform**
> Open-Source · Modular · License-Per-Module · Cloud-Agnostic
> Version 1.0 | Confidential

---

## Table of Contents

1. [Vision & Mission](#1-vision--mission)
2. [Platform Name & Identity](#2-platform-name--identity)
3. [Problem Statement](#3-problem-statement)
4. [Solution Overview](#4-solution-overview)
5. [Module Catalogue](#5-module-catalogue)
6. [Open-Source Technology Stack](#6-open-source-technology-stack)
7. [Platform Architecture](#7-platform-architecture)
8. [Data Platform Design](#8-data-platform-design)
9. [Licensing Model](#9-licensing-model)
10. [Security Architecture](#10-security-architecture)
11. [Monorepo Structure](#11-monorepo-structure)
12. [Development Roadmap](#12-development-roadmap)
13. [Phase 0 — Immediate Action Plan](#13-phase-0--immediate-action-plan)
14. [Team & Roles](#14-team--roles)
15. [Success Metrics](#15-success-metrics)
16. [Architecture Decision Records (ADRs)](#16-architecture-decision-records-adrs)

---

## 1. Vision & Mission

### Vision

> To become the **operating system of intelligent warehouse and cold chain operations** — the platform that distribution centers, 3PLs, and cold chain operators worldwide depend on to eliminate inefficiency, ensure compliance, and compete at the speed of AI.

### Mission

Build a **single, unified, open-source-first platform** that delivers enterprise-grade warehouse intelligence, cold chain visibility, AI-powered labor optimization, and computer vision analytics — available as independently licensable modules so every operator can start small and scale to full platform capability.

### Core Beliefs

- **Open source wins long-term.** No operator should be locked into a proprietary vendor for core warehouse operations infrastructure.
- **One platform beats six point solutions.** A shared data foundation makes every module smarter.
- **Module-based licensing removes adoption barriers.** Operators pay for capability, not bloat.
- **AI should be explainable and auditable.** Every recommendation must be traceable to data.
- **Privacy is non-negotiable.** No facial recognition. No raw video in the cloud. No biometric tracking.

---

## 2. Platform Name & Identity

| Attribute         | Value                                                              |
| ----------------- | ------------------------------------------------------------------ |
| **Platform Name** | **LogiSense**                                                      |
| **Tagline**       | _See Everything. Optimize Everything._                             |
| **Core Promise**  | One platform. Six modules. Zero lock-in.                           |
| **License Model** | Per-module subscription                                            |
| **Deployment**    | Self-hosted (K8s), Cloud-managed, or Hybrid                        |
| **Source Model**  | Open-core (platform + modules OSS; enterprise features commercial) |

---

## 3. Problem Statement

Distribution centers and cold chain operators face four critical, compounding pain points:

```
┌─────────────────────────────────────────────────────────────────┐
│  PAIN POINT           │  INDUSTRY COST                          │
├─────────────────────────────────────────────────────────────────┤
│  Inventory Inaccuracy │  $180B+ in misplaced/phantom inventory  │
│  Labor Inefficiency   │  15–22% of DC operating cost wasted     │
│  Fulfillment Slowness │  4–8 hr avg order cycle time in manual  │
│  Zero Cold Chain Viz  │  $35B+ annual cold chain loss globally  │
└─────────────────────────────────────────────────────────────────┘
```

**Root Cause:** Most DCs run 3–7 disconnected point solutions — a WMS, a labor tool, a temperature logger, a BI tool — each with its own data silo. There is no unified intelligence layer.

**LogiSense's Answer:** One platform. One data lake. Six modules. Full operational intelligence.

---

## 4. Solution Overview

LogiSense is architected as **one unified platform with six independently licensable modules**, all sharing:

- A single **Apache Iceberg** data lakehouse (on MinIO)
- A single **Apache Kafka** event bus
- A single **Keycloak** identity and RBAC system
- A single **Kong** API gateway with license enforcement
- A single **observability stack** (Prometheus + Grafana + Loki + Tempo)

Each module is a **self-contained FastAPI microservice** with its own:

- Kubernetes namespace and Helm chart
- PostgreSQL schema (shared cluster, isolated schema)
- React micro-frontend (loaded via Webpack Module Federation)
- MLflow model registry namespace (for AI modules)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         LOGISENSE PLATFORM                           │
│                                                                      │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │
│   │MOD-01│  │MOD-02│  │MOD-03│  │MOD-04│  │MOD-05│  │MOD-06│      │
│   │ iWMS │  │ LIP  │  │ CCVP │  │ PISE │  │ WCVP │  │ UOIH │      │
│   └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘      │
│      └─────────┴─────────┴─────────┴─────────┴─────────┘           │
│                          Shared Platform Core                        │
│      Kafka · Iceberg/MinIO · Keycloak · Kong · Vault · K8s          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Module Catalogue

### MOD-01 — Intelligent Warehouse Management (iWMS)

**License Tier:** Tier 1
**Pain Points:** Inventory Accuracy, Order Fulfillment Speed

| Capability                 | Description                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| Real-Time Inventory Ledger | Bin/LP-level inventory tracked in real time via PostgreSQL event sourcing                 |
| AI-Guided Putaway          | Optimal bin assignment on receipt using velocity, temperature zone, FEFO, and utilization |
| Wave Planning              | AI-optimized pick wave batching by zone, carrier deadline, SLA tier                       |
| Directed Workflows         | RF/voice-directed picking, receiving, putaway, cycle count — device agnostic              |
| Cross-Docking              | Inbound lines matched to open outbound orders and bypassed to staging                     |
| FEFO Enforcement           | First Expired, First Out enforced at directed pick level                                  |
| Cycle Count AI             | Error-risk-scored bin prioritization for directed cycle counts                            |

**Key Tech:** FastAPI · PostgreSQL 16 · Redis · Kafka · OpenSearch · React Native · LightGBM (slotting)

---

### MOD-02 — AI Labor Intelligence (LIP)

**License Tier:** Tier 2
**Pain Points:** Labor Efficiency

| Capability                   | Description                                                                      |
| ---------------------------- | -------------------------------------------------------------------------------- |
| Demand-Driven Forecasting    | Predicts required DC labor hours 7–14 days ahead by role and shift               |
| AI Schedule Generation       | OR-Tools constraint solver producing legally compliant, cost-minimized schedules |
| Real-Time Productivity       | Live picks/hr by worker and team, updated every 5 minutes from iWMS task feed    |
| Fatigue & Cold Room Rotation | Enforces cold room rotation limits and ergonomic load tracking                   |
| Compliance Automation        | Multi-jurisdiction labor law rules engine — configurable per country/state       |
| Worker Mobile App            | Schedule view, shift confirmation, swap requests via React Native PWA            |

**Key Tech:** FastAPI · PostgreSQL 16 · OR-Tools · Prophet · LightGBM · Kafka consumer · React Native

---

### MOD-03 — Cold Chain Visibility & Compliance (CCVP)

**License Tier:** Tier 2
**Pain Points:** Visibility & Tracking, Inventory Accuracy

| Capability                | Description                                                           |
| ------------------------- | --------------------------------------------------------------------- |
| Real-Time IoT Monitoring  | Continuous temp/humidity from all cold zones via MQTT → TimescaleDB   |
| Excursion Detection       | Apache Flink stream processing detects breaches in < 10 seconds       |
| Automated Compliance Hold | Affected lots auto-held in iWMS on excursion, pending QM release      |
| Chain of Custody          | Full lot traceability from supplier receipt to dispatch — audit-ready |
| HACCP Auto-Documentation  | Continuous CCP monitoring with one-click regulatory export            |
| Predictive Maintenance    | ML anomaly detection on compressor/equipment sensor patterns          |
| FEFO Registry             | Lot expiry database feeding iWMS directed pick sequence               |
| OTA Sensor Firmware       | Eclipse Hawkbit manages firmware updates for all IoT sensor devices   |

**Key Tech:** FastAPI · TimescaleDB · Eclipse Mosquitto · Apache Flink · MLflow · Scikit-learn · WeasyPrint · Eclipse Hawkbit

---

### MOD-04 — Predictive Inventory & Slotting (PISE)

**License Tier:** Tier 3
**Pain Points:** Inventory Accuracy, Order Fulfillment Speed

| Capability                    | Description                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------- |
| Dynamic Slotting Optimization | LightGBM + OR-Tools continuously optimizes slot assignments by velocity, ergonomics, co-picks |
| Seasonal Re-Slotting          | Auto-generates re-slotting plans ahead of peak seasons using demand forecasts                 |
| Demand-Aligned Positioning    | Pre-positions inventory in forward picks ahead of predicted demand spikes                     |
| AI Cycle Count Prioritization | Error-risk model scores every bin daily; generates AI-prioritized count lists                 |
| Root Cause Analysis           | Identifies systematic causes of inventory discrepancy by zone, SKU class, supplier            |

**Key Tech:** FastAPI · PostgreSQL 16 · LightGBM · OR-Tools · Feast · MLflow · Prophet · Kafka producer

---

### MOD-05 — Warehouse Computer Vision (WCVP)

**License Tier:** Tier 3
**Pain Points:** Inventory Accuracy, Labor Efficiency, Visibility & Tracking

| Capability                 | Description                                                                    |
| -------------------------- | ------------------------------------------------------------------------------ |
| Dock Activity Monitoring   | License plate recognition at yard; dwell time tracking per dock door           |
| PPE Compliance Detection   | Hard hat, hi-vis, safety footwear detection per zone — configurable thresholds |
| Forklift/Pedestrian Safety | Real-time conflict detection and overspeed alerts in shared zones              |
| Receiving Verification     | Pallet/case counting at dock — discrepancy flagging vs. PO/ASN                 |
| Zone Occupancy             | Real-time headcount by zone vs. planned staffing — feeds LIP alerts            |
| Anomaly Detection          | Autoencoder behavioral scoring for loss prevention zones                       |
| Edge-Only Processing       | All inference on Jetson — no raw video transmitted to cloud                    |
| OTA Model Updates          | Eclipse Hawkbit manages YOLOv8 model weight and runtime updates                |

**Key Tech:** NVIDIA Jetson AGX Orin · DeepStream 6.x · YOLOv8 (Ultralytics) · ByteTrack · Eclipse Mosquitto · PyTorch · OpenCV · Hawkbit

> ⚠️ **Privacy Guarantee:** WCVP uses anonymous bounding-box person detection only. No facial recognition. No biometric data. No raw video stored or transmitted.

---

### MOD-06 — Unified Operations Intelligence Hub (UOIH)

**License Tier:** Tier 1
**Pain Points:** All (reporting and intelligence layer)

| Capability                  | Description                                                          |
| --------------------------- | -------------------------------------------------------------------- |
| Apache Superset Dashboards  | Self-service analytics on all Gold-layer data — no BI license cost   |
| Role-Based Dashboard Shell  | Custom React dashboards per persona (Supervisor → COO)               |
| Unified Alert Inbox         | Aggregates alerts from all modules with escalation workflows         |
| Automated Report Engine     | Airflow + Jinja2 + WeasyPrint scheduled PDF/email reports            |
| KPI Computation             | dbt models transform Gold-layer data into standardized KPI tables    |
| Multi-Channel Notifications | Apprise OSS: Email, Slack, Teams, PagerDuty, SMS — single sender     |
| External Data API           | Exposes Gold-layer datasets via Iceberg REST catalog for external BI |

**Key Tech:** FastAPI · Apache Superset · React + Recharts · dbt · Airflow · Apprise · WeasyPrint · Alertmanager

---

## 6. Open-Source Technology Stack

### By Layer

```
LAYER                   OSS TECHNOLOGY              REPLACES
─────────────────────────────────────────────────────────────────────
Container Orchestration  K3s / K8s (CNCF)            AKS / EKS / GKE (managed)
Service Mesh             Istio                        AWS App Mesh
API Gateway              Kong OSS                     Azure API Management
Identity & Auth          Keycloak                     Azure AD / Okta
Policy Engine            Open Policy Agent (OPA)      Azure AD Conditional Access
Object Storage           MinIO (S3-compatible)        AWS S3 / Azure Data Lake
Table Format             Apache Iceberg               Databricks Delta Lake
Data Processing          Apache Spark 3.5             Databricks Runtime
Stream Processing        Apache Flink 1.19            Azure Stream Analytics
Message Bus              Apache Kafka (Strimzi)       Azure Event Hub
Workflow Orchestration   Apache Airflow 2.9           Azure Data Factory
Feature Store            Feast 0.40                   Databricks Feature Store
ML Lifecycle             MLflow 2.13                  Azure ML / SageMaker
Model Serving            BentoML / Seldon Core        Azure ML Endpoints
Time-Series DB           TimescaleDB                  Azure Data Explorer
Operational DB           PostgreSQL 16                Cosmos DB / DynamoDB
Cache                    Redis OSS 7.2                Azure Cache for Redis
Search                   OpenSearch 2.x               Azure Cognitive Search
IoT Broker               Eclipse Mosquitto            Azure IoT Hub
Edge AI Runtime          DeepStream + TensorRT        Azure IoT Edge modules
CV Models                YOLOv8 (Ultralytics OSS)     Custom proprietary models
Dashboards               Apache Superset              Power BI / Tableau
Metrics                  Prometheus + Grafana         Azure Monitor
Logs                     Loki + Promtail              Azure Log Analytics
Tracing                  Tempo + OpenTelemetry        Azure App Insights
Alerting                 Alertmanager                 PagerDuty (self-managed)
Secret Management        HashiCorp Vault              Azure Key Vault
Container Registry       Harbor                       Azure Container Registry
CI/CD                    Gitea Actions / GH Actions   Azure DevOps
IaC                      Terraform OSS + Helm         ARM Templates
API Framework            FastAPI (Python)             Azure Functions
Frontend                 React + Vite + Tailwind      Power Apps
Mobile / RF              React Native / PWA           Vendor RF terminals
Schema Registry          Apicurio (OSS)               Confluent Schema Registry
Feature Flags            Unleash OSS                  LaunchDarkly
Data Quality             Great Expectations           Azure Data Quality
Data Catalog             Apache Atlas / Nessie        Azure Purview
OTA Updates              Eclipse Hawkbit              Azure IoT Hub DPS
```

### Proprietary Dependencies (Minimized)

| Component                | Why Needed                                            | Can Be Replaced With                                  |
| ------------------------ | ----------------------------------------------------- | ----------------------------------------------------- |
| NVIDIA Jetson (hardware) | No OSS edge GPU equivalent at required inference perf | Hailo-8 accelerator on Raspberry Pi (lower accuracy)  |
| GPU compute (training)   | Speed of training — not a runtime dependency          | CPU-only training (slower, viable for smaller models) |
| Managed K8s (optional)   | Operational convenience only                          | K3s or RKE2 on bare metal                             |

---

## 7. Platform Architecture

### Architectural Layers

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — CLIENT                                                            │
│  React Web UI (Module Federation shell)                                      │
│  React Native Mobile/RF App    Apache Superset (BI)    External API clients  │
├──────────────────────────────────────────────────────────────────────────────┤
│  LAYER 2 — API & SECURITY                                                    │
│  Kong API Gateway  ·  Keycloak OAuth2/OIDC  ·  OPA Policy Engine            │
│  Istio mTLS (service mesh)  ·  License Service (JWT module validation)       │
├────────────┬────────────┬─────────────┬───────────┬──────────┬──────────────┤
│  MOD-01    │  MOD-02    │   MOD-03    │  MOD-04   │  MOD-05  │  MOD-06      │
│  iWMS      │  LIP       │   CCVP      │  PISE     │  WCVP    │  UOIH        │
│  :8001     │  :8002     │   :8003     │  :8004    │  :8005   │  :8006       │
│  ns:iwms   │  ns:lip    │   ns:ccvp   │  ns:pise  │  ns:wcvp │  ns:uoih     │
├────────────┴────────────┴─────────────┴───────────┴──────────┴──────────────┤
│  LAYER 3 — SHARED SERVICES                                                   │
│  Kafka (Strimzi)  ·  Redis  ·  HashiCorp Vault  ·  OpenSearch               │
│  Eclipse Mosquitto (IoT)  ·  Harbor Registry  ·  Alertmanager  ·  Unleash   │
├──────────────────────────────────────────────────────────────────────────────┤
│  LAYER 4 — DATA & AI PLATFORM                                                │
│  MinIO ──▶ Apache Iceberg (Bronze/Silver/Gold)                               │
│  Apache Spark (batch ETL)  ·  Apache Flink (stream ETL)                     │
│  Apache Airflow (orchestration)  ·  dbt (SQL transforms)                    │
│  Feast (feature store)  ·  MLflow (model registry)  ·  BentoML (serving)    │
│  TimescaleDB (IoT time-series)  ·  PostgreSQL 16 (operational)               │
├──────────────────────────────────────────────────────────────────────────────┤
│  LAYER 5 — EDGE (Physical Store / DC)                                        │
│  NVIDIA Jetson (CV inference)  ·  IoT Sensors (temp/humidity)                │
│  Eclipse Mosquitto edge broker  ·  Eclipse Hawkbit (OTA)                    │
├──────────────────────────────────────────────────────────────────────────────┤
│  LAYER 6 — OBSERVABILITY                                                     │
│  Prometheus  ·  Grafana  ·  Loki  ·  Tempo  ·  OpenTelemetry  ·  Alertmgr  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Module Communication Patterns

| Pattern               | Used For                                                        | Technology                            |
| --------------------- | --------------------------------------------------------------- | ------------------------------------- |
| Synchronous REST      | External API calls, UI data fetching, inter-module queries      | FastAPI over HTTPS via Kong           |
| Async Event Streaming | Inventory events, CV events, sensor telemetry, task completions | Apache Kafka (Strimzi)                |
| IoT Telemetry         | Sensor readings and edge CV events to cloud                     | Eclipse Mosquitto MQTT → Kafka bridge |
| Internal Service mTLS | All service-to-service communication inside K8s                 | Istio automatic mTLS                  |
| Feature Store Read    | ML model inference feature retrieval                            | Feast SDK (gRPC)                      |

---

## 8. Data Platform Design

### Medallion Architecture

```
RAW SOURCES
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BRONZE  (minio://logisense-bronze/)                                 │
│  Raw ingest — append only — Iceberg tables — 90 day retention        │
│  Sources: iWMS events, IoT telemetry, CV events, ERP imports         │
└──────────────────────┬──────────────────────────────────────────────┘
                       │  Apache Flink (streaming) + Spark (batch)
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SILVER  (minio://logisense-silver/)                                 │
│  Cleaned · Enriched · Deduplicated · Joined — 2 year retention       │
│  Great Expectations validation gates on all pipelines                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │  dbt models (SQL) + Spark
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GOLD  (minio://logisense-gold/)                                     │
│  KPI tables · Feature store snapshots · ML training datasets         │
│  Dashboard aggregates — indefinite retention                         │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
    Feast Feature Store       Apache Superset
    (ML inference)            (Dashboards)
```

### Key Iceberg Table Namespaces

| Namespace           | Owner Module   | Key Tables                                               |
| ------------------- | -------------- | -------------------------------------------------------- |
| `bronze.iwms`       | MOD-01         | `inventory_movements`, `task_events`, `wave_events`      |
| `bronze.ccvp`       | MOD-03         | `sensor_readings`, `excursion_events`, `lot_registry`    |
| `bronze.wcvp`       | MOD-05         | `cv_events`, `dock_events`, `safety_events`              |
| `silver.inventory`  | MOD-01/04      | `inventory_positions`, `order_lines`, `shipments`        |
| `silver.cold_chain` | MOD-03         | `lot_temperature_history`, `compliance_records`          |
| `silver.labor`      | MOD-02         | `schedules`, `productivity_actuals`, `compliance_checks` |
| `gold.kpis`         | MOD-06         | `dc_daily_kpis`, `cold_chain_kpis`, `labor_efficiency`   |
| `gold.features`     | All ML modules | `sku_velocity_features`, `equipment_health_features`     |

### Kafka Topic Naming Convention

```
logisense.{module}.{entity}.{event_type}

Examples:
  logisense.iwms.inventory.movement
  logisense.iwms.wave.released
  logisense.ccvp.sensor.reading
  logisense.ccvp.lot.excursion
  logisense.wcvp.zone.occupancy
  logisense.wcvp.dock.truck_arrival
  logisense.lip.schedule.published
  logisense.pise.slotting.recommendation
```

---

## 9. Licensing Model

### Tier Structure

| Tier                         | Modules Included                      | Use Case                                 |
| ---------------------------- | ------------------------------------- | ---------------------------------------- |
| **Core** _(always included)_ | Platform infrastructure only          | Not separately sold                      |
| **Tier 1 — Visibility**      | MOD-01 (iWMS) + MOD-06 (UOIH)         | Start with inventory control + reporting |
| **Tier 2 — Operations**      | Tier 1 + MOD-02 (LIP) + MOD-03 (CCVP) | Cold chain operators + labor management  |
| **Tier 3 — Intelligence**    | All 6 modules                         | Full AI-powered DC operations            |
| **Custom**                   | Any module combination                | Single module or non-standard bundle     |

### License Enforcement Flow

```
Client Request
      │
      ▼
Kong API Gateway
      │
      ├── Extract Bearer JWT
      ├── Call License Service: validate(tenant_id, module_id)
      │         │
      │         ├── Valid license → 200 OK → proxy to module service
      │         └── Invalid/missing → 402 Payment Required
      │
      ▼
Module FastAPI Service
      │
      └── On startup: verify LOGISENSE_LICENSE_KEY env var
                      register with License Service
                      fail fast if module not licensed
```

### License JWT Claims

```json
{
  "sub": "tenant_abc123",
  "tenant_id": "tenant_abc123",
  "tenant_name": "Acme Distribution Co.",
  "licensed_modules": ["MOD-01", "MOD-03", "MOD-06"],
  "facility_count": 5,
  "tier": "custom",
  "exp": 1767225600,
  "iss": "logisense-license-service"
}
```

---

## 10. Security Architecture

### Zero Trust Stack

| Layer              | Technology                       | Purpose                                        |
| ------------------ | -------------------------------- | ---------------------------------------------- |
| Identity Provider  | **Keycloak 24+**                 | OAuth2/OIDC, SSO, MFA, LDAP federation         |
| API Auth           | **Kong + Keycloak OIDC plugin**  | JWT validation on every request                |
| Authorization      | **Open Policy Agent (OPA)**      | RBAC + ABAC policies as code                   |
| Service Mesh       | **Istio 1.20+**                  | Automatic mTLS, traffic policies               |
| Secrets            | **HashiCorp Vault 1.16+**        | Dynamic secrets, PKI, DB credential rotation   |
| Network Policy     | **Cilium + K8s NetworkPolicy**   | Pod-level segmentation, deny-by-default        |
| Container Security | **Trivy + Falco**                | Image scanning (CI) + runtime threat detection |
| IoT Auth           | **Mosquitto + TLS client certs** | Per-device X.509 certificates                  |
| Encryption at Rest | **MinIO SSE (AES-256)**          | All lakehouse data encrypted                   |
| Audit Logs         | **OpenTelemetry + Loki**         | Tamper-evident structured audit events         |

### RBAC Roles

```
PLATFORM_ADMIN          → All modules, all tenants
TENANT_ADMIN            → All licensed modules for tenant
FACILITY_MANAGER        → All licensed modules, assigned facility
WAREHOUSE_OPERATOR      → MOD-01 operations, own task queue
LABOR_MANAGER           → MOD-02 full access, assigned facility
COLD_CHAIN_QUALITY      → MOD-03 full access + lot data
ANALYST_READ_ONLY       → MOD-06 read-only, aggregated data only
LOSS_PREVENTION         → MOD-05 alerts and reports
API_INTEGRATION         → Scoped per client credentials grant
```

---

## 11. Monorepo Structure

```
logisense/
├── .github/                        # GitHub Actions CI/CD workflows
│   └── workflows/
│       ├── ci.yml                  # Lint, test, scan, build
│       ├── deploy-dev.yml
│       ├── deploy-staging.yml
│       └── deploy-prod.yml
│
├── platform/                       # Shared platform services
│   ├── api-gateway/                # Kong declarative config (deck)
│   ├── identity/                   # Keycloak realm export / Terraform
│   ├── license-service/            # FastAPI license JWT issuer + validator
│   ├── data-platform/
│   │   ├── iceberg/                # Nessie catalog config
│   │   ├── spark/                  # Spark Operator config + base images
│   │   ├── airflow/                # DAGs, plugins, connections
│   │   ├── flink/                  # Flink jobs (Bronze ingest, Silver ETL)
│   │   └── feast/                  # Feature repo definitions
│   ├── messaging/                  # Strimzi Kafka operator + topic configs
│   ├── storage/                    # MinIO Helm values, bucket policies
│   ├── secret-management/          # Vault policies, PKI, dynamic secrets
│   └── observability/              # Prometheus rules, Grafana dashboards, Loki config
│
├── modules/
│   ├── iwms/                       # MOD-01
│   │   ├── api/                    # FastAPI service (Python)
│   │   ├── ui/                     # React micro-frontend
│   │   ├── mobile/                 # React Native RF/mobile app
│   │   ├── ml/                     # Slotting model training (MLflow)
│   │   ├── db/                     # Alembic migrations (PostgreSQL)
│   │   ├── helm/                   # Helm chart
│   │   └── tests/                  # pytest + integration tests
│   │
│   ├── lip/                        # MOD-02
│   │   ├── api/                    # FastAPI service
│   │   ├── ui/                     # React micro-frontend
│   │   ├── mobile/                 # Worker PWA
│   │   ├── optimizer/              # OR-Tools schedule solver
│   │   ├── ml/                     # Demand forecast models (MLflow)
│   │   ├── db/                     # Alembic migrations
│   │   ├── helm/
│   │   └── tests/
│   │
│   ├── ccvp/                       # MOD-03
│   │   ├── api/                    # FastAPI service
│   │   ├── ui/                     # React micro-frontend
│   │   ├── iot/                    # Mosquitto config, sensor schemas
│   │   ├── flink-jobs/             # Real-time excursion detection jobs
│   │   ├── ml/                     # Equipment anomaly models (MLflow)
│   │   ├── compliance/             # HACCP report templates (Jinja2)
│   │   ├── hawkbit/                # IoT OTA configuration
│   │   ├── db/                     # TimescaleDB + PostgreSQL migrations
│   │   ├── helm/
│   │   └── tests/
│   │
│   ├── pise/                       # MOD-04
│   │   ├── api/                    # FastAPI service
│   │   ├── ui/                     # React micro-frontend
│   │   ├── ml/                     # Slotting + error risk models (MLflow)
│   │   ├── db/                     # Alembic migrations
│   │   ├── helm/
│   │   └── tests/
│   │
│   ├── wcvp/                       # MOD-05
│   │   ├── api/                    # FastAPI service (cloud side)
│   │   ├── ui/                     # React micro-frontend
│   │   ├── ml/                     # Anomaly detection models (MLflow)
│   │   ├── db/                     # Alembic migrations
│   │   ├── helm/
│   │   └── tests/
│   │
│   └── uoih/                       # MOD-06
│       ├── api/                    # FastAPI service
│       ├── ui/                     # React dashboard shell + Superset config
│       ├── dbt/                    # dbt models (Silver → Gold KPI transforms)
│       ├── reports/                # Jinja2 report templates
│       ├── db/                     # Alembic migrations
│       ├── helm/
│       └── tests/
│
├── edge/                           # WCVP edge code (NVIDIA Jetson)
│   ├── deepstream-pipeline/        # DeepStream app config + plugins
│   ├── yolo-models/                # YOLOv8 training scripts + model weights
│   ├── mqtt-publisher/             # Structured event publisher to Mosquitto
│   ├── hawkbit-client/             # OTA update client
│   └── Dockerfile.jetson           # arm64 container for Jetson
│
├── infra/                          # Infrastructure as Code
│   ├── terraform/
│   │   ├── aws/                    # EKS, RDS, MSK, S3
│   │   ├── azure/                  # AKS, PostgreSQL, Event Hub
│   │   ├── gcp/                    # GKE, Cloud SQL, Pub/Sub
│   │   └── bare-metal/             # Ansible + K3s + MetalLB
│   └── helm/
│       ├── platform/               # Umbrella chart: all platform services
│       └── modules/                # Per-module charts (iwms, lip, ccvp, etc.)
│
├── dbt/                            # Shared dbt project (Gold layer transforms)
│   ├── models/
│   │   ├── silver/                 # Silver enrichment models
│   │   └── gold/                   # KPI and feature gold models
│   └── profiles.yml
│
├── ml/                             # Shared ML training infrastructure
│   ├── base/                       # Base training image, MLflow client utils
│   ├── slotting/                   # MOD-01/04 slotting models
│   ├── labor-forecast/             # MOD-02 demand forecast models
│   ├── cold-chain/                 # MOD-03 equipment anomaly models
│   └── cv-models/                  # MOD-05 YOLOv8 training pipelines
│
├── docs/                           # All documentation
│   ├── masterplan.md               # ← THIS FILE
│   ├── adr/                        # Architecture Decision Records
│   │   ├── ADR-001-iceberg-vs-delta.md
│   │   ├── ADR-002-keycloak-vs-zitadel.md
│   │   ├── ADR-003-fastapi-vs-grpc.md
│   │   └── ADR-004-minio-vs-seaweedfs.md
│   ├── api/                        # OpenAPI specs per module
│   └── runbooks/                   # Ops runbooks
│
└── scripts/                        # Developer utility scripts
    ├── dev-bootstrap.sh            # Local dev environment setup
    ├── seed-demo-data.py           # Demo data generator
    └── license-issue.py            # Dev license key generator
```

---

## 12. Development Roadmap

### Phase Overview

```
TIMELINE  ──────────────────────────────────────────────────────────────────▶
           M1   M2   M3   M4   M5   M6   M7   M8   M9  M10  M11  M12
PHASE 0    ████████████
Foundation

PHASE 1              ████████████████████
Inventory+Intel

PHASE 2                        ████████████████████
Cold Chain+Labor

PHASE 3                                   ████████████████████████
AI+Vision

PHASE 4                                              ████████████████████████
Enterprise
```

### Phase 0 — Foundation (Months 1–3)

**Goal:** Working platform skeleton. No modules yet. Every engineer can run the full stack locally.

- [ ] Monorepo initialization (Nx or Turborepo)
- [ ] Platform Helm charts: Kong, Keycloak, Kafka (Strimzi), MinIO, Vault, PostgreSQL, Redis
- [ ] Apache Iceberg + Nessie catalog on MinIO — Bronze/Silver/Gold namespaces created
- [ ] Apache Airflow deployment + first DAG skeleton
- [ ] Prometheus + Grafana + Loki + Tempo observability stack
- [ ] HashiCorp Vault with dynamic PostgreSQL credentials
- [ ] Keycloak realm with base RBAC roles defined
- [ ] Kong API gateway with Keycloak OIDC plugin
- [ ] License Service — JWT issuance + Kong validation plugin
- [ ] CI/CD: GitHub Actions (lint, test, scan, build, push to Harbor)
- [ ] Terraform modules for AWS (EKS) and bare-metal (K3s via Ansible)
- [ ] Apicurio Schema Registry for Kafka Avro schemas
- [ ] Unleash feature flag service
- [ ] React shell app with Module Federation skeleton (no modules loaded)
- [ ] OpenAPI spec contracts for all 6 module APIs (spec-first)
- [ ] ADR documents for all major technology decisions
- [ ] `dev-bootstrap.sh` — single command local dev environment via Docker Compose

**Exit Criteria:** Any engineer can run `./scripts/dev-bootstrap.sh` and have a fully working platform skeleton in < 15 minutes.

---

### Phase 1 — Inventory & Intelligence (Months 3–6)

**Goal:** MOD-01 (iWMS) and MOD-06 (UOIH) production-ready. First paying customer capable.

- [ ] MOD-01 iWMS: PostgreSQL schema + Alembic migrations
- [ ] MOD-01 iWMS: FastAPI service — all inventory, task, wave, receipt, shipment endpoints
- [ ] MOD-01 iWMS: Kafka producers for all inventory movement events
- [ ] MOD-01 iWMS: React web UI — inventory management, wave management dashboards
- [ ] MOD-01 iWMS: React Native RF/mobile app — directed picking, receiving, putaway workflows
- [ ] MOD-01 iWMS: OpenSearch integration for SKU/location search
- [ ] MOD-01 iWMS: AI cycle count prioritization (LightGBM error risk model — MLflow)
- [ ] MOD-06 UOIH: Airflow Bronze→Silver→Gold pipelines for iWMS data
- [ ] MOD-06 UOIH: dbt models for iWMS KPI Gold tables
- [ ] MOD-06 UOIH: Apache Superset configured with iWMS Gold tables
- [ ] MOD-06 UOIH: Custom React dashboards — Warehouse Operations, Inventory Intelligence
- [ ] MOD-06 UOIH: Unified alert inbox with Alertmanager integration
- [ ] MOD-06 UOIH: Apprise multi-channel notification sender
- [ ] Integration: ERP (SAP/Oracle) connector — PO/ASN ingest, GR posting outbound
- [ ] Integration: Barcode scanner (ZXing) and RFID (LLRP) device support
- [ ] License Service: Tier 1 license issuance and enforcement
- [ ] Load testing: 10,000 inventory transactions/second throughput validation

**Exit Criteria:** A DC operator can receive goods, manage bin-level inventory, run pick waves, ship orders, and view real-time KPIs — entirely on LogiSense.

---

### Phase 2 — Cold Chain & Labor (Months 6–9)

**Goal:** MOD-02 (LIP) and MOD-03 (CCVP) production-ready. Cold chain compliance customers capable.

- [ ] MOD-03 CCVP: TimescaleDB schema for sensor telemetry
- [ ] MOD-03 CCVP: Eclipse Mosquitto MQTT broker + Kafka bridge
- [ ] MOD-03 CCVP: Apache Flink job — real-time excursion detection from sensor stream
- [ ] MOD-03 CCVP: FastAPI service — sensor data, excursions, lot registry, compliance records
- [ ] MOD-03 CCVP: Auto-hold integration with iWMS (Kafka event → iWMS hold workflow)
- [ ] MOD-03 CCVP: HACCP PDF report generation (WeasyPrint + Jinja2)
- [ ] MOD-03 CCVP: Equipment anomaly ML model (Scikit-learn autoencoder — MLflow)
- [ ] MOD-03 CCVP: Eclipse Hawkbit OTA firmware update service
- [ ] MOD-03 CCVP: React UI — Cold Chain Monitor dashboard
- [ ] MOD-02 LIP: PostgreSQL schema for workers, schedules, availability, compliance rules
- [ ] MOD-02 LIP: OR-Tools constraint solver integration — schedule generation
- [ ] MOD-02 LIP: Prophet + LightGBM labor demand forecast models (MLflow)
- [ ] MOD-02 LIP: Real-time productivity feed (Kafka consumer from iWMS task events)
- [ ] MOD-02 LIP: Worker mobile PWA — schedule, confirmation, swap requests
- [ ] MOD-02 LIP: Compliance rules engine — multi-jurisdiction labor law configs
- [ ] MOD-02 LIP: Cold room rotation tracking and enforcement
- [ ] License Service: Tier 2 license issuance

**Exit Criteria:** A cold chain DC can monitor all temperature zones in real time, auto-generate compliance documentation, and run AI-optimized labor schedules with full legal compliance.

---

### Phase 3 — AI & Vision (Months 9–14)

**Goal:** MOD-04 (PISE) and MOD-05 (WCVP) production-ready. Full platform available.

- [ ] MOD-04 PISE: LightGBM slotting velocity model + OR-Tools slot optimizer (MLflow)
- [ ] MOD-04 PISE: Prophet demand forecast for pre-positioning logic
- [ ] MOD-04 PISE: Feast feature store population from Silver layer (SKU velocity, co-pick features)
- [ ] MOD-04 PISE: AI-prioritized cycle count with LightGBM error risk model
- [ ] MOD-04 PISE: FastAPI service + React UI — Slotting Intelligence dashboard
- [ ] MOD-05 WCVP: YOLOv8 custom training pipeline — person, forklift, pallet, PPE models
- [ ] MOD-05 WCVP: NVIDIA DeepStream pipeline — RTSP ingest, inference, ByteTrack tracking
- [ ] MOD-05 WCVP: Edge MQTT publisher for structured CV events
- [ ] MOD-05 WCVP: Eclipse Hawkbit OTA for Jetson model/runtime updates
- [ ] MOD-05 WCVP: Cloud CV service — event aggregation, anomaly scoring, heatmaps
- [ ] MOD-05 WCVP: Safety alert engine — PPE, forklift/pedestrian, overspeed
- [ ] MOD-05 WCVP: Dock activity monitoring — LPR at yard, dwell time tracking
- [ ] MOD-05 WCVP: React UI — Safety & Compliance, Loss Prevention dashboards
- [ ] Feast: Full feature store population across all modules
- [ ] BentoML: All ML models migrated to BentoML serving for production inference
- [ ] License Service: Tier 3 + Custom license enforcement

**Exit Criteria:** Full platform operational. All 6 modules running in production. Computer vision working on NVIDIA Jetson edge devices with < 33ms inference latency.

---

### Phase 4 — Enterprise Hardening (Months 14–18)

**Goal:** Enterprise-grade resilience, compliance, and multi-tenancy.

- [ ] Multi-tenant data isolation hardening (Apache Ranger for Iceberg ACLs)
- [ ] Active-active multi-region deployment (primary + DR region failover)
- [ ] Enterprise SSO / LDAP federation via Keycloak
- [ ] Advanced OPA policies — ABAC for fine-grained data access
- [ ] SOC 2 Type II audit readiness documentation
- [ ] GDPR / CCPA data residency configuration support
- [ ] FDA FSMA and EU FMD compliance documentation templates
- [ ] Load testing at scale: 50 DCs, 50,000 transactions/minute sustained
- [ ] Argo Rollouts blue/green for zero-downtime production deployments
- [ ] Velero cluster backup and restore automation
- [ ] SLA monitoring and automated SLA breach alerting

---

### Phase 5 — Ecosystem (Months 18–24)

**Goal:** Platform becomes an ecosystem.

- [ ] Connector marketplace — pre-built ERP/TMS/carrier connectors
- [ ] Third-party module SDK — external developers can build LogiSense modules
- [ ] White-label licensing for 3PL and SaaS resellers
- [ ] Native iOS + Android apps (Expo managed workflow)
- [ ] LLM-powered operations assistant (Ollama + open-weights LLM — Llama 3 / Mistral)
- [ ] Self-service onboarding portal — tenant provisioning in < 30 minutes
- [ ] Managed cloud offering (LogiSense Cloud) on top of OSS core

---

## 13. Phase 0 — Immediate Action Plan

> **Start here. Complete Phase 0 before writing a single line of module code.**

### Week 1–2: Repository & Tooling

```bash
# 1. Initialize monorepo
npx create-nx-workspace@latest logisense --preset=empty

# 2. Add core tooling
npm install -D turbo @biomejs/biome typescript

# 3. Set up pre-commit hooks
pip install pre-commit
pre-commit install

# 4. Configure Docker Compose for local dev
# Includes: PostgreSQL, Redis, Kafka, MinIO, Keycloak, Vault, Kong
```

### Week 2–4: Platform Helm Charts

```bash
# Bootstrap platform namespace
kubectl create namespace logisense-platform

# Install core platform via Helm
helm install logisense-platform ./infra/helm/platform \
  --namespace logisense-platform \
  -f ./infra/helm/platform/values.dev.yaml
```

### Week 3–5: CI/CD Pipeline

- GitHub Actions: `ci.yml` — lint, type check, test, Trivy scan, build, push
- Harbor registry deployed: `registry.logisense.internal`
- Trivy configured to block on Critical/High CVEs
- Codecov integration for coverage tracking

### Week 4–6: License Service

```
POST /licenses/issue     → Issue JWT for tenant + modules
GET  /licenses/validate  → Validate JWT (called by Kong plugin)
GET  /licenses/{tenant}  → Get license details
```

### Week 5–8: Data Platform Bootstrap

```bash
# MinIO buckets
mc mb minio/logisense-bronze
mc mb minio/logisense-silver
mc mb minio/logisense-gold
mc mb minio/logisense-mlflow

# Nessie catalog (Iceberg)
# Create namespaces: bronze, silver, gold per module

# Airflow first DAGs
# - bronze_ingest_healthcheck (validates pipeline connectivity)
# - silver_etl_skeleton (empty transforms per module namespace)
```

### Week 6–8: Developer Experience

```bash
# Single command to start full local dev environment
./scripts/dev-bootstrap.sh

# Should spin up:
# - All platform services (Docker Compose)
# - Sample data seeded
# - Dev license key generated and applied
# - Module stub services running
# - Grafana at http://localhost:3000
# - Superset at http://localhost:8088
# - Kong Admin at http://localhost:8001
# - Keycloak at http://localhost:8080
```

---

## 14. Team & Roles

| Role                           | Responsibilities                                              | Phase 0 Priority |
| ------------------------------ | ------------------------------------------------------------- | ---------------- |
| **Platform Architect**         | Monorepo structure, Helm charts, K8s architecture, ADRs       | 🔴 Critical      |
| **Backend Lead (Python)**      | FastAPI service patterns, PostgreSQL schemas, Kafka producers | 🔴 Critical      |
| **Data Engineer**              | Iceberg/MinIO setup, Airflow DAGs, Flink jobs, dbt models     | 🔴 Critical      |
| **DevOps / Platform Engineer** | CI/CD, Terraform, Vault, observability stack                  | 🔴 Critical      |
| **Frontend Lead**              | React shell, Module Federation, Tailwind design system        | 🟡 Phase 1       |
| **ML Engineer**                | MLflow, model training pipelines, BentoML serving             | 🟡 Phase 1/3     |
| **IoT / Edge Engineer**        | CCVP sensor stack, WCVP DeepStream pipeline, Hawkbit          | 🟠 Phase 2/3     |
| **QA Engineer**                | pytest, integration tests, load testing (k6), security tests  | 🟡 Phase 1       |
| **Security Engineer**          | OPA policies, Vault configuration, Falco rules, pen testing   | 🟡 Phase 1       |

---

## 15. Success Metrics

### Platform KPIs

| Metric                           | Target                      | Measurement                |
| -------------------------------- | --------------------------- | -------------------------- |
| Phase 0 bootstrap time           | < 15 min on any K8s cluster | Automated smoke test in CI |
| API availability (prod)          | 99.9% uptime                | Prometheus uptime probe    |
| API response time p95            | < 500ms all GET endpoints   | Prometheus histogram       |
| Inventory transaction throughput | > 10,000 TXN/second         | k6 load test               |
| CV inference latency             | < 33ms per frame (30fps)    | Edge device telemetry      |
| Cold chain excursion detection   | < 10 seconds from breach    | End-to-end alerting test   |
| Test coverage                    | > 80% all modules           | Codecov                    |
| CI pipeline duration             | < 12 minutes                | GitHub Actions metrics     |

### Business KPIs (Post-Deployment)

| Metric                     | Target                          |
| -------------------------- | ------------------------------- |
| Inventory accuracy         | > 99.5%                         |
| Pick accuracy              | > 99.8%                         |
| Order cycle time reduction | > 40% vs. pre-platform baseline |
| Cold chain product loss    | < 0.3% of cold chain inventory  |
| Labor cost efficiency      | 8–15% reduction                 |
| Schedule adherence         | > 91%                           |
| PPE compliance rate        | > 97% in monitored zones        |

---

## 16. Architecture Decision Records (ADRs)

> All major technology choices are documented as ADRs in `docs/adr/`. Key decisions:

| ADR     | Decision                                  | Rationale                                                                                     |
| ------- | ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| ADR-001 | **Apache Iceberg** over Delta Lake        | OSS, cloud-agnostic, no Databricks dependency, multi-engine query support                     |
| ADR-002 | **Keycloak** over Zitadel / Ory Hydra     | Mature, full-featured, enterprise LDAP/SSO support, large community                           |
| ADR-003 | **FastAPI** over gRPC for module APIs     | REST/OpenAPI universally accessible; gRPC adds complexity for minimal gain at this scale      |
| ADR-004 | **MinIO** over SeaweedFS                  | S3 API compatibility, Kubernetes Operator maturity, Iceberg integration                       |
| ADR-005 | **Kong OSS** over Traefik for API Gateway | Keycloak OIDC plugin, license enforcement plugin capability, Kong's plugin ecosystem          |
| ADR-006 | **OR-Tools** for schedule optimization    | Production-grade OSS constraint solver; used in Google supply chain; Python-native            |
| ADR-007 | **Apache Flink** for stream processing    | True streaming semantics; better than Spark Streaming for < 1-second latency requirements     |
| ADR-008 | **Eclipse Mosquitto** over EMQ X          | Lightweight, proven, C implementation, low resource footprint on edge and cloud               |
| ADR-009 | **Apache Superset** over Metabase         | Direct Iceberg/Spark connectivity; more powerful for custom SQL; better for engineering teams |
| ADR-010 | **YOLOv8 (Ultralytics)** for CV           | State-of-art accuracy/speed tradeoff; fully OSS; TensorRT export for Jetson optimization      |

---

_LogiSense Master Plan — v1.0_
_See Everything. Optimize Everything._
