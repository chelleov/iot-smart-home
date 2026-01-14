import json
import uuid
import threading
import time
import paho.mqtt.client as mqtt

class MQTTDeviceController:
    def __init__(self, broker_address, port=1883):
        self.client = mqtt.Client()
        self.broker_address = broker_address
        self.port = port

        self._handlers = {}
        self._pending_requests = {}

        # ---- Device registry ----
        # device_id -> device_type
        self.devices = {}
        self._device_lock = threading.Lock()

        self.client.on_message = self._on_message
        self.client.on_connect = self._on_connect

    def connect(self):
        self.client.connect(self.broker_address, self.port)

    def _on_connect(self, client, userdata, flags, rc):
        print("Connected with result code", rc)
        for topic in self._handlers:
            client.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload_raw = msg.payload.decode()

        # ---- Device connection handling ----
        if topic == "sim-device-control/connections":
            payload = json.loads(payload_raw)
            device_id = payload.get("device_id")
            device_type = payload.get("device_type")
            status = payload.get("status")

            if not device_id or not status:
                return

            with self._device_lock:
                if status == "connected":
                    self.devices[device_id] = device_type
                elif status == "disconnected":
                    self.devices.pop(device_id, None)
            return

        # ---- Normal JSON messages (commands / responses) ----
        payload = json.loads(payload_raw)

        request_id = payload.get("id")
        if request_id in self._pending_requests:
            event, storage = self._pending_requests[request_id]
            storage["response"] = payload
            event.set()
            return

        handler = self._handlers.get(topic)
        if handler:
            handler(topic, payload)

    def subscribe(self, topic, handler=None, qos=1):
        if handler:
            self._handlers[topic] = handler
        self.client.subscribe(topic, qos=qos)

    def publish(self, topic, message, qos=1, retain=False):
        self.client.publish(topic, json.dumps(message), qos=qos, retain=retain)

    def send_command_and_wait(
        self,
        cmd_topic,
        reply_topic,
        command,
        parameter,
        timeout=5
    ):
        request_id = str(uuid.uuid4())
        event = threading.Event()
        response_holder = {}

        self._pending_requests[request_id] = (event, response_holder)

        # Ensure we are subscribed to the reply topic
        self.subscribe(reply_topic)

        command_payload = {
            "id": request_id,
            "command": command,
            "parameter": parameter,
        }

        self.publish(cmd_topic, command_payload)

        if not event.wait(timeout):
            del self._pending_requests[request_id]
            raise TimeoutError("No reply received")

        response = response_holder["response"]
        del self._pending_requests[request_id]
        return response

    def start(self):
        # Subscribe to connection announcements
        self.subscribe("sim-device-control/connections")
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()



def device_monitor(controller):
    known = {}

    while True:
        time.sleep(1)
        with controller._device_lock:
            current = dict(controller.devices)

        # Newly connected
        for dev_id, dev_type in current.items():
            if dev_id not in known:
                print(f"[CONNECTED] {dev_id} ({dev_type})")

        # Disconnected
        for dev_id in known:
            if dev_id not in current:
                print(f"[DISCONNECTED] {dev_id}")

        known = current


controller = MQTTDeviceController("broker.hivemq.com")
controller.connect()
controller.start()

monitor_thread = threading.Thread(
    target=device_monitor,
    args=(controller,),
    daemon=True
)
monitor_thread.start()

try:
    response = controller.send_command_and_wait(
        cmd_topic="sim-device-control/dev1/command",
        reply_topic="sim-device-control/dev1/response",
        command="get_status",
        parameter="",
        timeout=5
    )
    print("response:", response)
except TimeoutError:
    print("Device did not reply")

while True:
    time.sleep(1)
