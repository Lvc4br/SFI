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
export type PurchaseConfirmation = { transaction_id: string; list_id: string; amount: string; currency: string; description: string; occurred_at: string; items_count: number };
export type StockBalance = { product_id: string; product_name: string; unit: string; balance: string };
export type FiscalPreview = {access_key:string;document_number:string;series:string;issuer_name:string;issuer_tax_id:string;issue_date:string;total_amount:string;currency:string;xml_sha256:string;qr_code_status:"not_provided"|"matches";qr_code_access_key:string|null;already_imported:boolean;items:{code:string;description:string;ncm:string;cfop:string;quantity:string;unit:string;unit_price:string;total:string}[]};
export type ExchangePreview = {total:number;valid:number;duplicates:number;invalid:number;rows:{line:number;status:string;description:string;amount:string;currency:string;error?:string|null}[]};
export type ExchangeImportResult = {created:number;duplicates_skipped:number;total:number};
export type BackupDocument = {format:string;version:number;exported_at:string;profile:{timezone:string};tables:Record<string,Record<string,unknown>[]>};
export type BackupPreview = {format:string;version:number;records_in_backup:number;records_current:number;tables:{name:string;backup_records:number;current_records:number}[];restore_mode:"replace";requires_confirmation:boolean};
export type AutomaticBackupStatus = {enabled:boolean;cadence?:"daily"|"weekly";local_time?:string;last_run?:string|null;last_error?:string|null;retention:number;history:{filename:string;size_bytes:number;created_at:string}[]};
export type BankStatementEntry = {id:string;account_id:string;matched_transaction_id:string|null;external_id:string|null;transaction_type:"income"|"expense";amount:string;currency:string;description:string;occurred_at:string;status:"pending"|"matched"|"ignored";matched_at:string|null;created_at:string|null};
export type ReconciliationSuggestion = {transaction_id:string;description:string;amount:string;currency:string;occurred_at:string;date_difference_days:number;description_similarity:number;score:number};
export type ReconciliationSummary = {entries_by_currency:{currency:string;pending:number;matched:number;ignored:number}[]};
export type PatrimonyItem = {id:string;name:string;item_kind:"asset"|"liability";category:string;currency:string;description:string|null;archived:boolean;created_at:string};
export type PatrimonyCurrency = {currency:string;assets_total:string;liabilities_total:string;net_worth:string;items_count:number};
export type PatrimonySnapshot = {as_of:string;currencies:PatrimonyCurrency[]};
export type InvestmentAsset = {id:string;name:string;ticker:string|null;asset_type:"stock"|"reit"|"etf"|"bond"|"fund"|"crypto"|"fixed_income"|"other";currency:string;notes:string|null;archived:boolean;created_at:string};
export type InvestmentPosition = {asset:InvestmentAsset;quantity:string;average_cost:string;invested_amount:string;dividends:string;realized_result:string;operations_count:number};
export type Goal = { id:string; name:string; description:string|null; currency:string; target_amount:string; current_amount:string; target_date:string|null; status:"active"|"completed"|"paused"|"archived"; created_at:string; updated_at:string };
export type GoalEntry = { id:string; goal_id:string; entry_type:"contribution"|"withdrawal"; amount:string; description:string|null; occurred_at:string; created_at:string };
export type Debt = { id:string; creditor:string; debt_type:"loan"|"financing"|"personal"|"mortgage"|"vehicle"|"other"; description:string; currency:string; original_amount:string; outstanding_principal:string; annual_interest_rate:string; amortization_method:"manual"|"price"|"sac"; contracted_at:string; first_due_date:string; next_due_date:string|null; installment_count:number|null; status:"active"|"paid"|"archived"; notes:string|null; created_at:string };
export type DebtRefinancePreview = {debt_id:string;currency:string;is_estimate:boolean;current:{method:string;installments:{number:number;due_date:string;payment:string;principal:string;interest:string;closing_balance:string}[];principal_total:string;interest_total:string;payment_total:string};proposed:{method:string;installments:{number:number;due_date:string;payment:string;principal:string;interest:string;closing_balance:string}[];principal_total:string;interest_total:string;monthly_fees_total:string;payment_total:string;monthly_effective_rate_percent:string;annual_effective_rate_percent:string;financed_fees:string};estimated_savings:string;saves_money:boolean;assumptions:string[]};
export type DebtPayment = { id:string; debt_id:string; source_account_id:string; transaction_id:string; amount:string; principal_amount:string; interest_amount:string; paid_at:string; created_at:string };
export type CreditCard = { id:string; account_id:string; name:string; brand:string|null; last_four:string|null; closing_day:number; due_day:number; credit_limit:string; created_at:string };
export type CreditInvoice = { id:string; card_id:string; period:string; closing_date:string; due_date:string; status:"open"|"closed"|"paid"; total_amount:string; paid_amount:string; remaining_amount:string };
export type StockMovement = { id: string; product_id: string; movement_type: "purchase" | "adjustment_in" | "adjustment_out" | "consumption" | "waste"; quantity: string; unit: string; reference: string | null; notes: string | null; occurred_at: string; created_at: string };
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

