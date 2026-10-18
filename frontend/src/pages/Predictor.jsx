import { useState } from "react";
import { Activity, ArrowRight, CheckCircle2, RotateCcw, Search } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { getCustomer, predictChurn, predictStoredCustomer } from "../services/api.js";

const featureFields = [
  { name: "tenure", label: "Customer tenure", kind: "number", initialValue: "12", min: 0, max: 120, step: 1, suffix: "months" },
  { name: "monthly_charges", label: "Monthly charges", kind: "number", initialValue: "70", min: 0.01, step: 0.01, prefix: "$", suffix: "/ mo" },
  { name: "total_charges", label: "Total charges to date", kind: "number", initialValue: "840", min: 0, step: 0.01, prefix: "$" },
  { name: "senior_citizen", label: "Senior citizen", kind: "select", initialValue: "0", options: [["", "Unknown"], ["0", "No"], ["1", "Yes"]], numeric: true },
  { name: "gender", label: "Gender", kind: "select", initialValue: "Female", options: ["Female", "Male"] },
  { name: "partner", label: "Partner", kind: "select", initialValue: "No", options: ["Yes", "No"] },
  { name: "dependents", label: "Dependents", kind: "select", initialValue: "No", options: ["Yes", "No"] },
  { name: "phone_service", label: "Phone service", kind: "select", initialValue: "Yes", options: ["Yes", "No"] },
  { name: "multiple_lines", label: "Multiple lines", kind: "select", initialValue: "No", options: ["Yes", "No", "No phone service"] },
  { name: "internet_service", label: "Internet service", kind: "select", initialValue: "Fiber optic", options: ["DSL", "Fiber optic", "No"] },
  { name: "online_security", label: "Online security", kind: "select", initialValue: "No", options: ["Yes", "No", "No internet service"] },
  { name: "online_backup", label: "Online backup", kind: "select", initialValue: "No", options: ["Yes", "No", "No internet service"] },
  { name: "device_protection", label: "Device protection", kind: "select", initialValue: "No", options: ["Yes", "No", "No internet service"] },
  { name: "tech_support", label: "Tech support", kind: "select", initialValue: "No", options: ["Yes", "No", "No internet service"] },
  { name: "streaming_tv", label: "Streaming TV", kind: "select", initialValue: "No", options: ["Yes", "No", "No internet service"] },
  { name: "streaming_movies", label: "Streaming movies", kind: "select", initialValue: "No", options: ["Yes", "No", "No internet service"] },
  { name: "contract_type", label: "Contract type", kind: "select", initialValue: "Month-to-month", options: ["Month-to-month", "One year", "Two year"] },
  { name: "paperless_billing", label: "Paperless billing", kind: "select", initialValue: "Yes", options: ["Yes", "No"] },
  { name: "payment_method", label: "Payment method", kind: "select", initialValue: "Electronic check", options: ["Electronic check", "Mailed check", "Bank transfer", "Credit card"] },
];

const initialValues = Object.fromEntries(
  featureFields.map(({ name, initialValue }) => [name, initialValue]),
);

