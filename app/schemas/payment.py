import uuid
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PaymentResponse(BaseModel):
    """Schema for simulated payment invoice and billing history."""
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    status: str
    transaction_ref: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

