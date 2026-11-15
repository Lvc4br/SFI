const DEFAULT_API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
declare global {
  interface Window { __SFI_API_BASE_URL__?: string }
}

const DESKTOP = typeof window !== "undefined" && (
  window.location.protocol === "tauri:"
  || window.location.hostname === "tauri.localhost"
  || "__TAURI_INTERNALS__" in window
);
let accessToken: string | null = null;
let desktopRefreshToken: string | null = null;

export const isDesktopApp = DESKTOP;

export async function waitForApiReady(timeoutMs = 15000): Promise<void> {
  if (!DESKTOP) return;
  const deadline = Date.now() + timeoutMs;
  while (!window.__SFI_API_BASE_URL__) {
    if (Date.now() >= deadline) {
      throw new Error("O mecanismo financeiro local não respondeu. Feche e abra o SFI novamente.");
    }
    await new Promise(resolve => window.setTimeout(resolve, 50));
  }
}
export function getApiBaseUrl(): string {
  if (DESKTOP) return window.__SFI_API_BASE_URL__ ?? DEFAULT_API_URL;
  if (typeof localStorage === "undefined") return DEFAULT_API_URL;
  return (localStorage.getItem("sfi.api-url") || DEFAULT_API_URL).replace(/\/$/, "");
}
let refreshInFlight: Promise<Session> | null = null;

export type User = { id: string; email: string; is_active: boolean; timezone: string; created_at: string };
export type SecurityEvent = { id: string; event_type: string; created_at: string };
export type ShoppingList = { id: string; name: string; is_favorite: boolean; is_template: boolean; archived_at: string | null; created_at: string; updated_at: string };
export type ShoppingItem = { id: string; list_id: string; product_id: string | null; name: string; quantity: string; unit: string; unit_price: string | null; is_checked: boolean; position: number; notes: string | null; created_at: string };
export type ShoppingProduct = { id: string; name: string; brand: string | null; category: string | null; barcode: string | null; unit: string; archived_at: string | null; created_at: string; updated_at: string };
export type ProductPrice = { id: string; product_id: string; price: string; currency: string; merchant: string | null; source: string; notes: string | null; observed_at: string; created_at: string };
export type ShoppingListDetail = ShoppingList & { items: ShoppingItem[] };
export type Session = { access_token: string; refresh_token: string | null; expires_in: number; user: User };
export type Account = { id: string; name: string; account_type: "checking" | "savings" | "cash" | "credit"; currency: string; opening_balance: string; archived_at: string | null; created_at: string };
export type Category = { id: string; name: string; category_type: "income" | "expense"; archived_at: string | null; created_at: string };
export type TransactionPage = { items: Transaction[]; total: number; limit: number; offset: number; has_more: boolean };
export type Transaction = { id: string; account_id: string; category_id: string | null; transaction_type: "income" | "expense"; amount: string; currency: string; description: string; occurred_at: string; created_at: string };
export type Budget = { id: string; category_id: string; category_name: string; period: string; currency: string; limit_amount: string; spent_amount: string; remaining_amount: string; usage_percent: string; status: "within_limit" | "reached_limit" | "over_limit"; created_at: string };
export type Summary = { start_date: string; end_date: string; totals_by_currency: { currency: string; income_total: string; expense_total: string; net_flow: string }[]; account_balances: { account_id: string; name: string; account_type: string; currency: string; opening_balance: string; income_total: string; expense_total: string; balance: string; balance_kind: "available_balance" | "credit_used" }[]; spending_by_category: { category_id: string; category_name: string; currency: string; amount: string }[] };

function readToken() { return accessToken; }
function readCookie(name: string) {
  const entry = document.cookie.split("; ").find(value => value.startsWith(name + "="));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : null;
}
function saveSession(session: Session) {
  accessToken = session.access_token;
  if (DESKTOP) desktopRefreshToken = session.refresh_token;
}
export function clearSession() {
  accessToken = null;
  desktopRefreshToken = null;
}

