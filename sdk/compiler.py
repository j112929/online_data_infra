"""
SDK Compiler: Generates Flink SQL from Python Feature Definitions

This compiler reads FeatureView definitions and transpiles them into:
1. Flink SQL DDL (Source table definition)
2. Flink SQL DML (Feature aggregation logic)
3. Complete PyFlink job file

Usage:
    python -m sdk.compiler --feature-view user_click_stats --output processing/generated_job.py
"""
import argparse
import os
import sys
from typing import List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.feature_definition import (
    FeatureView, Feature, Source, Sink, Window,
    AggregationType, WindowType, FEATURE_VIEWS
)


class FlinkSQLCompiler:
    """Compiles FeatureView definitions to Flink SQL."""
    
    def __init__(self, feature_view: FeatureView):
        self.fv = feature_view
    
    def generate_source_ddl(self) -> str:
        """Generate CREATE TABLE DDL for the source."""
        source = self.fv.source
        
        # Field definitions
        fields = []
        for field_name, field_type in source.fields.items():
            if field_name == source.timestamp_field:
                fields.append(f"            `{field_name}` {field_type}")
            else:
                fields.append(f"            {field_name} {field_type}")
        
        # Add computed event_time column and watermark
        fields.append(f"            event_time AS TO_TIMESTAMP_LTZ(`{source.timestamp_field}`, 3)")
        fields.append(f"            WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND")
        
        fields_str = ",\n".join(fields)
        
        ddl = f"""
        CREATE TABLE {self.fv.name}_source (
{fields_str}
        ) WITH (
            'connector' = 'kafka',
            'topic' = '{source.topic}',
            'properties.bootstrap.servers' = '{source.bootstrap_servers}',
            'properties.group.id' = '{source.group_id}',
            'scan.startup.mode' = 'earliest-offset',
            'format' = 'avro-confluent',
            'avro-confluent.schema-registry.url' = '{source.schema_registry_url}'
        )
        """
        return ddl.strip()
    
    def generate_feature_query(self) -> str:
        """Generate SELECT statement for feature aggregation."""
        window = self.fv.window
        entity_key = self.fv.entity_key
        
        # Build SELECT clause
        select_parts = [entity_key]
        
        for feature in self.fv.features:
            agg = feature.aggregation.value
            field = feature.source_field
            
            if feature.filter_condition:
                # Conditional aggregation using CASE WHEN
                expr = f"{agg}(CASE WHEN {feature.filter_condition} THEN 1 ELSE NULL END) as {feature.name}"
            else:
                if agg == "COUNT_DISTINCT":
                    expr = f"COUNT(DISTINCT {field}) as {feature.name}"
                else:
                    expr = f"{agg}({field}) as {feature.name}"
            
            select_parts.append(expr)
        
        # Window end timestamp
        if window.type == WindowType.TUMBLE:
            select_parts.append(f"TUMBLE_END(event_time, INTERVAL '{window.size_minutes}' MINUTE) as window_end")
            group_by = f"TUMBLE(event_time, INTERVAL '{window.size_minutes}' MINUTE)"
        elif window.type == WindowType.HOP:
            slide = window.slide_minutes or 1
            select_parts.append(f"HOP_END(event_time, INTERVAL '{slide}' MINUTE, INTERVAL '{window.size_minutes}' MINUTE) as window_end")
            group_by = f"HOP(event_time, INTERVAL '{slide}' MINUTE, INTERVAL '{window.size_minutes}' MINUTE)"
        else:
            raise ValueError(f"Unsupported window type: {window.type}")
        
        select_str = ",\n            ".join(select_parts)
        
        query = f"""
        SELECT 
            {select_str}
        FROM {self.fv.name}_source
        GROUP BY 
            {entity_key}, 
            {group_by}
        """
        return query.strip()
    
    def generate_full_job(self) -> str:
        """Generate a complete PyFlink job file."""
        source_ddl = self.generate_source_ddl()
        feature_query = self.generate_feature_query()
        
        # Generate feature sink logic (for RedisWriter)
        feature_names = [f.name for f in self.fv.features]
        sink_logic = self._generate_sink_logic(feature_names)
        
        job_code = f'''"""
Auto-generated Flink Job for FeatureView: {self.fv.name}
Generated at: {datetime.now().isoformat()}

DO NOT EDIT MANUALLY - Regenerate using:
    python -m sdk.compiler --feature-view {self.fv.name}
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
{sink_logic}


def main():
    # Setup DataStream Environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    # Add JARs
    current_dir = os.path.dirname(os.path.abspath(__file__))
    jar_paths = [
        f"file://{{current_dir}}/lib/flink-sql-connector-kafka-3.0.1-1.18.jar",
        f"file://{{current_dir}}/lib/flink-avro-confluent-registry-1.18.0.jar",
        f"file://{{current_dir}}/lib/flink-avro-1.18.0.jar",
        f"file://{{current_dir}}/lib/avro-1.11.3.jar",
        f"file://{{current_dir}}/lib/jackson-core-2.14.2.jar",
        f"file://{{current_dir}}/lib/jackson-databind-2.14.2.jar",
        f"file://{{current_dir}}/lib/jackson-annotations-2.14.2.jar",
        f"file://{{current_dir}}/lib/kafka-schema-registry-client-7.5.0.jar",
        f"file://{{current_dir}}/lib/common-config-7.5.0.jar",
        f"file://{{current_dir}}/lib/common-utils-7.5.0.jar",
        f"file://{{current_dir}}/lib/kafka-clients-3.4.0.jar",
        f"file://{{current_dir}}/lib/guava-32.0.1-jre.jar"
    ]
    env.add_jars(*jar_paths)

    # Create Table Environment
    t_env = StreamTableEnvironment.create(env)

    # Source DDL
    t_env.execute_sql("""
{source_ddl}
    """)

    # Feature Aggregation Query
    result_table = t_env.sql_query("""
{feature_query}
    """)

    # Convert to DataStream & Write to Redis
    ds = t_env.to_data_stream(result_table)
    ds.process(RedisFeatureWriter()).print()

    # Execute
    print(f"Starting job: {self.fv.name}")
    env.execute("{self.fv.name}")


if __name__ == '__main__':
    main()
'''
        return job_code
    
    def _generate_sink_logic(self, feature_names: List[str]) -> str:
        """Generate the Redis sink logic inside process_element."""
        entity_key = self.fv.entity_key
        
        lines = [
            f"        # Extract entity key",
            f"        entity_id = value[0]  # {entity_key}",
            f"        ",
        ]
        
        for idx, fname in enumerate(feature_names):
            lines.append(f"        # Feature: {fname}")
            lines.append(f"        {fname}_value = value[{idx + 1}]")
            lines.append(f"        key_{fname} = f\"user:{{entity_id}}:{fname}\"")
            lines.append(f"        try:")
            lines.append(f"            self.redis_client.set(key_{fname}, str({fname}_value))")
            lines.append(f"            print(f\"Sink: {{key_{fname}}} -> {{{fname}_value}}\", flush=True)")
            lines.append(f"        except Exception as e:")
            lines.append(f"            print(f\"Redis Error ({fname}): {{e}}\", flush=True)")
            lines.append(f"        ")
        
        return "\n".join(lines)


