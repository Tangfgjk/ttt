import type { UserRole } from "@/app/store/auth-store";

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  message: string;
  user: {
    id: number;
    username: string;
    email: string;
    role: UserRole;
    real_name?: string | null;
    is_verified: boolean;
  };
};
