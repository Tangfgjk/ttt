import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuthStore, type UserRole } from "@/app/store/auth-store";

export function RequireAuth() {
  const session = useAuthStore((state) => state.session);
  const location = useLocation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

export function RequireRole({ allowedRoles }: { allowedRoles: UserRole[] }) {
  const session = useAuthStore((state) => state.session);

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(session.role)) {
    return <Navigate to={session.role === "admin" ? "/" : "/workspace"} replace />;
  }

  return <Outlet />;
}

export function RoleLanding() {
  const session = useAuthStore((state) => state.session);

  if (!session) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={session.role === "admin" ? "/admin/overview" : "/workspace"} replace />;
}