def compile_feature_view(feature_view_name: str, output_path: str = None) -> str:
    """
    Compile a FeatureView by name and optionally write to file.
    
    Args:
        feature_view_name: Name of the FeatureView to compile
        output_path: Optional path to write the generated job
        
    Returns:
        Generated Python code as string
    """
    # Find the feature view
    fv = None
    for view in FEATURE_VIEWS:
        if view.name == feature_view_name:
            fv = view
            break
    
    if fv is None:
        available = [v.name for v in FEATURE_VIEWS]
        raise ValueError(f"FeatureView '{feature_view_name}' not found. Available: {available}")
    
    # Compile
    compiler = FlinkSQLCompiler(fv)
    code = compiler.generate_full_job()
    
    # Write if path specified
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(code)
        print(f"Generated job written to: {output_path}")
    
    return code


def main():
    parser = argparse.ArgumentParser(description="SDK Compiler - Generate Flink SQL from Feature Definitions")
    parser.add_argument(
        "--feature-view", "-f",
        default=None,
        help="Name of the FeatureView to compile"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output path for generated job (default: stdout)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available FeatureViews"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("Available FeatureViews:")
        for fv in FEATURE_VIEWS:
            print(f"  - {fv.name}")
            for feat in fv.features:
                print(f"      • {feat.name}: {feat.description}")
        return
    
    if not args.feature_view:
        parser.error("--feature-view/-f is required when not using --list")
    
    try:
        code = compile_feature_view(args.feature_view, args.output)
        if not args.output:
            print(code)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
