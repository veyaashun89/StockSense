import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.orm_models import Payment
from backend.repositories.base_repository import BaseRepository

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: Session):
        super().__init__(Payment, session)

    def get_by_provider_ref(self, provider_ref: str) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.provider_ref == provider_ref)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_payment(
        self,
        provider_ref: str,
        amount_paise: int,
        idempotency_key: str,
        currency: str = "INR",
        payment_method: str = "UPI_QR"
    ) -> Payment:
        payment = Payment(
            provider_ref=provider_ref,
            amount_paise=amount_paise,
            currency=currency,
            status="pending",
            idempotency_key=idempotency_key,
            payment_method=payment_method
        )
        self.session.add(payment)
        self.session.flush()
        return payment

    def mark_verified(self, payment: Payment, sale_id: Optional[int], utr_number: str) -> Payment:
        payment.status = "verified"
        payment.sale_id = sale_id
        payment.utr_number = utr_number
        payment.verified_at = datetime.datetime.utcnow()
        self.session.flush()
        return payment
