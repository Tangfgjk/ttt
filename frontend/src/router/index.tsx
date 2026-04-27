import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/layouts/AppShell";
import { AdminPage } from "@/pages/admin";
import { AnnotatePage } from "@/pages/annotate";
import { DedupReviewPage } from "@/pages/dedup-review";
import { HomePage } from "@/pages/home";
import { ImportsPage } from "@/pages/imports";
import { LoginPage } from "@/pages/login";
import { QuestionsPage } from "@/pages/questions";
import { TrainingPage } from "@/pages/training";
import { VisualizationPage } from "@/pages/visualization";
import { WorkspacePage } from "@/pages/workspace";
import { RequireAuth, RequireRole, RoleLanding } from "@/router/guards";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/",
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <RoleLanding />,
          },
          {
            path: "workspace",
            element: <WorkspacePage />,
          },
          {
            path: "questions",
            element: <QuestionsPage />,
          },
          {
            path: "annotate",
            element: <AnnotatePage />,
          },
          {
            path: "visualization",
            element: <VisualizationPage />,
          },
          {
            element: <RequireRole allowedRoles={["admin", "reviewer"]} />,
            children: [
              {
                path: "dedup-review",
                element: <DedupReviewPage />,
              },
            ],
          },
          {
            element: <RequireRole allowedRoles={["admin"]} />,
            children: [
              {
                path: "admin/overview",
                element: <HomePage />,
              },
              {
                path: "imports",
                element: <ImportsPage />,
              },
              {
                path: "training",
                element: <TrainingPage />,
              },
              {
                path: "admin",
                element: <AdminPage />,
              },
            ],
          },
        ],
      },
    ],
  },
]);
