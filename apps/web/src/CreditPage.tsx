import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import type { Account, CreditCard, CreditInvoice } from "./api";

type Props = { accounts: Account[] };
const brl = (value: string) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));
const today = () => {
  const date = new Date();
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
};

export default function CreditPage({ accounts }: Props) {
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [invoices, setInvoices] = useState<CreditInvoice[]>([]);
  const [selectedCard, setSelectedCard] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [cardName, setCardName] = useState("");
  const [accountId, setAccountId] = useState("");
  const [brand, setBrand] = useState("");
  const [lastFour, setLastFour] = useState("");
  const [closingDay, setClosingDay] = useState("10");
  const [dueDay, setDueDay] = useState("20");
  const [limit, setLimit] = useState("");
  const [purchaseDescription, setPurchaseDescription] = useState("");
  const [purchaseAmount, setPurchaseAmount] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(today());
  const [installments, setInstallments] = useState("1");
  const [paymentInvoice, setPaymentInvoice] = useState("");
  const [paymentAccount, setPaymentAccount] = useState("");
  const [paymentAmount, setPaymentAmount] = useState("");

  const creditAccounts = accounts.filter((item) => item.account_type === "credit" && !item.archived_at);
  const paymentAccounts = accounts.filter((item) => item.account_type !== "credit" && !item.archived_at);
  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [cardRows, invoiceRows] = await Promise.all([api.creditCards(), api.creditInvoices()]);
      setCards(cardRows);
      setInvoices(invoiceRows);
      setSelectedCard((current) => current && cardRows.some((card) => card.id === current) ? current : cardRows[0]?.id ?? "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Falha ao carregar cartões e faturas.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void reload(); }, [reload]);

  async function run(event: FormEvent, operation: () => Promise<unknown>, success: string) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await operation();
      setNotice(success);
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível concluir a operação.");
    } finally {
      setBusy(false);
    }
  }

  async function closeInvoice(id: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.closeCreditInvoice(id);
      setNotice("Fatura fechada.");
      await reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível fechar a fatura.");
    } finally {
      setBusy(false);
    }
  }

  const visibleInvoices = invoices.filter((invoice) => !selectedCard || invoice.card_id === selectedCard);
  return (
    <section className="content-grid credit-page">
      {notice && <div className="alert success" role="status">{notice}</div>}
      {error && <div className="alert error" role="alert">{error}</div>}
      <div className="two-column align-start">
        <section className="panel">
          <PanelTitle title="Cadastrar cartão" note="Vincule o cartão a uma conta do tipo crédito." />
          <form className="stack-form" onSubmit={(event) => void run(event, async () => {
            const card = await api.createCreditCard({
              account_id: accountId, name: cardName.trim(), brand: brand.trim() || null,
              last_four: lastFour || null, closing_day: Number(closingDay),
              due_day: Number(dueDay), credit_limit: limit,
            });
            setSelectedCard(card.id);
            setCardName("");
            setBrand("");
            setLastFour("");
            setLimit("");
          }, "Cartão cadastrado.")}>
            <label className="field">Nome<input value={cardName} onChange={(event) => setCardName(event.target.value)} required maxLength={80} /></label>
            <label className="field">Conta de crédito
              <select value={accountId} onChange={(event) => setAccountId(event.target.value)} required>
                <option value="">Selecione</option>
                {creditAccounts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            <div className="form-row">
              <label className="field">Bandeira<input value={brand} onChange={(event) => setBrand(event.target.value)} maxLength={30} placeholder="Visa, Mastercard..." /></label>
              <label className="field">Últimos 4 dígitos<input value={lastFour} onChange={(event) => setLastFour(event.target.value.replace(/\\D/g, "").slice(0, 4))} inputMode="numeric" pattern="\\d{4}" maxLength={4} /></label>
            </div>
            <div className="form-row">
              <label className="field">Dia de fechamento<input type="number" min="1" max="31" value={closingDay} onChange={(event) => setClosingDay(event.target.value)} required /></label>
              <label className="field">Dia de vencimento<input type="number" min="1" max="31" value={dueDay} onChange={(event) => setDueDay(event.target.value)} required /></label>
            </div>
            <label className="field">Limite (R$)<input type="number" min="0.01" step="0.01" value={limit} onChange={(event) => setLimit(event.target.value)} required /></label>
            <button className="button primary" disabled={busy || creditAccounts.length === 0}>Cadastrar cartão</button>
            {creditAccounts.length === 0 && <small className="muted">Cadastre primeiro uma conta do tipo crédito em Contas e categorias.</small>}
          </form>
        </section>
        <section className="panel">
          <PanelTitle title="Registrar compra" note="Parcelas são distribuídas pelos ciclos mensais." />
          <form className="stack-form" onSubmit={(event) => void run(event, () => api.createCreditPurchase({
            card_id: selectedCard, description: purchaseDescription.trim(), amount: purchaseAmount,
            purchase_date: purchaseDate, installments: Number(installments), idempotency_key: crypto.randomUUID(),
          }), "Compra registrada e parcelas distribuídas.")}>
            <label className="field">Cartão
              <select value={selectedCard} onChange={(event) => setSelectedCard(event.target.value)} required>
                <option value="">Selecione</option>
                {cards.map((card) => <option key={card.id} value={card.id}>{card.name}</option>)}
              </select>
            </label>
            <label className="field">Descrição<input value={purchaseDescription} onChange={(event) => setPurchaseDescription(event.target.value)} required maxLength={160} /></label>
            <div className="form-row">
              <label className="field">Valor total (R$)<input type="number" min="0.01" step="0.01" value={purchaseAmount} onChange={(event) => setPurchaseAmount(event.target.value)} required /></label>
              <label className="field">Parcelas<select value={installments} onChange={(event) => setInstallments(event.target.value)}>{Array.from({ length: 48 }, (_, index) => index + 1).map((count) => <option key={count} value={count}>{count}x</option>)}</select></label>
            </div>
            <label className="field">Data da compra<input type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} required /></label>
            <button className="button primary" disabled={busy || !selectedCard}>Registrar compra</button>
          </form>
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div><h3>Faturas</h3><p>Valores, vencimentos e pagamentos por ciclo.</p></div>
          <select aria-label="Filtrar cartão" value={selectedCard} onChange={(event) => setSelectedCard(event.target.value)}>
            <option value="">Todos os cartões</option>
            {cards.map((card) => <option key={card.id} value={card.id}>{card.name}</option>)}
          </select>
        </div>
        {loading ? <p className="muted">Carregando...</p> : visibleInvoices.length === 0 ? <p className="muted">Nenhuma fatura cadastrada.</p> : (
          <div className="credit-invoice-list">
            {visibleInvoices.map((invoice) => {
              const card = cards.find((item) => item.id === invoice.card_id);
              return <article className="credit-invoice" key={invoice.id}>
                <div className="credit-invoice-main"><strong>{card?.name ?? "Cartão"} · {invoice.period}</strong><small>Fecha {new Date(invoice.closing_date + "T12:00:00").toLocaleDateString("pt-BR")} · vence {new Date(invoice.due_date + "T12:00:00").toLocaleDateString("pt-BR")}</small></div>
                <div className="credit-invoice-values"><span>Total <strong>{brl(invoice.total_amount)}</strong></span><span>Pago <strong>{brl(invoice.paid_amount)}</strong></span><span>Restante <strong>{brl(invoice.remaining_amount)}</strong></span></div>
                <span className={invoice.status === "paid" ? "status" : "status over"}>{invoice.status === "paid" ? "Paga" : invoice.status === "closed" ? "Fechada" : "Aberta"}</span>
                <div className="credit-invoice-actions">
                  {invoice.status === "open" && <button className="button secondary" type="button" disabled={busy} onClick={() => void closeInvoice(invoice.id)}>Fechar</button>}
                  {Number(invoice.remaining_amount) > 0 && <button className="button secondary" type="button" onClick={() => { setPaymentInvoice(invoice.id); setPaymentAmount(invoice.remaining_amount); }}>Pagar</button>}
                </div>
              </article>;
            })}
          </div>
        )}
      </section>
      {paymentInvoice && <section className="panel">
        <PanelTitle title="Registrar pagamento" note="A saída e a baixa da conta do cartão são registradas juntas." />
        <form className="stack-form" onSubmit={(event) => void run(event, async () => {
          await api.payCreditInvoice(paymentInvoice, {
            source_account_id: paymentAccount, amount: paymentAmount, paid_at: new Date().toISOString(), idempotency_key: crypto.randomUUID(),
          });
          setPaymentInvoice("");
          setPaymentAmount("");
        }, "Pagamento registrado.")}>
          <label className="field">Conta de origem<select value={paymentAccount} onChange={(event) => setPaymentAccount(event.target.value)} required><option value="">Selecione</option>{paymentAccounts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="field">Valor pago (R$)<input type="number" min="0.01" step="0.01" value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} required /></label>
          <button className="button primary" disabled={busy || paymentAccounts.length === 0}>Confirmar pagamento</button>
          <button className="button secondary" type="button" onClick={() => setPaymentInvoice("")}>Cancelar</button>
        </form>
      </section>}
    </section>
  );
}

function PanelTitle({ title, note }: { title: string; note: string }) {
  return <div className="panel-heading"><div><h3>{title}</h3><p>{note}</p></div></div>;
}
