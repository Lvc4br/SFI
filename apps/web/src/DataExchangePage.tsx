import {useState} from "react";
import type {ChangeEvent,FormEvent} from "react";
import {api,type Account,type Category,type ExchangePreview} from "./api";

type ImportFormat="csv"|"json"|"ofx";
export default function DataExchangePage({accounts,categories}:{accounts:Account[];categories:Category[]}){
 const [format,setFormat]=useState<ImportFormat>("csv"),[content,setContent]=useState(""),[filename,setFilename]=useState("");
 const [accountId,setAccountId]=useState(accounts[0]?.id??""),[categoryId,setCategoryId]=useState("");
 const [preview,setPreview]=useState<ExchangePreview|null>(null),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [busy,setBusy]=useState(false);
 async function chooseFile(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  setError("");setNotice("");setPreview(null);
  const extension=file.name.toLowerCase().split(".").pop();
  if(extension!=="csv"&&extension!=="json"&&extension!=="ofx"){setError("Formato não suportado nesta etapa. Use CSV, JSON ou OFX.");return;}
  try{setContent(await file.text());setFilename(file.name);setFormat(extension);setNotice("Arquivo carregado. Gere a prévia antes de confirmar.");}
  catch{setError("Não foi possível ler o arquivo selecionado.");}
 }
 async function makePreview(event?:FormEvent){
  event?.preventDefault();setBusy(true);setError("");setNotice("");
  try{const result=await api.exchangePreview({format,content,default_account_id:accountId||null,default_category_id:categoryId||null});setPreview(result);setNotice("Prévia calculada. Nenhum dado foi gravado.");}
  catch(e){setError(e instanceof Error?e.message:"Falha ao analisar o arquivo.");}
  finally{setBusy(false);}
 }
 async function confirmImport(){
  if(!preview||preview.invalid>0||preview.valid===0)return;
  setBusy(true);setError("");setNotice("");
  try{
   const result=await api.exchangeImport({format,content,default_account_id:accountId||null,default_category_id:categoryId||null,confirmed:true});
   setNotice(`Importação concluída: ${result.created} registros criados; ${result.duplicates_skipped} duplicados ignorados.`);
   await makePreview();
  }catch(e){setError(e instanceof Error?e.message:"Falha ao importar movimentações.");}
  finally{setBusy(false);}
 }
 async function download(formatOut:"csv"|"json"){
  setBusy(true);setError("");
  try{const blob=await api.exportTransactions(formatOut);const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`sfi-transactions.${formatOut}`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);setNotice(`Exportação ${formatOut.toUpperCase()} gerada.`);}
  catch(e){setError(e instanceof Error?e.message:"Falha ao exportar movimentações.");}
  finally{setBusy(false);}
 }
 const validRows=preview?.rows.filter(row=>row.status==="valid")??[];
 return <div className="content-grid exchange-page">
  <section className="panel"><h3>Importar movimentações</h3><p className="muted">Carregue um extrato, confira a prévia e só então confirme. O sistema não altera nem apaga lançamentos existentes.</p>
   {error&&<p className="form-error" role="alert">{error}</p>}{notice&&<p className="form-hint" role="status">{notice}</p>}
   <form className="form-stack" onSubmit={makePreview}>
    <label>Arquivo de extrato<input type="file" accept=".csv,.json,.ofx,text/csv,application/json" onChange={chooseFile}/></label>
    {filename&&<small className="muted">Arquivo: {filename} · Formato: {format.toUpperCase()}</small>}
    <label>Conta padrão (quando o arquivo não informar a conta)<select value={accountId} onChange={e=>setAccountId(e.target.value)}><option value="">Exigir conta por linha</option>{accounts.map(a=><option key={a.id} value={a.id}>{a.name} · {a.currency}</option>)}</select></label>
    <label>Categoria padrão (opcional)<select value={categoryId} onChange={e=>setCategoryId(e.target.value)}><option value="">Sem categoria padrão</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name} · {c.category_type==="expense"?"Despesa":"Receita"}</option>)}</select></label>
    <button className="button primary" disabled={busy||!content.trim()}>Analisar e gerar prévia</button>
   </form>
  </section>
  <section className="panel"><h3>Exportar movimentações</h3><p className="muted">Exporte os lançamentos do usuário autenticado, mantendo valores monetários e moedas originais.</p><div className="button-row"><button className="button secondary" type="button" disabled={busy} onClick={()=>void download("csv")}>Exportar CSV</button><button className="button secondary" type="button" disabled={busy} onClick={()=>void download("json")}>Exportar JSON</button></div></section>
  {preview&&<section className="panel"><h3>Prévia da importação</h3><div className="metric-grid"><article className="metric-card"><span className="eyebrow">LINHAS</span><strong>{preview.total}</strong></article><article className="metric-card"><span className="eyebrow">PRONTAS</span><strong>{preview.valid}</strong></article><article className="metric-card"><span className="eyebrow">DUPLICADAS</span><strong>{preview.duplicates}</strong></article><article className="metric-card"><span className="eyebrow">INVÁLIDAS</span><strong>{preview.invalid}</strong></article></div>
   <div className="table-wrap"><table><thead><tr><th>Linha</th><th>Status</th><th>Descrição</th><th>Valor</th><th>Detalhe</th></tr></thead><tbody>{preview.rows.map(row=><tr key={row.line}><td>{row.line}</td><td>{row.status==="valid"?"Pronta":row.status==="duplicate"?"Duplicada":"Inválida"}</td><td>{row.description||"—"}</td><td>{row.amount||"—"} {row.currency}</td><td>{row.error||"—"}</td></tr>)}</tbody></table></div>
   <button className="button primary" type="button" disabled={busy||preview.invalid>0||preview.valid===0} onClick={()=>void confirmImport()}>Confirmar importação de {validRows.length} movimentações</button>
   {preview.invalid>0&&<p className="muted">Corrija todas as linhas inválidas no arquivo e gere uma nova prévia. A importação é atômica.</p>}
  </section>}
  <section className="panel"><h3>Regras de segurança</h3><ul className="muted"><li>Prévia não grava dados.</li><li>Confirmação é obrigatória; arquivos com linhas inválidas são rejeitados por inteiro.</li><li>Contas e categorias precisam pertencer à sua conta SFI.</li><li>Duplicatas são detectadas por chave determinística e ignoradas em reimportações.</li><li>Limite de 5 MB e 10.000 movimentações por arquivo.</li></ul></section>
 </div>;
}
