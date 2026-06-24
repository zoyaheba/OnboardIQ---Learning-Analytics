# OnboardIQ — Simple Explainer
### Understanding the core from first principles, no jargon

---

## The One-Line Problem

A manager can see **if** an employee finished a training module.  
They cannot see **how well** they understood it.

OnboardIQ fixes that.

---

## Part 1: What Data Do We Collect?

Every time a learner uses the platform, we silently record three types of events:

| Event | When it fires | What it captures |
|---|---|---|
| `page_opened` | Learner opens a concept | Timestamp only |
| `page_closed` | Learner leaves a concept | **How many seconds they spent reading** |
| `video_played` | Learner clicks play on the video | Timestamp only | ??

And when they take a quiz:

| Data point | What it means |
|---|---|
| `score_percentage` | How many questions they got right (0–100%) |
| `attempt_number` | Which attempt this is (1st, 2nd, 3rd...) |
| `started_at` | When they opened the quiz |
| `completed_at` | When they clicked submit |

That's it. **Six raw numbers per person.** Everything else is calculated from these.

---

## Part 2: Turning Raw Data Into Three Scores

We convert those raw numbers into three scores, each between 0 and 1.  
Think of 0 as "nothing" and 1 as "perfect."

---

### Score 1: Knowledge Score (K) — "Did they actually learn it?"

**The idea:** Quiz score alone isn't enough. If someone got 90% on their 5th attempt, they were mostly guessing earlier — that's weaker than someone who got 90% first try.

**The formula:**
```
K = (best quiz score / 100)  ×  e^(−0.1 × (attempts − 1)) ??
```

The `e^(−0.1 × ...)` part is an **exponential penalty** for retries. It says: every extra attempt, your knowledge score gets slightly reduced.

**Example:**

| Scenario | Calculation | K score |
|---|---|---|
| 90% on attempt 1 | 0.90 × e^0 = 0.90 × 1.0 | **0.90** |
| 90% on attempt 2 | 0.90 × e^−0.1 = 0.90 × 0.905 | **0.81** |
| 90% on attempt 4 | 0.90 × e^−0.3 = 0.90 × 0.741 | **0.67** |
| 50% on attempt 1 | 0.50 × e^0 = 0.50 | **0.50** |

So two employees who both score 90% are **not the same** — the one who needed 4 tries to get there has a meaningfully lower K. This isolates genuine mastery from eventual guessing.

---

### Score 2: Velocity Score (V) — "How fast can they work under pressure?"

**The idea:** In actuarial and finance roles, speed matters. An employee who takes 25 minutes to answer 5 questions under test conditions will struggle with real deadlines.

**The formula:**
```
V = min(1,  300 / average_seconds_to_complete_quiz) ?
```

The baseline is **300 seconds (5 minutes)** for a quiz.

**Example:**

| Time taken | Calculation | V score |
|---|---|---|
| 150 seconds | 300/150 = 2.0 → capped at 1.0 | **1.00** (fast) |
| 300 seconds | 300/300 = 1.0 | **1.00** (on target) |
| 600 seconds | 300/600 = 0.50 | **0.50** (slow) |
| 1500 seconds | 300/1500 = 0.20 | **0.20** (very slow) |

Alex Learner in our test took **1545 seconds** → V = 0.194. That single low number is why the system flagged him.

---

### Score 3: Engagement Score (E) — "Did they actually read the material?"

**The idea:** A learner who opens a concept for 3 seconds and moves on hasn't engaged. We measure actual time spent reading against a realistic target.

**The formula:**
```
E = min(1,  total_reading_seconds / (number_of_concepts × 300))
```

Each concept has a reading target of **300 seconds (5 minutes)**.

**Example** (module with 2 concepts, target = 600 seconds total):

| Time spent reading | Calculation | E score |
|---|---|---|
| 600 seconds | 600/600 = 1.0 | **1.00** (fully engaged) |
| 420 seconds | 420/600 = 0.70 | **0.70** (good) |
| 60 seconds | 60/600 = 0.10 | **0.10** (skimming) |
| 0 seconds | 0/600 = 0.0 | **0.00** (never read) |

Important: **all reading sessions accumulate**. If you read for 3 minutes, close the page, come back and read for 4 more minutes, E uses the full 7 minutes. This is intentional.

---

## Part 3: The ORI Score — "One Number for Readiness"

We combine K, V, and E into a single **Onboarding Readiness Index (ORI)**:

```
ORI = (0.5 × K) + (0.3 × V) + (0.2 × E)
```

