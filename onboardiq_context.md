# OnboardIQ: Master Project Context & Research Architecture

## 1. Academic Abstract
Traditional corporate onboarding frameworks rely on static, time-bound checklists (e.g., 3-month routines) and descriptive completion trackers that capture compliance rather than functional competence. This creates an operational blind spot, lengthening Time-to-Peak Productivity (TPP) and depending heavily on subjective mentor evaluations. 

This project introduces OnboardIQ, a data-driven workforce readiness and learning analytics platform that replaces static tracking with continuous, micro-level behavioral telemetry and unsupervised machine learning profiling. By capturing real-time user clickstreams—including active reading duration, video watch-time latency, quiz completion velocity, and error decay rates—the platform constructs multi-dimensional feature vectors for each new hire. These vectors are parsed through unsupervised clustering algorithms (K-Means, Gaussian Mixture Models) to dynamically segment learners into three distinct operational archetypes: Project Ready, Needs Coaching, and At-Risk. 

Cluster boundaries are mathematically validated using the Silhouette Coefficient and the Davies-Bouldin Index to ensure structural stability and separation. Experimental results demonstrate that modeling onboarding trajectories through empirical behavioral patterns provides automated early-risk alerts and enables flexible, performance-driven project allocation, shifting corporate training from a baseline administrative routine into an optimized capabilities asset.

## 2. Introduction & Research Framework
In knowledge-intensive domains like Actuarial Science, Financial Engineering, and Quantitative Analysis, the corporate onboarding process represents a massive operational bottleneck. Traditionally, when a new employee joins an organization, they are placed in a fixed 90-day training buffer managed via spreadsheets, SharePoint repositories, and ad-hoc mentorship. Managers lack granular visibility into how a new joiner interacts with dense, formula-heavy documentation (such as Actuarial Statistics or Business Finance manuals), creating an analytical disconnect. Because conventional Learning Management Systems (LMS) only track surface-level parameters ("Document Opened" or "Video 100% Watched"), they create an illusion of progress without verifying true cognitive retention or execution speed. This project develops a technical framework that translates passive user engagement logs into real-time operational indicators, enabling enterprise managers to make fast, data-driven staffing decisions.

## 3. Literature Review Gaps & Validations
The academic foundation of this platform draws heavily from the fields of Educational Data Mining (EDM) and Learning Analytics (LA). Historically, tracking student trajectories required active survey models, which are prone to human bias and fail to capture real-time learning shifts. Modern educational data mining has pivoted completely toward passive trace data collection.

### Unsupervised Clustering in Trajectory Mapping
Academic literature confirms that unsupervised learning algorithms can discover latent learner archetypes from unlabeled log profiles. In evaluations using the Open University UK dataset, researchers applied Agglomerative Hierarchical Clustering to trace sequences (click frequencies, material views, forum activity), effectively partitioning the user cohort into four distinct trajectories spanning exemplary, good, intermediate, and poor self-regulators. This classification correlated strongly with final evaluation outcomes. Similarly, Li et al. (2018) applied K-Means Clustering to temporal pacing arrays (quiz submission timings and access frequencies) to discover clear structural behavior categories, successfully grouping early completers, late completers, and early/late dropouts.

### Mathematical Boundary Validation
Because corporate learning data lacks ground-truth labels at inception, internal validation indexes are necessary to verify cluster quality. The literature validates the Silhouette Coefficient ($s$) as the primary indicator for optimizing cluster numbers:
$$s(i) = \frac{b(i) - a(i)}{\max\left(a(i), b(i)\right)}$$
Where $a(i)$ is the mean intra-cluster distance of point $i$, and $b(i)$ is the mean nearest-cluster distance. Researchers have used silhouette completions to demonstrate that hierarchical configurations (achieving a high coefficient of 0.7111) can outpace classic Expectation-Maximization layouts on specialized telemetry datasets. To maintain mathematical stability, systems also track the Davies-Bouldin Index (DBI) and the Dunn Index across multiple feature configurations.

### Real-Time Cluster Migrations
Static assessments wait until a training path is fully completed before identifying a failure event, making corrective training expensive or impossible. The literature supports the use of continuous scoring pipelines during the initial 5 to 10 days of a learning sequence to provide early risk detection. Tracking variations in active reading time or watching for sudden spikes in quiz retry counts allows predictive analytics engines to dynamically transition a student between behavioral profiles. This shifting of user statuses triggers proactive coaching or automates dynamic pacing loops to compress an organization's overall time-to-productivity.

