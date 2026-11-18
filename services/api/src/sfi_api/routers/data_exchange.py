import base64
import binascii
import csv
import hashlib
import io
import json
import re
import uuid
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel, Field
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.user import User

router = APIRouter(prefix="/exchange", tags=["data exchange"])
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 10000


class ImportRequest(BaseModel):
    format: Literal["csv", "json", "ofx", "xlsx", "qif", "pdf"]
    content: str = Field(min_length=1)
    default_account_id: uuid.UUID | None = None
    default_category_id: uuid.UUID | None = None


class ConfirmedImportRequest(ImportRequest):
    confirmed: bool


def _date_value(value: str | date | datetime | None) -> datetime:
    if value is None:
        raise ValueError("Data não informada.")
    if isinstance(value, datetime):
        parsed = value.replace(tzinfo=UTC) if value.tzinfo is None else value
        return parsed.astimezone(UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, 12, tzinfo=UTC)
    if not isinstance(value, str):
        raise ValueError(
            "Data inválida; informe uma data reconhecida pelo Excel ou texto ISO 8601."
        )
    raw = value.strip()
    if not raw:
        raise ValueError("Data não informada.")
    if re.fullmatch(r"\d{8}(?:\d{6})?.*", raw):
        parsed = datetime.strptime(raw[:8], "%Y%m%d").replace(tzinfo=UTC)
        return parsed
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%d/%m/%Y").replace(
                hour=12, tzinfo=UTC
            )
        except ValueError as exc:
            raise ValueError("Data inválida; use ISO 8601 ou DD/MM/AAAA.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("A data precisa conter fuso horário.")
    return parsed.astimezone(UTC)



def _parse_qif_date(value: str) -> datetime:
    raw = value.strip()
    for pattern in ("%m/%d'%y", "%m/%d/%y", "%m/%d/%Y", "%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError("Data QIF inválida ou ambígua; use MM/DD'AA ou DD/MM/AAAA.")


def _parse_qif(content: str) -> list[dict]:
    if not re.search(r"(?im)^!Type:(Bank|Cash|CCard|Oth A|Oth L)\s*$", content):
        raise HTTPException(422, "Cabeçalho QIF não reconhecido.")
    records = []
    current: dict[str, str] = {}
    line_number = 0
    for raw_line in content.replace("\r", "").split("\n"):
        line_number += 1
        line = raw_line.strip()
        if not line:
            continue
        if line == "^":
            if current:
                amount_text = current.get("T", "").strip()
                description = current.get("P") or current.get("M") or ""
                if not amount_text or not description.strip() or not current.get("D"):
                    records.append({
                        "line": line_number,
                        "error": (
                            "Registro QIF incompleto: exige data (D), valor (T) e favorecido/memo "
                            "(P/M)."
                        ),
                    })
                else:
                    try:
                        normalized = amount_text.replace("R$", "").replace(" ", "")
                        if "," in normalized and "." in normalized:
                            if normalized.rfind(".") > normalized.rfind(","):
                                normalized = normalized.replace(",", "")
                            else:
                                normalized = normalized.replace(".", "").replace(",", ".")
                        elif "," in normalized:
                            normalized = normalized.replace(".", "").replace(",", ".")
                        amount = Decimal(normalized)
                        if amount == 0:
                            raise ValueError("Valor zero.")
                        records.append({
                            "date": _parse_qif_date(current["D"]),
                            "amount": str(abs(amount)),
                            "type": "expense" if amount < 0 else "income",
                            "description": description.strip(),
                            "category": current.get("L", "").strip(),
                            "external_id": "",
                        })
                    except (InvalidOperation, ValueError) as exc:
                        records.append(
                        {"line": line_number, "error": f"Registro QIF inválido: {exc}"}
                    )
                current = {}
            continue
        if line.startswith("!"):
            continue
        if len(line) >= 2 and line[0] in {"D", "T", "P", "M", "L", "N", "C", "A"}:
            current[line[0]] = line[1:].strip()
    if current:
        records.append({
            "line": line_number,
            "error": "Registro QIF sem terminador ^; o último lançamento está incompleto.",
        })
    if not records:
        raise HTTPException(422, "O arquivo QIF não contém registros de movimentação.")
    return records


def _parse_pdf_statement(binary: bytes) -> list[dict]:
    try:
        reader = PdfReader(io.BytesIO(binary), strict=True)
        if reader.is_encrypted:
            raise HTTPException(422, "PDF protegido por senha não é aceito.")
        if len(reader.pages) > 100:
            raise HTTPException(413, "O PDF excede o limite de 100 páginas.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "PDF inválido ou sem camada de texto legível.") from exc
    if len(text) > 2 * 1024 * 1024:
        raise HTTPException(413, "O texto extraído do PDF excede o limite seguro.")
    if not text.strip():
        raise HTTPException(
            422,
            "PDF sem texto selecionável; OCR para documentos digitalizados ainda não disponível.",
        )

    date_pattern = r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})"
    amount_pattern = (
        r"([+-]?(?:\d{1,3}(?:\.\d{3})*|\d+)(?:,\d{2}|\.\d{2}))"
        r"(?:\s*([DC])|([+-]))?$"
    )
    groups: list[dict] = []
    current: dict | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = " ".join(raw_line.split())
        if not line:
            continue
        date_match = re.match("^" + date_pattern + r"\s+(.+)$", line)
        if date_match:
            if current is not None:
                groups.append(current)
            current = {
                "line": line_number,
                "date": date_match.group(1),
                "remainder": date_match.group(2).strip(),
                "continuations": 0,
            }
        elif current is not None and current["continuations"] < 2:
            if re.match(r"^(saldo|total|extrato|página|pagina|lançamentos|lancamentos)\b", line, re.I):
                groups.append(current)
                current = None
                continue
            if not re.search(amount_pattern, current["remainder"], re.IGNORECASE):
                current["remainder"] += " " + line
                current["continuations"] += 1
    if current is not None:
        groups.append(current)

    records = []
    for group in groups:
        remainder = group["remainder"]
        amount_match = re.search(amount_pattern, remainder, re.IGNORECASE)
        if not amount_match:
            records.append({
                "line": group["line"],
                "error": "Linha iniciada por data sem valor reconhecível no final.",
            })
            continue
        description = remainder[:amount_match.start()].strip(" -|")
        amount_text = amount_match.group(1)
        direction = (amount_match.group(2) or "").upper()
        trailing_sign = amount_match.group(3) or ""
        if not description:
            records.append({"line": group["line"], "error": "Descrição ausente na linha do PDF."})
            continue
        if direction:
            transaction_type = "expense" if direction == "D" else "income"
        elif amount_text.startswith("-") or trailing_sign == "-":
            transaction_type = "expense"
        elif amount_text.startswith("+") or trailing_sign == "+":
            transaction_type = "income"
        else:
            records.append({
                "line": group["line"],
                "error": (
                    "Valor sem sinal ou indicador D/C; não é seguro inferir receita ou despesa."
                ),
            })
            continue
        date_text = group["date"]
        try:
            parsed_date = datetime.strptime(date_text, "%d/%m/%Y").replace(
                hour=12, tzinfo=UTC
            )
        except ValueError:
            parsed_date = datetime.fromisoformat(date_text).replace(hour=12, tzinfo=UTC)
        records.append({
            "date": parsed_date,
            "amount": amount_text.lstrip("+-"),
            "type": transaction_type,
            "description": description,
            "external_id": "",
        })
    if not records:
        raise HTTPException(
            422,
            "PDF sem linhas reconhecidas no formato data, descrição e valor assinado ou D/C.",
        )
    return records

def _normalize_row(row: dict, line: int, source_format: str) -> dict:
    lowered = {
        str(key).strip().lstrip("\ufeff").lower(): value
        for key, value in row.items()
        if key
    }
    raw_amount = str(lowered.get("amount", lowered.get("trnamt", ""))).strip()
    normalized_amount = raw_amount.replace("R$", "").replace(" ", "")
    if "," in normalized_amount and "." in normalized_amount:
        normalized_amount = normalized_amount.replace(".", "").replace(",", ".")
    else:
        normalized_amount = normalized_amount.replace(",", ".")
    try:
        amount = Decimal(normalized_amount)
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido.") from exc
    transaction_type = str(
        lowered.get("transaction_type", lowered.get("type", lowered.get("trntype", "")))
    ).strip().lower()
    if transaction_type in {"credit", "dep", "directdep", "int", "div"}:
        transaction_type = "income"
    elif transaction_type in {
        "debit", "check", "payment", "fee", "srvchg", "pos", "atm", "directdebit"
    }:
        transaction_type = "expense"
    if amount < 0:
        amount = abs(amount)
        transaction_type = "expense"
    if transaction_type not in {"income", "expense"}:
        raise ValueError("Tipo deve ser income/expense ou equivalente OFX.")
    if amount <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("A movimentação não pode ter mais de duas casas decimais.")
    if amount > Decimal("9999999999999999.99"):
        raise ValueError("O valor excede o limite de precisão financeira.")
    date_text = lowered.get("occurred_at", lowered.get("date", lowered.get("dtposted", "")))
    description_value = lowered.get(
        "description", lowered.get("payee", lowered.get("name", lowered.get("memo", "")))
    )
    description = str(description_value).strip()
    if not description:
        raise ValueError("Descrição não informada.")
    return {
        "line": line,
        "amount": amount,
        "transaction_type": transaction_type,
        "occurred_at": _date_value(date_text),
        "description": description[:160],
        "account_id": str(lowered.get("account_id", "")).strip() or None,
        "account_name": (
            str(lowered.get("account_name", lowered.get("account", ""))).strip() or None
        ),
        "category_id": str(lowered.get("category_id", "")).strip() or None,
        "category_name": (
            str(lowered.get("category_name", lowered.get("category", ""))).strip() or None
        ),
        "external_id": str(lowered.get("external_id", lowered.get("fitid", ""))).strip(),
    }


def _parse_content(payload: ImportRequest) -> list[dict]:
    if payload.format == "pdf":
        try:
            binary = base64.b64decode(payload.content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(422, "O conteúdo PDF não está em Base64 válido.") from exc
        if len(binary) > MAX_IMPORT_BYTES:
            raise HTTPException(413, "O arquivo excede o limite de 5 MB.")
        rows = _parse_pdf_statement(binary)
    elif payload.format == "qif":
        if len(payload.content.encode("utf-8")) > MAX_IMPORT_BYTES:
            raise HTTPException(413, "O arquivo excede o limite de 5 MB.")
        rows = _parse_qif(payload.content)
    elif payload.format == "xlsx":
        try:
            binary = base64.b64decode(payload.content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(422, "O conteúdo XLSX não está em Base64 válido.") from exc
        if len(binary) > MAX_IMPORT_BYTES:
            raise HTTPException(413, "O arquivo excede o limite de 5 MB.")
        try:
            with zipfile.ZipFile(io.BytesIO(binary)) as archive:
                members = archive.infolist()
                expanded_size = sum(member.file_size for member in members)
                if expanded_size > 25 * 1024 * 1024 or any(
                    member.file_size > 1024 * 1024 and member.compress_size == 0
                    or member.compress_size > 0 and member.file_size / member.compress_size > 200
                    for member in members
                ):
                    raise HTTPException(
                        413,
                        "A planilha possui conteúdo compactado acima do limite seguro.",
                    )
            workbook = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
            sheet = workbook.active
            iterator = sheet.iter_rows(values_only=True)
            headers = next(iterator, None)
            if not headers or not any(value is not None for value in headers):
                raise HTTPException(422, "A planilha não possui cabeçalho na primeira linha.")
            names = [str(value).strip() if value is not None else "" for value in headers]
            duplicate_headers = len(set(name.lower() for name in names)) != len(names)
            if any(not name for name in names) or duplicate_headers:
                raise HTTPException(
                    422, "Os cabeçalhos da planilha devem ser preenchidos e únicos."
                )
            rows = []
            for values in iterator:
                if any(value is not None for value in values):
                    rows.append(dict(zip(names, values, strict=False)))
                    if len(rows) > MAX_IMPORT_ROWS:
                        raise HTTPException(413, "O arquivo excede 10.000 movimentações.")
            workbook.close()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                422, "Não foi possível ler a primeira planilha do arquivo XLSX."
            ) from exc
        if not rows:
            raise HTTPException(422, "A planilha não contém linhas de dados.")
    elif len(payload.content.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise HTTPException(413, "O arquivo excede o limite de 5 MB.")
    elif payload.format == "csv":
        try:
            sample = payload.content[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.DictReader(io.StringIO(payload.content), dialect=dialect))
        except csv.Error as exc:
            raise HTTPException(422, f"CSV inválido: {exc}") from exc
        if not rows:
            raise HTTPException(422, "O CSV não contém linhas de dados.")
    elif payload.format == "json":
        try:
            decoded = json.loads(payload.content)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, "JSON inválido.") from exc
        rows = decoded.get("transactions", []) if isinstance(decoded, dict) else decoded
        if not isinstance(rows, list) or not rows:
            raise HTTPException(422, "O JSON deve conter uma lista de transações.")
    else:
        rows = []
        pattern = r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>|</BANKTRANLIST>))"
        for match in re.finditer(pattern, payload.content, re.I | re.S):
            block = match.group(1)
            values = {
                key.lower(): value.strip()
                for key, value in re.findall(r"<([A-Z0-9]+)>([^<\r\n]+)", block, re.I)
            }
            rows.append(values)
        if not rows:
            raise HTTPException(422, "OFX sem registros STMTTRN.")
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(413, "O arquivo excede 10.000 movimentações.")
    normalized = []
    for index, row in enumerate(rows, start=2 if payload.format in {"csv", "xlsx"} else 1):
        if not isinstance(row, dict):
            normalized.append({"line": index, "error": "Registro precisa ser um objeto."})
            continue
        if "error" in row:
            normalized.append({"line": row.get("line", index), "error": row["error"]})
            continue
        try:
            normalized.append(_normalize_row(row, index, payload.format))
        except (ValueError, TypeError) as exc:
            normalized.append({"line": index, "error": str(exc)})
    return normalized


