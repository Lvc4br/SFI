import { useState, type FormEvent } from "react";
import { calculatorApi } from "./api";
import type { CompoundInterestResult, LoanCalculatorResult } from "./api";

type Mode = "compound" | "loan" | "real" | "equivalent";
const money = (value:string) => new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(value));
const rate = (value:string) => Number(value).toLocaleString("pt-BR",{maximumFractionDigits:6}) + "%";

export default function CalculatorsPage() {
  const [mode,setMode]=useState<Mode>("compound");
  const [principal,setPrincipal]=useState("10000.00");
  const [contribution,setContribution]=useState("0.00");
  const [annualRate,setAnnualRate]=useState("10");
  const [months,setMonths]=useState("12");
  const [installments,setInstallments]=useState("12");
  const [firstDueDate,setFirstDueDate]=useState(new Date().toISOString().slice(0,10));
  const [method,setMethod]=useState<"price"|"sac">("price");
  const [inflation,setInflation]=useState("4.5");
  const [frequency,setFrequency]=useState("12");
  const [compoundResult,setCompoundResult]=useState<CompoundInterestResult|null>(null);
  const [loanResult,setLoanResult]=useState<LoanCalculatorResult|null>(null);
  const [simpleResult,setSimpleResult]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");

  async function submit(event:FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setCompoundResult(null); setLoanResult(null); setSimpleResult("");
    try {
      if(mode==="compound") setCompoundResult(await calculatorApi.compoundInterest({principal,monthly_contribution:contribution,annual_rate_percent:annualRate,months:Number(months)}));
      if(mode==="loan") setLoanResult(await calculatorApi.loanSchedule({principal,annual_rate_percent:annualRate,installments:Number(installments),first_due_date:firstDueDate,method}));
      if(mode==="real") { const result=await calculatorApi.realReturn({nominal_return_percent:annualRate,inflation_percent:inflation}); setSimpleResult(result.real_return_percent); }
      if(mode==="equivalent") { const result=await calculatorApi.equivalentRate({annual_nominal_rate_percent:annualRate,compounds_per_year:Number(frequency)}); setSimpleResult(result.effective_annual_rate_percent); }
    } catch (reason) { setError(reason instanceof Error?reason.message:"Não foi possível calcular."); }
    finally { setBusy(false); }
  }

  return <section className="content-grid">
    <section className="panel">
      <div className="panel-heading"><div><h3>Simulações financeiras</h3><p className="muted">Cálculos determinísticos com Decimal. Nenhuma simulação altera suas contas ou movimentações.</p></div></div>
      <div className="transaction-tools" role="group" aria-label="Tipo de calculadora">
        <button className={mode==="compound"?"button primary":"button secondary"} type="button" onClick={()=>setMode("compound")}>Juros compostos</button>
        <button className={mode==="loan"?"button primary":"button secondary"} type="button" onClick={()=>setMode("loan")}>Price / SAC</button>
        <button className={mode==="real"?"button primary":"button secondary"} type="button" onClick={()=>setMode("real")}>Rentabilidade real</button>
        <button className={mode==="equivalent"?"button primary":"button secondary"} type="button" onClick={()=>setMode("equivalent")}>Taxas equivalentes</button>
      </div>
      <form className="form-stack" onSubmit={submit}>
        {(mode==="compound"||mode==="loan")&&<label className="field">Capital inicial (R$)<input inputMode="decimal" value={principal} onChange={e=>setPrincipal(e.target.value)} required/></label>}
        {mode==="compound"&&<label className="field">Aporte mensal (R$)<input inputMode="decimal" value={contribution} onChange={e=>setContribution(e.target.value)} required/></label>}
        <label className="field">Taxa anual nominal (%)<input inputMode="decimal" value={annualRate} onChange={e=>setAnnualRate(e.target.value)} required/></label>
        {mode==="compound"&&<label className="field">Prazo (meses)<input type="number" min="1" max="1200" value={months} onChange={e=>setMonths(e.target.value)} required/></label>}
        {mode==="loan"&&<>
          <label className="field">Quantidade de parcelas<input type="number" min="1" max="600" value={installments} onChange={e=>setInstallments(e.target.value)} required/></label>
          <label className="field">Primeiro vencimento<input type="date" value={firstDueDate} onChange={e=>setFirstDueDate(e.target.value)} required/></label>
          <label className="field">Sistema de amortização<select value={method} onChange={e=>setMethod(e.target.value as "price"|"sac")}><option value="price">Price — prestação constante</option><option value="sac">SAC — amortização constante</option></select></label>
        </>}
        {mode==="real"&&<label className="field">Inflação acumulada no período (%)<input inputMode="decimal" value={inflation} onChange={e=>setInflation(e.target.value)} required/></label>}
        {mode==="equivalent"&&<label className="field">Capitalizações por ano<input type="number" min="1" max="365" value={frequency} onChange={e=>setFrequency(e.target.value)} required/></label>}
        <button className="button primary" type="submit" disabled={busy}>{busy?"Calculando...":"Calcular"}</button>
      </form>
      {error&&<div className="alert error" role="alert">{error}</div>}
    </section>
    {(compoundResult||loanResult||simpleResult)&&<section className="panel" aria-live="polite">
      <div className="panel-heading"><div><h3>Resultado da simulação</h3><p className="muted">Valores estimados; confira as premissas antes de tomar decisões.</p></div></div>
      {compoundResult&&<div className="metric-grid"><article className="metric-card"><span>Valor futuro</span><strong>{money(compoundResult.future_value)}</strong></article><article className="metric-card"><span>Total investido</span><strong>{money(compoundResult.invested_amount)}</strong></article><article className="metric-card"><span>Juros estimados</span><strong>{money(compoundResult.interest_earned)}</strong></article></div>}
      {loanResult&&<>
        <div className="metric-grid"><article className="metric-card"><span>Total de juros</span><strong>{money(loanResult.interest_total)}</strong></article><article className="metric-card"><span>Total das parcelas</span><strong>{money(loanResult.payment_total)}</strong></article><article className="metric-card"><span>Taxa mensal</span><strong>{rate(loanResult.monthly_rate_percent)}</strong></article></div>
        <div className="table-wrap"><table><thead><tr><th>Parcela</th><th>Vencimento</th><th>Amortização</th><th>Juros</th><th>Prestação</th><th>Saldo</th></tr></thead><tbody>{loanResult.installments.map(item=><tr key={item.number}><td>{item.number}</td><td>{new Date(item.due_date+"T12:00:00").toLocaleDateString("pt-BR")}</td><td>{money(item.amortization)}</td><td>{money(item.interest)}</td><td>{money(item.payment)}</td><td>{money(item.closing_balance)}</td></tr>)}</tbody></table></div>
      </>}
      {simpleResult&&<article className="metric-card"><span>{mode==="real"?"Rentabilidade real":"Taxa efetiva anual"}</span><strong>{rate(simpleResult)}</strong></article>}
      <ul className="form-hint">{(compoundResult?.assumptions??loanResult?.assumptions??["Resultado calculado com a fórmula exibida na documentação."]).map(item=><li key={item}>{item}</li>)}</ul>
    </section>}
  </section>;
}
