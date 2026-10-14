import { useEffect, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Pencil, Plus, Search, Trash2 } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import {
  createCustomer,
  deleteCustomer,
  getCustomer,
  getCustomers,
  updateCustomer,
} from "../services/api.js";

const blankForm = {
  tenure: "12",
  monthly_charges: "70",
  total_charges: "840",
  contract_type: "Month-to-month",
  payment_method: "Electronic check",
  actual_churn: "",
};

function toPayload(form) {
  return {
    tenure: Number(form.tenure),
    monthly_charges: Number(form.monthly_charges),
    total_charges: Number(form.total_charges),
    contract_type: form.contract_type,
    payment_method: form.payment_method,
    actual_churn:
      form.actual_churn === "" ? null : form.actual_churn === "yes",
  };
}

function fromRecord(record) {
  return {
    tenure: String(record.tenure),
    monthly_charges: String(record.monthly_charges),
    total_charges: String(record.total_charges),
    contract_type: record.contract_type,
    payment_method: record.payment_method,
    actual_churn:
      record.actual_churn === null
        ? ""
        : record.actual_churn
          ? "yes"
          : "no",
  };
}

function Outcome({ value }) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-muted">Unknown</span>;
  }
  return (
    <span className={value ? "font-semibold text-rose-700" : "font-semibold text-emerald-700"}>
      {value ? "Yes" : "No"}
    </span>
  );
}

function CustomerForm({ initial = blankForm, onSave, saving, submitLabel, showId = false }) {
  const [form, setForm] = useState(initial);
  const [customerId, setCustomerId] = useState("");

  useEffect(() => {
    setForm(initial);
    setCustomerId("");
  }, [initial]);

  function change(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(toPayload(form), customerId.trim() || undefined);
      }}
    >
      {showId && (
        <label className="form-label">
          Customer ID (optional)
          <input
            value={customerId}
            onChange={(event) => setCustomerId(event.target.value)}
            className="form-input"
            maxLength={64}
            placeholder="Leave blank to generate an ID"
          />
        </label>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="form-label">
          Tenure (months)
          <input required className="form-input" type="number" min="0" max="120" name="tenure" value={form.tenure} onChange={change} />
        </label>
        <label className="form-label">
          Monthly charges
          <input required className="form-input" type="number" min="0.01" step="0.01" name="monthly_charges" value={form.monthly_charges} onChange={change} />
        </label>
        <label className="form-label">
          Total charges
          <input required className="form-input" type="number" min="0" step="0.01" name="total_charges" value={form.total_charges} onChange={change} />
        </label>
        <label className="form-label">
          Contract
          <select className="form-input" name="contract_type" value={form.contract_type} onChange={change}>
            <option>Month-to-month</option>
            <option>One year</option>
            <option>Two year</option>
          </select>
        </label>
        <label className="form-label">
          Payment method
          <select className="form-input" name="payment_method" value={form.payment_method} onChange={change}>
            <option>Electronic check</option>
            <option>Mailed check</option>
            <option>Bank transfer</option>
            <option>Credit card</option>
          </select>
        </label>
        <label className="form-label">
          Actual churn outcome
          <select className="form-input" name="actual_churn" value={form.actual_churn} onChange={change}>
            <option value="">Unknown / not observed</option>
            <option value="yes">Yes — actually churned</option>
            <option value="no">No — retained</option>
          </select>
        </label>
      </div>
      <p className="text-xs leading-5 text-muted">
        Actual churn is an observed outcome you enter. It is separate from the model&apos;s prediction.
      </p>
      <button className="primary-button" type="submit" disabled={saving}>
        {saving ? <LoadingSpinner label="Saving customer" compact /> : <><Check size={16} />{submitLabel}</>}
      </button>
    </form>
  );
}

