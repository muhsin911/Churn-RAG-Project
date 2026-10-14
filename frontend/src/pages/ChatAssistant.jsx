import { useEffect, useRef, useState } from "react";
import {
  Bot,
  CornerDownLeft,
  Database,
  MessageCircle,
  Send,
  Sparkles,
} from "lucide-react";
import ChatMessage from "../components/ChatMessage.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import {
  askCustomerData,
  getDatasetSummary,
} from "../services/api.js";

const suggestions = [
  "In the original Telco dataset, how many customers churned and what was the churn rate?",
  "Which contract types had the highest observed churn rate? Include customer counts.",
  "How did churn rates compare between month-to-month, one-year, and two-year contracts?",
  "How did observed churn vary across the tenure bands?",
  "Which payment method had the highest observed churn rate?",
  "Which internet service groups had higher churn, and how many customers were in each group?",
  "How many customers stayed, and what proportion of the original dataset is that?",
  "What retention experiments could address the highest-churn segments, and what outcomes should we measure?",
  "What can this dataset tell us about churn, and what can it not prove?",
];

export default function ChatAssistant() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! Ask me about customer churn, contracts, services, or patterns in the Telco dataset.",
      sources: [],
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState("");
  const inputRef = useRef(null);

  async function refreshSummary() {
    try {
      setSummary(await getDatasetSummary());
      setSummaryError("");
    } catch (requestError) {
      setSummaryError(requestError.message);
    }
  }

  useEffect(() => {
    refreshSummary();
  }, []);

  async function submitQuestion(event) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || loading) return;

    setQuestion("");
    setError("");
    setMessages((current) => [...current, { role: "user", content: text }]);
    setLoading(true);
    try {
      const response = await askCustomerData(text);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources ?? [],
        },
      ]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <section className="panel-card">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div>
            <span className="icon-tile"><Database size={19} /></span>
            <h3 className="mt-3 text-base font-bold text-ink">Live dataset insights</h3>
            {summary ? (
              <>
                <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] font-medium text-muted">Database records</p>
                    <p className="mt-1 text-lg font-bold text-ink">{summary.total_customers.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] font-medium text-muted">Known outcomes</p>
                    <p className="mt-1 text-lg font-bold text-ink">{summary.known_actual_outcomes.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl bg-rose-50 p-3">
                    <p className="text-[11px] font-medium text-rose-700">Actually churned</p>
                    <p className="mt-1 text-lg font-bold text-rose-800">{summary.churn_count.toLocaleString()}</p>
                  </div>
                  <div className="rounded-xl bg-brand-soft p-3">
                    <p className="text-[11px] font-medium text-brand">Actual churn rate</p>
                    <p className="mt-1 text-lg font-bold text-brand-dark">{(summary.churn_rate * 100).toFixed(1)}%</p>
                    <p className="text-[10px] text-muted">of known outcomes</p>
                  </div>
                </div>
                <p className="mt-3 max-w-xl text-xs leading-5 text-muted">
                  {summary.unlabeled_customers.toLocaleString()} records have no observed outcome and are excluded from actual churn rates.
                  Segment comparisons are descriptive associations, not proof of causes.
                </p>
              </>
            ) : (
              <p className={`mt-2 text-sm ${summaryError ? "text-rose-700" : "text-muted"}`}>
                {summaryError || "Loading exact dataset statistics..."}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="panel-card mx-auto max-w-4xl overflow-hidden p-0">
      <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4 sm:px-7">
        <span className="icon-tile"><Bot size={19} /></span>
        <div>
          <h3 className="font-bold text-ink">Telco data assistant</h3>
          <p className="text-xs text-muted">Answers grounded in retrieved customer records</p>
        </div>
        <span className="ml-auto hidden items-center gap-1.5 text-xs font-semibold text-brand sm:flex">
          <span className="size-2 rounded-full bg-brand" /> RAG assistant
        </span>
      </div>

      <div className="chat-scroll flex min-h-[360px] max-h-[530px] flex-col gap-5 overflow-y-auto bg-slate-50/70 px-5 py-6 sm:px-7">
        {messages.map((message, index) => (
          <ChatMessage key={`${message.role}-${index}`} message={message} />
        ))}
        {loading && (
          <div className="flex items-center gap-3 text-sm text-muted">
            <span className="grid size-9 place-items-center rounded-xl bg-brand-soft text-brand">
              <Bot size={18} />
            </span>
            <LoadingSpinner label="Searching customer records" compact />
          </div>
        )}
        {error && (
          <p className="ml-12 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
            {error}
          </p>
        )}
      </div>

      <div className="border-t border-slate-100 px-5 py-4 sm:px-7">
        <p className="mb-3 text-xs font-semibold text-muted">Questions to explore</p>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setQuestion(suggestion);
                inputRef.current?.focus();
              }}
              className="suggestion-chip"
            >
              <Sparkles size={13} /> {suggestion}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={submitQuestion} className="border-t border-slate-100 p-4 sm:px-7 sm:py-5">
        <label htmlFor="chat-question" className="sr-only">Ask a question about the data</label>
        <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2 pl-4 shadow-sm focus-within:border-brand/50 focus-within:ring-4 focus-within:ring-brand/10">
          <MessageCircle size={18} className="shrink-0 text-muted" aria-hidden="true" />
          <input
            ref={inputRef}
            id="chat-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question about customer churn..."
            maxLength={2000}
            className="min-w-0 flex-1 border-0 bg-transparent py-2 text-sm text-ink outline-none placeholder:text-slate-400"
            disabled={loading}
          />
          <button
            type="submit"
            className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Send question"
            disabled={loading || !question.trim()}
          >
            <Send size={17} />
          </button>
        </div>
        <p className="mt-2 flex items-center justify-center gap-1 text-[11px] text-muted">
          <CornerDownLeft size={12} /> Answers are AI-generated and should be verified.
        </p>
      </form>
      </section>
    </div>
  );
}