async def _resolve_account(
    session: AsyncSession, user_id: uuid.UUID, row: dict, default_id: uuid.UUID | None
) -> Account:
    account_id = row.get("account_id") or (str(default_id) if default_id else None)
    if account_id:
        try:
            parsed_id = uuid.UUID(account_id)
        except ValueError as exc:
            raise ValueError("Identificador de conta inválido.") from exc
        account = await session.scalar(
            select(Account).where(
                Account.id == parsed_id,
                Account.user_id == user_id,
                Account.archived_at.is_(None),
            )
        )
    elif row.get("account_name"):
        account = await session.scalar(
            select(Account).where(
                Account.user_id == user_id,
                Account.name == row["account_name"],
                Account.archived_at.is_(None),
            )
        )
    else:
        raise ValueError("Informe account_id/account_name ou uma conta padrão.")
    if account is None:
        raise ValueError("Conta inexistente, arquivada ou de outro usuário.")
    return account


async def _resolve_category(
    session: AsyncSession, user_id: uuid.UUID, row: dict, default_id: uuid.UUID | None
) -> Category | None:
    category_id = row.get("category_id") or (str(default_id) if default_id else None)
    if category_id:
        try:
            parsed_id = uuid.UUID(category_id)
        except ValueError as exc:
            raise ValueError("Identificador de categoria inválido.") from exc
        category = await session.scalar(
            select(Category).where(
                Category.id == parsed_id,
                Category.user_id == user_id,
                Category.archived_at.is_(None),
            )
        )
    elif row.get("category_name"):
        category = await session.scalar(
            select(Category).where(
                Category.user_id == user_id,
                Category.name == row["category_name"],
                Category.archived_at.is_(None),
            )
        )
    else:
        return None
    if category is None:
        raise ValueError("Categoria inexistente, arquivada ou de outro usuário.")
    if category.category_type != row["transaction_type"]:
        raise ValueError("A categoria não corresponde ao tipo da movimentação.")
    return category


