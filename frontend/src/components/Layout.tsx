import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useIsFetching, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, LayoutDashboard, Megaphone, Moon, RefreshCw, ShieldCheck, Sun, SunMoon, Users } from "lucide-react";
import { useHealth } from "../api/hooks";
import { Callout, Loading } from "./ui";

export function Logo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--canopy-raised)" />
      <path d="M9 21c0-7 5-12 14-12-1 8-5 13-12 13" fill="none" stroke="var(--sprout)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 23l7-7" stroke="var(--sprout)" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

const LINKS = [
  { to: "/customers", label: "Customers", note: "What to discuss, and why", icon: Users },
  { to: "/portfolio", label: "Portfolio", note: "Opportunities across the book", icon: LayoutDashboard },
  { to: "/planning", label: "Campaign planning", note: "Target and size campaigns", icon: Megaphone },
  { to: "/governance", label: "Governance", note: "Model quality and audit", icon: ShieldCheck },
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
    <button type="button" className="btn btn-sm" onClick={() => setTheme(next)} title={label} aria-label={`${label}. Switch theme`}>
      <Icon size={14} aria-hidden="true" /> {theme === "system" ? "Auto" : theme === "light" ? "Light" : "Dark"}
    </button>
  );
}

export function Layout() {
  const health = useHealth();
  const client = useQueryClient();
  const fetching = useIsFetching();
  const mode = health.data?.provider_mode;
  const healthy = health.data?.status === "ok" && health.data?.synthetic_demo === true;

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
      <div className="nav-rail">
      <nav className="nav" aria-label="Workspaces">
        <NavLink to="/customers" className="nav-brand">
          <Logo />
          <span>
            <strong>GreenPath</strong>
            <span>Sustainable opportunities</span>
          </span>
        </NavLink>
        <div className="nav-links">
          {LINKS.map(({ to, label, note, icon: Icon }) => (
            <NavLink key={to} to={to} className="nav-link">
              <Icon size={18} aria-hidden="true" />
              <span>{label}<small>{note}</small></span>
            </NavLink>
          ))}
        </div>
        <div className="nav-foot">
          <div className="nav-status" aria-live="polite">
            <span><i className="dot" data-down={String(!healthy)} />{healthy ? "API connected" : "API unavailable"}</span>
            {mode && <span>Data: <b>{mode === "trained" ? "Trained models" : mode === "fixture" ? "Demo personas" : mode}</b></span>}
            {health.data?.contract_version && <span>Contract {health.data.contract_version}</span>}
            {health.data?.source_version && (
              <span title={health.data.source_version} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                Source {health.data.source_version}
              </span>
            )}
          </div>
          <div className="nav-row">
            <button type="button" className="btn btn-sm" onClick={() => client.invalidateQueries()}
              title="Fetch fresh data from the API. Responses are otherwise reused for up to 15 seconds.">
              <RefreshCw size={14} className={fetching ? "spin" : undefined} aria-hidden="true" /> Refresh
            </button>
            <ThemeButton />
          </div>
        </div>
      </nav>
      </div>
      <div className="main">
        <div className="demo-strip">
          <FlaskConical size={14} aria-hidden="true" />
          <span>Synthetic demo. Shows product relevance only, not credit eligibility or approval.</span>
        </div>
        {content}
      </div>
    </div>
  );
}
