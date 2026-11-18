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
        browser_name = os.environ.get("SFI_E2E_BROWSER", "chromium").lower()
        browser_type = getattr(playwright, browser_name, None)
        if browser_type is None:
            raise ValueError(f"Unsupported SFI_E2E_BROWSER: {browser_name}")
        browser = browser_type.launch()
        page: Page = browser.new_page(accept_downloads=True)
        try:
            page.goto(base_url, wait_until="networkidle")
            expect(page.get_by_role("heading", name="Acesse sua conta")).to_be_visible()
            assert page.get_by_role("main").count() == 1, "The page must expose one main landmark"
            assert (
                page.get_by_role("heading", level=1).count() >= 1
            ), "A primary heading is required"
            page.keyboard.press("Tab")
            assert page.evaluate(
                "document.activeElement !== document.body"
            ), "Keyboard focus must enter the page"
            page.keyboard.press("Shift+Tab")
            page.get_by_role("button", name="Criar conta", exact=True).click()
            expect(page.get_by_role("heading", name="Crie sua conta")).to_be_visible()

            page.get_by_label("E-mail").fill(email)
            page.get_by_label("Senha").fill(password)
            page.get_by_role("button", name="Criar conta", exact=True).click()
            expect(page.get_by_role("heading", name="Visão geral")).to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.get_by_role("heading", name="Visão geral")).to_be_visible()
            page.set_viewport_size({"width": 1365, "height": 900})
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
                credit_account = api.post(
                    "/api/v1/finance/accounts",
                    json={"name": "Cartão E2E", "account_type": "credit"},
                )
                assert credit_account.status_code == 201, credit_account.text
                credit_card = api.post(
                    "/api/v1/credit/cards",
                    json={
                        "account_id": credit_account.json()["id"],
                        "name": "Cartão de teste E2E",
                        "brand": "Visa",
                        "last_four": "1234",
                        "closing_day": 10,
                        "due_day": 20,
                        "credit_limit": "3000.00",
                    },
                )
                assert credit_card.status_code == 201, credit_card.text
                credit_purchase = api.post(
                    "/api/v1/credit/purchases",
                    json={
                        "card_id": credit_card.json()["id"],
                        "description": "Compra parcelada E2E",
                        "amount": "300.00",
                        "purchase_date": today,
                        "installments": 3,
                        "idempotency_key": f"e2e-card-{uuid.uuid4().hex}",
                    },
                )
                assert credit_purchase.status_code == 201, credit_purchase.text
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

            page.get_by_role("button", name="Cartões").click()
            expect(page.locator(".credit-invoice-list")).to_be_visible()
            invoice = page.locator(".credit-invoice").filter(
                has_text="Cartão de teste E2E"
            ).first
            expect(invoice).to_be_visible()
            invoice.get_by_role("button", name="Fechar").click()
            expect(invoice.get_by_text("Fechada")).to_be_visible()
            invoice.get_by_role("button", name="Pagar").click()
            page.get_by_label("Conta de origem").select_option(label="Conta reserva E2E")
            page.get_by_role("button", name="Confirmar pagamento").click()
            expect(page.get_by_text("Pagamento registrado.")).to_be_visible()
            expect(invoice.get_by_text("Paga")).to_be_visible()

            page.get_by_role("button", name="Movimentações").click()

            # Wait for each server-side filter request before applying the next one.
            # This keeps the E2E deterministic and exercises the UI's stale-response guard.
            with page.expect_response(
                lambda response: (
                    "/api/v1/finance/transactions/page?" in response.url
                    and "offset=0" in response.url
                    and "transaction_type=expense" in response.url
                )
            ):
                page.get_by_label("Filtrar tipo").select_option("expense")
            with page.expect_response(
                lambda response: (
                    "/api/v1/finance/transactions/page?" in response.url
                    and "offset=0" in response.url
                    and "start_date=" in response.url
                )
            ):
                page.get_by_label("Data inicial").fill(today)
            with page.expect_response(
                lambda response: (
                    "/api/v1/finance/transactions/page?" in response.url
                    and "offset=0" in response.url
                    and "end_date=" in response.url
                )
            ):
                page.get_by_label("Data final").fill(today)
            expect(page.locator(".loading-line")).to_have_count(0)
            expect(page.get_by_text("Página 1 de 2")).to_be_visible()
            expect(page.locator(".results-note")).to_contain_text("Exibindo 1–25 de")
            with page.expect_response(
                lambda response: (
                    "/api/v1/finance/transactions/page?" in response.url
                    and "offset=25" in response.url
                )
            ) as next_page_response:
                page.get_by_role("button", name="Próxima").click()
            response = next_page_response.value
            assert response.ok, f"Next-page request failed: {response.status} {response.url}"
            page_payload = response.json()
            assert page_payload["offset"] == 25, page_payload
            # Setup transactions can also match the UTC/local calendar-day filter.
            # Validate the actual page contract; setup rows can affect page composition
            # when timestamps tie across records.
            assert page_payload["total"] >= 30, page_payload
            assert (
                len(page_payload["items"])
                == page_payload["total"] - page_payload["offset"]
            ), page_payload
            volume_items = [
                item for item in page_payload["items"]
                if item["description"].startswith("Volume E2E ")
            ]
            assert len(volume_items) >= 5, page_payload
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

            theme_select = page.get_by_label("Tema visual")
            theme_select.select_option("dark")
            expect(page.locator(".app-shell")).to_have_attribute("data-theme", "dark")
            theme_select.select_option("contrast")
            expect(page.locator(".app-shell")).to_have_attribute("data-theme", "contrast")
            theme_select.select_option("light")
            expect(page.locator(".app-shell")).to_have_attribute("data-theme", "light")

            page.get_by_role("button", name="Configurações").click()
            accent_picker = page.get_by_label("Cor de destaque")
            accent_picker.evaluate(
                "(element) => { element.value = '#4f46e5'; "
                "element.dispatchEvent(new Event('input', {bubbles: true})); "
                "element.dispatchEvent(new Event('change', {bubbles: true})); }"
            )
            assert "#4f46e5" in (page.locator(".app-shell").get_attribute("style") or "")
            page.get_by_role("button", name="Restaurar cores padrão").click()

            page.get_by_role("button", name="Calculadoras").click()
            page.get_by_role("button", name="Calcular").click()
            expect(page.get_by_text("Valor futuro")).to_be_visible()
            page.get_by_role("button", name="Price / SAC").click()
            page.get_by_role("button", name="Calcular").click()
            expect(page.get_by_role("columnheader", name="Prestação")).to_be_visible()

            page.get_by_role("button", name="Relatórios").click()
            expect(page.get_by_text("Relatório anual")).to_be_visible()
            expect(page.get_by_text(f"Consolidado de {datetime.now().year}")).to_be_visible()

            page.get_by_role("button", name="Orçamento").click()
            page.get_by_label("Categoria").select_option(label="Categoria E2E")
            page.locator("form").get_by_label("Valor em reais").fill("20000")
            page.get_by_role("button", name="Criar orçamento").click()
            expect(page.get_by_text("Orçamento criado.")).to_be_visible()
            expect(page.get_by_text("Dentro do limite")).to_be_visible()

            page.get_by_role("button", name="Metas").click()
            page.get_by_label("Nome da meta").fill("Meta E2E")
            page.get_by_label("Valor-alvo (R$)").fill("500.00")
            page.get_by_role("button", name="Criar meta").click()
            expect(page.get_by_text("Meta criada.")).to_be_visible()
            goal_form = page.locator("form").filter(
                has=page.get_by_label("Tipo de movimento")
            )
            goal_form.get_by_label("Meta").select_option(index=1)
            goal_form.get_by_label("Tipo de movimento").select_option("contribution")
            goal_form.get_by_label("Valor (R$)").fill("300.00")
            goal_form.get_by_role("button", name="Registrar movimento").click()
            expect(page.get_by_text("Aporte registrado.")).to_be_visible()
            goal_form.get_by_label("Tipo de movimento").select_option("withdrawal")
            goal_form.get_by_label("Valor (R$)").fill("50.00")
            goal_form.get_by_role("button", name="Registrar movimento").click()
            expect(page.get_by_text("Retirada registrada.")).to_be_visible()
            expect(goal_form.get_by_text("Saldo reservado:")).to_contain_text("250,00")

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
