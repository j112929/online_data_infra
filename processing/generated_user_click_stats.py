"""
Auto-generated Flink Job for FeatureView: user_click_stats
Generated at: 2026-01-28T03:27:32.700705

DO NOT EDIT MANUALLY - Regenerate using:
    python -m sdk.compiler --feature-view user_click_stats
"""
import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import ProcessFunction
from pyflink.table import StreamTableEnvironment
import redis


class RedisFeatureWriter(ProcessFunction):
    """Writes computed features to Redis."""
    
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.redis_client = None

    def open(self, runtime_context):
        self.redis_client = redis.Redis(
            host=self.host, 
            port=self.port, 
            decode_responses=True
        )

    def process_element(self, value, ctx):
        # Extract entity key
        entity_id = value[0]  # user_id
        
        # Feature: click_count_1m
        click_count_1m_value = value[1]
        key_click_count_1m = f"user:{entity_id}:click_count_1m"
        try:
            self.redis_client.set(key_click_count_1m, str(click_count_1m_value))
            print(f"Sink: {key_click_count_1m} -> {click_count_1m_value}", flush=True)
        except Exception as e:
            print(f"Redis Error (click_count_1m): {e}", flush=True)
        
        # Feature: view_count_1m
        view_count_1m_value = value[2]
        key_view_count_1m = f"user:{entity_id}:view_count_1m"
        try:
            self.redis_client.set(key_view_count_1m, str(view_count_1m_value))
            print(f"Sink: {key_view_count_1m} -> {view_count_1m_value}", flush=True)
        except Exception as e:
            print(f"Redis Error (view_count_1m): {e}", flush=True)
        


def main():
    # Setup DataStream Environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    # Add JARs
    current_dir = os.path.dirname(os.path.abspath(__file__))
    jar_paths = [
        f"file://{current_dir}/lib/flink-sql-connector-kafka-3.0.1-1.18.jar",
        f"file://{current_dir}/lib/flink-avro-confluent-registry-1.18.0.jar",
        f"file://{current_dir}/lib/flink-avro-1.18.0.jar",
        f"file://{current_dir}/lib/avro-1.11.3.jar",
        f"file://{current_dir}/lib/jackson-core-2.14.2.jar",
        f"file://{current_dir}/lib/jackson-databind-2.14.2.jar",
        f"file://{current_dir}/lib/jackson-annotations-2.14.2.jar",
        f"file://{current_dir}/lib/kafka-schema-registry-client-7.5.0.jar",
        f"file://{current_dir}/lib/common-config-7.5.0.jar",
        f"file://{current_dir}/lib/common-utils-7.5.0.jar",
        f"file://{current_dir}/lib/kafka-clients-3.4.0.jar",
        f"file://{current_dir}/lib/guava-32.0.1-jre.jar"
    ]
    env.add_jars(*jar_paths)

    # Create Table Environment
    t_env = StreamTableEnvironment.create(env)

    # Source DDL
    t_env.execute_sql("""
CREATE TABLE user_click_stats_source (
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
            'avro-confluent.schema-registry.url' = 'http://localhost:8082'
        )
    """)

    # Feature Aggregation Query
    result_table = t_env.sql_query("""
SELECT 
            user_id,
            COUNT(CASE WHEN action_type = 'click' THEN 1 ELSE NULL END) as click_count_1m,
            COUNT(CASE WHEN action_type = 'view' THEN 1 ELSE NULL END) as view_count_1m,
            TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end
        FROM user_click_stats_source
        GROUP BY 
            user_id, 
            TUMBLE(event_time, INTERVAL '1' MINUTE)
    """)

    # Convert to DataStream & Write to Redis
    ds = t_env.to_data_stream(result_table)
    ds.process(RedisFeatureWriter()).print()

    # Execute
    print(f"Starting job: user_click_stats")
    env.execute("user_click_stats")


if __name__ == '__main__':
    main()
