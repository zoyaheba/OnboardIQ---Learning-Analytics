const BASE_URL = "/api/v1";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  login: (payload: { email: string; password: string }) =>
    apiFetch<UserProfile>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  signup: (payload: { name: string; email: string; password: string; role: string; manager_id?: string | null }) =>
    apiFetch<UserProfile>("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  getManagers: () => apiFetch<ManagerSummary[]>("/auth/managers"),
  getTracks: () => apiFetch<Track[]>("/content"),
  getTracksForUser: (userId: string) =>
    apiFetch<UserTrack[]>(`/content/tracks/${userId}`),
  getModule: (moduleId: string) =>
    apiFetch<ModuleDetail>(`/content/modules/${moduleId}`),
  getTrackState: (userId: string) =>
    apiFetch<TrackState[]>(`/content/track-state/${userId}`),
  submitQuiz: (payload: QuizSubmitPayload) =>
    apiFetch<QuizResult>("/content/quiz/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logTelemetry: (payload: TelemetryPayload) =>
    apiFetch<{ log_id: number; status: string }>("/telemetry/log", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCohorts: async (managerId?: string) => {
    const qs = managerId ? `?manager_id=${encodeURIComponent(managerId)}` : "";
    const result = await apiFetch<CohortResponse & { error?: string }>(`/manager/cohorts${qs}`);
    if (result.error) throw new Error(result.error);
    return result as CohortResponse;
  },
};

export interface Track {
  id: string;
  name: string;
  description: string | null;
  modules: ModuleSummary[];
}

export interface ModuleSummary {
  id: string;
  track_id: string;
  title: string;
  difficulty_level: string;
  sequence_order: number;
}

export interface Concept {
  id: string;
  module_id: string;
  title: string;
  summary_text: string | null;
  youtube_video_id: string | null;
  sequence_order: number;
}

export interface QuizQuestion {
  id: string;
  module_id: string;
  question_text: string;
  options: Record<string, string>;
  correct_option: string;
}

export interface ModuleDetail extends ModuleSummary {
  concepts: Concept[];
  quiz_questions: QuizQuestion[];
}

export interface TelemetryPayload {
  user_id: string;
  concept_id: string;
  event_type: "page_opened" | "page_closed" | "video_played" | "video_paused";
  duration_seconds: number | null;
}

export interface QuizSubmitPayload {
  user_id: string;
  module_id: string;
  started_at: string;
  selected_options: Record<string, string>;
}

export interface UserConcept {
  id: string;
  module_id: string;
  title: string;
  summary_text: string | null;
  youtube_video_id: string | null;
  sequence_order: number;
  is_locked: boolean;
}

export interface UserModule {
  id: string;
  track_id: string;
  title: string;
  difficulty_level: string;
  sequence_order: number;
  is_locked: boolean;
  concepts: UserConcept[];
}

export interface UserTrack {
  id: string;
  name: string;
  description: string | null;
  dynamic_level: string;
  modules: UserModule[];
}

export interface ManagerSummary {
  id: string;
  name: string;
  email: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  manager_id: string | null;
}

export interface TrackState {
  track_id: string;
  current_module_id: string | null;
  status: "In Progress" | "Completed";
}

export interface QuizResult {
  attempt_id: string;
  score: number;
  is_passed: boolean;
  attempt_number: number;
  correct: number;
  total: number;
  next_module_id: string | null;
}

export interface TrackBreakdown {
  track: string;
  K: number;
  V: number;
  E: number;
  ori: number;
}

export interface CohortUser {
  user_name: string;
  user_email: string;
  track_name: string;
  numeric_ori_percentage: number;
  cluster_flag: "Project Ready" | "Needs Coaching" | "At-Risk";
  difficulty_label: "Beginner" | "Intermediate" | "Advanced";
  diagnostic_comment: string;
  scores: { K: number; V: number; E: number };
  track_breakdown: TrackBreakdown[];
}

export interface OuladStudent {
  student_id: string;
  K: number;
  V: number;
  E: number;
  cluster: "Project Ready" | "Needs Coaching" | "At-Risk";
}

export interface OuladCentroid {
  cluster: string;
  K: number;
  V: number;
  E: number;
  count: number;
}

export interface OuladValidation {
  silhouette_score: number;
  davies_bouldin_score: number;
  n_students: number;
  module: string;
  students: OuladStudent[];
  centroids: OuladCentroid[];
}

export interface CohortResponse {
  model_validation: {
    silhouette_score: number;
    davies_bouldin_score: number;
    n_users_clustered: number;
    oulad_validation: OuladValidation | null;
  };
  cohorts: CohortUser[];
}
