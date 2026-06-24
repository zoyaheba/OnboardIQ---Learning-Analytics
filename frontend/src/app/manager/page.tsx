"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, CohortResponse, CohortUser, OuladValidation, TrackBreakdown, UserProfile } from "@/lib/api";
import CohortChart from "@/components/CohortChart";
import ThemeToggle from "@/components/ThemeToggle";

const FLAG_STYLES: Record<string, { badge: string; bar: string; dot: string }> = {
  "Project Ready": {
    badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    bar: "bg-emerald-500",
    dot: "bg-emerald-400",
  },
  "Needs Coaching": {
    badge: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    bar: "bg-amber-400",
    dot: "bg-amber-400",
  },
  "At-Risk": {
    badge: "bg-rose-500/15 text-rose-300 border-rose-500/40",
    bar: "bg-rose-500",
    dot: "bg-rose-400",
  },
};

const FLAG_EMOJI: Record<string, string> = {
  "Project Ready": "🟢",
  "Needs Coaching": "🟡",
  "At-Risk": "🔴",
};

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl px-6 py-5">
      <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
      <p className="text-white text-3xl font-bold">{value}</p>
      {sub && <p className="text-slate-500 text-xs mt-1">{sub}</p>}
    </div>
  );
}

function ORIBar({ pct, flag }: { pct: number; flag: string }) {
  const style = FLAG_STYLES[flag] ?? FLAG_STYLES["Needs Coaching"];
  return (
    <div className="flex items-center gap-3 min-w-[140px]">
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${style.bar}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-slate-300 text-xs font-medium w-12 text-right">{pct}%</span>
    </div>
  );
}

