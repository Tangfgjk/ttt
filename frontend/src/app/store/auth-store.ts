import { create } from "zustand";
import { persist } from "zustand/middleware";

export type UserRole = "admin" | "annotator" | "reviewer";

export type UserSession = {
  id: number;
  username: string;
  email: string;
  name: string;
  role: UserRole;
  isVerified: boolean;
};

type AuthState = {
  session: UserSession | null;
  setSession: (session: UserSession) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      session: null,
      setSession: (session) => set({ session }),
      logout: () => set({ session: null }),
    }),
    {
      name: "ttt-auth-session",
    },
  ),
);
