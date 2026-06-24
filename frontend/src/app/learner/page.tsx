"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, UserConcept, UserModule, UserTrack, ModuleDetail, UserProfile, QuizResult } from "@/lib/api";
import QuizCard from "@/components/QuizCard";
import ThemeToggle from "@/components/ThemeToggle";

const LEVEL_STYLE: Record<string, string> = {
  Beginner: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  Intermediate: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  Advanced: "bg-rose-500/15 text-rose-400 border-rose-500/30",
};

const TRACK_ACCENT: Record<string, { border: string; glow: string; icon: string }> = {
  "Actuarial Statistics":  { border: "border-indigo-500/50",  glow: "hover:shadow-indigo-900/40",  icon: "📊" },
  "Actuarial Mathematics": { border: "border-violet-500/50",  glow: "hover:shadow-violet-900/40",  icon: "📐" },
  "Business Finance":      { border: "border-emerald-500/50", glow: "hover:shadow-emerald-900/40", icon: "💼" },
};

export default function LearnerPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [tracks, setTracks] = useState<UserTrack[]>([]);
  const [currentTrack, setCurrentTrack] = useState<UserTrack | null>(null);
  const [activeModuleDetail, setActiveModuleDetail] = useState<ModuleDetail | null>(null);
  const [activeConcept, setActiveConcept] = useState<UserConcept | null>(null);
  const [unlockedConceptIds, setUnlockedConceptIds] = useState<Set<string>>(new Set());
  const [showQuiz, setShowQuiz] = useState(false);
  const [loading, setLoading] = useState(true);
  const [progressionResult, setProgressionResult] = useState<QuizResult | null>(null);
  const [showVictory, setShowVictory] = useState(false);
  const conceptRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // ── Telemetry refs ────────────────────────────────────────────────────
  const pageOpenedAt = useRef<number | null>(null);
  const activeConceptRef = useRef<UserConcept | null>(null);
  const userRef = useRef<UserProfile | null>(null);

  // ── Bootstrap ─────────────────────────────────────────────────────────
  useEffect(() => {
    const stored = localStorage.getItem("onboardiq_user");
    if (!stored) { router.push("/"); return; }
    const profile: UserProfile = JSON.parse(stored);
    setUser(profile);
    userRef.current = profile;
    // Clear any stale refs from a previous session
    activeConceptRef.current = null;
    pageOpenedAt.current = null;

    api.getTracksForUser(profile.id).then((allTracks) => {
      setTracks(allTracks);
      setLoading(false);
      // seed initial unlocked concepts (first concept of first module)
      const initial = new Set<string>();
      allTracks.forEach((t) => {
        t.modules.forEach((m) => {
          m.concepts.forEach((c) => { if (!c.is_locked) initial.add(c.id); });
        });
      });
      setUnlockedConceptIds(initial);
    }).catch(() => {
      // Stale user ID (e.g. after DB re-seed) — clear and redirect to login
      localStorage.removeItem("onboardiq_user");
      router.push("/");
    });
  }, []);

  // ── Visibility telemetry (flush on tab-hide) ──────────────────────────
  const flushPageClose = async (concept: UserConcept) => {
    if (!pageOpenedAt.current) return;
    const duration = Math.floor((Date.now() - pageOpenedAt.current) / 1000);
    pageOpenedAt.current = null;
    await api.logTelemetry({
      user_id: userRef.current?.id ?? "",
      concept_id: concept.id,
      event_type: "page_closed",
      duration_seconds: duration,
    });
  };

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "hidden" && activeConceptRef.current) {
        flushPageClose(activeConceptRef.current);
      } else if (document.visibilityState === "visible" && activeConceptRef.current) {
        pageOpenedAt.current = Date.now();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  // ── Telemetry helpers ──────────────────────────────────────────────────
  const selectConcept = async (concept: UserConcept) => {
    if (activeConceptRef.current && activeConceptRef.current.id !== concept.id) {
      await flushPageClose(activeConceptRef.current);
    }
    activeConceptRef.current = concept;
    setActiveConcept(concept);
    pageOpenedAt.current = Date.now();
    api.logTelemetry({
      user_id: userRef.current?.id ?? "",
      concept_id: concept.id,
      event_type: "page_opened",
      duration_seconds: null,
    });
    // smooth scroll to concept section
    setTimeout(() => {
      conceptRefs.current[concept.id]?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  };

  const selectModule = async (mod: UserModule) => {
    if (mod.is_locked) return;
    const detail = await api.getModule(mod.id);
    setActiveModuleDetail(detail);
    setShowQuiz(false);
    // Select first unlocked concept
    const firstUnlocked = mod.concepts.find((c) => !c.is_locked || unlockedConceptIds.has(c.id));
    if (firstUnlocked) selectConcept(firstUnlocked);
  };

  const handleVideoPlay = () => {
    if (!activeConcept) return;
    api.logTelemetry({
      user_id: userRef.current?.id ?? "",
      concept_id: activeConcept.id,
      event_type: "video_played",
      duration_seconds: null,
    });
  };
  // ── End telemetry ─────────────────────────────────────────────────────

  const enterTrack = async (track: UserTrack) => {
    setCurrentTrack(track);
    setActiveModuleDetail(null);
    setActiveConcept(null);
    // Auto-open first unlocked module
    const firstMod = track.modules.find((m) => !m.is_locked);
    if (firstMod) await selectModule(firstMod);
  };

  const backToGateway = () => {
    if (activeConceptRef.current) flushPageClose(activeConceptRef.current);
    activeConceptRef.current = null;
    setCurrentTrack(null);
    setActiveModuleDetail(null);
    setActiveConcept(null);
    // Refresh tracks to get updated lock states
    if (user) {
      api.getTracksForUser(user.id).then((updated) => {
        setTracks(updated);
        const ids = new Set<string>();
        updated.forEach((t) => t.modules.forEach((m) => m.concepts.forEach((c) => { if (!c.is_locked) ids.add(c.id); })));
        setUnlockedConceptIds(ids);
      });
    }
  };

  // ── All concepts flat list for current module (with live lock state) ──
  const allConcepts: UserConcept[] = currentTrack
    ? currentTrack.modules.flatMap((m) =>
        m.concepts.map((c) => ({
          ...c,
          is_locked: c.is_locked && !unlockedConceptIds.has(c.id),
        }))
      )
    : [];

  // ─────────────────────────────────────────────────────────────────────
  // VIEW STATE 1: Track Gateway Grid
  // ─────────────────────────────────────────────────────────────────────
  if (!currentTrack) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col">
        {/* Top bar */}
        <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm">IQ</div>
            <span className="text-white font-semibold">Learner Portal</span>
          </div>
          {user && (
            <div className="flex items-center gap-4">
              <span className="text-slate-400 text-sm">{user.name}</span>
              <ThemeToggle />
              <button
                onClick={() => { localStorage.removeItem("onboardiq_user"); router.push("/"); }}
                className="text-slate-500 hover:text-rose-400 text-sm transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </header>

        <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
          <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Training Tracks</h1>
          <p className="text-slate-400 text-sm mb-12">Select a domain to begin your onboarding curriculum.</p>

          {loading ? (
            <div className="flex items-center gap-3 text-slate-500">
              <div className="w-5 h-5 border-2 border-slate-700 border-t-indigo-500 rounded-full animate-spin" />
              Loading curriculum…
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 w-full max-w-4xl">
              {tracks.map((track) => {
                const accent = TRACK_ACCENT[track.name] ?? { border: "border-slate-700", glow: "hover:shadow-slate-900/40", icon: "📚" };
                return (
                  <button
                    key={track.id}
                    onClick={() => enterTrack(track)}
                    className={`group bg-slate-900 border ${accent.border} hover:border-opacity-100 rounded-2xl p-8 flex flex-col gap-4 text-left transition-all duration-200 hover:shadow-xl ${accent.glow} hover:-translate-y-0.5`}
                  >
                    <div className="text-4xl">{accent.icon}</div>
                    <div>
                      <h2 className="text-white font-bold text-lg leading-snug mb-1">{track.name}</h2>
                      <p className="text-slate-500 text-xs leading-relaxed line-clamp-3">{track.description ?? ""}</p>
                    </div>
                    <div className="flex items-center justify-between mt-auto pt-2 border-t border-slate-800">
                      <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${LEVEL_STYLE[track.dynamic_level] ?? LEVEL_STYLE["Beginner"]}`}>
                        {track.dynamic_level}
                      </span>
                      <span className="text-slate-600 text-xs">{track.modules.length} module{track.modules.length !== 1 ? "s" : ""}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </main>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // VIEW STATE 2: Learning Workspace
  // ─────────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">

      {/* ── Sidebar ────────────────────────────────────────────────────── */}
      <aside className="w-72 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col">

        {/* Back nav + user */}
        <div className="px-5 py-4 border-b border-slate-800 flex-shrink-0">
          <button
            onClick={backToGateway}
            className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors mb-3"
          >
            ← Back to Tracks Dashboard
          </button>
          {user && (
            <div className="flex items-center justify-between">
              <span className="text-slate-500 text-xs truncate">{user.name}</span>
              <button
                onClick={() => { localStorage.removeItem("onboardiq_user"); router.push("/"); }}
                className="text-slate-600 hover:text-rose-400 text-xs transition-colors ml-2 flex-shrink-0"
              >
                Sign out
              </button>
            </div>
          )}
        </div>

        {/* Track title */}
        <div className="px-5 py-3 border-b border-slate-800/60">
          <p className="text-slate-500 text-[10px] uppercase tracking-widest font-semibold mb-0.5">Active Track</p>
          <p className="text-white text-sm font-semibold truncate">{currentTrack.name}</p>
          <span className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${LEVEL_STYLE[currentTrack.dynamic_level] ?? LEVEL_STYLE["Beginner"]}`}>
            {currentTrack.dynamic_level}
          </span>
        </div>

        {/* Module + concept tree */}
        <div className="flex-1 overflow-y-auto py-2">
          {currentTrack.modules.map((mod) => {
            const isModActive = activeModuleDetail?.id === mod.id;
            return (
              <div key={mod.id} className="mb-1">
                <button
                  onClick={() => selectModule(mod)}
                  disabled={mod.is_locked}
                  className={`w-full text-left px-5 py-3 flex items-center justify-between transition-colors ${
                    mod.is_locked
                      ? "opacity-40 cursor-not-allowed"
                      : isModActive
                      ? "bg-slate-800"
                      : "hover:bg-slate-800/60"
                  }`}
                >
                  <span className={`text-sm font-medium truncate pr-2 ${isModActive ? "text-white" : "text-slate-300"}`}>
                    {mod.is_locked && <span className="mr-1.5 text-xs">🔒</span>}
                    {mod.title}
                  </span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border flex-shrink-0 ${LEVEL_STYLE[mod.difficulty_level] ?? "bg-slate-700 text-slate-400 border-slate-600"}`}>
                    {mod.difficulty_level}
                  </span>
                </button>

                {isModActive && (
                  <div className="ml-4 border-l border-slate-700 pl-3 pb-1">
                    {mod.concepts.map((c) => {
                      const locked = c.is_locked && !unlockedConceptIds.has(c.id);
                      return (
                        <button
                          key={c.id}
                          onClick={() => !locked && selectConcept(c)}
                          disabled={locked}
                          className={`w-full text-left px-3 py-2 rounded-lg mb-0.5 text-xs font-medium transition-colors flex items-center justify-between ${
                            locked
                              ? "opacity-40 cursor-not-allowed text-slate-600"
                              : activeConcept?.id === c.id
                              ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                              : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                          }`}
                        >
                          <span>
                            <span className="text-slate-600 mr-1.5">{c.sequence_order}.</span>
                            {c.title}
                          </span>
                          {locked && <span className="text-xs ml-1 flex-shrink-0">🔒</span>}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {!activeConcept ? (
          <div className="flex-1 flex items-center justify-center flex-col gap-4 text-slate-600">
            <span className="text-6xl opacity-30">📖</span>
            <p className="text-slate-500 text-sm">Select a module from the sidebar to begin</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto" id="concept-scroll-area">

            {/* Breadcrumb */}
            <div className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur border-b border-slate-800 px-8 py-3 flex items-center gap-2">
              <span className="text-slate-500 text-xs">{activeModuleDetail?.title}</span>
              <span className="text-slate-700 text-xs">›</span>
              <span className="text-slate-300 text-xs font-medium">{activeConcept.title}</span>
            </div>

            <div className="max-w-4xl mx-auto px-8 py-8">
              <div ref={(el) => { conceptRefs.current[activeConcept.id] = el; }}>
                <h1 className="text-3xl font-bold text-white tracking-tight mb-6 leading-snug">
                  {activeConcept.title}
                </h1>

                {/* Video */}
                {activeConcept.youtube_video_id ? (
                  <div
                    className="mb-8 rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-black cursor-pointer"
                    onClick={handleVideoPlay}
                  >
                    <iframe
                      key={activeConcept.youtube_video_id}
                      src={`https://www.youtube.com/embed/${activeConcept.youtube_video_id}?enablejsapi=1&origin=${encodeURIComponent("http://localhost:3000")}`}
                      title={activeConcept.title}
                      className="w-full aspect-video"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    />
                  </div>
                ) : (
                  <div className="mb-8 rounded-2xl border border-dashed border-slate-700 bg-slate-900/50 aspect-video flex items-center justify-center">
                    <span className="text-slate-600 text-sm">No video for this concept</span>
                  </div>
                )}

                {/* Learning notes */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden mb-10">
                  <div className="px-8 py-4 border-b border-slate-800 flex items-center gap-3">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0" />
                    <span className="text-slate-300 text-sm font-semibold tracking-wide uppercase">Learning Notes</span>
                  </div>
                  <div className="px-8 py-7">
                    {(activeConcept.summary_text ?? "").split(/\n\n+/).map((para, i) => (
                      <p key={i} className="text-slate-300 leading-8 text-[15.5px] mb-5 last:mb-0">{para.trim()}</p>
                    ))}
                  </div>
                </div>

                {/* Next concepts (unlocked) */}
                {allConcepts.filter((c) => !c.is_locked && c.id !== activeConcept.id).length > 0 && (
                  <div className="mb-8">
                    <p className="text-slate-500 text-xs uppercase tracking-widest mb-3">Also available in this track</p>
                    <div className="flex flex-wrap gap-2">
                      {allConcepts.filter((c) => !c.is_locked && c.id !== activeConcept.id).map((c) => (
                        <button
                          key={c.id}
                          onClick={() => selectConcept(c)}
                          className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg transition-colors"
                        >
                          {c.title}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Quiz CTA */}
                {activeModuleDetail && (
                  <div className="border-t border-slate-800 pt-8 pb-4 flex flex-col items-center gap-3">
                    <p className="text-slate-500 text-sm text-center">
                      Finished studying this module? Test your knowledge.
                    </p>
                    <button
                      onClick={() => setShowQuiz(true)}
                      className="inline-flex items-center gap-2.5 px-8 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-indigo-900/40 transition-colors"
                    >
                      <span>📝</span> Take Module Quiz
                    </button>
                    <p className="text-slate-600 text-xs">{activeModuleDetail.quiz_questions.length} multiple-choice questions</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── Quiz Modal ───────────────────────────────────────────────── */}
      {showQuiz && activeModuleDetail && (
        <QuizCard
          moduleDetail={activeModuleDetail}
          userId={user?.id ?? ""}
          onClose={() => setShowQuiz(false)}
          onResult={async (result) => {
            if (result.is_passed) {
              setShowQuiz(false);
              setProgressionResult(result);
              setShowVictory(true);

              // Refresh lock states from backend
              if (userRef.current) {
                const updated = await api.getTracksForUser(userRef.current.id);
                setTracks(updated);
                const updatedTrack = updated.find((t) => t.id === currentTrack.id);
                if (updatedTrack) setCurrentTrack(updatedTrack);
                const ids = new Set<string>();
                updated.forEach((t) => t.modules.forEach((m) => m.concepts.forEach((c) => { if (!c.is_locked) ids.add(c.id); })));
                setUnlockedConceptIds(ids);

                // Auto-scroll to next concept after 1.8s
                if (result.next_module_id) {
                  setTimeout(async () => {
                    setShowVictory(false);
                    const detail = await api.getModule(result.next_module_id!);
                    setActiveModuleDetail(detail);
                    setProgressionResult(null);
                    if (detail.concepts.length > 0) {
                      const nextConcept = detail.concepts[0] as UserConcept;
                      await selectConcept({ ...nextConcept, is_locked: false });
                    }
                  }, 1800);
                }
              }
            }
          }}
        />
      )}

      {/* ── Victory badge overlay ─────────────────────────────────── */}
      {showVictory && progressionResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm px-4 pointer-events-none">
          <div className="bg-slate-900 border border-emerald-500/50 rounded-2xl w-full max-w-xs p-8 flex flex-col items-center gap-4 shadow-2xl shadow-emerald-900/40 text-center animate-[fadeInUp_0.35s_ease-out]">
            <div className="w-20 h-20 rounded-full bg-emerald-500/15 border-4 border-emerald-400 flex items-center justify-center text-4xl shadow-lg shadow-emerald-900/50">
              🏆
            </div>
            <div>
              <h2 className="text-white font-bold text-xl mb-1">Module Cleared!</h2>
              <p className="text-emerald-300 text-sm font-semibold">{progressionResult.score.toFixed(0)}% — Passed</p>
            </div>
            {progressionResult.next_module_id ? (
              <p className="text-slate-400 text-xs">Unlocking next module…</p>
            ) : (
              <p className="text-slate-400 text-xs">Track complete! Outstanding work.</p>
            )}
          </div>
        </div>
      )}

      {/* Manual dismiss for track-complete (no next module) */}
      {showVictory && progressionResult && !progressionResult.next_module_id && (
        <div className="fixed inset-0 z-50 flex items-end justify-center pb-10 px-4">
          <button
            onClick={() => { setShowVictory(false); setProgressionResult(null); }}
            className="pointer-events-auto py-3 px-8 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-xl transition-colors"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}