## 4. Problem Statement
Current corporate onboarding workflows suffer from the "Completion ≠ Mastery" Illusion. Because training progress is measured through static checklists, spreadsheets, and manual check-ins, organizations cannot objectively measure an employee's conceptual domain competence or practical operational readiness. This creates an information asymmetry for managers, leading to delayed project allocations, high senior-resource hand-holding costs, and a failure to catch struggling hires early in the training loop.

## 5. Primary & Sub-Objectives
To design, implement, and validate an AI-enabled onboarding analytics platform (OnboardIQ) that transforms raw user behavioral telemetry into structured readiness profiles through unsupervised machine learning, minimizing time-to-peak productivity and removing human bias from project allocation tasks.

### Structural Sub-Objectives:
- **Sub-Objective 1:** Develop a high-throughput, async FastAPI backend and PostgreSQL database schema to capture microscopic, append-only clickstream logs (durations, velocities, retry counts) across domain tracks without introducing UI latency.
- **Sub-Objective 2:** Build a processing service that transforms time-series log entries into a multi-dimensional feature matrix $X$, implements the mathematical Onboarding Readiness Index ($ORI$), and evaluates unsupervised algorithms (K-Means vs. GMM) using Silhouette scoring to map users into dense behavioral profiles.
- **Sub-Objective 3:** Construct a highly scannable Next.js and Tailwind CSS dashboard interface that charts cohort locations, issues automated "At-Risk" visual flags, and delivers deterministic, feature-driven diagnostic comments explaining exactly why an employee is experiencing a learning block.

## 6. Target Content & Data Scoping
To ground the platform in real corporate context, the static curriculum uses three target tracks:
1. **Actuarial Statistics**
2. **Actuarial Mathematics**
3. **Business Finance**

### Feature Vector Fields Collected (In-Scope)
- `duration_seconds`: Total time spent actively reading a specific concept block text.
- `video_watch_time`: Cumulative time spent viewing the embedded instructional YouTube player framework.
- `attempt_number`: Chronological count of module quiz takes, used to derive the Error Decay Rate ($E_D$).
- `score_percentage`: Grade metrics from MCQ testing arrays.
- `completion_latency`: Answering speed, derived from test layout mount to submission timestamps.

## 7. Mathematical Modeling Core

### The Onboarding Readiness Index ($ORI$)
Calculated at timestamp $t$ for user $i$ on an active tracking module:
$$ORI_{i,t} = 0.5 \cdot K_{i,t} + 0.3 \cdot V_{i,t} + 0.2 \cdot E_{i,t}$$

- **Knowledge Score ($K$):** Highest quiz score achieved, penalized exponentially by retry counts to isolate true mastery from guess patterns: $K = \text{max\_score} \cdot \exp(-0.1 \cdot (\text{attempts} - 1))$.
- **Velocity Score ($V$):** Normalized factor comparing completion time against a test standard duration of 300 seconds.
- **Engagement Score ($E$):** Ratio of captured concept page `duration_seconds` relative to a baseline target reading speed (word count / 3 words per second).

### Unsupervised Clustering Topology
A Scikit-Learn script acts on user aggregated feature rows to run K-Means ($k=3$). Centroid coordinates map directly to our target organizational classifications:
- High $K$ + High $E$ Centroid $\rightarrow$ **Project Ready** (🟢 Green Flag)
- Mid $K$ + Low $V$ Centroid $\rightarrow$ **Needs Coaching** (🟡 Yellow Flag)
- Low $K$ + High Attempts Centroid $\rightarrow$ **At-Risk** (🔴 Red Flag)

To prevent cold-start variance system crashes, a synthetic dataset generator populates historical metrics for 50 baseline users (20 Autonomous, 20 Methodical, 10 Struggling) on initialization.

## 8. Directory Architecture Map
```text
onboardiq/
├── backend/
│   ├── app/
│   │   ├── api/          # Routers (v1_auth, v1_content, v1_telemetry, v1_manager)
│   │   ├── core/         # Configs, Database engines
│   │   ├── models/       # ORM Tables (content_db, user_db, telemetry_db)
│   │   ├── schemas/      # Pydantic Schemas (content_pyd, telemetry_pyd)
│   │   └── services/     # Core Business/ML logic (scoring, ml_clustering)
│   ├── scripts/          # Database seeding scripts (seed_content.py)
│   └── requirements.txt
└── frontend/
    └── src/
        ├── app/          # Pages (layout, gateway, learner, manager panels)
        ├── components/   # Atom elements (VideoPlayer, QuizCard, CohortChart)
        └── lib/          # Utilities (api, telemetry_wm client monitors)