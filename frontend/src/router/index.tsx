import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/layouts/AppShell";
import { AdminPage } from "@/pages/admin";
import { AnnotatePage } from "@/pages/annotate";
import { AnnotationHistoryPage } from "@/pages/annotation-history";
import { AnnotatorTrainingPage } from "@/pages/annotator-training";
import { DedupReviewPage } from "@/pages/dedup-review";
import { ForgotPasswordPage } from "@/pages/forgot-password";
import { HomePage } from "@/pages/home";
import { ImportContentHashMatchesPage } from "@/pages/import-content-hash-matches";
import { ImportsPage } from "@/pages/imports";
import { LabelInsightsPage } from "@/pages/label-insights";
import { LoginPage } from "@/pages/login";
import { QuestionsPage } from "@/pages/questions";
import { RegisterPage } from "@/pages/register";
import { ReviewPage } from "@/pages/review";
import { ReviewHistoryPage } from "@/pages/review-history";
import { TrainingPage } from "@/pages/training";
import { VisualizationPage } from "@/pages/visualization";
import { WorkspacePage } from "@/pages/workspace";
import { PublicOnly, RequireAuth, RequireRole, RequireTraining, RoleLanding } from "@/router/guards";

export const router = createBrowserRouter([
  {
    element: <PublicOnly />,
    children: [
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/register",
        element: <RegisterPage />,
      },
      {
        path: "/forgot-password",
        element: <ForgotPasswordPage />,
      },
    ],
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
            element: <RequireRole allowedRoles={["admin"]} />,
            children: [
              {
                path: "questions",
                element: <QuestionsPage />,
              },
              {
                path: "visualization",
                element: <VisualizationPage />,
              },
              {
                path: "label-insights",
                element: <LabelInsightsPage />,
              },
            ],
          },
          {
            element: <RequireRole allowedRoles={["annotator"]} />,
            children: [
              {
                path: "annotator-training",
                element: <AnnotatorTrainingPage />,
              },
              {
                element: <RequireTraining />,
                children: [
                  {
                    path: "annotation-history",
                    element: <AnnotationHistoryPage />,
                  },
                ],
              },
            ],
          },
          {
            element: <RequireRole allowedRoles={["annotator"]} />,
            children: [
              {
                element: <RequireTraining />,
                children: [
                  {
                    path: "annotate",
                    element: <AnnotatePage />,
                  },
                ],
              },
            ],
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
            element: <RequireRole allowedRoles={["reviewer"]} />,
            children: [
              {
                path: "review",
                element: <ReviewPage />,
              },
              {
                path: "review-history",
                element: <ReviewHistoryPage />,
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
                path: "imports/batches/:batchId/content-hash-matches",
                element: <ImportContentHashMatchesPage />,
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