async function requestBlob(path: string, authenticated = true, retry = true): Promise<Blob> {
  const headers = new Headers();
  headers.set("X-SFI-Client", DESKTOP ? "desktop" : "web");
  const token = authenticated ? readToken() : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(getApiBaseUrl() + path, { headers, credentials: "include" });
  } catch {
    throw new Error("Não foi possível conectar à API. Verifique se o backend está em execução.");
  }
  if (response.status === 401 && authenticated && retry) {
    try { await renewSession(); return requestBlob(path, true, false); }
    catch { clearSession(); }
  }
  if (!response.ok) {
    let message = `Erro HTTP ${response.status}`;
    try { const payload = await response.json(); if (typeof payload.detail === "string") message = payload.detail; } catch { /* empty body */ }
    throw new Error(message);
  }
  return response.blob();
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
  goals: (includeArchived = false) => request<Goal[]>(`/api/v1/goals${includeArchived ? "?include_archived=true" : ""}`),
  createGoal: (data:{name:string;description?:string|null;currency?:string;target_amount:string;target_date?:string|null}) => request<Goal>("/api/v1/goals",{method:"POST",body:JSON.stringify(data)}),
  updateGoal: (id:string,data:{name?:string;description?:string|null;target_amount?:string;target_date?:string|null;status?:"active"|"paused"|"archived"}) => request<Goal>(`/api/v1/goals/${id}`,{method:"PATCH",body:JSON.stringify(data)}),
  goalEntries: (id:string) => request<GoalEntry[]>(`/api/v1/goals/${id}/entries`),
  createGoalEntry: (id:string,data:{entry_type:GoalEntry["entry_type"];amount:string;description?:string|null;occurred_at:string;idempotency_key:string}) => request<GoalEntry>(`/api/v1/goals/${id}/entries`,{method:"POST",body:JSON.stringify(data)}),
  fiscalPreview: (content:string,format:"xml"|"pdf"="xml",qr_code_payload?:string) => request<FiscalPreview>("/api/v1/fiscal/documents/preview",{method:"POST",body:JSON.stringify({content,format,qr_code_payload:qr_code_payload||null})}),
  fiscalConfirm: (data:{content:string;format?:"xml"|"pdf";qr_code_payload?:string|null;create_expense:boolean;account_id?:string|null;category_id?:string|null}) => request<{id:string;access_key:string;issuer_name:string;document_number:string;total_amount:string;transaction_id:string|null}>("/api/v1/fiscal/documents/confirm",{method:"POST",body:JSON.stringify(data)}),
  fiscalDocuments: () => request<{id:string;access_key:string;document_number:string;series:string;issuer_name:string;issuer_tax_id:string;issue_date:string;total_amount:string;currency:string;items:FiscalPreview["items"];transaction_id:string|null}[]>("/api/v1/fiscal/documents"),
  reconciliationImport: (data:{format:"csv"|"json"|"ofx";content:string;account_id:string}) => request<{created:number;duplicates_skipped:number;total:number}>("/api/v1/reconciliation/statements/import",{method:"POST",body:JSON.stringify(data)}),
  reconciliationEntries: (accountId?:string) => request<BankStatementEntry[]>(`/api/v1/reconciliation/entries?${accountId?"account_id="+encodeURIComponent(accountId):""}`),
  reconciliationSummary: () => request<ReconciliationSummary>("/api/v1/reconciliation/summary"),
  reconciliationSuggestions: (entryId:string) => request<ReconciliationSuggestion[]>(`/api/v1/reconciliation/entries/${entryId}/suggestions`),
  reconciliationMatch: (entryId:string,transactionId:string) => request<BankStatementEntry>(`/api/v1/reconciliation/entries/${entryId}/match`,{method:"POST",body:JSON.stringify({transaction_id:transactionId})}),
  reconciliationIgnore: (entryId:string) => request<BankStatementEntry>(`/api/v1/reconciliation/entries/${entryId}/ignore`,{method:"POST"}),
  reconciliationUnmatch: (entryId:string) => request<BankStatementEntry>(`/api/v1/reconciliation/entries/${entryId}/unmatch`,{method:"POST"}),
  exchangePreview: (data:{format:"csv"|"json"|"ofx"|"xlsx"|"qif"|"pdf";content:string;default_account_id?:string|null;default_category_id?:string|null}) => request<ExchangePreview>("/api/v1/exchange/transactions/preview",{method:"POST",body:JSON.stringify(data)}),
  exchangeImport: (data:{format:"csv"|"json"|"ofx"|"xlsx"|"qif"|"pdf";content:string;default_account_id?:string|null;default_category_id?:string|null;confirmed:true}) => request<ExchangeImportResult>("/api/v1/exchange/transactions/import",{method:"POST",body:JSON.stringify(data)}),
  exportTransactions: (format:"csv"|"json"|"xlsx"|"qif"|"pdf", accountId?:string) => requestBlob(`/api/v1/exchange/transactions/export?${new URLSearchParams({format,...(accountId?{account_id:accountId}:{})})}`),
  exportFullBackup: () => requestBlob("/api/v1/backup/export"),
  exportEncryptedBackup: (passphrase:string) => request<Record<string,unknown>>("/api/v1/backup/encrypted/export",{method:"POST",body:JSON.stringify({passphrase})}),
  previewEncryptedBackup: (envelope:Record<string,unknown>,passphrase:string) => request<BackupPreview>("/api/v1/backup/encrypted/preview",{method:"POST",body:JSON.stringify({envelope,passphrase})}),
  restoreEncryptedBackup: (envelope:Record<string,unknown>,passphrase:string) => request<{restored:boolean;records_restored:number;tables_restored:number;mode:string;encrypted:boolean}>("/api/v1/backup/encrypted/restore",{method:"POST",body:JSON.stringify({envelope,passphrase,confirmed:true})}),
  previewBackupRestore: (backup:BackupDocument) => request<BackupPreview>("/api/v1/backup/preview",{method:"POST",body:JSON.stringify({backup})}),
  restoreFullBackup: (backup:BackupDocument) => request<{restored:boolean;records_restored:number;tables_restored:number;mode:string}>("/api/v1/backup/restore",{method:"POST",body:JSON.stringify({backup,confirmed:true})}),
  automaticBackupStatus: () => request<AutomaticBackupStatus>("/api/v1/backup/automatic"),
  configureAutomaticBackup: (data:{cadence:"daily"|"weekly";local_time:string;passphrase:string}) => request<{enabled:boolean;cadence:string;local_time:string;retention:number}>("/api/v1/backup/automatic",{method:"PUT",body:JSON.stringify(data)}),
  disableAutomaticBackup: () => request<{enabled:boolean}>("/api/v1/backup/automatic",{method:"DELETE"}),
  downloadAutomaticBackup: (filename:string) => requestBlob("/api/v1/backup/automatic/"+encodeURIComponent(filename)),
  patrimonyItems: (includeArchived=false) => request<PatrimonyItem[]>(`/api/v1/patrimony${includeArchived?"?include_archived=true":""}`),
  createPatrimonyItem: (data:{name:string;item_kind:PatrimonyItem["item_kind"];category:string;currency?:string;description?:string|null}) => request<PatrimonyItem>("/api/v1/patrimony",{method:"POST",body:JSON.stringify(data)}),
  updatePatrimonyItem: (id:string,data:{archived:boolean}) => request<PatrimonyItem>(`/api/v1/patrimony/${id}`,{method:"PATCH",body:JSON.stringify(data)}),
  createPatrimonyValuation: (id:string,data:{amount:string;notes?:string|null;idempotency_key:string;valued_at:string}) => request<unknown>(`/api/v1/patrimony/${id}/valuations`,{method:"POST",body:JSON.stringify(data)}),
  patrimonySummary: (asOf?:string) => request<PatrimonySnapshot>(`/api/v1/patrimony/summary${asOf?"?as_of="+asOf:""}`),
  patrimonyHistory: (start?:string,end?:string) => request<PatrimonySnapshot[]>(`/api/v1/patrimony/history?${new URLSearchParams({...(start?{start_date:start}:{}),...(end?{end_date:end}:{})})}`),
  investmentAssets: () => request<InvestmentAsset[]>("/api/v1/investments/assets"),
  createInvestmentAsset: (data:{name:string;ticker?:string|null;asset_type:InvestmentAsset["asset_type"];currency?:string;notes?:string|null}) => request<InvestmentAsset>("/api/v1/investments/assets",{method:"POST",body:JSON.stringify(data)}),
  investmentPortfolio: () => request<InvestmentPosition[]>("/api/v1/investments/portfolio"),
  createInvestmentOperation: (assetId:string,data:{operation_type:"buy"|"sell"|"dividend";amount:string;quantity:string;unit_price:string;idempotency_key:string;occurred_at:string}) => request<unknown>(`/api/v1/investments/assets/${assetId}/operations`,{method:"POST",body:JSON.stringify(data)}),
  debts: () => request<Debt[]>("/api/v1/debts"),
  createDebt: (data:{creditor:string;debt_type:Debt["debt_type"];description:string;currency?:string;original_amount:string;annual_interest_rate:string;amortization_method:Debt["amortization_method"];contracted_at:string;first_due_date:string;installment_count?:number|null}) => request<Debt>("/api/v1/debts",{method:"POST",body:JSON.stringify(data)}),
  debtPayments: (id:string) => request<DebtPayment[]>(`/api/v1/debts/${id}/payments`),
  debtSchedule: (id:string) => request<{debt_id:string;method:string;currency:string;annual_rate_percent:string;monthly_rate_percent:string;installments:{number:number;due_date:string;opening_balance:string;principal:string;interest:string;payment:string;closing_balance:string}[];principal_total:string;interest_total:string;payment_total:string;is_estimate:boolean;assumptions:string[]}>(`/api/v1/debts/${id}/schedule`),
  debtRefinancePreview: (id:string,data:{new_principal:string;monthly_effective_rate_percent:string;installment_count:number;amortization_method:"price"|"sac";first_due_date:string;financed_fees:string;monthly_fees:string}) => request<DebtRefinancePreview>("/api/v1/debts/"+id+"/refinance-preview",{method:"POST",body:JSON.stringify(data)}),
  payDebt: (id:string,data:{source_account_id:string;principal_amount:string;interest_amount:string;paid_at:string;next_due_date:string|null;idempotency_key:string}) => request<DebtPayment>(`/api/v1/debts/${id}/payments`,{method:"POST",body:JSON.stringify(data)}),
  creditCards: () => request<CreditCard[]>("/api/v1/credit/cards"),
  createCreditCard: (data: { account_id:string; name:string; brand?:string|null; last_four?:string|null; closing_day:number; due_day:number; credit_limit:string }) => request<CreditCard>("/api/v1/credit/cards",{method:"POST",body:JSON.stringify(data)}),
  creditInvoices: (cardId?:string) => request<CreditInvoice[]>(`/api/v1/credit/invoices${cardId ? "?card_id="+encodeURIComponent(cardId) : ""}`),
  createCreditPurchase: (data:{card_id:string;description:string;amount:string;purchase_date:string;installments:number;idempotency_key:string}) => request<{purchase_id:string;installments_created:number;total_amount:string}>("/api/v1/credit/purchases",{method:"POST",body:JSON.stringify(data)}),
  closeCreditInvoice: (id:string) => request<CreditInvoice>(`/api/v1/credit/invoices/${id}/close`,{method:"POST"}),
  payCreditInvoice: (id:string,data:{source_account_id:string;amount:string;paid_at:string;idempotency_key:string}) => request<unknown>(`/api/v1/credit/invoices/${id}/payments`,{method:"POST",body:JSON.stringify(data)}),
  stockBalances: (includeZero = false) => request<StockBalance[]>(`/api/v1/shopping/stock${includeZero ? "?include_zero=true" : ""}`),
  createStockMovement: (productId: string, data: { movement_type: StockMovement["movement_type"]; quantity: string; notes?: string }) =>
    request<StockMovement>(`/api/v1/shopping/stock/${productId}/movements`, { method: "POST", body: JSON.stringify(data) }),
  stockMovements: (productId: string) => request<StockMovement[]>(`/api/v1/shopping/stock/${productId}/movements`),
  confirmShoppingPurchase: (listId: string, accountId: string, merchant?: string) =>
    request<PurchaseConfirmation>(`/api/v1/shopping/purchases/${listId}/confirm`, { method: "POST", body: JSON.stringify({ account_id: accountId, merchant: merchant?.trim() || null }) }),
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


