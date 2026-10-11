import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@fontsource-variable/literata/wght.css";
import "@fontsource-variable/figtree/wght.css";
import "./styles/app.css";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/Toast";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerPage } from "./pages/CustomerPage";
import { GreenHubPage } from "./pages/GreenHubPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { PlanningPage } from "./pages/PlanningPage";
import { GovernancePage } from "./pages/GovernancePage";
import { NotFound } from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
    mutations: { retry: false },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Navigate to="/customers" replace />} />
              <Route path="customers" element={<CustomersPage />} />
              <Route path="customers/:customerId" element={<CustomerPage />} />
              <Route path="customers/:customerId/hub" element={<GreenHubPage />} />
              <Route path="portfolio" element={<PortfolioPage />} />
              <Route path="planning" element={<PlanningPage />} />
              <Route path="governance" element={<GovernancePage />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
