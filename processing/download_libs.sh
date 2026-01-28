#!/bin/bash
mkdir -p lib
cd lib

echo "Downloading Flink & Kafka JARs..."

# Flink Kafka Connector (Decoupled version for Flink 1.18)
curl -L -O https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.1-1.18/flink-sql-connector-kafka-3.0.1-1.18.jar

# Flink Avro & Confluent Registry
curl -L -O https://repo1.maven.org/maven2/org/apache/flink/flink-avro-confluent-registry/1.18.0/flink-avro-confluent-registry-1.18.0.jar
curl -L -O https://repo1.maven.org/maven2/org/apache/flink/flink-avro/1.18.0/flink-avro-1.18.0.jar
curl -L -O https://repo1.maven.org/maven2/org/apache/avro/avro/1.11.3/avro-1.11.3.jar

# Jackson Dependencies (Required for Avro/Schema Registry)
curl -L -O https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.14.2/jackson-databind-2.14.2.jar
curl -L -O https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.14.2/jackson-core-2.14.2.jar
curl -L -O https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.14.2/jackson-annotations-2.14.2.jar

# Confluent Schema Registry Client & Common Utils
curl -L -O https://packages.confluent.io/maven/io/confluent/kafka-schema-registry-client/7.5.0/kafka-schema-registry-client-7.5.0.jar
curl -L -O https://packages.confluent.io/maven/io/confluent/common-config/7.5.0/common-config-7.5.0.jar
curl -L -O https://packages.confluent.io/maven/io/confluent/common-utils/7.5.0/common-utils-7.5.0.jar

# Transitive Dependencies (Kafka Clients, Guava)
curl -L -O https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar
curl -L -O https://repo1.maven.org/maven2/com/google/guava/guava/32.0.1-jre/guava-32.0.1-jre.jar

echo "All JARs downloaded to processing/lib/"