**Why these weights?**
- **K gets 50%** — In actuarial work, actually knowing the material is the most important thing. You can't bluff your way through actuarial calculations.
- **V gets 30%** — Execution speed is the second most important. You need to work at professional pace.
- **E gets 20%** — Reading engagement is a leading signal (shows up early) but not sufficient alone. You could read for hours and still fail the quiz.

**Example — Three Employees:**

| Employee | K | V | E | ORI Calculation | ORI % |
|---|---|---|---|---|---|
| Sarah (FastTrack) | 0.92 | 0.95 | 0.88 | 0.5×0.92 + 0.3×0.95 + 0.2×0.88 | **91.6%** |
| James (Methodical) | 0.78 | 0.45 | 0.90 | 0.5×0.78 + 0.3×0.45 + 0.2×0.90 | **70.5%** |
| Priya (At-Risk) | 0.45 | 0.30 | 0.12 | 0.5×0.45 + 0.3×0.30 + 0.2×0.12 | **33.9%** |

Now you have one number you can rank, compare, and act on.

---

## Part 4: Why Not Just Use the ORI Score Directly?

You could just say: "ORI > 75% = good, ORI < 50% = bad."  
That's a **threshold rule** — and it has a critical flaw.

**The problem with thresholds — a real example:**

Imagine an employee with:
- K = 0.85 (high quiz score, first attempt)
- V = 1.00 (very fast)
- E = 0.03 (read the concept for literally 9 seconds)

Their ORI = 0.5×0.85 + 0.3×1.0 + 0.2×0.03 = **0.731 → 73.1%**

A threshold rule says: **Project Ready**. ✅

But think about what actually happened: this person **never read the material**, flew through the quiz at suspicious speed, and scored 85% — strongly suggesting they already knew the content from a previous role, or guessed using the process of elimination.

For a manager, this is a **Needs Coaching** signal: the person may have surface familiarity but no deep engagement with *your specific* actuarial content. They need a targeted conversation, not project allocation.

**K-Means clustering catches this.** Because E = 0.03 makes this person geometrically similar to the At-Risk/Needs Coaching cluster in 3D space, even though their score alone looks fine.

---

## Part 5: The Machine Learning — K-Means Clustering

### What is K-Means?

K-Means is an algorithm that looks at a group of points in space and finds **natural groupings (clusters)** without being told what the groups should be.

In our case, each employee is a point in **3D space** — their [K, V, E] coordinates.

```
Example employees as points:

Sarah:  [0.92, 0.95, 0.88]  ← high on all three
James:  [0.78, 0.45, 0.90]  ← high K, low V, high E
Priya:  [0.45, 0.30, 0.12]  ← low on all three
```

K-Means finds the **centre point (centroid)** of each natural cluster, then assigns every employee to the cluster whose centroid they are closest to.

### The Three Steps

**Step 1: Normalise the data**  
K and V and E are all in [0,1] already, but their spreads differ. We apply **StandardScaler** to give each dimension zero mean and unit variance. This ensures V doesn't get mathematically dominated by K just because K has a wider spread in this cohort.

**Step 2: Run K-Means with k=3**  
We tell the algorithm: "Find 3 clusters." It iterates until the 3 centroid positions stabilise.

**Step 3: Map centroids to labels**  
The algorithm doesn't know what "Project Ready" means — it just finds 3 blobs of points. We rank the centroids by their combined K+E score:
- Highest K+E centroid → **Project Ready** 🟢
- Middle centroid → **Needs Coaching** 🟡  
- Lowest K+E centroid → **At-Risk** 🔴

This mapping is deterministic — it doesn't matter what order K-Means happened to label the clusters internally.

---

## Part 6: How Do We Know the Clustering is Working?

Two mathematical metrics validate that the clusters are meaningful and not just random blobs.

---

### Metric 1: Silhouette Score

**Simple explanation:** For each employee, ask: "How similar am I to my own cluster compared to the nearest other cluster?"

- Score of **+1.0** = perfectly placed, very different from other clusters
- Score of **0.0** = sitting on the boundary between two clusters
- Score of **−1.0** = probably in the wrong cluster

**Formula:**
```
s = (b − a) / max(a, b)

where:
  a = average distance to others in YOUR cluster (lower = tighter cluster)
  b = average distance to nearest OTHER cluster (higher = better separation)
```

**Our score: 0.6726** — This means on average, employees are much more similar to their own cluster-mates than to the other clusters. In research, > 0.60 is considered "strong structure."

**Example to feel it:**

