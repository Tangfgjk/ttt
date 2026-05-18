import { apiClient } from "@/services/api-client";
import type {
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
} from "@/types/auth";

export async function login(payload: LoginRequest) {
  const response = await apiClient.post<LoginResponse>("/auth/login", payload);
  return response.data;
}

export async function register(payload: RegisterRequest) {
  const response = await apiClient.post<RegisterResponse>("/auth/register", payload);
  return response.data;
}

export async function forgotPassword(payload: ForgotPasswordRequest) {
  const response = await apiClient.post<ForgotPasswordResponse>("/auth/forgot-password", payload);
  return response.data;
}
