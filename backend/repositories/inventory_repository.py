from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.orm_models import Inventory, InventoryMovement, InventoryBatch, Product
from backend.repositories.base_repository import BaseRepository

class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, session: Session):
        super().__init__(Inventory, session)

    def get_by_product_and_owner(self, product_id: int, owner_id: int = 1) -> Optional[Inventory]:
        stmt = select(Inventory).where(Inventory.product_id == product_id, Inventory.owner_id == owner_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create(self, product_id: int, owner_id: int = 1, initial_stock: int = 0) -> Inventory:
        inv = self.get_by_product_and_owner(product_id, owner_id)
        if not inv:
            inv = Inventory(product_id=product_id, owner_id=owner_id, on_hand=initial_stock)
            self.session.add(inv)
            self.session.flush()
        return inv

    def deduct_stock(
        self,
        product_id: int,
        owner_id: int,
        qty: int,
        reason: str = "SALE",
        reference: Optional[str] = None
    ) -> Tuple[int, InventoryMovement]:
        """
        Deducts stock atomically.
        Raises ValueError if stock would become negative.
        Returns (new_balance, movement_record).
        """
        if qty <= 0:
            raise ValueError(f"Deduction quantity must be positive, got {qty}")

        inv = self.get_or_create(product_id, owner_id)
        if inv.on_hand < qty:
            raise ValueError(
                f"Insufficient stock for product ID {product_id}. Available: {inv.on_hand}, Requested: {qty}"
            )

        new_balance = inv.on_hand - qty
        inv.on_hand = new_balance

        # Update cached counter on product
        prod = self.session.get(Product, product_id)
        if prod:
            prod.current_stock = new_balance

        movement = InventoryMovement(
            product_id=product_id,
            owner_id=owner_id,
            delta=-qty,
            balance_after=new_balance,
            reason=reason,
            reference=reference
        )
        self.session.add(movement)
        self.session.flush()

        # Check low_stock notification trigger
        if prod:
            try:
                from backend.services.notification_rules import evaluate_low_stock
                from backend.workers.notification_worker import enqueue_notification
                effective_reorder = inv.reorder_level if (inv and inv.reorder_level is not None) else (prod.min_order_qty or 10)
                notif_spec = evaluate_low_stock(
                    product_name=prod.name,
                    sku=prod.sku,
                    on_hand=new_balance,
                    reorder_level=effective_reorder,
                    location_name="Store-1",
                    product_id=prod.id
                )
                if notif_spec:
                    enqueue_notification(
                        rule=notif_spec["rule"],
                        title=notif_spec["title"],
                        message=notif_spec["message"],
                        priority=notif_spec["priority"],
                        tags=notif_spec["tags"],
                        event_ref=f"stock_deduct_{prod.id}_{new_balance}",
                        dedup_key=notif_spec["dedup_key"],
                        owner_id=owner_id,
                        db_session=self.session
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"deduct_stock notification error: {e}", exc_info=True)

        return new_balance, movement

    def add_stock(
        self,
        product_id: int,
        owner_id: int,
        qty: int,
        reason: str = "RESTOCK",
        reference: Optional[str] = None,
        batch_id: Optional[str] = None,
        expiry_date: Optional[str] = None
    ) -> Tuple[int, InventoryMovement]:
        """
        Increments stock atomically and logs movement audit.
        """
        if qty <= 0:
            raise ValueError(f"Stock addition quantity must be positive, got {qty}")

        inv = self.get_or_create(product_id, owner_id)
        new_balance = inv.on_hand + qty
        inv.on_hand = new_balance

        prod = self.session.get(Product, product_id)
        if prod:
            prod.current_stock = new_balance

        movement = InventoryMovement(
            product_id=product_id,
            owner_id=owner_id,
            delta=qty,
            balance_after=new_balance,
            reason=reason,
            reference=reference
        )
        self.session.add(movement)

        if batch_id or expiry_date:
            batch = InventoryBatch(
                product_id=product_id,
                owner_id=owner_id,
                batch_id=batch_id or f"BATCH-{reference or 'NEW'}",
                qty=qty,
                expiry_date=expiry_date
            )
            self.session.add(batch)

        self.session.flush()
        return new_balance, movement