def _idempotency_key(
    user_id: uuid.UUID, account: Account, category: Category | None, row: dict
) -> str:
    material = "|".join(
        [
            str(user_id), str(account.id), str(category.id if category else ""),
            row["transaction_type"], str(row["amount"]),
            row["occurred_at"].isoformat(), row["description"], row.get("external_id", ""),
        ]
    )
    return "exchange:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


async def _prepare(
    payload: ImportRequest, session: AsyncSession, user: User
) -> tuple[list[dict], int, int]:
    rows = _parse_content(payload)
    prepared = []
    seen_keys: set[str] = set()
    valid_count = 0
    duplicate_count = 0
    for row in rows:
        if "error" in row:
            prepared.append(row)
            continue
        try:
            account = await _resolve_account(session, user.id, row, payload.default_account_id)
            category = await _resolve_category(session, user.id, row, payload.default_category_id)
            key = _idempotency_key(user.id, account, category, row)
            duplicate = key in seen_keys or bool(
                await session.scalar(
                    select(Transaction.id).where(
                        Transaction.user_id == user.id,
                        Transaction.idempotency_key == key,
                    )
                )
            )
            seen_keys.add(key)
            entry = {
                **row,
                "account_id": account.id,
                "category_id": category.id if category else None,
                "currency": account.currency,
                "idempotency_key": key,
                "status": "duplicate" if duplicate else "valid",
            }
            duplicate_count += int(bool(duplicate))
            valid_count += int(not duplicate)
            prepared.append(entry)
        except ValueError as exc:
            prepared.append({"line": row["line"], "error": str(exc), "status": "invalid"})
    return prepared, valid_count, duplicate_count


