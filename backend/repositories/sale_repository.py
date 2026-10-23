import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.orm_models import Sale, SaleItem
from backend.repositories.base_repository import BaseRepository

class SaleRepository(BaseRepository[Sale]):
    def __init__(self, session: Session):
        super().__init__(Sale, session)

    def get_by_utr(self, utr: str) -> Optional[Sale]:
        stmt = select(Sale).where(Sale.utr == utr)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_sale_with_items(
        self,
        owner_id: int,
        utr: str,
        subtotal_paise: int,
        tax_paise: int,
        total_paise: int,
        items: List[Dict[str, Any]],
        source: str = "pos_scanner"
    ) -> Sale:
        first_item = items[0] if items else {}
        sale = Sale(
            owner_id=owner_id,
            product_id=first_item.get("product_id"),
            sku=first_item.get("sku"),
            quantity_sold=first_item.get("quantity", 1),
            utr=utr,
            subtotal_paise=subtotal_paise,
            tax_paise=tax_paise,
            total_paise=total_paise,
            payment_status="PAID",
            source=source,
            sale_date=datetime.date.today().isoformat()
        )
        self.session.add(sale)
        self.session.flush()

        for it in items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=it["product_id"],
                qty=it["quantity"],
                unit_price_paise=it["unit_price_paise"],
                line_total_paise=it["line_total_paise"]
            )
            self.session.add(sale_item)

        self.session.flush()
        return sale
