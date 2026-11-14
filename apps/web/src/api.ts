const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const ACCESS_KEY = "sfi.access";
const REFRESH_KEY = "sfi.refresh";

export type User = { id: string; email: string; is_active: boolean; created_at: string };
export type Session = { access_token: string; refresh_token: string | null; expires_in: number; user: User };
export type Account = { id: string; name: string; account_type: "checking" | "savings" | "cash" | "credit"; currency: string; opening_balance: string; archived_at: string | null; created_at: string };
export type Category = { id: string; name: string; category_type: "income" | "expense"; archived_at: string | null; created_at: string };
export type TransactionPage = { items: Transaction[]; total: number; limit: number; offset: number; has_more: boolean };
export type Transaction = { id: string; account_id: string; category_id: string | null; transaction_type: "income" | "expense"; amount: string; currency: string; description: string; occurred_at: string; created_at: string };
export type Budget = { id: string; category_id: string; category_name: string; period: string; currency: string; limit_amount: string; spent_amount: string; remaining_amount: string; usage_percent: string; status: "within_limit" | "reached_limit" | "over_limit"; created_at: string };
export type Summary = { start_date: string; end_date: string; totals_by_currency: { currency: string; income_total: string; expense_total: string; net_flow: string }[]; account_balances: { account_id: string; name: string; account_type: string; currency: string; opening_balance: string; income_total: string; expense_total: string; balance: string; balance_kind: "available_balance" | "credit_used" }[]; spending_by_category: { category_id: string; category_name: string; currency: string; amount: string }[] };

function readToken(key: string) { return sessionStorage.getItem(key); }
function readCookie(name: string) {
  const entry = document.cookie.split("; ").find(value => value.startsWith(name + "="));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : null;
}
function saveSession(session: Session) {
  sessionStorage.setItem(ACCESS_KEY, session.access_token);
  if (session.refresh_token) sessionStorage.setItem(REFRESH_KEY, session.refresh_token);
  else sessionStorage.removeItem(REFRESH_KEY);
}
export function clearSession() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}
export function hasSession() { return Boolean(readToken(ACCESS_KEY)); }

async function request<T>(path: string, options: RequestInit = {}, authenticated = true, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-SFI-Client", "web");
  if (path === "/api/v1/auth/refresh" || path === "/api/v1/auth/logout") {
    const csrfToken = readCookie("sfi_csrf");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = authenticated ? readToken(ACCESS_KEY) : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(API_URL + path, { ...options, headers, credentials: "include" });
  } catch {
    throw new Error("Não foi possível conectar à API. Verifique se o backend está em execução.");
  }
  if (response.status === 401 && authenticated && retry) {
    try {
      const renewed = await request<Session>("/api/v1/auth/refresh", { method: "POST" }, false, false);
      saveSession(renewed);
      return request<T>(path, options, true, false);
    } catch {
      clearSession();
    }
  }
  if (!response.ok) {
    let message = `Erro HTTP ${response.status}`;
    try {
      const payload = await response.json();
      const detail = payload.detail;
      message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg).join("; ") : message;
    } catch { /* response without JSON body */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: async (email: string, password: string) => {
    const session = await request<Session>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }, false);
    saveSession(session); return session;
  },
  login: async (email: string, password: string) => {
    const session = await request<Session>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);
    saveSession(session); return session;
  },
  me: () => request<User>("/api/v1/auth/me"),
  logout: async () => {
    try { await request<void>("/api/v1/auth/logout", { method: "POST" }); }
    finally { clearSession(); }
  },
  accounts: (includeArchived = false) => request<Account[]>(`/api/v1/finance/accounts${includeArchived ? "?include_archived=true" : ""}`),
  createAccount: (data: { name: string; account_type: Account["account_type"]; currency: string; opening_balance: string }) =>
    request<Account>("/api/v1/finance/accounts", { method: "POST", body: JSON.stringify(data) }),
  updateAccount: (id: string, name: string) =>
    request<Account>(`/api/v1/finance/accounts/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  archiveAccount: (id: string) =>
    request<Account>(`/api/v1/finance/accounts/${id}/archive`, { method: "POST" }),
  categories: (type?: Category["category_type"], includeArchived = false) => {
    const query = new URLSearchParams();
    if (type) query.set("category_type", type);
    if (includeArchived) query.set("include_archived", "true");
    return request<Category[]>(`/api/v1/finance/categories${query.size ? `?${query.toString()}` : ""}`);
  },
  createCategory: (data: { name: string; category_type: Category["category_type"] }) =>
    request<Category>("/api/v1/finance/categories", { method: "POST", body: JSON.stringify(data) }),
  updateCategory: (id: string, name: string) =>
    request<Category>(`/api/v1/finance/categories/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  archiveCategory: (id: string) =>
    request<Category>(`/api/v1/finance/categories/${id}/archive`, { method: "POST" }),
  transactions: (limit = 100) => request<Transaction[]>(`/api/v1/finance/transactions?limit=${limit}&offset=0`),
  transactionPage: (params: { limit?: number; offset?: number; account_id?: string; category_id?: string; transaction_type?: "income" | "expense"; start_at?: string; end_at?: string; min_amount?: string; max_amount?: string } = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== "") query.set(key, String(value));
    return request<TransactionPage>(`/api/v1/finance/transactions/page?${query.toString()}`);
  },
  createTransaction: (data: { account_id: string; category_id: string | null; transaction_type: "income" | "expense"; amount: string; description: string; occurred_at: string; idempotency_key: string }) =>
    request<Transaction>("/api/v1/finance/transactions", { method: "POST", body: JSON.stringify(data) }),
  reverseTransaction: (id: string) => request<unknown>(`/api/v1/finance/transactions/${id}/reverse?idempotency_key=${crypto.randomUUID()}`, { method: "POST" }),
  transfer: (data: { source_account_id: string; destination_account_id: string; amount: string; description: string; occurred_at: string; idempotency_key: string }) =>
    request<unknown>("/api/v1/finance/transfers", { method: "POST", body: JSON.stringify(data) }),
  budgets: (period: string) => request<Budget[]>(`/api/v1/finance/budgets?period=${period}`),
  createBudget: (data: { category_id: string; period: string; currency: string; limit_amount: string }) =>
    request<Budget>("/api/v1/finance/budgets", { method: "POST", body: JSON.stringify(data) }),
  summary: (start: string, end: string) => request<Summary>(`/api/v1/finance/summary?start_date=${start}&end_date=${end}`),
};
