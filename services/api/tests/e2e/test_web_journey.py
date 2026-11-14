import os
import uuid

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
            page.get_by_label("Filtrar tipo").select_option("all")

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

            page.get_by_role("button", name="Movimentações").click()
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Exportar CSV completo").click()
            download = download_info.value
            assert download.suggested_filename == "sfi-movimentacoes-filtradas.csv"

            page.get_by_role("button", name="Sair da conta").click()
            expect(page.get_by_role("heading", name="Crie sua conta")).to_be_visible()
            page.get_by_role("button", name="Entrar", exact=True).click()
            expect(page.get_by_role("heading", name="Acesse sua conta")).to_be_visible()
            page.get_by_label("E-mail").fill(email)
            page.get_by_label("Senha").fill(password)
            page.get_by_role("button", name="Entrar", exact=True).click()
            expect(page.get_by_role("heading", name="Visão geral")).to_be_visible()
        finally:
            browser.close()
