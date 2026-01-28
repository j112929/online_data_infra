import time
import random
import json
from confluent_kafka import Producer
from confluent_kafka.serialization import StringSerializer, SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from faker import Faker

# Configuration
SCHEMA_REGISTRY_URL = "http://localhost:8081"
BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "user_interactions"

# Load Schema
with open("user_interaction.avsc", "r") as f:
    schema_str = f.read()

def delivery_report(err, msg):
    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
    else:
        print("User record {} successfully produced to {} [{}] at offset {}".format(
            msg.key(), msg.topic(), msg.partition(), msg.offset()))

def main():
    schema_registry_conf = {'url': SCHEMA_REGISTRY_URL}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    avro_serializer = AvroSerializer(schema_registry_client,
                                     schema_str)

    string_serializer = StringSerializer('utf_8')

    producer_conf = {'bootstrap.servers': BOOTSTRAP_SERVERS}
    producer = Producer(producer_conf)

    faker = Faker()

    print(f"Producing records to topic {TOPIC}. Press Ctrl-C to abort.")
    while True:
        # Generate data
        user_id = str(random.randint(1, 100))
        data = {
            "user_id": user_id,
            "item_id": str(random.randint(1000, 5000)),
            "action_type": random.choice(["click", "view", "purchase", "cart"]),
            "timestamp": int(time.time() * 1000),
            "context": faker.sentence()
        }

        producer.produce(topic=TOPIC,
                         key=string_serializer(user_id),
                         value=avro_serializer(data, SerializationContext(TOPIC, MessageField.VALUE)),
                         on_delivery=delivery_report)
        
        # Flush periodically to optimize
        producer.poll(0)
        time.sleep(0.5)

    producer.flush()

if __name__ == '__main__':
    main()
