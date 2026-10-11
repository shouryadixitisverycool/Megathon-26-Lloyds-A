import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Moon, RefreshCw, Sun, SunMoon } from "lucide-react";
import { useExplanationMetrics, useHealth } from "../api/hooks";
import { aiEnabled, aiModel } from "../lib/ai";
import { Callout, Loading } from "./ui";

export function Logo({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M6 25c0-10 7-18 21-19-1 12-8 19-18 19" fill="currentColor" />
      <path d="M5 27l11-11" stroke="var(--brand)" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

const LINKS = [
  { to: "/customers", label: "Customers", note: "What to discuss, and why" },
  { to: "/portfolio", label: "Portfolio", note: "Opportunities across the book" },
  { to: "/planning", label: "Campaign planning", note: "Target and size campaigns" },
  { to: "/governance", label: "Governance", note: "Model quality and audit" },
];

type Theme = "system" | "light" | "dark";

function readTheme(): Theme {
  try {
    const value = localStorage.getItem("greenpath-theme");
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

function ThemeButton() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => {
    if (theme === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("greenpath-theme", theme); } catch { /* storage may be unavailable */ }
  }, [theme]);
  const next: Theme = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : SunMoon;
  const label = { system: "Theme: match system", light: "Theme: light", dark: "Theme: dark" }[theme];
  return (
    <button type="button" className="masthead-action" onClick={() => setTheme(next)} title={label} aria-label={`${label}. Switch theme`}>
      <Icon size={18} aria-hidden="true" /> {theme === "system" ? "Auto" : theme === "light" ? "Light" : "Dark"}
    </button>
  );
}

export function Layout() {
  const health = useHealth();
  const client = useQueryClient();
  const fetching = useIsFetching();
  const mode = health.data?.provider_mode;
  const healthy = health.data?.status === "ok" && health.data?.synthetic_demo === true;
  const metrics = useExplanationMetrics();
  const ai = aiEnabled(metrics.data);

  let content: ReactNode = <Outlet />;
  if (health.isPending) content = <div className="page"><Loading label="Connecting to the GreenPath API…" /></div>;
  else if (health.isError || !healthy) {
    content = (
      <div className="page">
        <h1 className="page-title">Can't reach GreenPath</h1>
        <p className="lede">No customer decisions or portfolio results are shown while the API is unavailable.</p>
        <div className="stack" style={{ marginTop: 24, maxWidth: 680 }}>
          <Callout kind="error" title={health.isError ? "The API isn't responding" : "This API isn't a healthy synthetic-demo service"}>
            {health.isError ? (health.error as Error).message : "The /health check didn't report a healthy synthetic demo."}
          </Callout>
          <div className="panel prose">
            <p><b>To start it</b>, run this from the repository root:</p>
            <pre className="json">make api</pre>
            <p className="small muted">
              The frontend expects the API at <code>http://127.0.0.1:8000</code>. Set <code>GREENPATH_API_URL</code> before
              <code> npm run dev</code> to point elsewhere. Trained mode can take a few minutes to warm up.
            </p>
            <div><button className="btn btn-primary" type="button" onClick={() => health.refetch()}>Try again</button></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="masthead">
        <div className="strip">
          <div className="masthead-inner">
            <nav className="strip-tabs" aria-label="Workspaces">
              {LINKS.map(({ to, label, note }) => (
                <NavLink key={to} to={to} className="strip-tab" title={note}>{label}</NavLink>
              ))}
            </nav>
            <div className="strip-status" aria-live="polite">
              <span><i className="dot" data-down={String(!healthy)} />{healthy ? "API connected" : "API unavailable"}</span>
              {mode && <span>Data: <b>{mode === "trained" ? "Trained models" : mode === "fixture" ? "Demo personas" : mode}</b></span>}
              {healthy && ai !== undefined && (
                <span title={ai ? `AI explanations use ${aiModel(metrics.data) ?? "the configured model"}` : "No AI key is set on the API, so explanations use standard wording"}>
                  Explanations: <b>{ai ? "AI on" : "Standard wording"}</b>
                </span>
              )}
              {health.data?.contract_version && <span>Contract {health.data.contract_version}</span>}
              {health.data?.source_version && (
                <span className="strip-source" title={health.data.source_version}>Source {health.data.source_version}</span>
              )}
            </div>
          </div>
        </div>
        <div className="brandbar">
          <div className="masthead-inner">
            <NavLink to="/customers" className="brand">
              <Logo />
              <span className="brand-word">GreenPath</span>
            </NavLink>
            <span className="brand-tag">Sustainable opportunities</span>
            <div className="masthead-actions">
              <button type="button" className="masthead-action" onClick={() => client.invalidateQueries()}
                title="Fetch fresh data from the API. Responses are otherwise reused for up to 15 seconds.">
                <RefreshCw size={18} className={fetching ? "spin" : undefined} aria-hidden="true" /> Refresh
              </button>
              <ThemeButton />
            </div>
          </div>
        </div>
        <div className="demo-strip">
          <div className="masthead-inner">
            <FlaskConical size={14} aria-hidden="true" />
            <span>Synthetic demo. Shows product relevance only, not credit eligibility or approval.</span>
          </div>
        </div>
      </header>
      <main className="main">{content}</main>
    </div>
  );
}
