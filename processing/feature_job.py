import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import ProcessFunction
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
import redis

# Custom Redis Writer
class RedisWriter(ProcessFunction):
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.redis_client = None

    def open(self, runtime_context):
        # Initialize Redis connection in the worker
        self.redis_client = redis.Redis(host=self.host, port=self.port, decode_responses=True)

    def process_element(self, value, ctx):
        # Value is a Row: (user_id, cnt, w_end)
        user_id = value[0]
        cnt = value[1]
        
        # Logic: Set key "user:{id}:click_count"
        # In production, use HSET or proper feature store encoding
        key = f"user:{user_id}:click_count"
        try:
            self.redis_client.set(key, str(cnt))
            print(f"Sink: {key} -> {cnt}", flush=True)
        except Exception as e:
            print(f"Redis Error: {e}", flush=True)
            # In production, handle retry or failure


def main():
    # Setup DataStream Environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1) # Simpler for local testing

    # Add JARs - MUST be added before creating TableEnvironment
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
    print("Loading JARs:", jar_paths)
    env.add_jars(*jar_paths)

    # Create Table Environment
    t_env = StreamTableEnvironment.create(env)

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
            'avro-confluent.schema-registry.url' = 'http://localhost:8082'
        )
    """)

    # 2. Logic: Window Aggregation
    result_table = t_env.sql_query("""
        SELECT 
            user_id, 
            COUNT(*) as cnt,
            TUMBLE_END(event_time, INTERVAL '1' MINUTE) as w_end
        FROM user_interactions
        GROUP BY 
            user_id, 
            TUMBLE(event_time, INTERVAL '1' MINUTE)
    """)

    # 3. Convert to DataStream & Sink to Redis
    # Note: Requires 'redis' pip package installed in the python env running this
    ds = t_env.to_data_stream(result_table)
    # Use process to execute Python logic (Redis write)
    # We add print() as a final sink to complete the topology, 
    # though RedisWriter emits nothing so it prints nothing.
    ds.process(RedisWriter()).print()

    # 4. Execute
    print("Submitting Job...", flush=True)
    env.execute("Feature Pipeline (Kafka -> Redis)")

if __name__ == '__main__':
    main()