export default function Predictor() {
  const [form, setForm] = useState(initialValues);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lookupId, setLookupId] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setSelectedCustomerId("");
  }

  async function lookupCustomer(event) {
    event.preventDefault();
    setLookupLoading(true);
    setError("");
    setResult(null);
    try {
      const customer = await getCustomer(lookupId.trim());
      setForm(Object.fromEntries(
        featureFields.map(({ name, initialValue }) => [
          name,
          customer[name] == null ? initialValue : String(customer[name]),
        ]),
      ));
      setSelectedCustomerId(customer.customer_id);
    } catch (requestError) {
      setError(requestError.message);
      setSelectedCustomerId("");
      setForm(initialValues);
    } finally {
      setLookupLoading(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const customerFeatures = Object.fromEntries(
        featureFields.map(({ name, kind, numeric }) => [
          name,
          kind === "number"
            ? Number(form[name])
            : numeric
              ? (form[name] === "" ? null : Number(form[name]))
              : form[name],
        ]),
      );
      const prediction = selectedCustomerId
        ? await predictStoredCustomer(selectedCustomerId)
        : await predictChurn(customerFeatures);
      setResult(prediction);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setForm(initialValues);
    setResult(null);
    setError("");
    setLookupId("");
    setSelectedCustomerId("");
  }

  const probabilityPercent = result
    ? Math.round(result.churn_probability * 100)
    : 0;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_0.88fr]">
      <section className="panel-card">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <span className="icon-tile"><Activity size={19} /></span>
            <h3 className="mt-4 text-lg font-bold text-ink">Customer profile</h3>
            <p className="mt-1 text-sm text-muted">
              Complete the profile fields for the churn estimate.
            </p>
          </div>
          <button type="button" className="icon-button" onClick={resetForm} aria-label="Reset form">
            <RotateCcw size={16} />
          </button>
        </div>

        <form onSubmit={lookupCustomer} className="mb-6 rounded-2xl bg-brand-soft/60 p-4">
          <label className="form-label">
            Or load an existing database customer by ID
            <span className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                className="form-input"
                value={lookupId}
                onChange={(event) => {
                  setLookupId(event.target.value);
                  setSelectedCustomerId("");
                }}
                placeholder="e.g. 7590-VHVEG or SYN-00000001"
                required
              />
              <button className="primary-button shrink-0" type="submit" disabled={lookupLoading}>
                {lookupLoading ? <LoadingSpinner label="Loading" compact /> : <><Search size={16} />Load</>}
              </button>
            </span>
          </label>
          {selectedCustomerId && (
            <p className="mt-2 text-xs font-semibold text-brand-dark">
              Loaded {selectedCustomerId}. Prediction will be saved to this customer record.
            </p>
          )}
        </form>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            {featureFields.map((field) => (
              <label className="form-label" key={field.name}>
                {field.label}
                {field.kind === "select" ? (
                  <select
                    name={field.name}
                    value={form[field.name]}
                    onChange={updateField}
                    className="form-input"
                  >
                    {field.options.map((option) => {
                      const [value, label] = Array.isArray(option)
                        ? option
                        : [option, option];
                      return <option key={value} value={value}>{label}</option>;
                    })}
                  </select>
                ) : (
                  <span className="form-suffix">
                    {field.prefix && <span>{field.prefix}</span>}
                    <input
                      required
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      type="number"
                      name={field.name}
                      value={form[field.name]}
                      onChange={updateField}
                      className="form-input"
                    />
                    {field.suffix && <span>{field.suffix}</span>}
                  </span>
                )}
              </label>
            ))}
          </div>
          <p className="text-xs leading-5 text-muted">
            Enter the customer&apos;s actual cumulative charges for the most faithful explanation.
          </p>
          <button className="primary-button w-full" disabled={loading} type="submit">
            {loading ? (
              <LoadingSpinner label="Analyzing customer" compact />
            ) : (
              <>{selectedCustomerId ? "Predict and save result" : "Predict churn risk"} <ArrowRight size={17} /></>
            )}
          </button>
        </form>
      </section>

      <section className="panel-card flex min-h-[370px] flex-col">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted">
            Prediction result
          </p>
          <h3 className="mt-2 text-lg font-bold text-ink">Risk assessment</h3>
        </div>

        {!result && !error && (
          <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
            <span className="grid size-16 place-items-center rounded-3xl bg-brand-soft text-brand">
              <Activity size={27} />
            </span>
            <p className="mt-4 font-semibold text-ink">Ready when you are</p>
            <p className="mt-1 max-w-xs text-sm leading-6 text-muted">
              Submit a customer profile to see the model&apos;s churn estimate.
            </p>
          </div>
        )}

        {error && (
          <div className="my-auto rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-800" role="alert">
            <strong className="block">Prediction unavailable</strong>
            {error}
          </div>
        )}

        {result && (
          <div className="my-auto py-8">
            <span
              className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold ${
                result.churn_prediction
                  ? "bg-rose-50 text-rose-700"
                  : "bg-emerald-50 text-emerald-700"
              }`}
            >
              <CheckCircle2 size={15} />
              {result.churn_prediction ? "Higher churn risk" : "Likely to stay"}
            </span>
            <div className="mt-7 flex items-end justify-between">
              <span className="text-sm font-semibold text-muted">Churn probability</span>
              <span className="text-4xl font-bold tracking-tight text-ink">
                {probabilityPercent}<span className="text-2xl">%</span>
              </span>
            </div>
            <div
              className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"
              role="progressbar"
              aria-label="Churn probability"
              aria-valuemin="0"
              aria-valuemax="100"
              aria-valuenow={probabilityPercent}
            >
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  result.churn_prediction ? "bg-rose-500" : "bg-emerald-500"
                }`}
                style={{ width: `${probabilityPercent}%` }}
              />
            </div>
            <p className="mt-5 text-sm leading-6 text-muted">{result.message}</p>
            <div className="mt-6 border-t border-slate-100 pt-5">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <h4 className="text-sm font-bold text-ink">Why this estimate?</h4>
                <span className="text-[11px] text-muted">
                  SHAP impact on churn probability
                </span>
              </div>
              <p className="mb-4 text-xs leading-5 text-muted">
                Baseline: {(result.baseline_probability * 100).toFixed(1)}%. Positive
                impacts push toward churn; negative impacts push away. These are
                model contributions, not causes.
              </p>
              <div className="space-y-3">
                {result.explanations.map((item) => {
                  const impactPoints = item.impact * 100;
                  const barWidth = Math.min(Math.abs(impactPoints) * 2.5, 100);
                  const pushesToChurn = impactPoints >= 0;
                  return (
                    <div key={item.feature}>
                      <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                        <span className="font-semibold text-ink">
                          {item.feature}
                          <span className="ml-1.5 font-normal text-muted">({item.value})</span>
                        </span>
                        <span className={pushesToChurn ? "font-bold text-rose-600" : "font-bold text-emerald-600"}>
                          {pushesToChurn ? "+" : ""}{impactPoints.toFixed(1)} pp
                        </span>
                      </div>
                      <div className={`h-1.5 rounded-full ${pushesToChurn ? "bg-rose-100" : "bg-emerald-100"}`}>
                        <div
                          className={`h-full rounded-full ${pushesToChurn ? "bg-rose-500" : "bg-emerald-500"}`}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <p className="mt-2 text-xs text-muted">
              This is a model estimate based on the training dataset, not a guarantee.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}