@router.post("/transactions/preview")
async def preview_transactions(
    payload: ImportRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    rows, valid_count, duplicate_count = await _prepare(payload, session, user)
    invalid = [row for row in rows if row.get("error")]
    return {
        "total": len(rows),
        "valid": valid_count,
        "duplicates": duplicate_count,
        "invalid": len(invalid),
        "rows": [
            {
                "line": row["line"],
                "status": row.get("status", "invalid"),
                "description": row.get("description", ""),
                "amount": str(row.get("amount", "")),
                "currency": row.get("currency", ""),
                "error": row.get("error"),
            }
            for row in rows
        ],
    }


@router.post("/transactions/import", status_code=status.HTTP_201_CREATED)
async def import_transactions(
    payload: ConfirmedImportRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if not payload.confirmed:
        raise HTTPException(409, "A importação exige confirmação explícita.")
    rows, valid_count, duplicate_count = await _prepare(payload, session, user)
    invalid = [row for row in rows if row.get("error")]
    if invalid:
        raise HTTPException(
            422,
            detail={
                "message": "Importação cancelada: corrija todas as linhas inválidas.",
                "invalid_rows": [
                    {"line": row["line"], "error": row["error"]} for row in invalid
                ],
            },
        )
    for row in rows:
        if row["status"] != "valid":
            continue
        session.add(
            Transaction(
                user_id=user.id,
                account_id=row["account_id"],
                category_id=row["category_id"],
                transaction_type=row["transaction_type"],
                amount=row["amount"],
                currency=row["currency"],
                description=row["description"],
                occurred_at=row["occurred_at"],
                idempotency_key=row["idempotency_key"],
            )
        )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409, "Conflito de idempotência; atualize a prévia e tente novamente."
        ) from None
    return {
        "created": valid_count,
        "duplicates_skipped": duplicate_count,
        "total": len(rows),
    }


@router.get("/transactions/export")
async def export_transactions(
    format: Literal["csv", "json", "xlsx", "qif", "pdf"] = "csv",
    account_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if format == "qif" and account_id is None:
        raise HTTPException(422, "A exportação QIF exige selecionar uma conta.")
    statement = (
        select(Transaction, Account.name, Category.name)
        .join(Account, Account.id == Transaction.account_id)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user.id, Account.user_id == user.id)
        .order_by(Transaction.occurred_at, Transaction.created_at)
    )
    if account_id is not None:
        owned_account = await session.scalar(
            select(Account.id).where(Account.id == account_id, Account.user_id == user.id)
        )
        if owned_account is None:
            raise HTTPException(404, "Conta não encontrada.")
        statement = statement.where(Transaction.account_id == account_id)
    result = await session.execute(statement)
    records = [
        {
            "id": str(row.id),
            "account_id": str(row.account_id),
            "account_name": account_name,
            "category_id": str(row.category_id) if row.category_id else "",
            "category_name": category_name or "",
            "transaction_type": row.transaction_type,
            "amount": str(row.amount),
            "currency": row.currency,
            "description": row.description,
            "occurred_at": row.occurred_at.isoformat(),
        }
        for row, account_name, category_name in result.all()
    ]
    if format == "qif":
        account = await session.scalar(
            select(Account).where(Account.id == account_id, Account.user_id == user.id)
        )
        output = ["!Type:CCard" if account.account_type == "credit" else "!Type:Cash" if account.account_type == "cash" else "!Type:Bank"]
        for record in records:
            parsed_date = datetime.fromisoformat(record["occurred_at"])\n            occurred = (\n                parsed_date.replace(tzinfo=UTC) if parsed_date.tzinfo is None else parsed_date\n            ).astimezone(ZoneInfo(user.timezone))
            amount = Decimal(record["amount"])
            signed_amount = -amount if record["transaction_type"] == "expense" else amount
            output.extend([
                f"D{occurred.month:02d}/{occurred.day:02d}'{occurred.year % 100:02d}",
                f"T{signed_amount:.2f}",
                "P" + record["description"].replace(chr(13), " ").replace(chr(10), " "),
            ])
            if record["category_name"]:
                output.append("L" + record["category_name"].replace(chr(13), " ").replace(chr(10), " "))
            output.append("^")
        content = chr(10).join(output) + chr(10)
        return Response(
            content=content,
            media_type="application/x-qif; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="sfi-{account.id}-transactions.qif"'
                )
            },
        )
    if format == "pdf":
        output = io.BytesIO()
        document = SimpleDocTemplate(
            output, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm,
            topMargin=12 * mm, bottomMargin=12 * mm,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph("SFI — Relatório de movimentações", styles["Title"]),
            Paragraph(
                f"Registros: {len(records)}",
                styles["Normal"],
            ),
            Spacer(1, 6 * mm),
        ]
        table_rows = [[
            "Data", "Conta", "Tipo", "Descrição", "Categoria", "Valor", "Moeda"
        ]]
        for record in records:
            occurred = datetime.fromisoformat(record["occurred_at"])
            description = Paragraph(escape(record["description"].encode("cp1252", errors="replace").decode("cp1252")), styles["BodyText"])
            table_rows.append([
                occurred.strftime("%d/%m/%Y"), Paragraph(escape(record["account_name"].encode("cp1252", errors="replace").decode("cp1252")), styles["BodyText"]),
                "Despesa" if record["transaction_type"] == "expense" else "Receita",
                description, Paragraph(escape(record["category_name"].encode("cp1252", errors="replace").decode("cp1252")), styles["BodyText"]),
                record["amount"], record["currency"],
            ])
        table = Table(
            table_rows, repeatRows=1,
            colWidths=[22 * mm, 32 * mm, 20 * mm, 78 * mm, 30 * mm, 25 * mm, 16 * mm],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263445")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F9")]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        document.build(story)
        return Response(
            content=output.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="sfi-transactions.pdf"'},
        )
    if format == "json":
        return Response(
            content=json.dumps(records, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="sfi-transactions.json"'},
        )
    if format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Movimentações"
        fields = [
            "id", "account_id", "category_id", "transaction_type", "amount",
            "currency", "description", "occurred_at",
        ]
        sheet.append(fields)
        for record in records:
            sheet.append([record[field] for field in fields])
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value, str):
                    if cell.value.startswith(("=", "+", "-", "@", "\t", "\r")):
                        cell.value = "'" + cell.value
                    cell.data_type = "s"
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        widths = {"A": 38, "B": 38, "C": 38, "D": 18, "E": 20, "F": 12, "G": 42, "H": 30}
        for column, width in widths.items():
            sheet.column_dimensions[column].width = width
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="sfi-transactions.xlsx"'},
        )
    buffer = io.StringIO(newline="")
    fields = [
        "id", "account_id", "category_id", "transaction_type", "amount",
        "currency", "description", "occurred_at",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for record in records:
        safe_record = dict(record)
        for field in fields:
            value = safe_record[field]
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                safe_record[field] = "'" + value
        writer.writerow(safe_record)
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sfi-transactions.csv"'},
    )
