"""
DAG: Bronze Layer - iWMS Inventory Movement Ingestion

Consumes events from Kafka topic `logisense.iwms.inventory.movement`
and writes raw events as Iceberg Parquet to MinIO bronze layer.

Schedule: Every 2 minutes
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "logisense-data",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

KAFKA_TOPIC = "logisense.iwms.inventory.movement"
ICEBERG_TABLE = "bronze.iwms_inventory_movements"
MINIO_BUCKET = "logisense-bronze"
MINIO_PATH = "iwms/inventory_movements"


def consume_and_write_to_iceberg(**context):
    """
    Consume messages from Kafka and write to Iceberg table.

    Writes raw events as Parquet files partitioned by date(performed_at).
    """
    import json
    import os
    from datetime import datetime

    # Get config from environment or params
    kafka_servers = os.environ.get(
        "KAFKA_BOOTSTRAP_SERVERS",
        context["params"].get("kafka_bootstrap_servers", "kafka:29092"),
    )

    try:
        from confluent_kafka import Consumer
    except ImportError:
        # Fallback message if confluent-kafka not installed
        print("confluent-kafka not installed, skipping Kafka consumption")
        context["ti"].xcom_push(key="records_ingested", value=0)
        context["ti"].xcom_push(key="status", value="skipped_no_kafka_client")
        return

    try:
        import pyarrow as pa
        from pyiceberg.catalog import load_catalog
    except ImportError:
        print("pyiceberg/pyarrow not installed, skipping Iceberg write")
        context["ti"].xcom_push(key="records_ingested", value=0)
        context["ti"].xcom_push(key="status", value="skipped_no_iceberg_client")
        return

    # Kafka consumer config
    consumer_config = {
        "bootstrap.servers": kafka_servers,
        "group.id": "uoih-bronze-iwms-ingest",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }

    try:
        consumer = Consumer(consumer_config)
        consumer.subscribe([KAFKA_TOPIC])
    except Exception as e:
        print(f"Failed to connect to Kafka: {e}")
        context["ti"].xcom_push(key="records_ingested", value=0)
        context["ti"].xcom_push(key="status", value="kafka_connection_failed")
        return

    # Load Iceberg catalog
    try:
        catalog = load_catalog(
            "logisense",
            **{
                "type": "rest",
                "uri": os.environ.get(
                    "ICEBERG_CATALOG_URI",
                    context["params"].get(
                        "iceberg_catalog_uri", "http://iceberg-rest:8181"
                    ),
                ),
                "s3.endpoint": os.environ.get(
                    "MINIO_ENDPOINT",
                    context["params"].get("minio_endpoint", "http://minio:9000"),
                ),
                "s3.access-key-id": os.environ.get(
                    "MINIO_ACCESS_KEY",
                    context["params"].get("minio_access_key", "minioadmin"),
                ),
                "s3.secret-access-key": os.environ.get(
                    "MINIO_SECRET_KEY",
                    context["params"].get("minio_secret_key", "minioadmin123"),
                ),
                "s3.path-style-access": "true",
            },
        )
    except Exception as e:
        print(f"Failed to connect to Iceberg catalog: {e}")
        consumer.close()
        context["ti"].xcom_push(key="records_ingested", value=0)
        context["ti"].xcom_push(key="status", value="iceberg_connection_failed")
        return

    # Get or create table
    try:
        table = catalog.load_table(ICEBERG_TABLE)
    except Exception:
        # Create table if not exists
        schema = pa.schema(
            [
                ("event_id", pa.string()),
                ("facility_id", pa.string()),
                ("location_id", pa.string()),
                ("sku_id", pa.string()),
                ("lot_number", pa.string()),
                ("movement_type", pa.string()),
                ("quantity", pa.int64()),
                ("performed_at", pa.timestamp("us", tz="UTC")),
                ("performed_by", pa.string()),
                ("reference_id", pa.string()),
                ("raw_payload", pa.string()),
                ("ingested_at", pa.timestamp("us", tz="UTC")),
                ("partition_date", pa.date32()),
            ]
        )
        try:
            table = catalog.create_table(
                ICEBERG_TABLE,
                schema=schema,
                partition_spec=[("partition_date", "identity")],
            )
        except Exception as e:
            print(f"Failed to create Iceberg table: {e}")
            consumer.close()
            context["ti"].xcom_push(key="records_ingested", value=0)
            context["ti"].xcom_push(key="status", value="table_creation_failed")
            return

    # Consume messages in batches
    messages = []
    batch_size = 1000
    poll_timeout = 1.0
    max_empty_polls = 5
    empty_polls = 0

    try:
        while len(messages) < batch_size and empty_polls < max_empty_polls:
            msg = consumer.poll(poll_timeout)

            if msg is None:
                empty_polls += 1
                continue

            if msg.error():
                print(f"Kafka error: {msg.error()}")
                continue

            empty_polls = 0

            try:
                payload = json.loads(msg.value().decode("utf-8"))
            except json.JSONDecodeError as e:
                print(f"Failed to parse message: {e}")
                continue

            # Extract partition date from performed_at
            performed_at_str = payload.get("performed_at")
            if performed_at_str:
                try:
                    performed_at = datetime.fromisoformat(
                        performed_at_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    performed_at = datetime.utcnow()
            else:
                performed_at = datetime.utcnow()

            partition_date = performed_at.date()

            messages.append(
                {
                    "event_id": payload.get(
                        "event_id", msg.key().decode("utf-8") if msg.key() else ""
                    ),
                    "facility_id": payload.get("facility_id"),
                    "location_id": payload.get("location_id"),
                    "sku_id": payload.get("sku_id"),
                    "lot_number": payload.get("lot_number"),
                    "movement_type": payload.get("movement_type"),
                    "quantity": payload.get("quantity", 0),
                    "performed_at": performed_at,
                    "performed_by": payload.get("performed_by"),
                    "reference_id": payload.get("reference_id"),
                    "raw_payload": json.dumps(payload),
                    "ingested_at": datetime.utcnow(),
                    "partition_date": partition_date,
                }
            )

        if messages:
            # Convert to Arrow table and append to Iceberg
            arrow_table = pa.Table.from_pylist(messages)
            table.append(arrow_table)

            # Commit Kafka offsets
            consumer.commit()

            print(f"Ingested {len(messages)} messages to {ICEBERG_TABLE}")
            context["ti"].xcom_push(key="records_ingested", value=len(messages))
            context["ti"].xcom_push(key="status", value="success")
        else:
            print("No new messages to ingest")
            context["ti"].xcom_push(key="records_ingested", value=0)
            context["ti"].xcom_push(key="status", value="no_messages")

    except Exception as e:
        print(f"Error during ingestion: {e}")
        context["ti"].xcom_push(key="records_ingested", value=0)
        context["ti"].xcom_push(key="status", value=f"error: {e!s}")

    finally:
        consumer.close()


with DAG(
    dag_id="bronze_iwms_inventory_ingest",
    default_args=default_args,
    description="Ingest iWMS inventory movements from Kafka to Bronze Iceberg",
    schedule_interval=timedelta(minutes=2),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["bronze", "iwms", "kafka", "iceberg"],
    params={
        "kafka_bootstrap_servers": "kafka:29092",
        "iceberg_catalog_uri": "http://iceberg-rest:8181",
        "minio_endpoint": "http://minio:9000",
        "minio_access_key": "minioadmin",
        "minio_secret_key": "minioadmin123",  # pragma: allowlist secret
    },
) as dag:
    # Task: Consume from Kafka and write to Iceberg
    ingest_to_iceberg = PythonOperator(
        task_id="ingest_to_iceberg",
        python_callable=consume_and_write_to_iceberg,
        provide_context=True,
    )
