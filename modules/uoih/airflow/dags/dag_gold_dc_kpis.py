"""
DAG: Gold Layer - DC Daily KPIs

Runs dbt model to compute daily KPIs per facility.
Creates CRITICAL alert on failure.

Schedule: Every hour
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "logisense-data",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

DBT_PROJECT_DIR = "/opt/airflow/dbt/uoih"
DBT_PROFILES_DIR = "/opt/airflow/dbt/profiles"
UOIH_API_URL = "http://uoih-api:8006"


def create_failure_alert(**context):
    """
    Create a CRITICAL alert in UOIH when dbt model fails.
    """

    import requests

    ti = context["ti"]
    dag_run = context["dag_run"]

    # Get error info from upstream task
    exception = context.get("exception")
    error_msg = str(exception) if exception else "Unknown error in dbt model execution"

    alert_payload = {
        "facility_id": "SYSTEM",  # System-wide alert
        "module_id": "uoih",
        "alert_type": "DATA_PIPELINE_FAILURE",
        "severity": "CRITICAL",
        "title": "Gold KPI Pipeline Failed",
        "body": f"The dc_daily_kpis dbt model failed to execute.\n\nDAG Run: {dag_run.run_id}\nError: {error_msg}",
        "metadata": {
            "dag_id": dag_run.dag_id,
            "run_id": dag_run.run_id,
            "execution_date": dag_run.execution_date.isoformat(),
            "error": error_msg,
        },
    }

    try:
        response = requests.post(
            f"{UOIH_API_URL}/v1/uoih/alerts",
            json=alert_payload,
            timeout=10,
        )
        response.raise_for_status()
        alert_id = response.json().get("id")
        print(f"Created CRITICAL alert: {alert_id}")
        ti.xcom_push(key="alert_id", value=alert_id)
    except Exception as e:
        print(f"Failed to create alert: {e}")
        # Don't fail the task - alert creation is best-effort
        raise


def log_success_metrics(**context):
    """
    Log success metrics after dbt model completes.
    """

    ti = context["ti"]
    dag_run = context["dag_run"]

    print(f"Gold KPI model completed successfully for run: {dag_run.run_id}")

    # Could push metrics to Prometheus pushgateway here
    # For now, just log success
    ti.xcom_push(key="status", value="success")


with DAG(
    dag_id="gold_dc_kpis",
    default_args=default_args,
    description="Compute daily DC KPIs using dbt",
    schedule_interval=timedelta(hours=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["gold", "kpis", "dbt", "iceberg"],
) as dag:
    # Task: Run dbt model
    run_dbt_model = BashOperator(
        task_id="run_dbt_dc_daily_kpis",
        bash_command=f"""
            cd {DBT_PROJECT_DIR} && \
            dbt run \
                --profiles-dir {DBT_PROFILES_DIR} \
                --select gold.dc_daily_kpis \
                --vars '{{"run_date": "{{{{ ds }}}}"}}' \
                --log-format json
        """,
        env={
            "DBT_PROFILES_DIR": DBT_PROFILES_DIR,
        },
    )

    # Task: Log success metrics
    log_success = PythonOperator(
        task_id="log_success_metrics",
        python_callable=log_success_metrics,
        provide_context=True,
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    # Task: Create failure alert (only runs on failure)
    create_alert = PythonOperator(
        task_id="create_failure_alert",
        python_callable=create_failure_alert,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    run_dbt_model >> [log_success, create_alert]
