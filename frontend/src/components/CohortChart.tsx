"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { CohortUser } from "@/lib/api";

interface Props {
  cohorts: CohortUser[];
}

const FLAG_COLORS: Record<string, string> = {
  "Project Ready": "#34d399",   // emerald-400
  "Needs Coaching": "#fbbf24",  // amber-400
  "At-Risk": "#f87171",         // rose-400
};

interface TooltipPayload {
  payload: CohortUser & { x: number; y: number };
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-xl px-4 py-3 shadow-2xl text-xs">
      <p className="text-white font-semibold mb-1">{d.user_name}</p>
      <p className="text-slate-400 mb-2">{d.user_email}</p>
      <p className="text-slate-300">
        ORI: <span className="text-white font-bold">{d.numeric_ori_percentage}%</span>
      </p>
      <p className="text-slate-300 mt-0.5">
        K=<span className="text-emerald-400">{d.scores.K.toFixed(2)}</span>
        {" · "}V=<span className="text-indigo-400">{d.scores.V.toFixed(2)}</span>
        {" · "}E=<span className="text-amber-400">{d.scores.E.toFixed(2)}</span>
      </p>
      <p className="mt-1.5">
        <span
          className="px-2 py-0.5 rounded-full text-[10px] font-medium"
          style={{ backgroundColor: FLAG_COLORS[d.cluster_flag] + "33", color: FLAG_COLORS[d.cluster_flag] }}
        >
          {d.cluster_flag}
        </span>
      </p>
    </div>
  );
}

export default function CohortChart({ cohorts }: Props) {
  const points = cohorts.map((u) => ({
    ...u,
    x: parseFloat(u.scores.E.toFixed(3)),
    y: parseFloat(u.scores.K.toFixed(3)),
  }));

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-white font-semibold text-sm">Cohort Scatter Plot</h3>
          <p className="text-slate-500 text-xs mt-0.5">K-Means cluster positions · hover for details</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {Object.entries(FLAG_COLORS).map(([label, color]) => (
            <span key={label} className="flex items-center gap-1.5 text-slate-400">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              {label}
            </span>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, 1]}
            tick={{ fill: "#64748b", fontSize: 10 }}
            label={{ value: "Engagement Score (E)", position: "insideBottom", offset: -12, fill: "#64748b", fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 1]}
            tick={{ fill: "#64748b", fontSize: 10 }}
            label={{ value: "Knowledge Score (K)", angle: -90, position: "insideLeft", offset: 12, fill: "#64748b", fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "#334155" }} />
          <Scatter data={points} isAnimationActive={false}>
            {points.map((entry, index) => (
              <Cell
                key={index}
                fill={FLAG_COLORS[entry.cluster_flag] ?? "#94a3b8"}
                fillOpacity={0.85}
                r={5}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
