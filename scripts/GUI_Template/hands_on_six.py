import os
import sys
import json
import random
from typing import Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QTextEdit,
    QWidget,
)

import smtplib
import ssl
from email.message import EmailMessage

import paho.mqtt.client as mqtt
import smtplib
import ssl
from email.message import EmailMessage

# Defaults based on existing template/example
DEFAULT_HOST = "139.162.222.115"
DEFAULT_PORT = 80
DEFAULT_TOPIC = "matzi/#"
DEFAULT_USERNAME = "MATZI"
DEFAULT_PASSWORD = "MATZI"
DEFAULT_RUNTIME = 60


def unique_client_id(prefix: str = "IOT_clientId-") -> str:
    r = random.randrange(1, 10000)
    return f"{prefix}{r}"


class MqttClient(QtCore.QObject):
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal(int)
    message_received = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.broker: str = DEFAULT_HOST
        self.port: int = DEFAULT_PORT
        self.client_id: str = unique_client_id()
        self.username: str = DEFAULT_USERNAME
        self.password: str = DEFAULT_PASSWORD
        self.keepalive: int = DEFAULT_RUNTIME
        self._runtime_seconds: int = DEFAULT_RUNTIME
        self._client: Optional[mqtt.Client] = None
        self._runtime_timer = QtCore.QTimer()
        self._runtime_timer.setSingleShot(True)
        self._runtime_timer.timeout.connect(self.stop_listening)

    def configure(self, broker: str, port: int, client_id: str, username: str, password: str, runtime: int, keepalive: Optional[int] = None):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        self._runtime_seconds = max(1, int(runtime))
        if keepalive is not None:
            self.keepalive = int(keepalive)

    def connect(self):
        self._client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311, transport="websockets")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.username_pw_set(self.username, self.password)
        try:
            self._client.connect(self.broker, self.port, keepalive=self.keepalive)
        except Exception as e:
            # Emit a disconnect with rc = 1 to indicate failure
            self.disconnected.emit(1)
            raise e

    def disconnect(self):
        if self._client is not None:
            self._client.disconnect()

    def start_listening(self):
        if self._client is None:
            return
        self._client.loop_start()
        self._runtime_timer.start(self._runtime_seconds * 1000)

    def stop_listening(self):
        if self._client is not None:
            self._client.loop_stop()
            self._runtime_timer.stop()

    def subscribe(self, topic: str):
        if self._client is not None:
            self._client.subscribe(topic)

    def publish(self, topic: str, message: str):
        if self._client is not None:
            self._client.publish(topic, message)

    # paho callbacks
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected.emit()
        else:
            self.disconnected.emit(rc)

    def _on_disconnect(self, client, userdata, rc):
        self.disconnected.emit(rc)

    def _on_message(self, client, userdata, msg):
        try:
            m_decode = msg.payload.decode("utf-8", "ignore")
        except Exception:
            m_decode = str(msg.payload)
        self.message_received.emit(msg.topic, m_decode)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(30, 100, 700, 700)
        self.setWindowTitle("White Cubes GUI")

        # MQTT client
        self.mc = MqttClient()
        self.mc.connected.connect(self.on_connected)
        self.mc.disconnected.connect(self.on_disconnected)
        self.mc.message_received.connect(self.on_message)

        # UI: Connection form
        self.host_input = QLineEdit(DEFAULT_HOST)
        self.host_input.setInputMask("999.999.999.999")

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(DEFAULT_PORT)

        self.runtime_input = QSpinBox()
        self.runtime_input.setRange(1, 86400)
        self.runtime_input.setValue(DEFAULT_RUNTIME)

        self.client_id_input = QLineEdit(unique_client_id())
        self.username_input = QLineEdit(DEFAULT_USERNAME)
        self.password_input = QLineEdit(DEFAULT_PASSWORD)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.topic_input = QLineEdit(DEFAULT_TOPIC)

        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold")

        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")

        self.connect_button.clicked.connect(self.handle_connect)
        self.disconnect_button.clicked.connect(self.handle_disconnect)

        form = QFormLayout()
        form.addRow("Host", self.host_input)
        form.addRow("Port", self.port_input)
        form.addRow("Running Time (s)", self.runtime_input)
        form.addRow("Client ID", self.client_id_input)
        form.addRow("Username", self.username_input)
        form.addRow("Password", self.password_input)
        form.addRow("Topic", self.topic_input)
        form.addRow("Status", self.status_label)
        form.addRow(self.connect_button, self.disconnect_button)

        conn_widget = QWidget()
        conn_widget.setLayout(form)
        conn_dock = QDockWidget("Connection")
        conn_dock.setWidget(conn_widget)
        self.addDockWidget(Qt.TopDockWidgetArea, conn_dock)

        # UI: Publish/Subscribe
        self.pub_topic_input = QLineEdit(DEFAULT_TOPIC)
        self.pub_message_input = QPlainTextEdit()
        self.publish_button = QPushButton("Publish")
        self.publish_button.clicked.connect(self.handle_publish)

        pub_form = QFormLayout()
        pub_form.addRow("Publish Topic", self.pub_topic_input)
        pub_form.addRow("Message", self.pub_message_input)
        pub_form.addRow(self.publish_button)

        pub_widget = QWidget()
        pub_widget.setLayout(pub_form)
        pub_dock = QDockWidget("Publish")
        pub_dock.setWidget(pub_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, pub_dock)

        self.sub_topic_input = QLineEdit(DEFAULT_TOPIC)
        self.subscribe_button = QPushButton("Subscribe")
        self.subscribe_button.clicked.connect(self.handle_subscribe)

        self.received_text = QTextEdit()
        self.received_text.setReadOnly(True)

        sub_form = QFormLayout()
        sub_form.addRow("Subscribe Topic", self.sub_topic_input)
        sub_form.addRow(self.subscribe_button)
        sub_form.addRow("Received", self.received_text)

        sub_widget = QWidget()
        sub_widget.setLayout(sub_form)
        sub_dock = QDockWidget("Subscribe")
        sub_dock.setWidget(sub_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, sub_dock)

        # Email alert configuration
        self.alert_email_input = QLineEdit("")
        self.smtp_host_input = QLineEdit("smtp.gmail.com")
        self.smtp_port_input = QSpinBox()
        self.smtp_port_input.setRange(1, 65535)
        self.smtp_port_input.setValue(587)
        self.smtp_tls_checkbox = QCheckBox()
        self.smtp_tls_checkbox.setChecked(True)
        self.smtp_user_input = QLineEdit("")
        self.smtp_pass_input = QLineEdit("")
        self.smtp_pass_input.setEchoMode(QLineEdit.Password)
        self.send_test_email_button = QPushButton("Send Test Email")
        self.send_test_email_button.clicked.connect(self.handle_send_test_email)

        email_form = QFormLayout()
        email_form.addRow("Alert Email (recipient)", self.alert_email_input)
        email_form.addRow("SMTP Host", self.smtp_host_input)
        email_form.addRow("SMTP Port", self.smtp_port_input)
        email_form.addRow("Use TLS", self.smtp_tls_checkbox)
        email_form.addRow("SMTP Username", self.smtp_user_input)
        email_form.addRow("SMTP Password", self.smtp_pass_input)
        email_form.addRow(self.send_test_email_button)

        email_widget = QWidget()
        email_widget.setLayout(email_form)
        email_dock = QDockWidget("Email Alerts")
        email_dock.setWidget(email_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, email_dock)

        # DHT sensor thresholds
        self.dht_topic_input = QLineEdit("matzi/#")
        self.temp_low_input = QSpinBox()
        self.temp_low_input.setRange(-50, 150)
        self.temp_low_input.setValue(15)
        self.temp_high_input = QSpinBox()
        self.temp_high_input.setRange(-50, 150)
        self.temp_high_input.setValue(30)
        self.humidity_low_input = QSpinBox()
        self.humidity_low_input.setRange(0, 100)
        self.humidity_low_input.setValue(30)
        self.humidity_high_input = QSpinBox()
        self.humidity_high_input.setRange(0, 100)
        self.humidity_high_input.setValue(70)

        dht_form = QFormLayout()
        dht_form.addRow("DHT Topic Filter", self.dht_topic_input)
        dht_form.addRow("Temperature Low Limit (°C)", self.temp_low_input)
        dht_form.addRow("Temperature High Limit (°C)", self.temp_high_input)
        dht_form.addRow("Humidity Low Limit (%)", self.humidity_low_input)
        dht_form.addRow("Humidity High Limit (%)", self.humidity_high_input)

        dht_widget = QWidget()
        dht_widget.setLayout(dht_form)
        dht_dock = QDockWidget("DHT Sensor Alerts")
        dht_dock.setWidget(dht_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, dht_dock)

    # Connection Handlers
    def handle_connect(self):
        self.mc.configure(
            broker=self.host_input.text(),
            port=int(self.port_input.value()),
            client_id=self.client_id_input.text(),
            username=self.username_input.text(),
            password=self.password_input.text(),
            runtime=int(self.runtime_input.value()),
            keepalive=int(self.runtime_input.value()),
        )
        try:
            self.mc.connect()
            self.mc.start_listening()
            self.mc.subscribe(self.topic_input.text())
        except Exception as e:
            self.status_label.setText(f"Connect error: {e}")
            self.status_label.setStyleSheet("color: orange; font-weight: bold")

    def handle_disconnect(self):
        self.mc.stop_listening()
        self.mc.disconnect()

    def on_connected(self):
        self.status_label.setText("Connected")
        self.status_label.setStyleSheet("color: green; font-weight: bold")

    def on_disconnected(self, rc: int):
        self.status_label.setText(f"Disconnected (rc={rc})")
        self.status_label.setStyleSheet("color: red; font-weight: bold")

    # Messaging
    def handle_publish(self):
        self.mc.publish(self.pub_topic_input.text(), self.pub_message_input.toPlainText())

    def handle_subscribe(self):
        self.mc.subscribe(self.sub_topic_input.text())

    def on_message(self, topic: str, payload: str):
        self.received_text.append(f"{topic}: {payload}")
        
        # DHT sensor reading detection: "Temperature: 22.6 Humidity: 76.1"
        if "Temperature:" in payload and "Humidity:" in payload:
            try:
                # Parse DHT data
                temp_str = payload.split("Temperature:")[1].split("Humidity:")[0].strip()
                humidity_str = payload.split("Humidity:")[1].strip()
                
                temp = float(temp_str)
                humidity = float(humidity_str)
                
                temp_low = float(self.temp_low_input.value())
                temp_high = float(self.temp_high_input.value())
                humidity_low = float(self.humidity_low_input.value())
                humidity_high = float(self.humidity_high_input.value())
                
                # Check thresholds and send warning if exceeded
                alert_message = []
                if temp < temp_low:
                    alert_message.append(f"Temperature too LOW: {temp}°C (limit: {temp_low}°C)")
                if temp > temp_high:
                    alert_message.append(f"Temperature too HIGH: {temp}°C (limit: {temp_high}°C)")
                if humidity < humidity_low:
                    alert_message.append(f"Humidity too LOW: {humidity}% (limit: {humidity_low}%)")
                if humidity > humidity_high:
                    alert_message.append(f"Humidity too HIGH: {humidity}% (limit: {humidity_high}%)")
                
                if alert_message:
                    subject = "DHT Sensor Warning"
                    body = f"Topic: {topic}\n{payload}\n\nAlerts:\n" + "\n".join(alert_message)
                    self.send_alert_email(subject, body)
            except (ValueError, IndexError):
                pass

    def handle_send_test_email(self):
        subject = "White Cube Test Email"
        body = "This is a test email from the White Cubes GUI."
        self.send_alert_email(subject, body)

    def send_alert_email(self, subject: str, body: str):
        recipient = self.alert_email_input.text().strip()
        smtp_host = self.smtp_host_input.text().strip()
        smtp_port = int(self.smtp_port_input.value())
        use_tls = self.smtp_tls_checkbox.isChecked()
        smtp_user = self.smtp_user_input.text().strip()
        smtp_pass = self.smtp_pass_input.text()

        if not recipient:
            self.status_label.setText("Email error: recipient empty")
            self.status_label.setStyleSheet("color: orange; font-weight: bold")
            return
        if not smtp_host:
            self.status_label.setText("Email error: SMTP host empty")
            self.status_label.setStyleSheet("color: orange; font-weight: bold")
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        # Prefer smtp_user for From if available
        msg["From"] = smtp_user if smtp_user else "noreply@example.com"
        msg["To"] = recipient
        msg.set_content(body)

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            self.status_label.setText("Alert email sent")
            self.status_label.setStyleSheet("color: green; font-weight: bold")
        except Exception as e:
            self.status_label.setText(f"Email error: {e}")
            self.status_label.setStyleSheet("color: orange; font-weight: bold")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