export type CompoundInterestResult = {
  currency: string; future_value: string; invested_amount: string;
  interest_earned: string; monthly_rate_percent: string; months: number;
  assumptions: string[];
};
export type LoanCalculatorResult = {
  method: "price" | "sac"; currency: string; monthly_rate_percent: string;
  installments: {number:number;due_date:string;opening_balance:string;amortization:string;interest:string;payment:string;closing_balance:string}[];
  principal_total:string;interest_total:string;payment_total:string;is_estimate:boolean;assumptions:string[];
};
export type LatePaymentEstimateResult = {
  currency: string; principal: string; corrected_principal: string; days_overdue: number;
  penalty: string; interest: string; total_due: string; interest_method: "simple" | "compound";
  index_correction_factor: string; is_estimate: boolean; assumptions: string[];
};
export type CetEstimateResult = {
  currency: string; net_disbursement: string; total_paid: string; upfront_costs: string;
  monthly_charges_total: string; effective_annual_cost_percent: string;
  effective_monthly_cost_percent: string; is_estimate: boolean;
  cash_flows: { number: number; due_date: string; payment: string }[];
  assumptions: string[];
};
export const calculatorApi = {
  latePaymentEstimate: (data:{principal:string;due_date:string;payment_date:string;penalty_percent:string;monthly_interest_percent:string;interest_method:"simple"|"compound";index_correction_factor:string}) =>
    request<LatePaymentEstimateResult>("/api/v1/calculators/late-payment-estimate",{method:"POST",body:JSON.stringify(data)}),
  cetEstimate: (data:{gross_credit_amount:string;upfront_costs:string;installment_amount:string;monthly_charges:string;installments:number;contract_date:string;first_due_date:string}) =>
    request<CetEstimateResult>("/api/v1/calculators/cet-estimate",{method:"POST",body:JSON.stringify(data)}),
  compoundInterest: (data:{principal:string;monthly_contribution:string;annual_rate_percent:string;months:number}) =>
    request<CompoundInterestResult>("/api/v1/calculators/compound-interest",{method:"POST",body:JSON.stringify(data)}),
  loanSchedule: (data:{principal:string;annual_rate_percent:string;installments:number;first_due_date:string;method:"price"|"sac"}) =>
    request<LoanCalculatorResult>("/api/v1/calculators/loan-schedule",{method:"POST",body:JSON.stringify(data)}),
  realReturn: (data:{nominal_return_percent:string;inflation_percent:string}) =>
    request<{real_return_percent:string;formula:string;is_estimate:boolean}>("/api/v1/calculators/real-return",{method:"POST",body:JSON.stringify(data)}),
  equivalentRate: (data:{annual_nominal_rate_percent:string;compounds_per_year:number}) =>
    request<{periodic_rate_percent:string;effective_annual_rate_percent:string;compounds_per_year:number;is_estimate:boolean}>("/api/v1/calculators/equivalent-rate",{method:"POST",body:JSON.stringify(data)}),
};