Imagine Sarah's point is 0.05 units from her Project Ready cluster-mates on average (a = 0.05) and 0.28 units from the Needs Coaching cluster (b = 0.28).

```
s = (0.28 − 0.05) / max(0.05, 0.28) = 0.23 / 0.28 = 0.82
```
Sarah is very confidently in the right cluster.

---

### Metric 2: Davies-Bouldin Index (DBI)

**Simple explanation:** For each cluster, find the worst-case comparison: "Which other cluster am I most similar to?" Average those worst-case scores.

- **Lower is better.** A score near 0 means clusters are compact and far apart.
- A score > 1.0 means clusters are overlapping — not useful.

**Our score: 0.4241** — Very good. Our three archetypes are well-separated in feature space.

**Together, Silhouette = 0.67 and DBI = 0.42 confirm:** the three behavioural archetypes (Project Ready, Needs Coaching, At-Risk) are real, distinct groupings — not arbitrary labels we forced onto random noise.

---

## Part 7: The Diagnostic Comment — Making It Human

The cluster flag tells the manager **what** the problem is. The diagnostic comment explains **why**, using the actual feature values:

```
IF cluster = At-Risk:
    IF attempts >= 3   → "Multiple retries, retention issues, recommend remediation"
    IF E < 0.20        → "Not reading material, skimming content"
    IF V < 0.25        → "Slow velocity despite good scores — timed practice needed"
    ELSE               → "Below threshold — schedule a check-in"

IF cluster = Needs Coaching:
    IF V < 0.40        → "Good understanding but slow — time management coaching"
    IF E > 0.60        → "High engagement but not converting to quiz performance"
    ELSE               → "Solid foundation, periodic mentor check-ins recommended"

IF cluster = Project Ready:
    → "Strong retention, fast completion, deep engagement — ready for allocation"
```

This means the manager never sees a confusing number alone — every flag comes with a plain English explanation traceable to the raw data.

---

## Part 8: The Full Journey in One Picture

```
Learner opens concept
        ↓
   [page_opened event logged]
        ↓
Learner reads for 7 minutes
        ↓
   [page_closed event: duration_seconds = 420]
        ↓
Learner watches video
        ↓
   [video_played event logged]
        ↓
Learner takes quiz — scores 80% in 1545 seconds
        ↓
   [quiz_attempt: score=80, attempts=1, latency=1545s]
        ↓
   ┌─────────────────────────────────────────┐
   │          scoring.py calculates:         │
   │  K = 0.80 × exp(0)        = 0.800      │
   │  V = 300 / 1545           = 0.194      │
   │  E = 420 / (2×300)        = 0.700      │
   │  ORI = 0.5K+0.3V+0.2E    = 0.610      │
   └─────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────┐
   │       ml_clustering.py runs:            │
   │  X = [0.800, 0.194, 0.700]             │
   │  StandardScaler normalises X            │
   │  KMeans(k=3) assigns to cluster         │
   │  → Nearest centroid: At-Risk            │
   │  (V=0.194 is geometrically close to     │
   │   At-Risk cluster despite high K+E)     │
   └─────────────────────────────────────────┘
        ↓
   Manager sees on dashboard:
   🔴 Alex Learner | ORI: 61.0% | At-Risk
   "Unusually slow quiz velocity despite adequate
    knowledge scores. Consider timed practice drills."
```

---

## Part 9: Why K-Means Is Better Than a Spreadsheet Rule

| Rule Type | What it sees | What it misses |
|---|---|---|
| "Score > 70% = passed" | Pass/fail | Engagement, speed, retry pattern |
| "Score > 75% = Ready" | Single number | High scorer who never read the material |
| **K-Means on [K, V, E]** | All three dimensions simultaneously | Nothing in the feature space |

The power is **multidimensional detection**. A threshold can only draw a line. K-Means draws a boundary in 3D space, catching edge cases that no single threshold would flag.

---

## Summary: The Five Key Ideas

1. **Three raw signals** — reading time, quiz score, quiz speed — are all you need
2. **Three derived scores** (K, V, E) each capture a different dimension of learning
3. **ORI** combines them into one actionable number (50% knowledge, 30% velocity, 20% engagement)
4. **K-Means** groups employees by their [K, V, E] position in 3D space — no labels needed
5. **Silhouette + DBI** prove the three groups are real and mathematically distinct

The entire system has **one job**: tell a manager, within the first week of onboarding, exactly which employees need help and why — before they fail on a real project.

---

*This document is a plain-language companion to the full technical research report (`OnboardIQ_Research_Report.md`).*
