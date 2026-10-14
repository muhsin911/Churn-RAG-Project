import { Activity, MessageCircle, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/predict", label: "Churn predictor", icon: Activity },
  { to: "/assistant", label: "Data assistant", icon: MessageCircle },
];

export default function Header() {
  return (
    <header className="border-b border-slate-200/80 bg-white/90">
      <div className="page-shell flex min-h-[76px] items-center justify-between gap-5">
        <NavLink to="/predict" className="flex items-center gap-3" aria-label="ChurnIQ home">
          <span className="grid size-10 place-items-center rounded-2xl bg-brand text-white shadow-lg shadow-brand/20">
            <ShieldCheck size={21} strokeWidth={2.2} />
          </span>
          <span>
            <span className="block text-[15px] font-bold tracking-tight text-ink">ChurnIQ</span>
            <span className="block text-[11px] font-medium text-muted">Customer intelligence</span>
          </span>
        </NavLink>
        <nav className="flex items-center gap-1 rounded-full bg-slate-100 p-1" aria-label="Main navigation">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link-active" : ""}`
              }
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="hidden items-center gap-2 text-xs font-semibold text-emerald-700 sm:flex">
          <span className="size-2 rounded-full bg-emerald-500" />
          ML workspace
        </div>
      </div>
    </header>
  );
}