"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("onboardiq_theme");
    if (stored === "light") {
      document.documentElement.classList.add("light");
      setLight(true);
    }
  }, []);

  const toggle = () => {
    const next = !light;
    setLight(next);
    if (next) {
      document.documentElement.classList.add("light");
      localStorage.setItem("onboardiq_theme", "light");
    } else {
      document.documentElement.classList.remove("light");
      localStorage.setItem("onboardiq_theme", "dark");
    }
  };

  return (
    <button
      onClick={toggle}
      title={light ? "Switch to dark mode" : "Switch to light mode"}
      className="flex items-center gap-1.5 text-slate-400 hover:text-white text-sm transition-colors px-3 py-1.5 border border-slate-700 rounded-lg hover:border-slate-500"
    >
      {light ? "🌙 Dark" : "☀️ Light"}
    </button>
  );
}
