import time
import os
import json
import logging
from kafka import KafkaConsumer
from psycopg2 import connect


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("udaconnect-location-consumer")

# wait for kafka to start
time.sleep(20)

try:
    DB_USERNAME = os.environ["DB_USERNAME"]
    DB_PASSWORD = os.environ["DB_PASSWORD"]
    DB_HOST = os.environ["DB_HOST"]
    DB_PORT = os.environ["DB_PORT"]
    DB_NAME = os.environ["DB_NAME"]
    logger.info('Connecting to the database')
    conn = connect(
        dbname=DB_NAME,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
except Exception as e:
    logger.error(f"Error connecting to the database: {e}")
    raise

KAFKA_SERVER = os.environ["KAFKA_SERVER"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]

# wait for kafka to start
time.sleep(15)
max_retries = 3
retry_delay = 7

for attempt in range(max_retries):
    try:
        consumer = KafkaConsumer(KAFKA_TOPIC, bootstrap_servers=[KAFKA_SERVER])
        for message in consumer:
            data = message.value.decode('utf-8')
            json_data = json.loads(data)
            person_id = int(json_data["person_id"])
            latitude = int(json_data["latitude"])
            longitude = int(json_data["longitude"])

            query = "insert into public.location (person_id, coordinate) values ({}, ST_Point({}, {}))".format(
                person_id, latitude, longitude)
            try:
                cursor = conn.cursor()
                cursor.execute(query)
                cursor.close()
                conn.close()
            except Exception as e:
                logger.error(f"Error inserting data into the database: {e}")
    except Exception as e:
        logger.error(f"Attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
        else:
            logger.error("All attempts to connect to Kafka failed.")
            raise