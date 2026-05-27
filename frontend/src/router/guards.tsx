import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import {
  getRoleLandingPath,
  isValidSession,
  useAuthStore,
  type UserRole,
} from "@/app/store/auth-store";

function getAttemptedPath(location: ReturnType<typeof useLocation>) {
  return `${location.pathname}${location.search}${location.hash}`;
}

function shouldForceLogin(location: ReturnType<typeof useLocation>) {
  return (
    location.state !== null &&
    typeof location.state === "object" &&
    "forceLogin" in location.state &&
    location.state.forceLogin === true
  );
}

function useValidSession() {
  const session = useAuthStore((state) => state.session);
  const logout = useAuthStore((state) => state.logout);
  const valid = isValidSession(session);

  useEffect(() => {
    if (session && !valid) {
      logout();
    }
  }, [logout, session, valid]);

  if (!valid) {
    return null;
  }
  return session;
}

function ClearSessionAndLogin({ from }: { from: string }) {
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    logout();
  }, [logout]);

  return <Navigate to="/login" replace state={{ from, forceLogin: true }} />;
}

export function RequireAuth() {
  const session = useValidSession();
  const location = useLocation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: getAttemptedPath(location) }} />;
  }

  return <Outlet />;
}

export function PublicOnly() {
  const session = useValidSession();
  const logout = useAuthStore((state) => state.logout);
  const location = useLocation();
  const forceLogin = shouldForceLogin(location);

  useEffect(() => {
    if (forceLogin && session) {
      logout();
    }
  }, [forceLogin, logout, session]);

  if (forceLogin) {
    return <Outlet />;
  }

  if (!session) {
    return <Outlet />;
  }

  return <Navigate to={getRoleLandingPath(session)} replace />;
}

export function RequireRole({ allowedRoles }: { allowedRoles: UserRole[] }) {
  const session = useValidSession();
  const location = useLocation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: getAttemptedPath(location) }} />;
  }

  if (!allowedRoles.includes(session.role)) {
    return <ClearSessionAndLogin from={getAttemptedPath(location)} />;
  }

  return <Outlet />;
}

export function RequireTraining() {
  const session = useValidSession();
  const location = useLocation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: getAttemptedPath(location) }} />;
  }

  const trainingScope = session.trainingScope ?? "none";
  if (session.role === "annotator" && trainingScope === "none") {
    return (
      <Navigate
        to="/annotator-training"
        replace
        state={{ trainingRequired: true, attemptedPath: location.pathname }}
      />
    );
  }

  return <Outlet />;
}

export function RoleLanding() {
  const session = useValidSession();
  const location = useLocation();

  if (!session) {
    return <Navigate to="/login" replace state={{ from: getAttemptedPath(location) }} />;
  }

  return <Navigate to={getRoleLandingPath(session)} replace />;
}
