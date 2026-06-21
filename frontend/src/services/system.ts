import { apiClient } from "@/services/api-client";


export type SystemCapabilities = {
  ml_runtime_available: boolean;
  missing_packages: string[];
  message: string;
};


export async function getSystemCapabilities() {
  const response = await apiClient.get<SystemCapabilities>("/system/capabilities");
  return response.data;
}
