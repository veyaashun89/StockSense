from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.orm_models import Product
from backend.repositories.base_repository import BaseRepository

class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: Session):
        super().__init__(Product, session)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        stmt = select(Product).where(Product.sku == sku)
        return self.session.execute(stmt).scalar_one_or_none()

    def find_by_sku_flexible(self, sku_or_tag: str) -> Optional[Product]:
        core = sku_or_tag.replace("SKU-", "").split("-")[0]
        stmt = select(Product).where(
            (Product.sku == sku_or_tag) |
            (Product.sku.like(f"%{sku_or_tag}%")) |
            (Product.sku.like(f"%{core}%"))
        ).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_products(self, active_only: bool = True) -> List[Product]:
        stmt = select(Product)
        if active_only:
            stmt = stmt.where(Product.is_active == 1)
        return list(self.session.execute(stmt).scalars().all())
