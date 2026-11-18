import {useEffect,useState} from "react";
import {api,type PatrimonyItem,type PatrimonySnapshot} from "./api";

const money=(value:string,currency:string)=>new Intl.NumberFormat("pt-BR",{style:"currency",currency}).format(Number(value));
const assetCategories:Record<string,string>={property:"Imóvel",vehicle:"Veículo",cash:"Dinheiro/conta",receivable:"A receber",investment:"Investimento",other_asset:"Outro bem"};
const liabilityCategories:Record<string,string>={loan:"Empréstimo",financing:"Financiamento",credit_card:"Cartão",tax:"Tributo",other_liability:"Outro passivo"};

export default function PatrimonyPage(){
 const [items,setItems]=useState<PatrimonyItem[]>([]),[snapshot,setSnapshot]=useState<PatrimonySnapshot|null>(null),[history,setHistory]=useState<PatrimonySnapshot[]>([]);
 const [name,setName]=useState(""),[kind,setKind]=useState<"asset"|"liability">("asset"),[category,setCategory]=useState("property"),[currency,setCurrency]=useState("BRL");
 const [itemId,setItemId]=useState(""),[amount,setAmount]=useState(""),[valuedAt,setValuedAt]=useState(new Date().toISOString().slice(0,16)),[notes,setNotes]=useState("");
 const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false);
 async function reload(){const [i,s,h]=await Promise.all([api.patrimonyItems(),api.patrimonySummary(),api.patrimonyHistory()]);setItems(i);setSnapshot(s);setHistory(h);if(!itemId&&i[0])setItemId(i[0].id);}
 useEffect(()=>{void reload().catch(e=>setError(e instanceof Error?e.message:"Falha ao carregar patrimônio."));},[]);
 async function createItem(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{const item=await api.createPatrimonyItem({name,item_kind:kind,category,currency});setName("");setItemId(item.id);await reload();setNotice("Item patrimonial cadastrado. Registre uma avaliação para incluí-lo no cálculo.");}catch(e){setError(e instanceof Error?e.message:"Falha ao cadastrar item.");}finally{setBusy(false);}}
 async function addValuation(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");try{await api.createPatrimonyValuation(itemId,{amount,notes:notes||null,idempotency_key:crypto.randomUUID(),valued_at:new Date(valuedAt).toISOString()});setAmount("");setNotes("");await reload();setNotice("Avaliação registrada.");}catch(e){setError(e instanceof Error?e.message:"Falha ao registrar avaliação.");}finally{setBusy(false);}}
 async function archive(item:PatrimonyItem){setBusy(true);try{await api.updatePatrimonyItem(item.id,{archived:!item.archived});await reload();setNotice(item.archived?"Item reativado.":"Item arquivado.");}catch(e){setError(e instanceof Error?e.message:"Falha ao atualizar item.");}finally{setBusy(false);}}
 const categories=kind==="asset"?assetCategories:liabilityCategories;
 return <div className="content-grid patrimony-page">
  {error&&<p className="form-error" role="alert">{error}</p>}{notice&&<p className="form-hint" role="status">{notice}</p>}
  <section className="panel"><h3>Patrimônio líquido</h3><p className="muted">Valores informados manualmente, separados por moeda e calculados pela avaliação mais recente de cada item.</p>
   <div className="metric-grid">{snapshot?.currencies.map(row=><article className="metric-card" key={row.currency}><span className="eyebrow">{row.currency} · PATRIMÔNIO LÍQUIDO</span><strong>{money(row.net_worth,row.currency)}</strong><small>{money(row.assets_total,row.currency)} em bens · {money(row.liabilities_total,row.currency)} em passivos</small></article>)}</div>
   {!snapshot?.currencies.length&&<p className="muted">Cadastre bens e passivos e registre suas avaliações.</p>}
  </section>
  <div className="two-column align-start">
   <section className="panel"><h3>Cadastrar bem ou passivo</h3><form className="form-stack" onSubmit={createItem}>
    <label>Tipo<select value={kind} onChange={e=>{const next=e.target.value as typeof kind;setKind(next);setCategory(next==="asset"?"property":"loan");}}><option value="asset">Bem / ativo</option><option value="liability">Passivo / dívida</option></select></label>
    <label>Nome<input value={name} onChange={e=>setName(e.target.value)} required maxLength={120}/></label>
    <label>Categoria<select value={category} onChange={e=>setCategory(e.target.value)}>{Object.entries(categories).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
    <label>Moeda<input value={currency} onChange={e=>setCurrency(e.target.value.toUpperCase())} pattern="[A-Z]{3}" maxLength={3} required/></label>
    <button className="button primary" disabled={busy||!name.trim()}>Cadastrar item</button>
   </form></section>
   <section className="panel"><h3>Registrar avaliação</h3><form className="form-stack" onSubmit={addValuation}>
    <label>Bem ou passivo<select value={itemId} onChange={e=>setItemId(e.target.value)} required><option value="">Selecione</option>{items.map(item=><option key={item.id} value={item.id}>{item.name} · {item.currency}</option>)}</select></label>
    <label>Valor atual<input type="number" min="0" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)} required/></label>
    <label>Data e hora<input type="datetime-local" value={valuedAt} onChange={e=>setValuedAt(e.target.value)} required/></label>
    <label>Observação<input value={notes} onChange={e=>setNotes(e.target.value)} maxLength={500}/></label>
    <button className="button primary" disabled={busy||!itemId}>Salvar avaliação</button>
   </form></section>
  </div>
  <section className="panel"><h3>Bens e passivos cadastrados</h3><div className="data-list">{items.map(item=><article className="data-row" key={item.id}><div><strong>{item.name}</strong><small>{item.item_kind==="asset"?"Bem":"Passivo"} · {(item.item_kind==="asset"?assetCategories:liabilityCategories)[item.category]??item.category} · {item.currency}</small></div><div className="button-row"><button className="button secondary" type="button" disabled={busy} onClick={()=>{setItemId(item.id);window.scrollTo({top:0,behavior:"smooth"});}}>Avaliar</button><button className="button secondary" type="button" disabled={busy} onClick={()=>void archive(item)}>{item.archived?"Reativar":"Arquivar"}</button></div></article>)}</div>{!items.length&&<p className="muted">Nenhum item cadastrado.</p>}</section>
  <section className="panel"><h3>Evolução patrimonial</h3><p className="muted">Cada ponto representa uma data em que houve avaliação. Não há conversão cambial.</p><div className="table-wrap"><table><thead><tr><th>Data</th><th>Moeda</th><th>Bens</th><th>Passivos</th><th>Patrimônio líquido</th></tr></thead><tbody>{history.flatMap(row=>row.currencies.map(c=><tr key={row.as_of+c.currency}><td>{new Date(row.as_of+"T12:00:00").toLocaleDateString("pt-BR")}</td><td>{c.currency}</td><td>{money(c.assets_total,c.currency)}</td><td>{money(c.liabilities_total,c.currency)}</td><td><strong>{money(c.net_worth,c.currency)}</strong></td></tr>))}</tbody></table></div>{!history.length&&<p className="muted">O histórico será exibido após as primeiras avaliações.</p>}</section>
 </div>;
}
