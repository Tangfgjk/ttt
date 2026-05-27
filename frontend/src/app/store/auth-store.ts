import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type UserRole = "admin" | "annotator" | "reviewer";

const AUTH_STORAGE_VERSION = 2;
const AUTH_STORAGE_KEY = "ttt-auth-session";
const AUTH_SESSION_TTL_MS = 12 * 60 * 60 * 1000;
const VALID_ROLES: UserRole[] = ["admin", "annotator", "reviewer"];
const VALID_TRAINING_SCOPES: UserSession["trainingScope"][] = ["none", "junior", "senior", "both"];

export type UserSession = {
  id: number;
  username: string;
  email?: string | null;
  name: string;
  role: UserRole;
  isVerified: boolean;
  trainingScope: "none" | "junior" | "senior" | "both";
  mustChangePassword?: boolean;
  issuedAt: number;
  expiresAt: number;
};

type AuthState = {
  session: UserSession | null;
  setSession: (session: Omit<UserSession, "issuedAt" | "expiresAt"> | UserSession) => void;
  logout: () => void;
};

function withSessionExpiry(session: Omit<UserSession, "issuedAt" | "expiresAt"> | UserSession): UserSession {
  const issuedAt = "issuedAt" in session ? session.issuedAt : Date.now();
  return {
    ...session,
    issuedAt,
    expiresAt: Date.now() + AUTH_SESSION_TTL_MS,
  };
}

function getAuthStorage() {
  try {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // Ignore browsers that block storage access in restricted modes.
  }
  return window.sessionStorage;
}

export function isValidSession(session: UserSession | null): session is UserSession {
  if (!session) return false;
  if (!Number.isFinite(session.id) || session.id <= 0) return false;
  if (!session.username || !session.name) return false;
  if (!VALID_ROLES.includes(session.role)) return false;
  if (!VALID_TRAINING_SCOPES.includes(session.trainingScope)) return false;
  if (!Number.isFinite(session.expiresAt) || session.expiresAt <= Date.now()) return false;
  return true;
}

export function getRoleLandingPath(session: UserSession) {
  if (session.role === "admin") return "/admin/overview";
  if (session.role === "annotator" && session.trainingScope === "none") return "/annotator-training";
  return "/workspace";
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      session: null,
      setSession: (session) => set({ session: withSessionExpiry(session) }),
      logout: () => set({ session: null }),
    }),
    {
      name: AUTH_STORAGE_KEY,
      version: AUTH_STORAGE_VERSION,
      storage: createJSONStorage(getAuthStorage),
      migrate: () => ({ session: null }),
      partialize: (state) => ({
        session: isValidSession(state.session) ? state.session : null,
      }),
    },
  ),
);
