import {useEffect,useState} from "react";
import type {ChangeEvent} from "react";
import {api,type Account,type Category,type FiscalPreview} from "./api";

type SavedDocument={id:string;access_key:string;document_number:string;series:string;issuer_name:string;issuer_tax_id:string;issue_date:string;total_amount:string;currency:string;items:FiscalPreview["items"];transaction_id:string|null};
const money=(value:string,currency="BRL")=>new Intl.NumberFormat("pt-BR",{style:"currency",currency}).format(Number(value));

export default function FiscalPage({accounts,categories}:{accounts:Account[];categories:Category[]}){
 const [content,setContent]=useState(""),[filename,setFilename]=useState(""),[format,setFormat]=useState<"xml"|"pdf">("xml"),[qrPayload,setQrPayload]=useState("");
 const [preview,setPreview]=useState<FiscalPreview|null>(null),[documents,setDocuments]=useState<SavedDocument[]>([]);
 const [accountId,setAccountId]=useState(accounts[0]?.id??""),[categoryId,setCategoryId]=useState("");
 const [createExpense,setCreateExpense]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
 async function reload(){try{setDocuments(await api.fiscalDocuments());}catch(e){setError(e instanceof Error?e.message:"Não foi possível carregar as notas.");}}
 useEffect(()=>{void reload();},[]);
 async function chooseFile(event:ChangeEvent<HTMLInputElement>){
  const file=event.target.files?.[0];if(!file)return;
  setPreview(null);setError("");setNotice("");
  const extension=file.name.toLowerCase().split(".").pop();
  if(extension!=="xml"&&extension!=="pdf"){setError("Selecione um XML ou PDF de NF-e/NFC-e.");return;}
  const selectedFormat=extension==="pdf"?"pdf":"xml";
  if(file.size>(selectedFormat==="pdf"?10:2)*1024*1024){setError(selectedFormat==="pdf"?"O PDF excede o limite de 10 MB.":"O XML excede o limite de 2 MB.");return;}
  try{
   if(selectedFormat==="xml")setContent(await file.text());
   else{
    const bytes=new Uint8Array(await file.arrayBuffer());
    let binary="";
    for(let offset=0;offset<bytes.length;offset+=0x8000)binary+=String.fromCharCode(...bytes.subarray(offset,offset+0x8000));
    setContent(btoa(binary));
   }
   setFormat(selectedFormat);setFilename(file.name);setNotice((selectedFormat==="pdf"?"PDF":"XML")+" carregado. Gere a prévia para conferir os dados.");
  }
  catch{setError("Não foi possível ler o arquivo.");}
 }
 async function makePreview(){setBusy(true);setError("");setNotice("");try{setPreview(await api.fiscalPreview(content,format,qrPayload));setNotice("Prévia pronta. Nenhuma nota ou despesa foi gravada.");}catch(e){setError(e instanceof Error?e.message:"Falha ao analisar o XML.");}finally{setBusy(false);}}
 async function confirm(){if(!preview)return;setBusy(true);setError("");setNotice("");try{await api.fiscalConfirm({content,format,qr_code_payload:qrPayload||null,create_expense:createExpense,account_id:createExpense?accountId:null,category_id:createExpense?(categoryId||null):null});setNotice(createExpense? "Nota importada e despesa registrada.":"Nota importada sem criar movimentação.");setPreview(null);setContent("");setFilename("");setQrPayload("");await reload();}catch(e){setError(e instanceof Error?e.message:"Falha ao importar a nota.");}finally{setBusy(false);}}
 return <div className="content-grid">
  <section className="panel">
   <h3>Importar NF-e / NFC-e</h3>
   <p className="muted">Leia XMLs oficiais ou DANFEs em PDF com texto selecionável. O SFI guarda os dados extraídos e o hash, não o arquivo original. PDF digitalizado/OCR ainda não é suportado.</p>
   {error&&<p className="form-error" role="alert">{error}</p>}{notice&&<p className="form-hint" role="status">{notice}</p>}
   <div className="form-stack">
    <label>Arquivo XML ou PDF<input type="file" accept=".xml,.pdf,application/xml,text/xml,application/pdf" onChange={chooseFile}/></label>
    {filename&&<small className="muted">{filename}</small>}
    <label>Conteúdo do QR Code (opcional)<textarea value={qrPayload} maxLength={4096} rows={3} onChange={event=>{setQrPayload(event.target.value);setPreview(null);}} placeholder="Cole o texto/URL obtido do QR Code da NF-e/NFC-e"/></label>
    <p className="muted">O SFI compara a chave do QR com a chave do documento. Isso não consulta a SEFAZ nem comprova autenticidade ou situação fiscal.</p>
    <button className="button primary" type="button" disabled={busy||!content} onClick={()=>void makePreview()}>{busy?"Analisando...":"Analisar documento"}</button>
   </div>
  </section>
  {preview&&<section className="panel">
   <h3>Revisão da nota fiscal</h3>
   <div className="metric-grid">
    <article className="metric-card"><span className="eyebrow">VALOR TOTAL</span><strong>{money(preview.total_amount,preview.currency)}</strong></article>
    <article className="metric-card"><span className="eyebrow">ITENS</span><strong>{preview.items.length}</strong></article>
   </div>
   <dl className="detail-list">
    <div><dt>Emitente</dt><dd>{preview.issuer_name}</dd></div>
    <div><dt>CNPJ / CPF</dt><dd>{preview.issuer_tax_id}</dd></div>
    <div><dt>Número / série</dt><dd>{preview.document_number} / {preview.series}</dd></div>
    <div><dt>Emissão</dt><dd>{new Date(preview.issue_date).toLocaleString("pt-BR")}</dd></div>
    <div><dt>Chave de acesso</dt><dd className="key-wrap">{preview.access_key}</dd></div>
    <div><dt>QR Code</dt><dd>{preview.qr_code_status==="matches"?"Chave confere com o documento": "Não informado"}</dd></div>
   </dl>
   <div className="table-wrap"><table><thead><tr><th>Produto</th><th>NCM</th><th>CFOP</th><th>Qtd.</th><th>Total</th></tr></thead><tbody>{preview.items.map((item,index)=><tr key={item.code+"-"+index}><td>{item.description||item.code}</td><td>{item.ncm||"—"}</td><td>{item.cfop||"—"}</td><td>{item.quantity} {item.unit}</td><td>{money(item.total)}</td></tr>)}</tbody></table></div>
   <label className="checkbox-field"><input type="checkbox" checked={createExpense} onChange={e=>setCreateExpense(e.target.checked)}/> Criar despesa com o valor total da nota</label>
   {createExpense&&<div className="form-row">
    <label>Conta<select value={accountId} onChange={e=>setAccountId(e.target.value)} required><option value="">Selecione</option>{accounts.map(a=><option key={a.id} value={a.id}>{a.name} · {a.currency}</option>)}</select></label>
    <label>Categoria<select value={categoryId} onChange={e=>setCategoryId(e.target.value)}><option value="">Sem categoria</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
   </div>}
   <p className="muted">A despesa é criada apenas após sua confirmação. O total será lançado uma única vez; itens são mantidos para consulta.</p>
   {preview.already_imported&&<p className="form-error" role="alert">Esta chave de acesso já consta no SFI.</p>}
   <button className="button primary" type="button" disabled={busy||preview.already_imported||(createExpense&&!accountId)} onClick={()=>void confirm()}>Confirmar importação</button>
  </section>}
  <section className="panel">
   <h3>Notas fiscais importadas</h3>
   {documents.length?<div className="table-wrap"><table><thead><tr><th>Emitente</th><th>Número</th><th>Emissão</th><th>Total</th><th>Despesa</th></tr></thead><tbody>{documents.map(doc=><tr key={doc.id}><td>{doc.issuer_name}<small>{doc.issuer_tax_id}</small></td><td>{doc.document_number}/{doc.series}</td><td>{new Date(doc.issue_date).toLocaleDateString("pt-BR")}</td><td>{money(doc.total_amount,doc.currency)}</td><td>{doc.transaction_id?"Registrada":"Não criada"}</td></tr>)}</tbody></table></div>:<p className="muted">Nenhuma nota fiscal importada ainda.</p>}
  </section>
 </div>;
}
