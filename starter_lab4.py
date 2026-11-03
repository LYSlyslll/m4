"""
starter_lab4.py — STARTER VERSION

Module 4 Lab: Error Handling, Reliability, and Resource Management

Complete the functions and classes below. The tests in test_lab4.py
should pass when your implementation is complete.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterable, Any


class OrderProcessingError(Exception):
    """Base exception for order processing failures."""


class ValidationError(OrderProcessingError):
    """Raised when an order is invalid."""


class InventoryError(OrderProcessingError):
    """Raised when inventory reservation fails."""


class PaymentError(OrderProcessingError):
    """Raised when payment processing fails."""


class TemporaryPaymentError(PaymentError):
    """Raised when payment failure may be temporary."""


def validate_order(order: dict) -> None:
    """
    Validate order structure and amount.

    Requirements:
    - must contain order_id, customer, amount
    - amount must be > 0
    - raise ValidationError when invalid
    """
    for field in ("order_id", "customer", "amount"):
        if field not in order:
            raise ValidationError(f"order missing required field: {field!r}")
    amount = order["amount"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValidationError("order amount must be a number")
    if amount <= 0:
        raise ValidationError("order amount must be greater than zero")


class InventoryManager:
    """
    Tracks reserved order IDs.
    """

    def __init__(self) -> None:
        self._reservations: set[str] = set()

    def reserve(self, order_id: str) -> None:
        if order_id in self._reservations:
            raise InventoryError(f"order {order_id!r} is already reserved")
        self._reservations.add(order_id)

    def release(self, order_id: str) -> None:
        self._reservations.discard(order_id)

    @property
    def active_reservations(self) -> int:
        return len(self._reservations)


class PaymentGateway:
    """
    Simulates payment outcomes.

    Outcomes:
    - success
    - temporary_failure
    - permanent_failure
    """

    def __init__(self, outcomes: Iterable[str]) -> None:
        self._outcomes = list(outcomes)

    def charge(self, amount: int | float) -> str:
        if not self._outcomes:
            raise RuntimeError("no payment outcomes remaining")
        outcome = self._outcomes.pop(0)
        if outcome == "success":
            return "APPROVED"
        if outcome == "temporary_failure":
            raise TemporaryPaymentError("payment temporarily failed")
        if outcome == "permanent_failure":
            raise PaymentError("payment permanently failed")
        raise RuntimeError(f"unknown payment outcome: {outcome!r}")


def retry_payment(func: Callable[[], Any], retries: int = 3) -> Any:
    """
    Retry only TemporaryPaymentError.

    Permanent PaymentError must not be retried.
    """
    last_error: TemporaryPaymentError | None = None
    for _ in range(retries):
        try:
            return func()
        except TemporaryPaymentError as exc:
            last_error = exc
    if last_error is None:
        raise RuntimeError("retries must be at least 1")
    raise last_error


class ProcessingSession:
    """
    Context manager for processing lifecycle logging.

    Event behavior:
    - normal: OPEN, CLOSE
    - exception: OPEN, ERROR, CLOSE
    """

    def __init__(self) -> None:
        self._events: list[str] = []

    def __enter__(self) -> "ProcessingSession":
        self._events.append("OPEN")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self._events.append("ERROR")
        self._events.append("CLOSE")
        return False

    @property
    def events(self) -> list[str]:
        return self._events


def process_order(
    order: dict,
    inventory_manager: InventoryManager,
    payment_gateway: PaymentGateway,
) -> str:
    """
    Process an order transactionally.

    Requirements:
    - validate order
    - reserve inventory
    - charge payment using retry_payment
    - release inventory on payment failure
    - use ProcessingSession
    - return COMPLETE on success
    """
    validate_order(order)
    with ProcessingSession():
        inventory_manager.reserve(order["order_id"])
        try:
            retry_payment(lambda: payment_gateway.charge(order["amount"]))
        except PaymentError as exc:
            inventory_manager.release(order["order_id"])
            raise PaymentError(
                f"payment failed for order {order['order_id']!r}"
            ) from exc
    return "COMPLETE"


def log_failure(logger: logging.Logger, exc: Exception) -> None:
    """
    Log exception with traceback visibility.
    """
    logger.error(
        "Order processing failed: %s",
        exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
