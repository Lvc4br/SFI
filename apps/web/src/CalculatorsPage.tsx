import { useState, type FormEvent } from "react";
import { calculatorApi } from "./api";
import type { CetEstimateResult, CompoundInterestResult, LatePaymentEstimateResult, LoanCalculatorResult } from "./api";

type Mode = "compound" | "loan" | "real" | "equivalent" | "cet" | "late";
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
  const [frequency,setFrequency]=useState("12");\n  const [upfrontCosts,setUpfrontCosts]=useState("0.00");\n  const [monthlyCharges,setMonthlyCharges]=useState("0.00");\n  const [installmentAmount,setInstallmentAmount]=useState("950.00");\n  const [contractDate,setContractDate]=useState(new Date().toISOString().slice(0,10));\n  const [dueDate,setDueDate]=useState(new Date().toISOString().slice(0,10));\n  const [paymentDate,setPaymentDate]=useState(new Date().toISOString().slice(0,10));\n  const [penaltyPercent,setPenaltyPercent]=useState("2");\n  const [monthlyInterest,setMonthlyInterest]=useState("1");\n  const [correctionFactor,setCorrectionFactor]=useState("1");\n  const [lateMethod,setLateMethod]=useState<"simple"|"compound">("simple");
  const [compoundResult,setCompoundResult]=useState<CompoundInterestResult|null>(null);
  const [loanResult,setLoanResult]=useState<LoanCalculatorResult|null>(null);\n  const [cetResult,setCetResult]=useState<CetEstimateResult|null>(null);\n  const [lateResult,setLateResult]=useState<LatePaymentEstimateResult|null>(null);
  const [simpleResult,setSimpleResult]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");

  async function submit(event:FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setCompoundResult(null); setLoanResult(null); setCetResult(null); setLateResult(null); setSimpleResult("");
    try {
      if(mode==="compound") setCompoundResult(await calculatorApi.compoundInterest({principal,monthly_contribution:contribution,annual_rate_percent:annualRate,months:Number(months)}));
      if(mode==="loan") setLoanResult(await calculatorApi.loanSchedule({principal,annual_rate_percent:annualRate,installments:Number(installments),first_due_date:firstDueDate,method}));
      if(mode==="cet") setCetResult(await calculatorApi.cetEstimate({gross_credit_amount:principal,upfront_costs:upfrontCosts,installment_amount:installmentAmount,monthly_charges:monthlyCharges,installments:Number(installments),contract_date:contractDate,first_due_date:firstDueDate}));
      if(mode==="late") setLateResult(await calculatorApi.latePaymentEstimate({principal,due_date:dueDate,payment_date:paymentDate,penalty_percent:penaltyPercent,monthly_interest_percent:monthlyInterest,interest_method:lateMethod,index_correction_factor:correctionFactor}));
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
        <button className={mode==="equivalent"?"button primary":"button secondary"} type="button" onClick={()=>setMode("equivalent")}>Taxas equivalentes</button>\n        <button className={mode==="cet"?"button primary":"button secondary"} type="button" onClick={()=>setMode("cet")}>CET estimado</button>\n        <button className={mode==="late"?"button primary":"button secondary"} type="button" onClick={()=>setMode("late")}>Encargos por atraso</button>
      </div>
      <form className="form-stack" onSubmit={submit}>
        {(mode==="compound"||mode==="loan"||mode==="cet"||mode==="late")&&<label className="field">{mode==="cet"?"Crédito bruto contratado (R$)":mode==="late"?"Principal em atraso (R$)":"Capital inicial (R$)"}<input inputMode="decimal" value={principal} onChange={e=>setPrincipal(e.target.value)} required/></label>}
        {mode==="compound"&&<label className="field">Aporte mensal (R$)<input inputMode="decimal" value={contribution} onChange={e=>setContribution(e.target.value)} required/></label>}
        {mode!=="cet"&&<label className="field">Taxa anual nominal (%)<input inputMode="decimal" value={annualRate} onChange={e=>setAnnualRate(e.target.value)} required/></label>}
        {mode==="compound"&&<label className="field">Prazo (meses)<input type="number" min="1" max="1200" value={months} onChange={e=>setMonths(e.target.value)} required/></label>}
        {mode==="late"&&<>
          <label className="field">Data de vencimento<input type="date" value={dueDate} onChange={e=>setDueDate(e.target.value)} required/></label>
          <label className="field">Data prevista de pagamento<input type="date" value={paymentDate} onChange={e=>setPaymentDate(e.target.value)} required/></label>
          <label className="field">Multa contratual (%)<input inputMode="decimal" value={penaltyPercent} onChange={e=>setPenaltyPercent(e.target.value)} required/></label>
          <label className="field">Juros mensais (%)<input inputMode="decimal" value={monthlyInterest} onChange={e=>setMonthlyInterest(e.target.value)} required/></label>
          <label className="field">Fator de correção monetária<input inputMode="decimal" value={correctionFactor} onChange={e=>setCorrectionFactor(e.target.value)} required/></label>
          <label className="field">Método de juros<select value={lateMethod} onChange={e=>setLateMethod(e.target.value as "simple"|"compound")}><option value="simple">Simples, proporcional a 30 dias</option><option value="compound">Compostos, proporcional a 30 dias</option></select></label>
        </>}
        {mode==="cet"&&<>
          <label className="field">Custos descontados na liberação (R$)<input inputMode="decimal" value={upfrontCosts} onChange={e=>setUpfrontCosts(e.target.value)} required/></label>
          <label className="field">Valor base de cada parcela (R$)<input inputMode="decimal" value={installmentAmount} onChange={e=>setInstallmentAmount(e.target.value)} required/></label>
          <label className="field">Encargos adicionais por mês (R$)<input inputMode="decimal" value={monthlyCharges} onChange={e=>setMonthlyCharges(e.target.value)} required/></label>
          <label className="field">Data de contratação/liberação<input type="date" value={contractDate} onChange={e=>setContractDate(e.target.value)} required/></label>
          <label className="field">Primeiro vencimento<input type="date" value={firstDueDate} onChange={e=>setFirstDueDate(e.target.value)} required/></label>
          <label className="field">Quantidade de parcelas<input type="number" min="1" max="600" value={installments} onChange={e=>setInstallments(e.target.value)} required/></label>
        </>}
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
    {(compoundResult||loanResult||cetResult||lateResult||simpleResult)&&<section className="panel" aria-live="polite">
      <div className="panel-heading"><div><h3>Resultado da simulação</h3><p className="muted">Valores estimados; confira as premissas antes de tomar decisões.</p></div></div>
      {compoundResult&&<div className="metric-grid"><article className="metric-card"><span>Valor futuro</span><strong>{money(compoundResult.future_value)}</strong></article><article className="metric-card"><span>Total investido</span><strong>{money(compoundResult.invested_amount)}</strong></article><article className="metric-card"><span>Juros estimados</span><strong>{money(compoundResult.interest_earned)}</strong></article></div>}
      {lateResult&&<>
        <div className="metric-grid">
          <article className="metric-card"><span>VALOR CORRIGIDO</span><strong>{money(lateResult.corrected_principal)}</strong></article>
          <article className="metric-card"><span>MULTA</span><strong>{money(lateResult.penalty)}</strong></article>
          <article className="metric-card"><span>JUROS</span><strong>{money(lateResult.interest)}</strong></article>
          <article className="metric-card"><span>TOTAL ESTIMADO</span><strong>{money(lateResult.total_due)}</strong></article>
        </div>
        <p className="muted">Dias em atraso: {lateResult.days_overdue}. O cálculo usa os parâmetros informados e não determina se eles são legalmente aplicáveis ao seu contrato.</p>
        <ul className="form-hint">{lateResult.assumptions.map(item=><li key={item}>{item}</li>)}</ul>
      </>}
      {cetResult&&<>
        <div className="metric-grid">
          <article className="metric-card"><span>CRÉDITO LÍQUIDO RECEBIDO</span><strong>{money(cetResult.net_disbursement)}</strong></article>
          <article className="metric-card"><span>CUSTO EFETIVO ANUAL ESTIMADO</span><strong>{rate(cetResult.effective_annual_cost_percent)}</strong></article>
          <article className="metric-card"><span>CUSTO EFETIVO MENSAL</span><strong>{rate(cetResult.effective_monthly_cost_percent)}</strong></article>
          <article className="metric-card"><span>TOTAL PAGO</span><strong>{money(cetResult.total_paid)}</strong></article>
        </div>
        <div className="table-wrap"><table><thead><tr><th>Parcela</th><th>Vencimento</th><th>Pagamento considerado</th></tr></thead><tbody>{cetResult.cash_flows.map(item=><tr key={item.number}><td>{item.number}</td><td>{new Date(item.due_date+"T12:00:00").toLocaleDateString("pt-BR")}</td><td>{money(item.payment)}</td></tr>)}</tbody></table></div>
        <ul className="form-hint">{cetResult.assumptions.map(item=><li key={item}>{item}</li>)}</ul>
      </>}
      {loanResult&&<>
        <div className="metric-grid"><article className="metric-card"><span>Total de juros</span><strong>{money(loanResult.interest_total)}</strong></article><article className="metric-card"><span>Total das parcelas</span><strong>{money(loanResult.payment_total)}</strong></article><article className="metric-card"><span>Taxa mensal</span><strong>{rate(loanResult.monthly_rate_percent)}</strong></article></div>
        <div className="table-wrap"><table><thead><tr><th>Parcela</th><th>Vencimento</th><th>Amortização</th><th>Juros</th><th>Prestação</th><th>Saldo</th></tr></thead><tbody>{loanResult.installments.map(item=><tr key={item.number}><td>{item.number}</td><td>{new Date(item.due_date+"T12:00:00").toLocaleDateString("pt-BR")}</td><td>{money(item.amortization)}</td><td>{money(item.interest)}</td><td>{money(item.payment)}</td><td>{money(item.closing_balance)}</td></tr>)}</tbody></table></div>
      </>}
      {simpleResult&&<article className="metric-card"><span>{mode==="real"?"Rentabilidade real":"Taxa efetiva anual"}</span><strong>{rate(simpleResult)}</strong></article>}
      <ul className="form-hint">{(compoundResult?.assumptions??loanResult?.assumptions??["Resultado calculado com a fórmula exibida na documentação."]).map(item=><li key={item}>{item}</li>)}</ul>
    </section>}
  </section>;
}
