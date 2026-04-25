import { apiClient } from "@/services/api-client";
import type { LoginRequest, LoginResponse } from "@/types/auth";

export async function login(payload: LoginRequest) {
  const response = await apiClient.post<LoginResponse>("/auth/login", payload);
  return response.data;
}
