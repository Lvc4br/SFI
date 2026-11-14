const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const ACCESS_KEY = "sfi.access";
const REFRESH_KEY = "sfi.refresh";

export type User = { id: string; email: string; is_active: boolean; created_at: string };
export type Session = { access_token: string; refresh_token: string; expires_in: number; user: User };
export type Account = { id: string; name: string; account_type: "checking" | "savings" | "cash" | "credit"; currency: string; opening_balance: string; created_at: string };
export type Category = { id: string; name: string; category_type: "income" | "expense"; created_at: string };
export type Transaction = { id: string; account_id: string; category_id: string | null; transaction_type: "income" | "expense"; amount: string; currency: string; description: string; occurred_at: string; created_at: string };
export type Budget = { id: string; category_id: string; category_name: string; period: string; currency: string; limit_amount: string; spent_amount: string; remaining_amount: string; usage_percent: string; status: "within_limit" | "reached_limit" | "over_limit"; created_at: string };
export type Summary = { start_date: string; end_date: string; totals_by_currency: { currency: string; income_total: string; expense_total: string; net_flow: string }[]; account_balances: { account_id: string; name: string; account_type: string; currency: string; opening_balance: string; income_total: string; expense_total: string; balance: string; balance_kind: "available_balance" | "credit_used" }[]; spending_by_category: { category_id: string; category_name: string; currency: string; amount: string }[] };

function readToken(key: string) { return sessionStorage.getItem(key); }
function saveSession(session: Session) {
  sessionStorage.setItem(ACCESS_KEY, session.access_token);
  sessionStorage.setItem(REFRESH_KEY, session.refresh_token);
}
export function clearSession() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}
export function hasSession() { return Boolean(readToken(ACCESS_KEY) && readToken(REFRESH_KEY)); }

async function request<T>(path: string, options: RequestInit = {}, authenticated = true, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = authenticated ? readToken(ACCESS_KEY) : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(API_URL + path, { ...options, headers });
  } catch {
    throw new Error("Não foi possível conectar à API. Verifique se o backend está em execução.");
  }
  if (response.status === 401 && authenticated && retry) {
    const refreshToken = readToken(REFRESH_KEY);
    if (refreshToken) {
      try {
        const renewed = await request<Session>("/api/v1/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) }, false, false);
        saveSession(renewed);
        return request<T>(path, options, true, false);
      } catch {
        clearSession();
      }
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
    const refresh_token = readToken(REFRESH_KEY);
    try { await request<void>("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }); }
    finally { clearSession(); }
  },
  accounts: () => request<Account[]>("/api/v1/finance/accounts"),
  createAccount: (data: { name: string; account_type: Account["account_type"]; currency: string; opening_balance: string }) =>
    request<Account>("/api/v1/finance/accounts", { method: "POST", body: JSON.stringify(data) }),
  categories: (type?: Category["category_type"]) => request<Category[]>(`/api/v1/finance/categories${type ? `?category_type=${type}` : ""}`),
  createCategory: (data: { name: string; category_type: Category["category_type"] }) =>
    request<Category>("/api/v1/finance/categories", { method: "POST", body: JSON.stringify(data) }),
  transactions: (limit = 100) => request<Transaction[]>(`/api/v1/finance/transactions?limit=${limit}&offset=0`),
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
