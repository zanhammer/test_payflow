from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.domain.exceptions import IdempotencyConflict
from tests.factories import make_payment, make_test_app


class TestCreatePaymentEndpoint:
    def test_returns_201_for_new_payment(self) -> None:
        payment = make_payment()
        use_case = AsyncMock()
        use_case.execute.return_value = (payment, True)

        client = TestClient(make_test_app(create_use_case=use_case))
        response = client.post(
            "/api/v1/payments",
            json={
                "amount": "100.00",
                "currency": "USD",
                "description": "Test",
                "webhook_url": "https://example.com/hook",
            },
            headers={
                "X-API-Key": "test-key",
                "Idempotency-Key": "key-123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "payment_id" in data
        assert data["status"] == "pending"

    def test_returns_200_for_duplicate_request(self) -> None:
        payment = make_payment()
        use_case = AsyncMock()
        use_case.execute.return_value = (payment, False)

        client = TestClient(make_test_app(create_use_case=use_case))
        response = client.post(
            "/api/v1/payments",
            json={
                "amount": "100.00",
                "currency": "USD",
                "description": "Test",
                "webhook_url": "https://example.com/hook",
            },
            headers={
                "X-API-Key": "test-key",
                "Idempotency-Key": "key-123",
            },
        )

        assert response.status_code == 200
        assert response.json()["payment_id"] == str(payment.id)

    def test_returns_409_on_idempotency_conflict(self) -> None:
        use_case = AsyncMock()
        use_case.execute.side_effect = IdempotencyConflict(
            "Idempotency key already used with a different request body"
        )

        client = TestClient(make_test_app(create_use_case=use_case))
        response = client.post(
            "/api/v1/payments",
            json={
                "amount": "100.00",
                "currency": "USD",
                "description": "Test",
                "webhook_url": "https://example.com/hook",
            },
            headers={
                "X-API-Key": "test-key",
                "Idempotency-Key": "key-123",
            },
        )

        assert response.status_code == 409

    def test_returns_422_when_amount_missing(self) -> None:
        client = TestClient(make_test_app())
        response = client.post(
            "/api/v1/payments",
            json={
                "currency": "USD",
                "description": "Test",
                "webhook_url": "https://example.com/hook",
            },
            headers={"X-API-Key": "test-key", "Idempotency-Key": "key-123"},
        )
        assert response.status_code == 422

    def test_returns_422_when_idempotency_key_header_missing(self) -> None:
        client = TestClient(make_test_app())
        response = client.post(
            "/api/v1/payments",
            json={
                "amount": "100",
                "currency": "USD",
                "description": "Test",
                "webhook_url": "https://a.com",
            },
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422


class TestGetPaymentEndpoint:
    def test_returns_payment_detail(self) -> None:
        payment = make_payment()
        use_case = AsyncMock()
        use_case.execute.return_value = payment

        client = TestClient(make_test_app(get_use_case=use_case))
        response = client.get(
            f"/api/v1/payments/{payment.id}",
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == str(payment.id)
        assert data["status"] == "pending"

    def test_passes_correct_payment_id_to_use_case(self) -> None:
        payment = make_payment()
        use_case = AsyncMock()
        use_case.execute.return_value = payment

        client = TestClient(make_test_app(get_use_case=use_case))
        client.get(
            f"/api/v1/payments/{payment.id}",
            headers={"X-API-Key": "test-key"},
        )

        call_arg = use_case.execute.call_args[0][0]
        assert call_arg == payment.id


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
