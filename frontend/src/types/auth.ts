import type { UserRole } from "@/app/store/auth-store";

export type LoginRequest = {
  username: string;
  password: string;
};

export type RegisterRequest = {
  username: string;
  password: string;
  confirm_password: string;
};

export type ForgotPasswordRequest = {
  username: string;
};

export type AuthUser = {
  id: number;
  username: string;
  email?: string | null;
  role: UserRole;
  real_name?: string | null;
  is_verified: boolean;
  training_scope: "none" | "junior" | "senior" | "both";
  must_change_password?: boolean;
};

export type LoginResponse = {
  message: string;
  user: AuthUser;
};

export type RegisterResponse = LoginResponse;

export type ForgotPasswordResponse = {
  message: string;
};
