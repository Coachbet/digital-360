import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AuthPage from "@/features/auth/components/AuthPage";
import { AuthProvider, useAuth } from "@/features/auth/AuthContext";
import AdvertisingPage from "@/features/advertising/components/AdvertisingPage";
import AutoReviewPage from "@/features/auto-review/components/AutoReviewPage";
import CalendarPage from "@/features/calendar/components/CalendarPage";
import DataPage from "@/features/data/components/DataPage";
import InvoicingPage from "@/features/invoicing/components/InvoicingPage";
import OrganizationPage from "@/features/organization/components/OrganizationPage";
import HomePage from "@/pages/Home";
import AppLayout from "@/shared/components/AppLayout";
import Logo from "@/shared/components/Logo";

/** Écran d'attente le temps de savoir si une session existe déjà. */
function Booting() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Logo className="animate-pulse" />
    </div>
  );
}

function Shell() {
  const { user, loading } = useAuth();

  if (loading) return <Booting />;

  // Pas de session : tout le routage se réduit à l'écran de connexion, plutôt
  // que de protéger chaque route une par une.
  if (!user) return <AuthPage />;

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/data" element={<DataPage />} />
        <Route path="/auto-review" element={<AutoReviewPage />} />
        <Route path="/publicite" element={<AdvertisingPage />} />
        <Route path="/calendrier" element={<CalendarPage />} />
        <Route path="/facturation" element={<InvoicingPage />} />
        <Route path="/agence" element={<OrganizationPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  );
}
