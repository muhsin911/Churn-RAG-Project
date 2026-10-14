import { ArrowUpRight, Database, ShieldCheck, Sparkles } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import Footer from "../components/Footer.jsx";
import Header from "../components/Header.jsx";

const sections = [
  { to: "/predict", label: "Predict risk", number: "01" },
  { to: "/customers", label: "Customers", number: "02" },
  { to: "/assistant", label: "Explore data", number: "03" },
];

export default function Dashboard() {
  const { pathname } = useLocation();
  const isAssistant = pathname.startsWith("/assistant");
  const isCustomers = pathname.startsWith("/customers");

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="page-shell flex-1 py-9 sm:py-12">
        <section className="mb-8 grid gap-6 rounded-[28px] bg-ink px-6 py-7 text-white shadow-card sm:grid-cols-[1fr_auto] sm:items-center sm:px-9 sm:py-9">
          <div>
            <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold text-indigo-100">
              <Sparkles size={14} />
              Intelligent customer insights
            </p>
            <h1 className="max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
              Understand churn.
              <span className="text-indigo-300"> Act with confidence.</span>
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">
              Predict customer risk with machine learning, then ask questions
              about the real Telco customer dataset.
            </p>
          </div>
          <div className="hidden gap-3 sm:flex">
            <div className="hero-stat">
              <Database size={18} className="text-indigo-300" />
              <span className="text-lg font-bold">30,000+</span>
              <span className="text-xs text-slate-300">PostgreSQL records</span>
            </div>
            <div className="hero-stat">
              <ShieldCheck size={18} className="text-emerald-300" />
              <span className="text-lg font-bold">ML + RAG</span>
              <span className="text-xs text-slate-300">two insight tools</span>
            </div>
          </div>
        </section>

        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand">
              Workspace
            </p>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-ink">
              {isAssistant
                ? "Ask your customer data"
                : isCustomers
                  ? "Customer database"
                  : "Churn risk predictor"}
            </h2>
          </div>
          <nav className="flex gap-2" aria-label="Dashboard sections">
            {sections.map(({ to, label, number }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `section-tab ${isActive ? "section-tab-active" : ""}`
                }
              >
                <span className="mr-2 text-[10px] opacity-60">{number}</span>
                {label}
                <ArrowUpRight size={14} className="ml-1" />
              </NavLink>
            ))}
          </nav>
        </div>

        <Outlet />
      </main>
      <Footer />
    </div>
  );
}