export default function ManagerPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [data, setData] = useState<CohortResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("All");
  const [trackFilter, setTrackFilter] = useState<string>("All");
  const [search, setSearch] = useState("");
  const [showML, setShowML] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("onboardiq_user");
    if (!stored) { router.push("/"); return; }
    const profile: UserProfile = JSON.parse(stored);
    setUser(profile);
    api
      .getCohorts(profile.id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const cohorts = data?.cohorts ?? [];
  const flags = ["All", "Project Ready", "Needs Coaching", "At-Risk"];

  const flagCounts = flags.slice(1).reduce<Record<string, number>>((acc, f) => {
    acc[f] = cohorts.filter((u) => u.cluster_flag === f).length;
    return acc;
  }, {});

  const uniqueTracks = ["All", ...Array.from(new Set(cohorts.map((u) => u.track_name))).sort()];

  const filtered = cohorts.filter((u) => {
    const matchFlag = filter === "All" || u.cluster_flag === filter;
    const matchTrack = trackFilter === "All" || u.track_name === trackFilter;
    const matchSearch =
      search === "" ||
      u.user_name.toLowerCase().includes(search.toLowerCase()) ||
      u.user_email.toLowerCase().includes(search.toLowerCase());
    return matchFlag && matchTrack && matchSearch;
  });

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Top nav */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">
              ← Home
            </Link>
            <span className="text-slate-600">|</span>
            <div>
              <span className="text-white font-semibold">Manager Dashboard</span>
              <span className="ml-2 text-slate-500 text-sm">Cohort Intelligence Panel</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-slate-400 text-sm hidden sm:block">
                {user.name}
              </span>
            )}
            <ThemeToggle />
            <button
              onClick={() => { setLoading(true); if (user) api.getCohorts(user.id).then(setData).finally(() => setLoading(false)); }}
              className="text-slate-400 hover:text-white text-sm transition-colors px-3 py-1.5 border border-slate-700 rounded-lg hover:border-slate-500"
            >
              ↻ Refresh
            </button>
            <button
              onClick={() => { localStorage.removeItem("onboardiq_user"); router.push("/"); }}
              className="text-slate-400 hover:text-rose-400 text-sm transition-colors px-3 py-1.5 border border-slate-700 rounded-lg hover:border-rose-500/50"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-32 text-slate-500 flex-col gap-3">
            <div className="w-8 h-8 border-2 border-slate-700 border-t-indigo-500 rounded-full animate-spin" />
            <p className="text-sm">Running ML clustering pipeline…</p>
          </div>
        ) : error ? (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-8 text-center">
            <p className="text-amber-300 text-lg font-semibold mb-2">Not enough data to run clustering</p>
            <p className="text-slate-400 text-sm max-w-md mx-auto">
              {error.includes("Insufficient") 
                ? "Clustering requires at least 3 learners with activity data. As more employees complete onboarding modules, the ML pipeline will activate automatically."
                : error}
            </p>
          </div>
        ) : data ? (
          <>
            {/* Business summary cards */}
            <section className="mb-8">
              <h2 className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-4">
                Cohort Overview
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <StatCard
                  label="Total Employees"
                  value={String(data.model_validation.n_users_clustered)}
                  sub="Active learners in your cohort"
                />
                <StatCard
                  label="Project Ready"
                  value={String(flagCounts["Project Ready"] ?? 0)}
                  sub="On track for project allocation"
                />
                <StatCard
                  label="Needs Coaching"
                  value={String(flagCounts["Needs Coaching"] ?? 0)}
                  sub="Targeted support recommended"
                />
                <StatCard
                  label="At-Risk"
                  value={String(flagCounts["At-Risk"] ?? 0)}
                  sub="Immediate intervention advised"
                />
              </div>
            </section>

            {/* Cohort scatter chart */}
            <section className="mb-8 grid grid-cols-1 xl:grid-cols-2 gap-4">
              <CohortChart cohorts={cohorts} />
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3">
                <div>
                  <h3 className="text-white font-semibold text-sm mb-1">Cluster Legend</h3>
                  <p className="text-slate-500 text-xs">K-Means (k=3) · Scikit-Learn · random_state=42</p>
                </div>
                <div className="space-y-3 mt-1">
                  <div className="flex items-start gap-3">
                    <span className="w-3 h-3 rounded-full bg-emerald-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-emerald-300 text-xs font-semibold">Project Ready</p>
                      <p className="text-slate-500 text-xs mt-0.5">High K + High E · fast quiz completion · strong engagement</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="w-3 h-3 rounded-full bg-amber-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-amber-300 text-xs font-semibold">Needs Coaching</p>
                      <p className="text-slate-500 text-xs mt-0.5">Mid K + Low V · thorough but slow · targeted support recommended</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="w-3 h-3 rounded-full bg-rose-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-rose-300 text-xs font-semibold">At-Risk</p>
                      <p className="text-slate-500 text-xs mt-0.5">Low K + High attempts · poor engagement · early intervention needed</p>
                    </div>
                  </div>
                </div>
                <div className="mt-auto pt-3 border-t border-slate-800">
                  <p className="text-slate-500 text-xs">X-axis: Engagement Score (E) · Y-axis: Knowledge Score (K)</p>
                  <p className="text-slate-600 text-xs mt-0.5">ORI = 0.5·K + 0.3·V + 0.2·E</p>
                </div>
              </div>
            </section>

            {/* Filter + Search bar */}
            <section className="mb-5 flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
                {flags.map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      filter === f
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {f === "All" ? `All (${cohorts.length})` : `${FLAG_EMOJI[f]} ${f} (${flagCounts[f] ?? 0})`}
                  </button>
                ))}
              </div>
              <select
                value={trackFilter}
                onChange={(e) => setTrackFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
              >
                {uniqueTracks.map((t) => (
                  <option key={t} value={t}>
                    {t === "All" ? "All Tracks" : t}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Search by name or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-600 text-sm rounded-xl px-4 py-2 focus:outline-none focus:border-indigo-500 w-64"
              />
              <span className="text-slate-500 text-xs ml-auto">{filtered.length} employees</span>
            </section>

            {/* Cohort table */}
            <section className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    {["Employee", "Track Domain", "ORI Score", "Difficulty", "Cluster Flag", "Diagnostic Comment"].map((h) => (
                      <th key={h} className="text-left px-5 py-4 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((user: CohortUser, i) => {
                    const style = FLAG_STYLES[user.cluster_flag] ?? FLAG_STYLES["Needs Coaching"];
                    return (
                      <tr
                        key={user.user_email}
                        className={`border-b border-slate-800/50 hover:bg-slate-800/40 transition-colors ${
                          i === filtered.length - 1 ? "border-b-0" : ""
                        }`}
                      >
                        <td className="px-5 py-4">
                          <div className="text-slate-200 font-medium">{user.user_name}</div>
                          <div className="text-slate-500 text-xs mt-0.5">{user.user_email}</div>
                        </td>
                        <td className="px-5 py-4">
                          {user.track_breakdown && user.track_breakdown.length > 0 ? (
                            <div className="flex flex-col gap-1.5">
                              {user.track_breakdown.map((t: TrackBreakdown) => (
                                <div key={t.track} className="flex items-center gap-2">
                                  <span
                                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                                      t.ori >= 0.70 ? "bg-emerald-400" : t.ori >= 0.45 ? "bg-amber-400" : "bg-rose-400"
                                    }`}
                                  />
                                  <span className="text-slate-300 text-xs truncate max-w-[120px]" title={t.track}>{t.track}</span>
                                  <span
                                    className={`text-[10px] font-semibold ml-auto ${
                                      t.ori >= 0.70 ? "text-emerald-400" : t.ori >= 0.45 ? "text-amber-400" : "text-rose-400"
                                    }`}
                                  >
                                    {Math.round(t.ori * 100)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-500 text-xs">No data</span>
                          )}
                        </td>
                        <td className="px-5 py-4">
                          <ORIBar pct={user.numeric_ori_percentage} flag={user.cluster_flag} />
                          <div className="text-slate-500 text-[10px] mt-1">
                            K={user.scores.K.toFixed(2)} · V={user.scores.V.toFixed(2)} · E={user.scores.E.toFixed(2)}
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                            user.difficulty_label === "Advanced"
                              ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                              : user.difficulty_label === "Intermediate"
                              ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                              : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          }`}>
                            {user.difficulty_label ?? "Beginner"}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${style.badge}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                            {user.cluster_flag}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-slate-400 text-xs leading-relaxed max-w-xs">
                          {user.diagnostic_comment}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filtered.length === 0 && (
                <div className="py-12 text-center text-slate-600 text-sm">
                  No employees match the current filter.
                </div>
              )}
            </section>

            {/* ML Validation accordion */}
            <section className="mt-8">
              <button
                onClick={() => setShowML((v) => !v)}
                className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-900 border border-slate-800 rounded-2xl text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-colors text-sm"
              >
                <span className="flex items-center gap-2 font-medium">
                  <span className="text-indigo-400 text-base">⚙</span>
                  ML Model Validation — Technical Details
                </span>
                <span className="text-xs text-slate-600">{showML ? "▲ Hide" : "▼ Show"}</span>
              </button>

              {showML && (
                <div className="mt-3 bg-slate-900 border border-slate-700 rounded-2xl p-6">
                  <p className="text-slate-300 text-xs mb-5 leading-relaxed">
                    Internal clustering quality metrics computed by the K-Means pipeline (StandardScaler + k=3, random_state=42).
                    These validate the ML model structure — not visible to managers in normal use.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl px-5 py-4">
                      <p className="text-slate-300 text-xs uppercase tracking-wider mb-1 font-semibold">Silhouette Score</p>
                      <p className="text-indigo-300 text-2xl font-bold">{data.model_validation.silhouette_score.toFixed(4)}</p>
                      <p className="text-slate-400 text-xs mt-1">Cluster separation quality · higher = better · threshold 0.60</p>
                    </div>
                    <div className="bg-slate-800 border border-slate-700 rounded-xl px-5 py-4">
                      <p className="text-slate-300 text-xs uppercase tracking-wider mb-1 font-semibold">Davies-Bouldin Index</p>
                      <p className="text-indigo-300 text-2xl font-bold">{data.model_validation.davies_bouldin_score.toFixed(4)}</p>
                      <p className="text-slate-400 text-xs mt-1">Intra/inter cluster ratio · lower = better · threshold &lt;1.0</p>
                    </div>
                    <div className="bg-slate-800 border border-slate-700 rounded-xl px-5 py-4">
                      <p className="text-slate-300 text-xs uppercase tracking-wider mb-1 font-semibold">Cluster Distribution</p>
                      <p className="text-indigo-300 text-2xl font-bold">
                        {flagCounts["Project Ready"] ?? 0} / {flagCounts["Needs Coaching"] ?? 0} / {flagCounts["At-Risk"] ?? 0}
                      </p>
                      <p className="text-slate-400 text-xs mt-1">Project Ready / Needs Coaching / At-Risk</p>
                    </div>
                  </div>
                  <div className="border-t border-slate-700 pt-4">
                    <p className="text-slate-300 text-xs leading-relaxed">
                      <span className="text-white font-medium">Algorithm:</span> KMeans(n_clusters=3, random_state=42, n_init=10) · StandardScaler normalisation ·
                      ORI = 0.5·K + 0.3·V + 0.2·E · Feature vector averaged across all completed tracks per user
                    </p>
                  </div>

                  {/* OULAD external validation */}
                  {data.model_validation.oulad_validation ? (() => {
                    const ov = data.model_validation.oulad_validation!;
                    const CLUSTER_STYLE: Record<string, string> = {
                      "Project Ready": "text-emerald-400 border-emerald-700/40",
                      "Needs Coaching": "text-amber-400 border-amber-700/40",
                      "At-Risk":        "text-rose-400 border-rose-700/40",
                    };
                    const BADGE: Record<string, string> = {
                      "Project Ready": "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
                      "Needs Coaching": "bg-amber-500/15 text-amber-300 border-amber-500/40",
                      "At-Risk":        "bg-rose-500/15 text-rose-300 border-rose-500/40",
                    };
                    return (
                      <div className="mt-5 border-t border-slate-700 pt-5">
                        <p className="text-white text-xs font-semibold uppercase tracking-wider mb-1 flex items-center gap-2">
                          <span className="text-emerald-400">✓</span>
                          External Validation — Real Student Data (OULAD)
                        </p>
                        <p className="text-slate-300 text-xs mb-4 leading-relaxed">
                          Same K/V/E derivation + KMeans(k=3) applied to{" "}
                          <span className="text-white font-medium">{ov.n_students} real students</span>{" "}
                          from the Open University Learning Analytics Dataset ({ov.module}).
                          Silhouette <span className="text-emerald-400 font-semibold">{ov.silhouette_score.toFixed(4)}</span>
                          {ov.silhouette_score >= 0.50
                            ? " — strong cluster separation confirmed in real student data. The Project Ready, Needs Coaching, and At-Risk archetypes generalise beyond synthetic users."
                            : ov.silhouette_score >= 0.40
                            ? " — moderate cluster separation detected in real student data. Archetypes are present, with some overlap between Needs Coaching and At-Risk."
                            : " — weaker separation in real student data; archetypes are directionally valid but overlap more than in the synthetic cohort."}
                        </p>

                        {/* Centroid cluster summary cards */}
                        <div className="grid grid-cols-3 gap-3 mb-5">
                          {ov.centroids.map((c) => (
                            <div key={c.cluster} className={`bg-slate-800 border rounded-xl px-4 py-3 ${CLUSTER_STYLE[c.cluster] ?? "border-slate-700"}`}>
                              <p className={`text-xs font-bold mb-2 ${CLUSTER_STYLE[c.cluster]?.split(" ")[0] ?? "text-white"}`}>{c.cluster}</p>
                              <p className="text-white text-lg font-bold">{c.count} <span className="text-slate-400 text-xs font-normal">students</span></p>
                              <div className="mt-2 grid grid-cols-3 gap-1 text-center">
                                {(["K","V","E"] as const).map((key) => (
                                  <div key={key}>
                                    <p className="text-slate-400 text-xs">{key}</p>
                                    <p className="text-white text-xs font-semibold">{c[key].toFixed(2)}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Per-student data table */}
                        <div className="overflow-x-auto rounded-xl border border-slate-700">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-slate-700 bg-slate-800/60">
                                <th className="text-left text-slate-300 font-semibold px-4 py-2">Student</th>
                                <th className="text-center text-slate-300 font-semibold px-3 py-2">K</th>
                                <th className="text-center text-slate-300 font-semibold px-3 py-2">V</th>
                                <th className="text-center text-slate-300 font-semibold px-3 py-2">E</th>
                                <th className="text-center text-slate-300 font-semibold px-4 py-2">Cluster</th>
                              </tr>
                            </thead>
                            <tbody>
                              {ov.students.map((s, idx) => (
                                <tr key={s.student_id} className={`border-b border-slate-700/50 ${idx % 2 === 0 ? "bg-slate-800/20" : ""}`}>
                                  <td className="text-slate-300 px-4 py-2 font-mono">{s.student_id}</td>
                                  <td className="text-center text-indigo-300 px-3 py-2 font-semibold">{s.K.toFixed(3)}</td>
                                  <td className="text-center text-indigo-300 px-3 py-2 font-semibold">{s.V.toFixed(3)}</td>
                                  <td className="text-center text-indigo-300 px-3 py-2 font-semibold">{s.E.toFixed(3)}</td>
                                  <td className="text-center px-4 py-2">
                                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${BADGE[s.cluster] ?? "bg-slate-700 text-slate-300 border-slate-600"}`}>
                                      {s.cluster}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    );
                  })() : (
                    <div className="mt-4 border-t border-slate-700 pt-4">
                      <p className="text-slate-500 text-xs italic">OULAD external validation not available — run validate_oulad.py to cache data.</p>
                    </div>
                  )}
                </div>
              )}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
