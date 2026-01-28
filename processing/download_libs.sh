#!/bin/bash
mkdir -p lib
cd lib

# Flink Kafka Connector (Decoupled version for Flink 1.18)
curl -L -O https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.1-1.18/flink-sql-connector-kafka-3.0.1-1.18.jar

# Flink Avro Confluent Registry
curl -L -O https://repo1.maven.org/maven2/org/apache/flink/flink-avro-confluent-registry/1.18.0/flink-avro-confluent-registry-1.18.0.jar
curl -L -O https://repo1.maven.org/maven2/org/apache/flink/flink-avro/1.18.0/flink-avro-1.18.0.jar

echo "Jars downloaded to processing/lib/"
