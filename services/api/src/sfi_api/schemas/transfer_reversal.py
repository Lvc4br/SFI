import uuid
from datetime import datetime

from pydantic import BaseModel

from sfi_api.schemas.finance import TransactionResponse


class TransferReversalResponse(BaseModel):
    transfer_id: uuid.UUID
    reversal_id: uuid.UUID
    occurred_at: datetime
    reversal_transactions: list[TransactionResponse]
