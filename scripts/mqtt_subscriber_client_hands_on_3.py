from datetime import datetime
import uuid
import paho.mqtt.client as mqtt
import time

brokers=["iot.eclipse.org",
         "broker.hivemq.com",
         "test.mosquitto.org",
         "192.168.8.167",
         "139.162.222.115"]

broker=brokers[1]
port=1883

client = mqtt.Client("IoT_MB_4091_" + str(uuid.uuid4()), clean_session=True)

def on_log(client, userdata, level, buf):
        print("log: " + buf)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK")
    else:
        print("Bad connection Returned code=", rc)

def on_disconnect(client, userdata, flags, rc = 0):
        print("Disconnected result code " + str(rc))

def on_message(client,userdata,msg):
        topic = msg.topic
        m_decode = str(msg.payload.decode("utf-8", "ignore"))
        print("Received Time: ", datetime.now().strftime("%H:%M:%S"))
        print("Message Topic: ", topic)
        print("message received: ", m_decode)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_log = on_log
client.on_message = on_message

print("Connecting to broker ", broker)
client.connect(broker, port)

subscriber_topic = "iot/home_MB/sensor_4091"

client.loop_start()
client.subscribe(subscriber_topic, qos = 0)
time.sleep(10)
client.loop_stop()

client.disconnect()

print("End subscribe_client run script")