export default function Customers() {
  const [tab, setTab] = useState("browse");
  const [page, setPage] = useState(1);
  const [pageData, setPageData] = useState(null);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [recordId, setRecordId] = useState("");
  const [record, setRecord] = useState(null);
  const [editForm, setEditForm] = useState(blankForm);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  async function refreshCustomers(nextPage = page, nextSearch = search) {
    setLoading(true);
    setError("");
    try {
      setPageData(await getCustomers({ page: nextPage, pageSize: 20, search: nextSearch }));
      setPage(nextPage);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshCustomers(1, "");
  }, []);

  function changeTab(nextTab) {
    setTab(nextTab);
    setMessage("");
    setError("");
  }

  async function addOne(payload, customerId) {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const created = await createCustomer({ ...payload, customer_id: customerId });
      setMessage(`Created customer ${created.customer_id}.`);
      await refreshCustomers(1, "");
      setTab("browse");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function findOne(event) {
    event.preventDefault();
    await loadCustomer(query.trim());
  }

  async function loadCustomer(customerId) {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const found = await getCustomer(customerId);
      setRecord(found);
      setRecordId(found.customer_id);
      setQuery(found.customer_id);
      setEditForm(fromRecord(found));
    } catch (requestError) {
      setRecord(null);
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveChanges(payload) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await updateCustomer(recordId, payload);
      setRecord(updated);
      setEditForm(fromRecord(updated));
      setMessage(`Updated customer ${updated.customer_id}.`);
      await refreshCustomers(page);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeOne(customerId) {
    if (!window.confirm(`Delete customer ${customerId}? This cannot be undone.`)) return;
    setError("");
    setMessage("");
    try {
      await deleteCustomer(customerId);
      setMessage(`Deleted customer ${customerId}.`);
      await refreshCustomers(page);
      if (recordId === customerId) setRecord(null);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const tabs = [
    ["browse", "Browse records"],
    ["add", "Add one customer"],
    ["edit", "Find / edit by ID"],
  ];

  return (
    <section className="panel-card space-y-5">
      <div>
        <span className="icon-tile"><Search size={18} /></span>
        <h3 className="mt-3 text-lg font-bold text-ink">Customer database</h3>
        <p className="mt-1 text-sm text-muted">
          PostgreSQL records. Predictions and observed churn are stored separately.
        </p>
      </div>

      <nav className="flex flex-wrap gap-2" aria-label="Customer database sections">
        {tabs.map(([id, label]) => (
          <button key={id} type="button" className={`section-tab ${tab === id ? "section-tab-active" : ""}`} onClick={() => changeTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      {message && <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">{message}</p>}
      {error && <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">{error}</p>}

      {tab === "browse" && (
        <div className="space-y-4">
          <form
            className="flex flex-col gap-3 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault();
              refreshCustomers(1, search);
            }}
          >
            <input className="form-input" aria-label="Search customer ID" placeholder="Search by customer ID" value={search} onChange={(event) => setSearch(event.target.value)} />
            <button className="primary-button shrink-0" type="submit"><Search size={16} />Search</button>
          </form>
          {loading ? (
            <LoadingSpinner label="Loading customers" />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                  <thead><tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-muted">
                    <th className="p-3">Customer ID</th><th className="p-3">Tenure</th><th className="p-3">Contract</th><th className="p-3">Predicted</th><th className="p-3">Actual</th><th className="p-3">Source</th><th className="p-3">Actions</th>
                  </tr></thead>
                  <tbody>
                    {pageData?.items.map((customer) => (
                      <tr className="border-b border-slate-100" key={customer.customer_id}>
                        <td className="p-3 font-semibold text-ink">{customer.customer_id}</td>
                        <td className="p-3">{customer.tenure} mo</td>
                        <td className="p-3">{customer.contract_type}</td>
                        <td className="p-3"><Outcome value={customer.predicted_churn} />{customer.churn_probability !== null && <span className="ml-1 text-xs text-muted">({(customer.churn_probability * 100).toFixed(1)}%)</span>}</td>
                        <td className="p-3"><Outcome value={customer.actual_churn} /></td>
                        <td className="p-3 text-xs text-muted">{customer.record_source}</td>
                        <td className="p-3">
                          <div className="flex gap-2">
                            <button type="button" className="icon-button" aria-label={`Edit ${customer.customer_id}`} onClick={() => { setQuery(customer.customer_id); setTab("edit"); loadCustomer(customer.customer_id); }}><Pencil size={15} /></button>
                            <button type="button" className="icon-button text-rose-600" aria-label={`Delete ${customer.customer_id}`} onClick={() => removeOne(customer.customer_id)}><Trash2 size={15} /></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
                <span>{pageData?.total.toLocaleString() ?? 0} records · Page {pageData?.page ?? 1} of {pageData?.total_pages ?? 0}</span>
                <div className="flex gap-2">
                  <button className="icon-button" type="button" disabled={page <= 1 || loading} onClick={() => refreshCustomers(page - 1)} aria-label="Previous page"><ChevronLeft size={17} /></button>
                  <button className="icon-button" type="button" disabled={page >= (pageData?.total_pages ?? 0) || loading} onClick={() => refreshCustomers(page + 1)} aria-label="Next page"><ChevronRight size={17} /></button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {tab === "add" && (
        <div className="max-w-3xl">
          <CustomerForm key="new-customer-form" onSave={addOne} saving={saving} submitLabel="Create customer" showId />
        </div>
      )}

      {tab === "edit" && (
        <div className="max-w-3xl space-y-5">
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={findOne}>
            <input className="form-input" aria-label="Customer ID to find" placeholder="Enter a customer ID" value={query} onChange={(event) => setQuery(event.target.value)} required />
            <button className="primary-button shrink-0" type="submit" disabled={loading}>{loading ? <LoadingSpinner label="Finding customer" compact /> : <><Search size={16} />Find</>}</button>
          </form>
          {record && (
            <>
              <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-muted">
                Editing <strong className="text-ink">{record.customer_id}</strong> · Predicted churn: <strong className="text-ink">{record.predicted_churn === null ? "not predicted yet" : record.predicted_churn ? "Yes" : "No"}</strong> · Actual churn: <strong className="text-ink">{record.actual_churn === null ? "unknown" : record.actual_churn ? "Yes" : "No"}</strong>
              </p>
              <CustomerForm key={record.customer_id} initial={editForm} onSave={saveChanges} saving={saving} submitLabel="Save changes" />
            </>
          )}
        </div>
      )}
    </section>
  );
}
