# OnboardIQ — Learning Analytics Platform

> **AI-Powered Workforce Readiness & Learning Analytics**
> A capstone research platform that applies unsupervised machine learning to measure, cluster, and visualise employee onboarding readiness in real time.

---

## Table of Contents

1. [What is OnboardIQ?](#what-is-onboardiq)
2. [Key Features](#key-features)
3. [System Architecture](#system-architecture)
4. [How It Works — End to End](#how-it-works--end-to-end)
   - [1. Content & Curriculum Layer](#1-content--curriculum-layer)
   - [2. Learner Interaction & Telemetry](#2-learner-interaction--telemetry)
   - [3. Scoring Engine (K, V, E → ORI)](#3-scoring-engine-k-v-e--ori)
   - [4. ML Clustering Pipeline](#4-ml-clustering-pipeline)
   - [5. Manager Dashboard](#5-manager-dashboard)
   - [6. External Validation (OULAD)](#6-external-validation-oulad)
5. [Tech Stack](#tech-stack)
6. [Project Structure](#project-structure)
7. [Local Setup](#local-setup)
   - [Backend](#backend)
   - [Frontend](#frontend)
   - [One-Command Start](#one-command-start)
8. [API Reference](#api-reference)
9. [Demo Accounts](#demo-accounts)
10. [Research Background](#research-background)

---

## What is OnboardIQ?

OnboardIQ is a full-stack learning analytics platform built as a capstone research project. It simulates a corporate onboarding environment where new employees work through structured training tracks (e.g. *Actuarial Statistics*, *Actuarial Mathematics*, *Business Finance*), and a machine learning pipeline automatically clusters them into readiness tiers — **Project Ready**, **Needs Coaching**, or **At-Risk** — based purely on their behaviour, not just test scores.

The goal is to move beyond static pass/fail assessments and give managers a data-driven, real-time view of workforce readiness with actionable diagnostic commentary per employee.

---

## Key Features

- **Adaptive curriculum** — 3 domain tracks, each with 2 sequential modules, 3 concepts per module, and a 5-question multiple-choice quiz gating progression
- **Real-time telemetry** — tracks page open/close events, video plays, and time-on-concept down to the second
- **ORI scoring** — a composite Onboarding Readiness Index derived from three behavioural signals (K, V, E)
- **Unsupervised ML clustering** — KMeans (k=3) with StandardScaler, producing deterministic cohort flags
- **Manager dashboard** — scatter plot visualisation, filterable cohort table, per-employee diagnostic comments, and ML validation metrics
- **External dataset validation** — the same K/V/E pipeline is applied to real student data from the Open University Learning Analytics Dataset (OULAD) to confirm archetype validity
- **Role-based access** — Learner and Manager roles with separate views
- **Dark-mode UI** — built with Next.js 14, TailwindCSS, and Recharts

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Next.js Frontend                   │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ Gateway/Auth │  │   Learner   │  │  Manager   │  │
│  │   page.tsx   │  │  page.tsx   │  │  page.tsx  │  │
│  └──────────────┘  └─────────────┘  └────────────┘  │
│              ↕  REST API (/api/v1/*)                 │
└─────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────┐
│                  FastAPI Backend                     │
│  ┌────────┐  ┌─────────┐  ┌──────────┐  ┌───────┐  │
│  │  Auth  │  │ Content │  │Telemetry │  │Manager│  │
│  │ Router │  │ Router  │  │  Router  │  │Router │  │
│  └────────┘  └─────────┘  └──────────┘  └───────┘  │
│                          ↕                          │
│  ┌─────────────────────────────────────────────┐    │
│  │          Scoring + ML Clustering            │    │
│  │   scoring.py  →  ml_clustering.py           │    │
│  └─────────────────────────────────────────────┘    │
│                          ↕                          │
│              SQLite (onboardiq.db)                  │
└─────────────────────────────────────────────────────┘
```

---

## How It Works — End to End

### 1. Content & Curriculum Layer

The database is seeded via `backend/scripts/seed_content.py` with:

| Layer | Count | Description |
|-------|-------|-------------|
| Tracks | 3 | Actuarial Statistics · Actuarial Mathematics · Business Finance |
| Modules | 6 | 2 per track, sequentially gated |
| Concepts | 9 | 3 per module, each with a YouTube video + summary notes |
| Quiz questions | 30 | 5 per module, multiple-choice with correct answer flags |

Module progression is **locked by default**. A learner must pass the quiz of the current module (score ≥ 70%) to unlock the next one.

---

### 2. Learner Interaction & Telemetry

Every learner action is recorded silently in the background via `POST /api/v1/telemetry/log`:

| Event | Trigger | Data captured |
|-------|---------|---------------|
| `page_opened` | Learner selects a concept | `concept_id`, timestamp |
| `page_closed` | Learner leaves / switches concept / hides tab | `concept_id`, `duration_seconds` |
| `video_played` | Learner clicks the embedded YouTube video | `concept_id`, timestamp |

The frontend uses the `visibilitychange` browser API to flush timing data even when a tab is backgrounded. This gives an accurate **time-on-content** measurement for each concept.

Quiz attempts are recorded via `POST /api/v1/content/modules/{id}/quiz/submit` and store the score, start time, and completion time — enabling **velocity** measurement.

---

### 3. Scoring Engine (K, V, E → ORI)

Defined in `backend/app/services/scoring.py`, three normalised [0, 1] feature scores are computed per user per module:

**K — Knowledge Retention Score**
```
K = max_quiz_score × exp(−0.1 × (total_attempts − 1))
```
Rewards high scores achieved with fewer attempts. A perfect score on the first try → K = 1.0. Each additional attempt applies an exponential decay penalty.

**V — Velocity Score**
```
V = min(1, 300 / avg_quiz_latency_seconds)
```
Measures how quickly a learner completes quizzes relative to a 5-minute benchmark. Fast, confident completion → V closer to 1.0.

**E — Engagement Score**
```
E = min(1, total_reading_time / (n_concepts × 300 seconds))
```
Measures depth of content engagement. A learner who spends at least 5 minutes per concept → E = 1.0.

**ORI — Onboarding Readiness Index**
```
ORI = 0.5·K + 0.3·V + 0.2·E
```
A weighted composite score emphasising knowledge quality (50%), completion speed (30%), and reading depth (20%). Scores are averaged across all tracks a learner has activity in.

---

### 4. ML Clustering Pipeline

Defined in `backend/app/services/ml_clustering.py`, triggered on every call to `GET /api/v1/manager/cohorts`:

```
1. Query all Learner users from DB
2. Compute [K, V, E] feature vector per user (averaged across tracks)
3. StandardScaler → normalise to zero mean, unit variance
4. KMeans(n_clusters=3, random_state=42, n_init=10)
5. Map cluster centroids → flags by ranking on (K+E, V) descending:
     Rank 1 → "Project Ready"
     Rank 2 → "Needs Coaching"
     Rank 3 → "At-Risk"
6. Compute internal validation metrics:
     - Silhouette Score (higher = better, threshold ≥ 0.60)
     - Davies-Bouldin Index (lower = better, threshold < 1.0)
7. Generate per-user diagnostic comment based on flag + weak/strong tracks
```

The cluster flag labels are **deterministic** — the highest-K+E centroid is always "Project Ready" regardless of cluster index assignment.

A difficulty label (**Beginner / Intermediate / Advanced**) is also derived from average K:
- K ≥ 0.7 → Advanced
- K ≥ 0.4 → Intermediate
- K < 0.4 → Beginner

---

### 5. Manager Dashboard

The manager view (`frontend/src/app/manager/page.tsx`) provides:

- **Cohort Overview cards** — total employees, count per flag tier
- **Scatter plot** (Recharts) — X: Engagement Score, Y: Knowledge Score, coloured by cluster flag
- **Cluster legend** — explains archetype definitions
- **Filterable cohort table** — filter by flag, track, or name/email search; shows ORI bar, K/V/E breakdown, difficulty badge, and AI-generated diagnostic comment
- **ML Validation panel** (collapsible) — silhouette score, Davies-Bouldin index, cluster distribution, OULAD external validation results

---

### 6. External Validation (OULAD)

To validate that the K/V/E archetypes generalise beyond synthetic data, the same pipeline is applied to real Open University students:

- **Dataset**: Open University Learning Analytics Dataset (OULAD), module BBB-2013J
- **Derivation**: K from max assessment score with attempt decay · V from submission timing vs due date · E from VLE click volume normalised to cohort median
- **Result**: KMeans(k=3) on OULAD data produces a comparable silhouette score, confirming the three archetypes exist in real student behaviour

Run `backend/scripts/validate_oulad.py` after placing the OULAD CSV files in `backend/scripts/oulad_data/` to cache this validation. The manager dashboard will display it automatically.

> **Note:** OULAD data files are excluded from this repository due to file size. Download from [analyse.kmi.open.ac.uk/open_dataset](https://analyse.kmi.open.ac.uk/open_dataset).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend framework | Next.js 14 (App Router) |
| Styling | TailwindCSS 3 |
| Charts | Recharts 3 |
| Language | TypeScript |
| Backend framework | FastAPI 0.111 |
| ORM | SQLAlchemy 2 |
| Validation | Pydantic v2 |
| Database | SQLite |
| ML | scikit-learn 1.5 (KMeans, StandardScaler, silhouette_score, davies_bouldin_score) |
| Data processing | pandas 2.2, numpy 1.26 |

---

## Project Structure

```
OnboardIQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1_auth.py          # Login / signup endpoints
│   │   │   ├── v1_content.py       # Tracks, modules, concepts, quiz submit
│   │   │   ├── v1_telemetry.py     # Telemetry event logging
│   │   │   └── v1_manager.py       # Cohort clustering endpoint
│   │   ├── core/
│   │   │   ├── config.py           # App settings
│   │   │   └── database.py         # SQLAlchemy engine + session
│   │   ├── models/
│   │   │   ├── user_db.py          # User ORM model
│   │   │   ├── content_db.py       # Track / Module / Concept / Question models
│   │   │   └── telemetry_db.py     # QuizAttempt / TelemetryLog models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── scoring.py          # K / V / E / ORI computation
│   │   │   └── ml_clustering.py    # Full KMeans pipeline + OULAD validation
│   │   └── main.py                 # FastAPI app entry point
│   ├── scripts/
│   │   ├── seed_content.py         # Seeds tracks, modules, concepts, questions
│   │   ├── validate_oulad.py       # Runs OULAD external validation
│   │   └── oulad_data/             # (gitignored) place OULAD CSVs here
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx            # Login / signup gateway
│   │   │   ├── learner/page.tsx    # Learner learning workspace
│   │   │   └── manager/page.tsx    # Manager cohort dashboard
│   │   ├── components/
│   │   │   ├── CohortChart.tsx     # Recharts scatter plot
│   │   │   ├── QuizCard.tsx        # Quiz modal component
│   │   │   ├── ThemeToggle.tsx     # Dark/light mode toggle
│   │   │   └── VideoPlayer.tsx     # YouTube embed wrapper
│   │   └── lib/
│   │       ├── api.ts              # Typed API client functions
│   │       └── telemetry_wm.ts     # Telemetry watermark helpers
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── package.json
├── start.sh                        # Starts both backend + frontend
├── stop.sh                         # Stops all OnboardIQ processes
└── README.md
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed the database (creates onboardiq.db + populates content + 50 synthetic users)
python scripts/seed_content.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Frontend runs on **http://localhost:3000** · Backend API on **http://localhost:8000**

### One-Command Start

From the project root:

```bash
chmod +x start.sh
./start.sh
```

This starts both servers in the background. Use `./stop.sh` to shut them down.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | Authenticate user, returns profile |
| `POST` | `/api/v1/auth/signup` | Register new user |
| `GET` | `/api/v1/auth/managers` | List all manager accounts |
| `GET` | `/api/v1/content/tracks` | Get all tracks with modules and concepts for a user |
| `GET` | `/api/v1/content/modules/{id}` | Get module detail with quiz questions |
| `POST` | `/api/v1/content/modules/{id}/quiz/submit` | Submit quiz answers, returns score + pass/fail + next module |
| `POST` | `/api/v1/telemetry/log` | Log a telemetry event (page_opened, page_closed, video_played) |
| `GET` | `/api/v1/manager/cohorts` | Run ML pipeline and return full cohort clustering results |
| `GET` | `/health` | Health check |

---

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Learner | `learner@onboardiq.io` | `learner123` |
| Manager | `manager@onboardiq.io` | `manager123` |

Quick-fill buttons are available on the login screen.

---

## Research Background

This platform was built as a capstone research project exploring the application of **unsupervised learning** to corporate onboarding analytics. The core research questions were:

1. Can behavioural signals (quiz performance, completion speed, reading depth) reliably cluster employees into distinct readiness archetypes?
2. Do these archetypes generalise beyond synthetic data to real student populations?
3. Can an ORI composite score serve as a practical proxy for workforce deployment readiness?

The OULAD external validation (silhouette score parity between synthetic and real data) provides evidence that the three archetypes — **Project Ready**, **Needs Coaching**, and **At-Risk** — reflect genuine patterns in learner behaviour rather than artefacts of the synthetic data generation process.

---

*OnboardIQ · Capstone Research Platform*
