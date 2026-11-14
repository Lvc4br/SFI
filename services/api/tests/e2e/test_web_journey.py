import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, expect, sync_playwright


@pytest.mark.e2e
def test_complete_web_financial_journey() -> None:
    base_url = os.environ.get("SFI_E2E_WEB_URL", "http://127.0.0.1:5173")
    email = f"e2e-{uuid.uuid4().hex[:12]}@example.test"
    password = "E2e-SFI-Strong-Password-2026"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page: Page = browser.new_page(accept_downloads=True)
        try:
            page.goto(base_url, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Acesse sua conta")).to_be_visible()
            page.get_by_role("button", name="Criar conta", exact=True).click()
            expect(page.get_by_role("heading", name="Crie sua conta")).to_be_visible()

            page.get_by_label("E-mail").fill(email)
            page.get_by_label("Senha").fill(password)
            page.get_by_role("button", name="Criar conta", exact=True).click()
            expect(page.get_by_role("heading", name="Visão geral")).to_be_visible()
            expect(page.get_by_text(email)).to_be_visible()
            assert page.evaluate("() => sessionStorage.getItem('sfi.access')") is None
            assert page.evaluate("() => sessionStorage.getItem('sfi.refresh')") is None
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text(email)).to_be_visible(timeout=10000)
            unnamed_controls = page.locator("button,input,select,textarea").evaluate_all(
                """
                (elements) => elements.filter((element) => {
                    const name = element.getAttribute("aria-label")
                        || element.getAttribute("aria-labelledby");
                    const label = element.labels && element.labels.length > 0;
                    const text = (element.innerText || element.value || "").trim();
                    return !name && !label && !text;
                }).map((element) => element.outerHTML)
                """
            )
            assert not unnamed_controls, unnamed_controls

            page.get_by_role("button", name="Configurações").click()
            expect(page.locator(".security-event-list").get_by_text("Conta criada")).to_be_visible()
            page.get_by_label("Fuso horário IANA").fill("America/Sao_Paulo")
            page.get_by_role("button", name="Salvar fuso horário").click()
            expect(
                page.get_by_text(
                    "Fuso horário atualizado. Os períodos financeiros serão calculados nesse fuso."
                )
            ).to_be_visible()

            page.get_by_role("button", name="Contas e categorias").click()
            account_form = page.locator("form").filter(
                has=page.get_by_placeholder("Ex.: Conta principal")
            )
            account_form.get_by_placeholder("Ex.: Conta principal").fill("Conta E2E")
            account_form.get_by_label("Valor em reais").fill("50000")
            page.get_by_role("button", name="Adicionar conta").click()
            expect(page.get_by_text("Conta adicionada.")).to_be_visible()
            expect(page.get_by_role("heading", name="Conta E2E")).to_be_visible()

            account_form = page.locator("form").filter(
                has=page.get_by_placeholder("Ex.: Conta principal")
            )
            account_form.get_by_placeholder("Ex.: Conta principal").fill("Conta reserva E2E")
            page.get_by_role("button", name="Adicionar conta").click()
            expect(page.get_by_text("Conta adicionada.")).to_be_visible()

            page.get_by_placeholder("Ex.: Alimentação").fill("Categoria E2E")
            page.get_by_role("button", name="Criar categoria").click()
            expect(page.get_by_text("Categoria criada.")).to_be_visible()
            expect(page.get_by_text("Categoria E2E")).to_be_visible()

            page.get_by_role("button", name="Movimentações").click()
            transfer_form = page.locator("form").filter(has=page.get_by_label("Conta de origem"))
            transfer_form.get_by_label("Conta de origem").select_option(label="Conta E2E · BRL")
            transfer_form.get_by_label("Conta de destino").select_option(label="Conta reserva E2E")
            transfer_form.get_by_label("Valor em reais").fill("1000")
            page.get_by_role("button", name="Confirmar transferência").click()
            expect(page.get_by_text("Transferência registrada.")).to_be_visible()

            page.get_by_placeholder("Ex.: Compra no mercado").fill("Compra E2E")
            transaction_form = page.locator("form").filter(
                has=page.get_by_placeholder("Ex.: Compra no mercado")
            )
            transaction_form.get_by_label("Valor em reais").fill("12345")
            transaction_form.get_by_label("Conta").select_option(label="Conta E2E")
            page.get_by_label("Categoria (opcional)").select_option(label="Categoria E2E")
            page.get_by_role("button", name="Registrar movimentação").click()
            expect(page.get_by_text("Movimentação registrada.")).to_be_visible()
            expect(page.get_by_text("Compra E2E")).to_be_visible()
            expect(page.get_by_text("123,45", exact=False)).to_be_visible()

            page.get_by_label("Filtrar tipo").select_option("expense")
            expect(page.get_by_text("Exibindo 1–2 de 2 movimentações filtradas.")).to_be_visible()
            page.once("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name="Estornar Compra E2E").click()
            expect(
                page.get_by_text("Estorno registrado. O lançamento original foi preservado.")
            ).to_be_visible()
            expect(page.get_by_text("Estornada")).to_be_visible()

            api_url = os.environ.get("SFI_E2E_API_URL", "http://127.0.0.1:8000")
            today = datetime.now(UTC).date().isoformat()
            with httpx.Client(base_url=api_url, timeout=10.0) as api:
                test_login = api.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": password},
                )
                assert test_login.status_code == 200, test_login.text
                api.headers["Authorization"] = f"Bearer {test_login.json()['access_token']}"
                account_rows = api.get("/api/v1/finance/accounts").json()
                category_rows = api.get("/api/v1/finance/categories").json()
                account_id = next(row["id"] for row in account_rows if row["name"] == "Conta E2E")
                category_id = next(
                    row["id"] for row in category_rows if row["name"] == "Categoria E2E"
                )
                for index in range(30):
                    created = api.post(
                        "/api/v1/finance/transactions",
                        json={
                            "account_id": account_id,
                            "category_id": category_id,
                            "transaction_type": "expense",
                            "amount": "1.00",
                            "description": f"Volume E2E {index:02d}",
                            "occurred_at": f"{today}T12:00:00+00:00",
                            "idempotency_key": f"e2e-volume-{uuid.uuid4().hex}",
                        },
                    )
                    assert created.status_code == 201, created.text

            page.get_by_label("Filtrar tipo").select_option("expense")
            page.get_by_label("Data inicial").fill(today)
            page.get_by_label("Data final").fill(today)
            expect(page.get_by_text("Página 1 de 2")).to_be_visible()
            expect(page.locator(".results-note")).to_contain_text("Exibindo 1–25 de")
            page.get_by_role("button", name="Próxima").click()
            expect(page.get_by_text("Página 2 de 2")).to_be_visible()
            expect(page.locator(".results-note")).to_contain_text("Exibindo 26–")
            page.get_by_role("button", name="Anterior").click()
            page.get_by_label("Buscar movimentação").fill("Volume E2E")
            with page.expect_download() as volume_download_info:
                page.get_by_role("button", name="Exportar CSV completo").click()
            volume_download = volume_download_info.value
            volume_path = volume_download.path()
            assert volume_path is not None
            volume_rows = Path(volume_path).read_text(encoding="utf-8-sig").splitlines()
            assert len(volume_rows) == 31
            page.get_by_label("Buscar movimentação").fill("")
            page.get_by_label("Filtrar tipo").select_option("all")
            page.get_by_label("Data inicial").fill("")
            page.get_by_label("Data final").fill("")

            page.get_by_role("button", name="Ativar tema escuro").click()
            expect(page.locator(".app-shell")).to_have_attribute("data-theme", "dark")
            page.get_by_role("button", name="Ativar tema claro").click()
            expect(page.locator(".app-shell")).to_have_attribute("data-theme", "light")

            page.get_by_role("button", name="Orçamento").click()
            page.get_by_label("Categoria").select_option(label="Categoria E2E")
            page.locator("form").get_by_label("Valor em reais").fill("20000")
            page.get_by_role("button", name="Criar orçamento").click()
            expect(page.get_by_text("Orçamento criado.")).to_be_visible()
            expect(page.get_by_text("Dentro do limite")).to_be_visible()

            page.get_by_role("button", name="Contas e categorias").click()
            page.once("dialog", lambda dialog: dialog.accept("Conta E2E renomeada"))
            page.locator(".account-card").filter(
                has=page.get_by_role("heading", name="Conta E2E")
            ).get_by_role("button", name="Renomear").click()
            expect(page.get_by_role("heading", name="Conta E2E renomeada")).to_be_visible()

            page.once("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name="Arquivar Categoria E2E").click()
            expect(
                page.get_by_text("Categoria arquivada. O histórico foi preservado.")
            ).to_be_visible()

            page.get_by_role("button", name="Movimentações").click()
            expect(page.get_by_role("cell", name="Conta E2E renomeada").first).to_be_visible()
            expect(page.get_by_role("cell", name="Categoria E2E").first).to_be_visible()
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Exportar CSV completo").click()
            download = download_info.value
            assert download.suggested_filename == "sfi-movimentacoes-filtradas.csv"

            page.get_by_role("button", name="Sair da conta").click()
            expect(page.get_by_role("heading", name="Acesse sua conta")).to_be_visible()
            page.get_by_label("E-mail").fill(email)
            page.get_by_label("Senha").fill(password)
            page.get_by_role("button", name="Entrar", exact=True).click()
            expect(page.get_by_text(email)).to_be_visible()
            page.get_by_role("button", name="Visão geral").click()
            expect(page.get_by_role("heading", name="Visão geral")).to_be_visible()
        finally:
            browser.close()
