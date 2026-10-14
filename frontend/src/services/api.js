import axios from "axios";

const RAG_REQUEST_TIMEOUT_MS = 180_000;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 60_000,
  headers: {
    "Content-Type": "application/json",
  },
});

function getApiErrorMessage(error) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).filter(Boolean).join(", ");
    }
    if (error.code === "ECONNABORTED") {
      return "The request took too long. Please try again.";
    }
    if (!error.response) {
      return "Cannot reach the API. Check that the backend is running.";
    }
  }
  return "An unexpected error occurred. Please try again.";
}

export async function predictChurn(customer) {
  try {
    const { data } = await api.post("/predict", customer);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function askCustomerData(question) {
  try {
    const { data } = await api.post(
      "/chat",
      { question },
      { timeout: RAG_REQUEST_TIMEOUT_MS },
    );
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function getDatasetSummary() {
  try {
    const { data } = await api.get("/analytics/summary");
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function getCustomers({ page = 1, pageSize = 25, search = "" } = {}) {
  try {
    const { data } = await api.get("/customers", {
      params: { page, page_size: pageSize, search: search || undefined },
    });
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function getCustomer(customerId) {
  try {
    const { data } = await api.get(`/customers/${encodeURIComponent(customerId)}`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function createCustomer(customer) {
  try {
    const { data } = await api.post("/customers", customer);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function updateCustomer(customerId, customer, replace = false) {
  try {
    const method = replace ? "put" : "patch";
    const { data } = await api[method](
      `/customers/${encodeURIComponent(customerId)}`,
      customer,
    );
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function deleteCustomer(customerId) {
  try {
    await api.delete(`/customers/${encodeURIComponent(customerId)}`);
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export async function predictStoredCustomer(customerId) {
  try {
    const { data } = await api.post(
      `/customers/${encodeURIComponent(customerId)}/predict`,
    );
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error), { cause: error });
  }
}

export default api;