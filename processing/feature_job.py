import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import SinkFunction
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
import redis

# Custom Redis Sink
class RedisSink(SinkFunction):
    def __init__(self, host='localhost', port=6379):
        self.host = host
        self.port = port
        self.redis_client = None

    def open(self, runtime_context):
        # Initialize Redis connection in the worker
        self.redis_client = redis.Redis(host=self.host, port=self.port, decode_responses=True)

    def invoke(self, value, context):
        # Value is a Row: (user_id, cnt, w_end)
        user_id = value[0]
        cnt = value[1]
        
        # Logic: Set key "user:{id}:click_count"
        # In production, use HSET or proper feature store encoding
        key = f"user:{user_id}:click_count"
        self.redis_client.set(key, str(cnt))
        print(f"Sink: {key} -> {cnt}", flush=True)

def main():
    # Setup DataStream + Table Environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1) # Simpler for local testing
    t_env = StreamTableEnvironment.create(env)

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
    ds.add_sink(RedisSink(host='localhost', port=6379))

    # 4. Execute
    print("Submitting Job...", flush=True)
    env.execute("Feature Pipeline (Kafka -> Redis)")

if __name__ == '__main__':
    main()