async function renewSession(): Promise<Session> {
  if (!refreshInFlight) {
    const rotate = () => DESKTOP
      ? request<Session>("/api/v1/auth/refresh", {
          method: "POST",
          body: JSON.stringify({ refresh_token: desktopRefreshToken }),
        }, false, false)
      : request<Session>("/api/v1/auth/refresh", { method: "POST" }, false, false);
    const coordinated: Promise<Session> = !DESKTOP && typeof navigator !== "undefined" && navigator.locks
      ? navigator.locks.request("sfi-auth-refresh", async () => rotate()).then(session => session)
      : rotate();
    refreshInFlight = coordinated
      .then(session => { saveSession(session); return session; })
      .finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

async function request<T>(path: string, options: RequestInit = {}, authenticated = true, retry = true): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-SFI-Client", DESKTOP ? "desktop" : "web");
  if (!DESKTOP && (path === "/api/v1/auth/refresh" || path === "/api/v1/auth/logout")) {
    const csrfToken = readCookie("sfi_csrf");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = authenticated ? readToken() : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(getApiBaseUrl() + path, { ...options, headers, credentials: "include" });
  } catch {
    throw new Error("Não foi possível conectar à API. Verifique se o backend está em execução.");
  }
  if (response.status === 401 && authenticated && retry) {
    try {
      await renewSession();
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
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Sao_Paulo";
    const session = await request<Session>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password, timezone }) }, false);
    saveSession(session); return session;
  },
  login: async (email: string, password: string) => {
    const session = await request<Session>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);
    saveSession(session); return session;
  },
  me: () => request<User>("/api/v1/auth/me"),
  updateTimezone: (timezone: string) =>
    request<User>("/api/v1/auth/me/timezone", { method: "PATCH", body: JSON.stringify({ timezone }) }),
  securityEvents: () => request<SecurityEvent[]>("/api/v1/auth/security-events"),
  logout: async () => {
    try {
      const body = DESKTOP && desktopRefreshToken
        ? JSON.stringify({ refresh_token: desktopRefreshToken })
        : undefined;
      await request<void>("/api/v1/auth/logout", { method: "POST", body });
    } finally { clearSession(); }
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
  transactionPage: (params: { limit?: number; offset?: number; account_id?: string; category_id?: string; transaction_type?: "income" | "expense"; start_at?: string; end_at?: string; start_date?: string; end_date?: string; min_amount?: string; max_amount?: string } = {}) => {
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
  shoppingLists: (favoritesOnly = false, templatesOnly = false) => { const query = new URLSearchParams(); if (favoritesOnly) query.set("favorites_only", "true"); if (templatesOnly) query.set("templates_only", "true"); return request<ShoppingList[]>(`/api/v1/shopping/lists${query.size ? "?" + query.toString() : ""}`); },
  shoppingList: (id: string) => request<ShoppingListDetail>(`/api/v1/shopping/lists/${id}`),
  createShoppingList: (name: string, is_favorite = false, is_template = false) => request<ShoppingList>("/api/v1/shopping/lists", { method: "POST", body: JSON.stringify({ name, is_favorite, is_template }) }),
  createShoppingListFromTemplate: (templateId: string) => request<ShoppingListDetail>(`/api/v1/shopping/lists/from-template/${templateId}`, { method: "POST" }),
  shoppingProducts: (search = "") => request<ShoppingProduct[]>(`/api/v1/shopping/products${search.trim() ? "?search=" + encodeURIComponent(search.trim()) : ""}`),
  createShoppingProduct: (data: { name: string; brand?: string | null; category?: string | null; barcode?: string | null; unit: string }) => request<ShoppingProduct>("/api/v1/shopping/products", { method: "POST", body: JSON.stringify(data) }),
  productPrices: (productId: string, currency = "BRL") => request<ProductPrice[]>(`/api/v1/shopping/products/${productId}/prices?currency=${encodeURIComponent(currency)}`),
  createProductPrice: (productId: string, data: { price: string; currency?: string; merchant?: string | null; source?: "manual" | "receipt" | "import"; notes?: string | null; observed_at: string }) => request<ProductPrice>(`/api/v1/shopping/products/${productId}/prices`, { method: "POST", body: JSON.stringify(data) }),
  updateShoppingList: (id: string, data: { name?: string; is_favorite?: boolean; is_template?: boolean }) => request<ShoppingList>(`/api/v1/shopping/lists/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  archiveShoppingList: (id: string) => request<ShoppingList>(`/api/v1/shopping/lists/${id}/archive`, { method: "POST" }),
  createShoppingItem: (listId: string, data: { name: string; product_id?: string | null; quantity: string; unit: string; unit_price?: string | null; notes?: string | null; position: number }) => request<ShoppingItem>(`/api/v1/shopping/lists/${listId}/items`, { method: "POST", body: JSON.stringify(data) }),
  updateShoppingItem: (listId: string, itemId: string, data: Partial<Pick<ShoppingItem, "name" | "product_id" | "quantity" | "unit" | "unit_price" | "is_checked" | "notes" | "position">>) => request<ShoppingItem>(`/api/v1/shopping/lists/${listId}/items/${itemId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteShoppingItem: (listId: string, itemId: string) => request<void>(`/api/v1/shopping/lists/${listId}/items/${itemId}`, { method: "DELETE" }),
};
