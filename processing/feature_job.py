import os
import sys
from pyflink.table import EnvironmentSettings, TableEnvironment

def main():
    # Setup environment
    env_settings = EnvironmentSettings.in_streaming_mode()
    t_env = TableEnvironment.create(env_settings)

    # Add JARs
    current_dir = os.getcwd()
    jar_files = [
        f"file://{current_dir}/lib/flink-sql-connector-kafka-3.0.1-1.18.jar",
        f"file://{current_dir}/lib/flink-avro-confluent-registry-1.18.0.jar",
        f"file://{current_dir}/lib/flink-avro-1.18.0.jar"
    ]
    t_env.get_config().set("pipeline.jars", ";".join(jar_files))

    # 1. Define Source
    t_env.execute_sql("""
        CREATE TABLE user_interactions (
            user_id STRING,
            item_id STRING,
            action_type STRING,
            `timestamp` BIGINT,
            context STRING,
            event_time AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
            WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'user_interactions',
            'properties.bootstrap.servers' = 'localhost:9092',
            'properties.group.id' = 'feature_group',
            'scan.startup.mode' = 'earliest-offset',
            'format' = 'avro-confluent',
            'avro-confluent.schema-registry.url' = 'http://localhost:8081'
        )
    """)

    # 2. Define Sink (Printing to console for demo, representing Feature Store write)
    t_env.execute_sql("""
        CREATE TABLE feature_sink (
            user_id STRING,
            cnt BIGINT,
            w_end TIMESTAMP(3)
        ) WITH (
            'connector' = 'print'
        )
    """)

    # 3. Logic: Window Aggregation
    # "Calculate number of actions per user per minute"
    t_env.execute_sql("""
        INSERT INTO feature_sink
        SELECT 
            user_id, 
            COUNT(*) as cnt,
            TUMBLE_END(event_time, INTERVAL '1' MINUTE) as w_end
        FROM user_interactions
        GROUP BY 
            user_id, 
            TUMBLE(event_time, INTERVAL '1' MINUTE)
    """).wait()

if __name__ == '__main__':
    main()
