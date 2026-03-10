"""Async Kafka producer for iWMS events."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from aiokafka import AIOKafkaProducer

from ..config import Settings

logger = structlog.get_logger()

# Topic names
TOPIC_INVENTORY_MOVEMENT = "logisense.iwms.inventory.movement"
TOPIC_WAVE_RELEASED = "logisense.iwms.wave.released"


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and UUID."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class KafkaProducer:
    """Async Kafka producer for publishing iWMS events."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._producer: AIOKafkaProducer | None = None
        self._started = False

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._started:
            return

        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
                client_id=self.settings.KAFKA_CLIENT_ID,
                value_serializer=lambda v: json.dumps(v, cls=JSONEncoder).encode(
                    "utf-8"
                ),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()
            self._started = True
            logger.info(
                "kafka_producer_started",
                bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
            )
        except Exception as e:
            logger.error("kafka_producer_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer and self._started:
            await self._producer.stop()
            self._started = False
            logger.info("kafka_producer_stopped")

    async def _send(self, topic: str, key: str, value: dict[str, Any]) -> None:
        """Send a message to Kafka."""
        if not self._producer or not self._started:
            logger.warning("kafka_producer_not_started", topic=topic)
            return

        try:
            await self._producer.send_and_wait(topic, key=key, value=value)
            logger.debug("kafka_message_sent", topic=topic, key=key)
        except Exception as e:
            logger.error("kafka_send_failed", topic=topic, key=key, error=str(e))
            # Don't raise - Kafka failures shouldn't break the API

    async def publish_inventory_movement(
        self,
        movement_id: UUID,
        facility_id: str,
        movement_type: str,
        sku_id: UUID,
        quantity: int,
        from_location_id: UUID | None = None,
        to_location_id: UUID | None = None,
        lot_number: str | None = None,
        performed_by: str | None = None,
        performed_at: datetime | None = None,
    ) -> None:
        """Publish an inventory movement event."""
        event = {
            "event_type": "inventory.movement",
            "movement_id": movement_id,
            "facility_id": facility_id,
            "movement_type": movement_type,
            "sku_id": sku_id,
            "quantity": quantity,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "lot_number": lot_number,
            "performed_by": performed_by,
            "performed_at": performed_at or datetime.utcnow(),
        }
        await self._send(TOPIC_INVENTORY_MOVEMENT, str(facility_id), event)

    async def publish_wave_released(
        self,
        wave_id: UUID,
        wave_number: str,
        facility_id: str,
        total_orders: int,
        total_lines: int,
        total_units: int,
        task_count: int,
        released_at: datetime,
        released_by: str | None = None,
    ) -> None:
        """Publish a wave released event."""
        event = {
            "event_type": "wave.released",
            "wave_id": wave_id,
            "wave_number": wave_number,
            "facility_id": facility_id,
            "total_orders": total_orders,
            "total_lines": total_lines,
            "total_units": total_units,
            "task_count": task_count,
            "released_at": released_at,
            "released_by": released_by,
        }
        await self._send(TOPIC_WAVE_RELEASED, str(facility_id), event)


class MockKafkaProducer(KafkaProducer):
    """Mock Kafka producer for testing - does not connect to Kafka."""

    def __init__(self) -> None:
        self._started = True
        self._messages: list[dict[str, Any]] = []

    async def start(self) -> None:
        """No-op for mock."""
        pass

    async def stop(self) -> None:
        """No-op for mock."""
        pass

    async def _send(self, topic: str, key: str, value: dict[str, Any]) -> None:
        """Store message instead of sending to Kafka."""
        self._messages.append({"topic": topic, "key": key, "value": value})
        logger.debug("mock_kafka_message_stored", topic=topic, key=key)


# Global producer instance
_producer: KafkaProducer | None = None


async def init_kafka_producer(settings: Settings) -> KafkaProducer:
    """Initialize the global Kafka producer."""
    global _producer

    if settings.TEST_MODE:
        _producer = MockKafkaProducer()
        logger.info("mock_kafka_producer_initialized")
        return _producer

    _producer = KafkaProducer(settings)
    await _producer.start()
    return _producer


async def close_kafka_producer() -> None:
    """Close the global Kafka producer."""
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


def get_kafka_producer() -> KafkaProducer:
    """Get the global Kafka producer."""
    if _producer is None:
        raise RuntimeError("Kafka producer not initialized")
    return _producer
