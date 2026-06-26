"""
seed_content.py
Wipes existing schema, rebuilds all tables, and seeds:
  - 3 Tracks / 10 Modules each / 10 Concepts each / 5 QuizQuestions each
  - 4 core users (Learner, Manager x2, Admin)
  - 50 synthetic onboarding users + quiz_attempts + telemetry_logs
"""

import sys
import os
import uuid
import random
import hashlib
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import engine, Base, SessionLocal
import app.models  # noqa: F401 — register all ORM classes

from app.models.content_db import Track, Module, Concept, QuizQuestion
from app.models.user_db import User, UserTrackState
from app.models.telemetry_db import QuizAttempt, TelemetryLog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def uid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(plain: str) -> str:
    """Lightweight SHA-256 mock hash for local SQLite MVP."""
    return hashlib.sha256(plain.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Static curriculum content
# ---------------------------------------------------------------------------

TRACKS = [
    {
        "name": "Actuarial Statistics",
        "description": (
            "Covers core statistical theory underpinning actuarial science: "
            "probability distributions, hypothesis testing, regression analysis, "
            "and credibility theory applied to insurance risk modeling."
        ),
        "modules": [{
            "title": "Foundations of Probability & Distributions",
            "difficulty_level": "Beginner",
            "sequence_order": 1,
            "concepts": [
                {
                    "title": "Random Variables and Probability Distributions",
                    "summary_text": (
                        "A random variable is a numerical outcome of a random experiment. "
                        "Discrete random variables take countable values (e.g., number of claims), "
                        "while continuous random variables span a range (e.g., claim severity). "
                        "Key distributions in actuarial work include the Binomial, Poisson, Normal, "
                        "Exponential, and Pareto. The Expected Value E[X] measures the long-run "
                        "average, while Variance Var[X] = E[X²] - (E[X])² captures spread around "
                        "the mean. Moment Generating Functions (MGFs) allow analytical derivation "
                        "of all moments and are central to risk aggregate modeling."
                    ),
                    "youtube_video_id": "3v9w79NhsfI",
                    "sequence_order": 1,
                },
                {
                    "title": "Hypothesis Testing and Confidence Intervals",
                    "summary_text": (
                        "Hypothesis testing provides a structured decision framework for evaluating "
                        "statistical claims about population parameters. The null hypothesis H₀ "
                        "represents the status quo, while H₁ is the alternative. A p-value measures "
                        "the probability of observing data as extreme as the sample under H₀. "
                        "Confidence intervals provide an estimated range of plausible parameter values "
                        "at a given confidence level (e.g., 95%). In actuarial reserving, these tools "
                        "are used to validate loss development factors and IBNR estimate stability."
                    ),
                    "youtube_video_id": "-FtlH4svqx4",
                    "sequence_order": 2,
                },
            ],
            "questions": [
                {
                    "question_text": "Which distribution is most appropriate for modeling the number of insurance claims per year?",
                    "options": {"A": "Normal", "B": "Poisson", "C": "Exponential", "D": "Uniform"},
                    "correct_option": "B",
                },
                {
                    "question_text": "If E[X] = 5 and E[X²] = 30, what is Var[X]?",
                    "options": {"A": "25", "B": "5", "C": "30", "D": "6"},
                    "correct_option": "B",
                },
                {
                    "question_text": "A p-value of 0.03 with α = 0.05 means:",
                    "options": {
                        "A": "Fail to reject H₀",
                        "B": "Reject H₀",
                        "C": "Accept H₁ with certainty",
                        "D": "The test is inconclusive",
                    },
                    "correct_option": "B",
                },
                {
                    "question_text": "Which function uniquely characterizes a probability distribution and can derive all its moments?",
                    "options": {
                        "A": "Cumulative Distribution Function",
                        "B": "Probability Density Function",
                        "C": "Moment Generating Function",
                        "D": "Characteristic Function",
                    },
                    "correct_option": "C",
                },
                {
                    "question_text": "A 95% confidence interval means:",
                    "options": {
                        "A": "There is a 95% probability the parameter is in this interval",
                        "B": "95% of samples would produce intervals containing the true parameter",
                        "C": "The sample mean is within 5% of the true mean",
                        "D": "The test has 5% power",
                    },
                    "correct_option": "B",
                },
            ],
        },
        {
            "title": "Sampling Distributions & Central Limit Theorem",
            "difficulty_level": "Intermediate",
            "sequence_order": 2,
            "concepts": [
                {
                    "title": "Sampling Distributions and the Central Limit Theorem",
                    "summary_text": (
                        "The Central Limit Theorem (CLT) states that for large n, the sampling "
                        "distribution of the sample mean X-bar approaches N(mu, sigma^2/n) "
                        "regardless of the population distribution. Standard error SE=sigma/sqrt(n) "
                        "quantifies sampling variability. The CLT justifies Normal-based inference "
                        "for large claim portfolios and underpins confidence interval construction."
                    ),
                    "youtube_video_id": "JNm3M9cqWyc",
                    "sequence_order": 1,
                },
            ],
            "questions": [
                {
                    "question_text": "The CLT states that for large n, the distribution of X-bar is:",
                    "options": {"A": "Uniform", "B": "Normal regardless of population shape", "C": "Poisson", "D": "Identical to population"},
                    "correct_option": "B",
                },
                {
                    "question_text": "If sigma=20 and n=100, the standard error of X-bar is:",
                    "options": {"A": "20", "B": "2", "C": "0.2", "D": "200"},
                    "correct_option": "B",
                },
                {
                    "question_text": "As sample size n increases, the standard error:",
                    "options": {"A": "Increases", "B": "Stays constant", "C": "Decreases proportional to 1/sqrt(n)", "D": "Becomes undefined"},
                    "correct_option": "C",
                },
                {
                    "question_text": "The sampling distribution of X-bar has mean equal to:",
                    "options": {"A": "sigma/sqrt(n)", "B": "Population mean mu", "C": "Sample variance", "D": "n*mu"},
                    "correct_option": "B",
                },
                {
                    "question_text": "The CLT is useful in actuarial science because:",
                    "options": {"A": "It proves all distributions are Normal", "B": "It allows Normal inference for large insurance portfolios", "C": "It eliminates data collection", "D": "It applies only to Poisson claims"},
                    "correct_option": "B",
                },
            ],
        },
        ],
    },
    {
        "name": "Actuarial Mathematics",
        "description": (
            "Explores life contingency theory, survival models, annuities, "
            "and net premium calculations used in life insurance and pension valuations."
        ),
        "modules": [{
            "title": "Life Tables and Survival Models",
            "difficulty_level": "Intermediate",
            "sequence_order": 1,
            "concepts": [
                {
                    "title": "The Life Table: Mortality and Survival Functions",
                    "summary_text": (
                        "A life table models the mortality experience of a cohort. The survival "
                        "function S(x) = P(T > x) gives the probability a life survives beyond age x. "
                        "The force of mortality μ(x) = -S'(x)/S(x) is the instantaneous death rate "
                        "analogous to a hazard rate. From a standard life table, key quantities include "
                        "qₓ (probability of death between age x and x+1), lₓ (survivors at age x), "
                        "and dₓ = lₓ - lₓ₊₁ (deaths in the interval). These form the foundation for "
                        "pricing term life insurance, whole life policies, and annuity products."
                    ),
                    "youtube_video_id": "uAnyTwlwQbQ",
                    "sequence_order": 1,
                },
                {
                    "title": "Present Value of Life Annuities and Insurance",
                    "summary_text": (
                        "The Actuarial Present Value (APV) of a life insurance benefit is the "
                        "expected discounted payment. For a whole life insurance paying 1 at death, "
                        "Āₓ = ∫₀^∞ e^(−δt) · tpₓ · μ(x+t) dt where δ is the force of interest. "
                        "A life annuity-due pays 1 at the start of each year the insured is alive: "
                        "äₓ = Σₖ₌₀^∞ vᵏ · ₖpₓ. The fundamental relationship Āₓ = 1 − d·äₓ connects "
                        "insurance and annuity values, allowing efficient calculation of net premiums "
                        "using Pₓ = Āₓ / äₓ."
                    ),
                    "youtube_video_id": "ngb4wl4Ic4E",
                    "sequence_order": 2,
                },
            ],
            "questions": [
                {
                    "question_text": "What does qₓ represent in a standard life table?",
                    "options": {
                        "A": "Probability of surviving from age x to x+1",
                        "B": "Number of lives at age x",
                        "C": "Probability of dying between age x and x+1",
                        "D": "Force of mortality at age x",
                    },
                    "correct_option": "C",
                },
                {
                    "question_text": "The survival function S(x) equals:",
                    "options": {
                        "A": "P(T ≤ x)",
                        "B": "P(T > x)",
                        "C": "1 − qₓ",
                        "D": "μ(x) · lₓ",
                    },
                    "correct_option": "B",
                },
                {
                    "question_text": "For a whole life annuity-due, which formula relates it to whole life insurance?",
                    "options": {
                        "A": "Āₓ = 1 + d·äₓ",
                        "B": "äₓ = (1 − Āₓ) / d",
                        "C": "Āₓ = d / äₓ",
                        "D": "äₓ = Āₓ · (1 + i)",
                    },
                    "correct_option": "B",
                },
                {
                    "question_text": "The net premium for a whole life policy is calculated as:",
                    "options": {
                        "A": "Pₓ = äₓ / Āₓ",
                        "B": "Pₓ = Āₓ · äₓ",
                        "C": "Pₓ = Āₓ / äₓ",
                        "D": "Pₓ = 1 − Āₓ",
                    },
                    "correct_option": "C",
                },
                {
                    "question_text": "The force of mortality μ(x) is most analogous to which statistical concept?",
                    "options": {
                        "A": "Probability mass function",
                        "B": "Hazard rate",
                        "C": "Cumulative distribution function",
                        "D": "Variance",
                    },
                    "correct_option": "B",
                },
            ],
        },
        {
            "title": "Net Premium Calculation",
            "difficulty_level": "Advanced",
            "sequence_order": 2,
            "concepts": [
                {
                    "title": "Net Premium Calculation Foundations",
                    "summary_text": (
                        "The net premium P is set so APV of future premiums equals APV of future "
                        "benefits (equivalence principle). For whole life: Px = Ax / ax-due. "
                        "For n-year term: P = A^1_x:n / ax:n-due. Net premiums ignore expenses; "
                        "gross premiums add expense loadings. The equivalence principle ensures "
                        "the insurer breaks even in expectation under statutory reserve standards."
                    ),
                    "youtube_video_id": "XLgbvHJG2GE",
                    "sequence_order": 1,
                },
            ],
            "questions": [
                {
                    "question_text": "The equivalence principle states:",
                    "options": {"A": "APV premiums = APV expenses", "B": "APV future premiums = APV future benefits", "C": "Gross premium = net premium", "D": "Reserve = zero always"},
                    "correct_option": "B",
                },
                {
                    "question_text": "The net annual premium for whole life Px is:",
                    "options": {"A": "ax / Ax", "B": "Ax / ax", "C": "Ax * ax", "D": "1/(ax+Ax)"},
                    "correct_option": "B",
                },
                {
                    "question_text": "If Ax=0.40 and ax=12.5, the net annual premium Px is:",
                    "options": {"A": "0.032", "B": "31.25", "C": "5.0", "D": "0.50"},
                    "correct_option": "A",
                },
                {
                    "question_text": "A gross premium differs from a net premium because it:",
                    "options": {"A": "Uses higher survival probability", "B": "Includes expense loadings", "C": "Uses a different interest rate", "D": "Ignores the benefit amount"},
                    "correct_option": "B",
                },
                {
                    "question_text": "For a 20-year endowment, the net premium uses:",
                    "options": {"A": "Whole life annuity ax", "B": "20-year temporary annuity ax:20", "C": "Perpetuity annuity", "D": "Immediate annuity ax"},
                    "correct_option": "B",
                },
            ],
        },
        ],
    },
    {
        "name": "Business Finance",
        "description": (
            "Introduces corporate finance fundamentals: time value of money, "
            "capital budgeting, risk-return frameworks, and financial statement analysis "
            "for business decision-making."
        ),
        "modules": [{
            "title": "Time Value of Money and Capital Budgeting",
            "difficulty_level": "Beginner",
            "sequence_order": 1,
            "concepts": [
                {
                    "title": "Present Value, Future Value, and Discounting",
                    "summary_text": (
                        "The time value of money (TVM) principle states that a dollar today is worth "
                        "more than a dollar in the future due to its earning potential. Future Value "
                        "FV = PV · (1 + r)ⁿ compounds a present sum at rate r over n periods. "
                        "Conversely, PV = FV / (1 + r)ⁿ discounts a future cash flow back to today. "
                        "Annuities produce a stream of equal cash flows; the PV of an ordinary annuity "
                        "is PV = C · [1 − (1+r)^(−n)] / r. Perpetuities extend this infinitely: "
                        "PV = C / r. These mechanics underpin bond pricing, loan amortization, "
                        "and all discounted cash flow (DCF) valuations."
                    ),
                    "youtube_video_id": "733mgqrzNKs",
                    "sequence_order": 1,
                },
                {
                    "title": "Net Present Value and Internal Rate of Return",
                    "summary_text": (
                        "Net Present Value (NPV) = Σ [Cₜ / (1+r)ᵗ] − I₀ where Cₜ is the cash flow "
                        "at time t, r is the discount rate, and I₀ is the initial investment. "
                        "A positive NPV signals value creation; NPV > 0 means accept the project. "
                        "The Internal Rate of Return (IRR) is the discount rate that sets NPV = 0. "
                        "When IRR > WACC (Weighted Average Cost of Capital), the project is viable. "
                        "However, IRR can be misleading for mutually exclusive projects or non-conventional "
                        "cash flows (multiple sign changes), where NPV should take precedence."
                    ),
                    "youtube_video_id": "Fw5-wccViOM",
                    "sequence_order": 2,
                },
            ],
            "questions": [
                {
                    "question_text": "What is the Future Value of $1,000 invested at 8% per annum for 3 years?",
                    "options": {
                        "A": "$1,240.00",
                        "B": "$1,259.71",
                        "C": "$1,300.00",
                        "D": "$1,080.00",
                    },
                    "correct_option": "B",
                },
                {
                    "question_text": "The Present Value of a perpetuity paying $500/year at a 10% discount rate is:",
                    "options": {
                        "A": "$5,000",
                        "B": "$500",
                        "C": "$50,000",
                        "D": "$4,500",
                    },
                    "correct_option": "A",
                },
                {
                    "question_text": "A project with NPV = −$50,000 should be:",
                    "options": {
                        "A": "Accepted if IRR > 0",
                        "B": "Rejected because it destroys value",
                        "C": "Accepted if payback period < 3 years",
                        "D": "Accepted because the cash flows are positive",
                    },
                    "correct_option": "B",
                },
                {
                    "question_text": "When should IRR NOT be the sole capital budgeting criterion?",
                    "options": {
                        "A": "When all cash flows are conventional",
                        "B": "When evaluating a single independent project",
                        "C": "When comparing mutually exclusive projects with different scales",
                        "D": "When WACC is known",
                    },
                    "correct_option": "C",
                },
                {
                    "question_text": "The discount rate that makes NPV equal to zero is called:",
                    "options": {
                        "A": "WACC",
                        "B": "Cost of Equity",
                        "C": "Internal Rate of Return",
                        "D": "Hurdle Rate",
                    },
                    "correct_option": "C",
                },
            ],
        },
        {
            "title": "Bond Valuation and Yield to Maturity",
            "difficulty_level": "Intermediate",
            "sequence_order": 2,
            "concepts": [
                {
                    "title": "Bond Valuation and Yield to Maturity (YTM)",
                    "summary_text": (
                        "A bond's price is the PV of coupon payments plus par value: "
                        "P = sum C/(1+y)^t + F/(1+y)^n where y is the YTM. "
                        "Bond price and YTM are inversely related: when rates rise, prices fall. "
                        "Premium bond: coupon > YTM. Discount bond: coupon < YTM. "
                        "Duration measures interest rate sensitivity. Core tool for "
                        "fixed-income portfolio management and actuarial asset-liability matching."
                    ),
                    "youtube_video_id": "I7FDx4DPapw",
                    "sequence_order": 1,
                },
            ],
            "questions": [
                {
                    "question_text": "If a bond's coupon rate exceeds its YTM, it trades:",
                    "options": {"A": "At a discount", "B": "At a premium", "C": "Exactly at par", "D": "At zero"},
                    "correct_option": "B",
                },
                {
                    "question_text": "When market interest rates rise, existing bond prices:",
                    "options": {"A": "Also rise", "B": "Fall (inverse relationship)", "C": "Are unaffected", "D": "Become negative"},
                    "correct_option": "B",
                },
                {
                    "question_text": "YTM is the discount rate that:",
                    "options": {"A": "Sets price equal to face value", "B": "Makes PV of all cash flows equal to current market price", "C": "Equals the coupon rate", "D": "Maximises bondholder return"},
                    "correct_option": "B",
                },
                {
                    "question_text": "Bond duration measures:",
                    "options": {"A": "Coupon payment frequency", "B": "Weighted average time to receive cash flows (interest rate sensitivity)", "C": "Remaining term to maturity only", "D": "Default probability"},
                    "correct_option": "B",
                },
                {
                    "question_text": "In actuarial asset-liability matching, bond duration is used to:",
                    "options": {"A": "Select highest-yielding bonds", "B": "Match interest rate sensitivity of assets to liabilities", "C": "Forecast equity returns", "D": "Calculate policy reserve"},
                    "correct_option": "B",
                },
            ],
        },
        ],
    },
]

CORE_USERS = [
    {"name": "Alex Learner", "email": "learner@onboardiq.io", "role": "Learner", "password": "learner123", "manager_email": "jordan@onboardiq.io"},
    {"name": "Huzaif",       "email": "huzaif@onboardiq.io",  "role": "Learner", "password": "huzaif123",  "manager_email": "jordan@onboardiq.io"},
    {"name": "Zubeen",       "email": "zubeen@onboardiq.io",  "role": "Learner", "password": "zubeen123",  "manager_email": "jordan@onboardiq.io"},
    {"name": "Asfi",         "email": "asfi@onboardiq.io",    "role": "Learner", "password": "asfi123",    "manager_email": "jordan@onboardiq.io"},
    {"name": "Morgan Manager", "email": "manager@onboardiq.io", "role": "Manager", "password": "manager123"},
    {"name": "Jordan Manager", "email": "jordan@onboardiq.io", "role": "Manager", "password": "manager456"},
    {"name": "Admin Root", "email": "admin@onboardiq.io", "role": "Admin", "password": "admin123"},
]

# ---------------------------------------------------------------------------
# Real OULAD-mapped learner cohort (30 users under Jordan Manager)
# Behavioural profiles derived from OULAD BBB-2013J cluster archetypes:
#   Project Ready  (~10): high score, 1 attempt, fast, good reading
#   Needs Coaching (~12): decent score, 1-2 attempts, moderate engagement
#   At-Risk        (~8) : low score, 3+ attempts, minimal reading
# ---------------------------------------------------------------------------

REAL_LEARNERS = [
    # ── Project Ready (~10) ───────────────────────────────────────────────
    {"name": "Sahil P",          "email": "sahil.p@onboardiq.io",        "score": 92.0, "attempts": 1, "completion_seconds": 55,  "reading_duration": 160},
    {"name": "Vincy Grover",     "email": "vincy.grover@onboardiq.io",   "score": 88.0, "attempts": 1, "completion_seconds": 70,  "reading_duration": 175},
    {"name": "Priya Tripathi",   "email": "priya.tripathi@onboardiq.io", "score": 95.0, "attempts": 1, "completion_seconds": 45,  "reading_duration": 190},
    {"name": "Athiq Rahaman",    "email": "athiq.r@onboardiq.io",        "score": 90.0, "attempts": 1, "completion_seconds": 60,  "reading_duration": 155},
    {"name": "Sharath K",        "email": "sharath.k@onboardiq.io",      "score": 87.0, "attempts": 1, "completion_seconds": 80,  "reading_duration": 170},
    {"name": "Akshay V",         "email": "akshay.v@onboardiq.io",       "score": 93.0, "attempts": 1, "completion_seconds": 50,  "reading_duration": 180},
    {"name": "Adarsh S",         "email": "adarsh.s@onboardiq.io",       "score": 89.0, "attempts": 1, "completion_seconds": 65,  "reading_duration": 165},
    {"name": "Sai Krishna",      "email": "sai.krishna@onboardiq.io",    "score": 91.0, "attempts": 1, "completion_seconds": 58,  "reading_duration": 172},
    {"name": "Vijay Tripathi",   "email": "vijay.t@onboardiq.io",        "score": 86.0, "attempts": 1, "completion_seconds": 75,  "reading_duration": 158},
    {"name": "Surya Kumar",      "email": "surya.kumar@onboardiq.io",    "score": 94.0, "attempts": 1, "completion_seconds": 48,  "reading_duration": 185},
    # ── Needs Coaching (~12) ─────────────────────────────────────────────
    {"name": "Mark Willson",     "email": "mark.w@onboardiq.io",         "score": 82.0, "attempts": 2, "completion_seconds": 210, "reading_duration": 260},
    {"name": "Hussain",          "email": "hussain@onboardiq.io",        "score": 79.0, "attempts": 2, "completion_seconds": 240, "reading_duration": 280},
    {"name": "Malikarjun Kumar", "email": "malikarjun.k@onboardiq.io",   "score": 75.0, "attempts": 2, "completion_seconds": 270, "reading_duration": 245},
    {"name": "Afreen Khan",      "email": "afreen.k@onboardiq.io",       "score": 81.0, "attempts": 1, "completion_seconds": 200, "reading_duration": 255},
    {"name": "Daisy Shah",       "email": "daisy.shah@onboardiq.io",     "score": 77.0, "attempts": 2, "completion_seconds": 255, "reading_duration": 270},
    {"name": "Tanya G",          "email": "tanya.g@onboardiq.io",        "score": 80.0, "attempts": 2, "completion_seconds": 230, "reading_duration": 265},
    {"name": "Raghav S",         "email": "raghav.s@onboardiq.io",       "score": 78.0, "attempts": 2, "completion_seconds": 245, "reading_duration": 250},
    {"name": "Deepshika Goyal",  "email": "deepshika.g@onboardiq.io",    "score": 83.0, "attempts": 1, "completion_seconds": 195, "reading_duration": 275},
    {"name": "Nikhil B",         "email": "nikhil.b@onboardiq.io",       "score": 76.0, "attempts": 2, "completion_seconds": 260, "reading_duration": 240},
    {"name": "Zubia Khan",       "email": "zubia.khan@onboardiq.io",     "score": 84.0, "attempts": 1, "completion_seconds": 185, "reading_duration": 290},
    {"name": "Santosh Kumar",    "email": "santosh.k@onboardiq.io",      "score": 74.0, "attempts": 2, "completion_seconds": 280, "reading_duration": 235},
    {"name": "Arti Sharma",      "email": "arti.sharma@onboardiq.io",    "score": 80.0, "attempts": 2, "completion_seconds": 220, "reading_duration": 260},
    # ── At-Risk (~8) ──────────────────────────────────────────────────────
    {"name": "Shashank Kumar",   "email": "shashank.k@onboardiq.io",     "score": 55.0, "attempts": 4, "completion_seconds": 380, "reading_duration": 35},
    {"name": "Harsha Iyyer",     "email": "harsha.i@onboardiq.io",       "score": 48.0, "attempts": 5, "completion_seconds": 420, "reading_duration": 28},
    {"name": "Somnath G",        "email": "somnath.g@onboardiq.io",      "score": 52.0, "attempts": 4, "completion_seconds": 400, "reading_duration": 32},
    {"name": "Arvind Kumar",     "email": "arvind.k@onboardiq.io",       "score": 45.0, "attempts": 5, "completion_seconds": 450, "reading_duration": 22},
    {"name": "Prateeksha Singh", "email": "prateeksha.s@onboardiq.io",   "score": 58.0, "attempts": 3, "completion_seconds": 360, "reading_duration": 40},
    {"name": "Juveria Anjum",    "email": "juveria.a@onboardiq.io",      "score": 50.0, "attempts": 4, "completion_seconds": 410, "reading_duration": 30},
    {"name": "Neha J",           "email": "neha.j@onboardiq.io",         "score": 43.0, "attempts": 5, "completion_seconds": 470, "reading_duration": 20},
    {"name": "Athira S",         "email": "athira.s@onboardiq.io",       "score": 57.0, "attempts": 3, "completion_seconds": 350, "reading_duration": 38},
]


# ---------------------------------------------------------------------------
# Main seeding routine
# ---------------------------------------------------------------------------

def seed():
    print("→ Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------ #
        # 1. Curriculum content                                               #
        # ------------------------------------------------------------------ #
        print("→ Seeding tracks, modules, concepts, and quiz questions...")
        seeded_modules = []
        seeded_concepts = []

        for track_data in TRACKS:
            track = Track(
                id=uid(),
                name=track_data["name"],
                description=track_data["description"],
            )
            db.add(track)
            db.flush()

            for mod_data in track_data["modules"]:
                module = Module(
                    id=uid(),
                    track_id=track.id,
                    title=mod_data["title"],
                    difficulty_level=mod_data["difficulty_level"],
                    sequence_order=mod_data["sequence_order"],
                )
                db.add(module)
                db.flush()
                seeded_modules.append(module)

                for concept_data in mod_data["concepts"]:
                    concept = Concept(
                        id=uid(),
                        module_id=module.id,
                        title=concept_data["title"],
                        summary_text=concept_data["summary_text"],
                        youtube_video_id=concept_data["youtube_video_id"],
                        sequence_order=concept_data["sequence_order"],
                    )
                    db.add(concept)
                    seeded_concepts.append(concept)

                for q_data in mod_data["questions"]:
                    question = QuizQuestion(
                        id=uid(),
                        module_id=module.id,
                        question_text=q_data["question_text"],
                        options=q_data["options"],
                        correct_option=q_data["correct_option"],
                    )
                    db.add(question)

        db.flush()

        # ------------------------------------------------------------------ #
        # 2. Core users                                                       #
        # ------------------------------------------------------------------ #
        print("→ Seeding core users (Learner, Manager x2, Admin)...")
        core_user_objs: dict[str, User] = {}
        for cu in CORE_USERS:
            user = User(
                id=uid(),
                name=cu["name"],
                email=cu["email"],
                role=cu["role"],
                hashed_password=hash_password(cu["password"]),
            )
            db.add(user)
            core_user_objs[cu["email"]] = user

        db.flush()

        # Assign real learners to their manager now that all core users are flushed
        for cu in CORE_USERS:
            if cu.get("manager_email"):
                core_user_objs[cu["email"]].manager_id = core_user_objs[cu["manager_email"]].id

        db.flush()

        jordan_id = core_user_objs["jordan@onboardiq.io"].id

        # ------------------------------------------------------------------ #
        # 3. Real OULAD-mapped learner cohort (30 users under Jordan)        #
        # ------------------------------------------------------------------ #
        print("→ Seeding 30 real OULAD-mapped learners under Jordan Manager...")

        base_time = now_utc() - timedelta(days=14)

        # Build per-module first-concept lookup
        module_concepts: dict = {}
        for concept in seeded_concepts:
            if concept.module_id not in module_concepts:
                module_concepts[concept.module_id] = concept

        # seeded_modules layout (2 per track × 3 tracks):
        #   [0,1] = Actuarial Statistics
        #   [2,3] = Actuarial Mathematics
        #   [4,5] = Business Finance
        # Assign each user 1 module from every track so all 3 track domains appear.
        TRACK_OFFSETS = [0, 2, 4]  # module 0 = Stats, 2 = Math, 4 = Finance

        for i, profile in enumerate(REAL_LEARNERS):
            user = User(
                id=uid(),
                name=profile["name"],
                email=profile["email"],
                role="Learner",
                hashed_password=hash_password("password123"),
                manager_id=jordan_id,
            )
            db.add(user)
            db.flush()

            # Pick one module from each of the 3 tracks
            assigned_modules = [
                seeded_modules[TRACK_OFFSETS[0]],
                seeded_modules[TRACK_OFFSETS[1]],
                seeded_modules[TRACK_OFFSETS[2]],
            ]

            for mod in assigned_modules:
                concept = module_concepts.get(mod.id)

                for attempt_num in range(1, profile["attempts"] + 1):
                    started = base_time + timedelta(
                        days=random.randint(0, 10),
                        seconds=random.randint(0, 3600),
                    )
                    completed = started + timedelta(seconds=profile["completion_seconds"])
                    score = float(profile["score"]) if attempt_num == profile["attempts"] else float(profile["score"]) * 0.7
                    quiz_attempt = QuizAttempt(
                        id=uid(),
                        user_id=user.id,
                        module_id=mod.id,
                        attempt_number=attempt_num,
                        score_percentage=round(score, 2),
                        is_passed=score >= 70,
                        started_at=started,
                        completed_at=completed,
                    )
                    db.add(quiz_attempt)

                if concept:
                    for event_type in ("page_opened", "page_closed"):
                        tlog = TelemetryLog(
                            user_id=user.id,
                            concept_id=concept.id,
                            event_type=event_type,
                            duration_seconds=profile["reading_duration"] if event_type == "page_closed" else None,
                            timestamp=base_time + timedelta(days=random.randint(0, 10)),
                        )
                        db.add(tlog)

        db.commit()
        print("\n✅ Seeding complete. Summary:")
        total_mods = sum(len(t["modules"]) for t in TRACKS)
        total_concepts = sum(len(m["concepts"]) for t in TRACKS for m in t["modules"])
        print(f"   Tracks           : {len(TRACKS)}")
        print(f"   Modules          : {total_mods}")
        print(f"   Concepts         : {total_concepts}")
        print(f"   Core users       : {len(CORE_USERS)}")
        print(f"   Real OULAD users : {len(REAL_LEARNERS)}")

    except Exception as exc:
        db.rollback()
        print(f"\n❌ Seeding failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
