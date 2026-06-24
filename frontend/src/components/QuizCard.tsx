"use client";

import { useState, useRef } from "react";
import { api, ModuleDetail, QuizResult } from "@/lib/api";

interface QuizCardProps {
  moduleDetail: ModuleDetail;
  userId: string;
  onClose: () => void;
  onResult?: (result: QuizResult) => void;
}

export default function QuizCard({ moduleDetail, userId, onClose, onResult }: QuizCardProps) {
  const startedAt = useRef<string>(new Date().toISOString());
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allAnswered = moduleDetail.quiz_questions.every((q) => selections[q.id]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.submitQuiz({
        user_id: userId,
        module_id: moduleDetail.id,
        started_at: startedAt.current,
        selected_options: selections,
      });
      setResult(res);
      onResult?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  const optionLabel: Record<string, string> = { A: "A", B: "B", C: "C", D: "D" };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-7 py-5 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-white font-semibold text-lg">Module Assessment</h2>
            <p className="text-slate-400 text-sm mt-0.5">{moduleDetail.title}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-white text-xl transition-colors leading-none"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-7 py-6">
          {result ? (
            /* ── Result screen ── */
            <div className="flex flex-col items-center py-8 gap-5">
              <div
                className={`w-24 h-24 rounded-full flex items-center justify-center text-3xl font-bold border-4 ${
                  result.is_passed
                    ? "border-emerald-500 text-emerald-400 bg-emerald-500/10"
                    : "border-rose-500 text-rose-400 bg-rose-500/10"
                }`}
              >
                {result.score.toFixed(0)}%
              </div>

              <div className="text-center">
                <span
                  className={`inline-block px-4 py-1.5 rounded-full text-sm font-semibold ${
                    result.is_passed
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                  }`}
                >
                  {result.is_passed ? "✓ PASSED" : "✗ NOT PASSED"}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4 w-full mt-2">
                {[
                  { label: "Score", value: `${result.score.toFixed(1)}%` },
                  { label: "Correct", value: `${result.correct} / ${result.total}` },
                  { label: "Attempt #", value: result.attempt_number },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-4 text-center"
                  >
                    <div className="text-slate-400 text-xs mb-1">{stat.label}</div>
                    <div className="text-white font-bold text-lg">{stat.value}</div>
                  </div>
                ))}
              </div>

              <button
                onClick={onClose}
                className="mt-4 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          ) : (
            /* ── Questions ── */
            <div className="space-y-7">
              {moduleDetail.quiz_questions.map((q, idx) => (
                <div key={q.id}>
                  <p className="text-slate-200 text-sm font-medium mb-3 leading-relaxed">
                    <span className="text-indigo-400 font-bold mr-2">Q{idx + 1}.</span>
                    {q.question_text}
                  </p>
                  <div className="space-y-2">
                    {Object.entries(q.options).map(([key, text]) => (
                      <label
                        key={key}
                        className={`flex items-start gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-colors ${
                          selections[q.id] === key
                            ? "bg-indigo-500/15 border-indigo-500/60 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500"
                        }`}
                      >
                        <input
                          type="radio"
                          name={q.id}
                          value={key}
                          checked={selections[q.id] === key}
                          onChange={() =>
                            setSelections((prev) => ({ ...prev, [q.id]: key }))
                          }
                          className="mt-0.5 accent-indigo-500 flex-shrink-0"
                        />
                        <span className="text-sm">
                          <span className="font-semibold mr-2">{optionLabel[key]}.</span>
                          {text}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {!result && (
          <div className="px-7 py-5 border-t border-slate-800 flex items-center justify-between flex-shrink-0">
            {error && <p className="text-rose-400 text-sm">{error}</p>}
            {!error && (
              <p className="text-slate-500 text-sm">
                {Object.keys(selections).length} / {moduleDetail.quiz_questions.length} answered
              </p>
            )}
            <button
              onClick={handleSubmit}
              disabled={!allAnswered || submitting}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {submitting ? "Submitting…" : "Submit Answers"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
