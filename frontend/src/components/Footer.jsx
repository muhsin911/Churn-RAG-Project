import { Sparkles } from "lucide-react";

export default function Footer() {
  return (
    <footer className="page-shell flex flex-col items-center justify-between gap-2 border-t border-slate-200 py-5 text-xs text-muted sm:flex-row">
      <span>ChurnIQ · Customer churn intelligence</span>
      <span className="inline-flex items-center gap-1.5">
        <Sparkles size={13} className="text-brand" />
        Research prototype using the Telco churn dataset
      </span>
    </footer>
  );
}