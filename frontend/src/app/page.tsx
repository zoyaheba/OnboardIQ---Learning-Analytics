"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, ManagerSummary } from "@/lib/api";
import ThemeToggle from "@/components/ThemeToggle";

type Mode = "login" | "signup";

const HINT_ACCOUNTS = [
  { label: "Learner demo", email: "learner@onboardiq.io", password: "learner123" },
  { label: "Manager demo", email: "manager@onboardiq.io", password: "manager123" },
];

export default function GatewayPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Learner");
  const [managerId, setManagerId] = useState<string>("");
  const [managers, setManagers] = useState<ManagerSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === "signup") {
      api.getManagers().then(setManagers).catch(() => setManagers([]));
    }
  }, [mode]);

  const fillDemo = (e: string, p: string) => {
    setEmail(e);
    setPassword(p);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const profile =
        mode === "login"
          ? await api.login({ email, password })
          : await api.signup({
              name,
              email,
              password,
              role,
              manager_id: role === "Learner" && managerId ? managerId : null,
            });

      localStorage.setItem("onboardiq_user", JSON.stringify(profile));

      if (profile.role === "Manager" || profile.role === "Admin") {
        router.push("/manager");
      } else {
        router.push("/learner");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center px-6">
      {/* Theme toggle — top right */}
      <div className="fixed top-4 right-4 z-50">
        <ThemeToggle />
      </div>

      {/* Brand header */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-3 mb-3">
          <div className="w-11 h-11 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-indigo-900/50">
            IQ
          </div>
          <span className="text-3xl font-bold text-white tracking-tight">OnboardIQ</span>
        </div>
        <p className="text-slate-400 text-sm max-w-xs">
          AI-Powered Workforce Readiness &amp; Learning Analytics
        </p>
      </div>

      {/* Auth card */}
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Mode toggle */}
        <div className="flex border-b border-slate-800">
          {(["login", "signup"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null); }}
              className={`flex-1 py-4 text-sm font-semibold transition-colors ${
                mode === m
                  ? "text-white border-b-2 border-indigo-500 bg-slate-900"
                  : "text-slate-500 hover:text-slate-300 bg-slate-950/40"
              }`}
            >
              {m === "login" ? "Sign In" : "Create Account"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="px-8 py-7 flex flex-col gap-4">
          {mode === "signup" && (
            <div className="flex flex-col gap-1.5">
              <label className="text-slate-400 text-xs font-medium uppercase tracking-wider">Full Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Smith"
                className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 placeholder-slate-600"
              />
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-slate-400 text-xs font-medium uppercase tracking-wider">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 placeholder-slate-600"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-slate-400 text-xs font-medium uppercase tracking-wider">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 placeholder-slate-600"
            />
          </div>

          {mode === "signup" && (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs font-medium uppercase tracking-wider">Role</label>
                <select
                  value={role}
                  onChange={(e) => { setRole(e.target.value); setManagerId(""); }}
                  className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500"
                >
                  <option value="Learner">Learner</option>
                  <option value="Manager">Manager</option>
                </select>
              </div>

              {role === "Learner" && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-slate-400 text-xs font-medium uppercase tracking-wider">
                    Reports To <span className="normal-case text-slate-600">(optional)</span>
                  </label>
                  {managers.length === 0 ? (
                    <p className="text-slate-600 text-xs px-1">Loading managers…</p>
                  ) : (
                    <select
                      value={managerId}
                      onChange={(e) => setManagerId(e.target.value)}
                      className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="">— Unassigned —</option>
                      {managers.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}
            </>
          )}

          {error && (
            <p className="text-rose-400 text-sm bg-rose-500/10 border border-rose-500/30 rounded-xl px-4 py-3">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold text-sm rounded-xl transition-colors shadow-lg shadow-indigo-900/30"
          >
            {loading ? "Please wait…" : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        {/* Demo quick-fill */}
        {mode === "login" && (
          <div className="px-8 pb-7">
            <p className="text-slate-600 text-xs text-center mb-3">— Demo accounts —</p>
            <div className="flex gap-2">
              {HINT_ACCOUNTS.map((a) => (
                <button
                  key={a.email}
                  type="button"
                  onClick={() => fillDemo(a.email, a.password)}
                  className="flex-1 text-xs py-2 px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-slate-200 rounded-lg transition-colors"
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <p className="mt-8 text-slate-600 text-xs">OnboardIQ · Capstone Research Platform · Phase 5</p>
    </main>
  );
}
