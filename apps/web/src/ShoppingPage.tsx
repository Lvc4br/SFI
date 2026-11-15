import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "./api";
import type { ShoppingItem, ShoppingList, ShoppingListDetail } from "./api";

const money = (value: string | null) => value === null ? "—" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));

export default function ShoppingPage() {
  const [lists, setLists] = useState<ShoppingList[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [detail, setDetail] = useState<ShoppingListDetail | null>(null);
  const [name, setName] = useState("");
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("un");
  const [price, setPrice] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refreshLists = useCallback(async (preferredId?: string) => {
    const data = await api.shoppingLists(favoritesOnly);
    setLists(data);
    const nextId = preferredId && data.some(list => list.id === preferredId)
      ? preferredId
      : data.some(list => list.id === selected) ? selected : data[0]?.id ?? "";
    setSelected(nextId);
    if (!nextId) setDetail(null);
    return nextId;
  }, [favoritesOnly, selected]);

  const refreshDetail = useCallback(async (id: string) => {
    if (!id) { setDetail(null); return; }
    setDetail(await api.shoppingList(id));
  }, []);

  useEffect(() => {
    let active = true;
    void api.shoppingLists(favoritesOnly).then(data => {
      if (!active) return;
      setLists(data);
      setSelected(current => data.some(list => list.id === current) ? current : data[0]?.id ?? "");
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : "Falha ao carregar listas."); });
    return () => { active = false; };
  }, [favoritesOnly]);

  useEffect(() => {
    let active = true;
    if (!selected) { setDetail(null); return; }
    void api.shoppingList(selected).then(data => { if (active) setDetail(data); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "Falha ao abrir lista."); });
    return () => { active = false; };
  }, [selected]);

  const total = useMemo(() => detail?.items.reduce((sum, item) =>
    sum + (item.unit_price === null ? 0 : Number(item.unit_price) * Number(item.quantity)), 0) ?? 0, [detail]);
  const pending = detail?.items.filter(item => !item.is_checked).length ?? 0;
  const checked = detail?.items.filter(item => item.is_checked).length ?? 0;

  async function run(operation: () => Promise<unknown>, success: string, refresh = true) {
    setBusy(true); setError(""); setNotice("");
    try {
      await operation();
      if (refresh && selected) await refreshDetail(selected);
      setNotice(success);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível concluir a operação."); }
    finally { setBusy(false); }
  }

  async function createList(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const created = await api.createShoppingList(name.trim());
      setName("");
      await refreshLists(created.id);
      setNotice("Lista criada.");
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível criar a lista."); }
    finally { setBusy(false); }
  }

  async function addItem(event: FormEvent) {
    event.preventDefault();
    if (!detail || !itemName.trim()) return;
    const parsedQuantity = Number(quantity.replace(",", "."));
    const parsedPrice = price.trim() ? Number(price.replace(",", ".")) : null;
    if (!Number.isFinite(parsedQuantity) || parsedQuantity <= 0) { setError("Informe uma quantidade maior que zero."); return; }
    if (parsedPrice !== null && (!Number.isFinite(parsedPrice) || parsedPrice < 0)) { setError("Informe um preço válido ou deixe o campo vazio."); return; }
    await run(async () => {
      await api.createShoppingItem(detail.id, {
        name: itemName.trim(), quantity: parsedQuantity.toFixed(3), unit: unit.trim() || "un",
        unit_price: parsedPrice === null ? null : parsedPrice.toFixed(2),
        position: detail.items.length,
      });
      setItemName(""); setQuantity("1"); setUnit("un"); setPrice("");
    }, "Item adicionado.");
  }

  async function toggleItem(item: ShoppingItem) {
    await run(() => api.updateShoppingItem(item.list_id, item.id, { is_checked: !item.is_checked }),
      item.is_checked ? "Item voltou para a lista." : "Item marcado como comprado.");
  }

  async function renameList() {
    if (!detail) return;
    const next = window.prompt("Nome da lista:", detail.name);
    if (next === null || !next.trim() || next.trim() === detail.name) return;
    await run(async () => {
      await api.updateShoppingList(detail.id, { name: next.trim() });
      await refreshLists(detail.id);
    }, "Lista renomeada.");
  }

  async function archiveList() {
    if (!detail || !window.confirm("Arquivar esta lista? Os itens e o histórico serão preservados.")) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await api.archiveShoppingList(detail.id);
      const next = await refreshLists();
      if (next) await refreshDetail(next);
      setNotice("Lista arquivada. O histórico foi preservado.");
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível arquivar a lista."); }
    finally { setBusy(false); }
  }

  return <section className="content-grid shopping-page">
    {error && <div className="alert error" role="alert">{error}<button onClick={() => setError("")} aria-label="Fechar erro">×</button></div>}
    {notice && <div className="alert success" role="status">{notice}<button onClick={() => setNotice("")} aria-label="Fechar aviso">×</button></div>}
    <div className="shopping-layout">
      <aside className="panel shopping-sidebar">
        <div className="panel-heading"><div><h3>Suas listas</h3><p className="muted">Mercado, farmácia e outras compras</p></div></div>
        <form className="shopping-create-list" onSubmit={createList}>
          <input aria-label="Nome da nova lista" placeholder="Nome da lista" value={name} onChange={e => setName(e.target.value)} maxLength={100} required />
          <button className="button primary" disabled={busy || !name.trim()}>Criar lista</button>
        </form>
        <label className="shopping-favorites-filter"><input type="checkbox" checked={favoritesOnly} onChange={e => setFavoritesOnly(e.target.checked)} /> Mostrar apenas favoritas</label>
        <div className="shopping-list-options">
          {lists.map(list => <button type="button" key={list.id} className={selected === list.id ? "shopping-list-option active" : "shopping-list-option"} onClick={() => setSelected(list.id)}>
            <span className="shopping-list-icon">☷</span><span className="shopping-list-name">{list.name}<small>{list.is_favorite ? "Favorita" : "Lista pessoal"}</small></span><span className="shopping-fav-mark">{list.is_favorite ? "★" : ""}</span>
          </button>)}
          {!lists.length && <p className="muted shopping-empty">Nenhuma lista encontrada. Crie sua primeira lista.</p>}
        </div>
      </aside>
      <section className="panel shopping-detail">
        {detail ? <>
          <div className="shopping-detail-heading">
            <div><span className="eyebrow">LISTA DE COMPRAS</span><h2>{detail.name}</h2><p className="muted">{pending} pendentes · {checked} comprados</p></div>
            <div className="shopping-actions">
              <button className="button secondary" type="button" disabled={busy} onClick={() => void run(() => api.updateShoppingList(detail.id, { is_favorite: !detail.is_favorite }), detail.is_favorite ? "Removida das favoritas." : "Adicionada às favoritas.")}>{detail.is_favorite ? "★ Favorita" : "☆ Favoritar"}</button>
              <button className="button secondary" type="button" disabled={busy} onClick={renameList}>Renomear</button>
              <button className="button secondary" type="button" disabled={busy} onClick={archiveList}>Arquivar</button>
            </div>
          </div>
          <form className="shopping-add-item" onSubmit={addItem}>
            <input className="shopping-item-name" aria-label="Nome do item" placeholder="O que você precisa comprar?" value={itemName} onChange={e => setItemName(e.target.value)} maxLength={120} required />
            <input aria-label="Quantidade" type="number" min="0.001" step="0.001" value={quantity} onChange={e => setQuantity(e.target.value)} required />
            <input aria-label="Unidade" value={unit} onChange={e => setUnit(e.target.value)} maxLength={20} required />
            <input aria-label="Preço unitário estimado" inputMode="decimal" placeholder="Preço (R$)" value={price} onChange={e => setPrice(e.target.value)} />
            <button className="button primary" disabled={busy || !itemName.trim()}>Adicionar</button>
          </form>
          <div className="shopping-items-heading"><strong>Itens</strong><span>Estimativa dos itens com preço informado</span></div>
          {detail.items.length ? <div className="shopping-items">
            {detail.items.map(item => <article className={item.is_checked ? "shopping-item checked" : "shopping-item"} key={item.id}>
              <input type="checkbox" checked={item.is_checked} disabled={busy} aria-label={"Marcar " + item.name + " como comprado"} onChange={() => void toggleItem(item)} />
              <div className="shopping-item-description"><strong>{item.name}</strong><small>{Number(item.quantity).toLocaleString("pt-BR")} {item.unit} · {money(item.unit_price)} por unidade</small></div>
              <strong className="shopping-item-total">{item.unit_price === null ? "—" : money((Number(item.unit_price) * Number(item.quantity)).toFixed(2))}</strong>
              <button className="shopping-delete" type="button" disabled={busy} aria-label={"Excluir " + item.name} onClick={() => { if (window.confirm("Excluir este item da lista?")) void run(() => api.deleteShoppingItem(item.list_id, item.id), "Item removido."); }}>×</button>
            </article>)}
          </div> : <div className="empty-state"><span>◌</span><p>Esta lista ainda não tem itens. Adicione o primeiro acima.</p></div>}
          <div className="shopping-total"><div><span>Total estimado</span><strong>{money(total.toFixed(2))}</strong></div><small>Não é uma despesa registrada. Os valores são apenas uma estimativa de compras.</small></div>
        </> : <div className="empty-state shopping-no-selection"><span>🛒</span><p>Selecione uma lista ou crie uma nova para organizar suas compras.</p></div>}
      </section>
    </div>
  </section>;
}
