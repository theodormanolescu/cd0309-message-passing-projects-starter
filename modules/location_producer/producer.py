import logging
import time
import os
from concurrent import futures

import grpc
import location_pb2
import location_pb2_grpc
import json
from kafka import KafkaProducer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("udaconnect-location-producer")


kafka_server = os.environ["KAFKA_SERVER"]
kafka_topic = os.environ["KAFKA_TOPIC"]
# wait for kafka to start
time.sleep(10)
max_retries = 3
retry_delay = 7

for attempt in range(max_retries):
    try:
        producer = KafkaProducer(
            bootstrap_servers=kafka_server,
            request_timeout_ms=120000,  # Increase the request timeout to 120 seconds
            metadata_max_age_ms=120000  # Increase the metadata max age to 120 seconds
        )
        break
    except Exception as e:
        logger.error(f"Attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
        else:
            logger.error("All attempts to connect to Kafka failed.")
            raise

class LocationServicer(location_pb2_grpc.LocationServiceServicer):
    def Create(self, request, context):
        request_value = {
            "person_id": request.person_id,
            "latitude": request.latitude,
            "longitude": request.longitude,
        }
        encoded_message = json.dumps(request_value).encode('utf-8')
        self.publishMessage(encoded_message)

        return location_pb2.LocationMessage(**request_value)

    def publishMessage(self, encoded_message):
        logger.info(f"Producing message: {encoded_message}")
        try:
            producer.send(kafka_topic, encoded_message)
        except Exception as e:
            logger.error(f"Error producing message: {e}")
            raise

# Initialize gRPC server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
location_pb2_grpc.add_LocationServiceServicer_to_server(LocationServicer(), server)

print("gRPC Server listening on port 5005...")
server.add_insecure_port("[::]:5005")
server.start()

# Keep thread alive
server.wait_for_termination()



