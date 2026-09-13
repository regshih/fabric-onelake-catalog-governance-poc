# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# PARAMETERS CELL ********************

workspace_id = ""
lakehouse_id = ""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from datetime import date

from pyspark.sql import Row

if not workspace_id or not lakehouse_id:
    raise ValueError("workspace_id and lakehouse_id are required run parameters")

base = f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}/Tables"

# All values are deterministic and synthetic. There are no real people, accounts, or contacts.
public_metrics = [
    Row(
        metric_id=f"METRIC-{index:03d}",
        business_domain="Retail Banking",
        reporting_date=date(2026, 1, 31),
        metric_name=name,
        metric_value=float(value),
        classification="Public",
    )
    for index, (name, value) in enumerate(
        [
            ("digital_adoption_percent", 81.4),
            ("service_availability_percent", 99.95),
            ("synthetic_accounts", 1000),
        ],
        start=1,
    )
]

restricted_metrics = [
    Row(
        customer_id=f"SYN-CUST-{index:05d}",
        region=region,
        segment=segment,
        annual_value=float(1000 + index * 37),
        contact_alias=f"synthetic.customer.{index:05d}@example.invalid",
        classification="Confidential-Synthetic",
    )
    for index, (region, segment) in enumerate(
        ((region, segment) for region in ("US", "CA", "GB") for segment in ("Retail", "SMB")),
        start=1,
    )
]

spark.createDataFrame(public_metrics).write.format("delta").mode("overwrite").save(
    f"{base}/public_metrics"
)
spark.createDataFrame(restricted_metrics).write.format("delta").mode("overwrite").save(
    f"{base}/restricted_customer_metrics"
)

print("Created two synthetic governance demo tables; row values are intentionally not displayed.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
