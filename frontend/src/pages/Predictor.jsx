import { useState } from "react";
import { Activity, ArrowRight, CheckCircle2, RotateCcw, Search } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import { getCustomer, predictChurn, predictStoredCustomer } from "../services/api.js";

const initialValues = {
  tenure: "12",
  monthly_charges: "70",
  total_charges: "",
  contract_type: "Month-to-month",
  payment_method: "Electronic check",
};

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
      setForm({
        tenure: String(customer.tenure),
        monthly_charges: String(customer.monthly_charges),
        total_charges: String(customer.total_charges),
        contract_type: customer.contract_type,
        payment_method: customer.payment_method,
      });
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
      const prediction = selectedCustomerId
        ? await predictStoredCustomer(selectedCustomerId)
        : await predictChurn({
            ...form,
            tenure: Number(form.tenure),
            monthly_charges: Number(form.monthly_charges),
            total_charges: Number(form.total_charges),
          });
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
              Enter a few details to estimate churn likelihood.
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
            <label className="form-label">
              Customer tenure
              <span className="form-suffix">
                <input
                  required
                  min="0"
                  max="120"
                  type="number"
                  name="tenure"
                  value={form.tenure}
                  onChange={updateField}
                  className="form-input"
                  placeholder="e.g. 18"
                />
                <span>months</span>
              </span>
            </label>
            <label className="form-label">
              Monthly charges
              <span className="form-suffix">
                <span>$</span>
                <input
                  required
                  min="0.01"
                  step="0.01"
                  type="number"
                  name="monthly_charges"
                  value={form.monthly_charges}
                  onChange={updateField}
                  className="form-input"
                  placeholder="e.g. 70"
                />
                <span>/ mo</span>
              </span>
            </label>
            <label className="form-label">
              Total charges to date
              <span className="form-suffix">
                <span>$</span>
                <input
                  required
                  min="0"
                  step="0.01"
                  type="number"
                  name="total_charges"
                  value={form.total_charges}
                  onChange={updateField}
                  className="form-input"
                  placeholder="e.g. 840.00"
                />
              </span>
            </label>
            <label className="form-label">
              Contract type
              <select
                name="contract_type"
                value={form.contract_type}
                onChange={updateField}
                className="form-input"
              >
                <option>Month-to-month</option>
                <option>One year</option>
                <option>Two year</option>
              </select>
            </label>
            <label className="form-label">
              Payment method
              <select
                name="payment_method"
                value={form.payment_method}
                onChange={updateField}
                className="form-input"
              >
                <option>Electronic check</option>
                <option>Mailed check</option>
                <option>Bank transfer</option>
                <option>Credit card</option>
              </select>
            </label>
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