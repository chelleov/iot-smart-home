import os
import sys
import PyQt5
import random
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import paho.mqtt.client as mqtt
import time
import datetime
from mqtt_init import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import re

# Creating Client name - should be unique 
global clientname, CONNECTED
CONNECTED = False
r = random.randrange(1, 10000000)
clientname = "IOT_client-Listener-" + str(r)

# Device topics
button_topic = 'pr/home/button_123_YY/sts'
dht_topic = 'pr/home/5976397/sts'
relay_topic = 'pr/home/relay_device/cmd'  # Topic to publish to relay
subscribe_topics = [button_topic, dht_topic, '#']  # Subscribe to all to catch relay messages


class Mqtt_client():
    
    def __init__(self):
        # broker IP adress:
        self.broker = ''
        self.topic = ''
        self.port = '' 
        self.clientname = ''
        self.username = ''
        self.password = ''        
        self.subscribeTopic = ''
        self.publishTopic = ''
        self.publishMessage = ''
        self.on_connected_to_form = ''
        
    # Setters and getters
    def set_on_connected_to_form(self, on_connected_to_form):
        self.on_connected_to_form = on_connected_to_form
    def get_broker(self):
        return self.broker
    def set_broker(self, value):
        self.broker = value         
    def get_port(self):
        return self.port
    def set_port(self, value):
        self.port = value     
    def get_clientName(self):
        return self.clientName
    def set_clientName(self, value):
        self.clientName = value        
    def get_username(self):
        return self.username
    def set_username(self, value):
        self.username = value     
    def get_password(self):
        return self.password
    def set_password(self, value):
        self.password = value         
    def get_subscribeTopic(self):
        return self.subscribeTopic
    def set_subscribeTopic(self, value):
        self.subscribeTopic = value        
    def get_publishTopic(self):
        return self.publishTopic
    def set_publishTopic(self, value):
        self.publishTopic = value         
    def get_publishMessage(self):
        return self.publishMessage
    def set_publishMessage(self, value):
        self.publishMessage = value 
        
        
    def on_log(self, client, userdata, level, buf):
        print("log: " + buf)
            
    def on_connect(self, client, userdata, flags, rc):
        global CONNECTED
        if rc == 0:
            print("connected OK")
            CONNECTED = True
            self.on_connected_to_form()            
        else:
            print("Bad connection Returned code=", rc)
            
    def on_disconnect(self, client, userdata, flags, rc=0):
        CONNECTED = False
        print("DisConnected result code " + str(rc))
            
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        m_decode = str(msg.payload.decode("utf-8", "ignore"))
        print("message from:" + topic, m_decode)
        mainwin.subscribeDock.update_mess_win(topic, m_decode)
        
        # Parse DHT messages for temperature and humidity
        if 'Temperature:' in m_decode and 'Humidity:' in m_decode:
            try:
                temp_match = re.search(r'Temperature:\s*([\d.]+)', m_decode)
                hum_match = re.search(r'Humidity:\s*([\d.]+)', m_decode)
                if temp_match and hum_match:
                    temp = float(temp_match.group(1))
                    hum = float(hum_match.group(1))
                    mainwin.graphDock.add_data(temp, hum)
            except:
                pass
        
        # Handle button messages and control relay by publishing to relay's subscribed topic
        if 'value' in m_decode and 'button' in topic.lower():
            try:
                relay_cmd_topic = mainwin.connectionDock.get_relay_topic()
                if relay_cmd_topic:
                    if '"value":1' in m_decode or '"value": 1' in m_decode:
                        # Button pressed - publish to relay topic (relay will toggle on any message)
                        print(f"Publishing to relay topic: {relay_cmd_topic}")
                        self.publish_to(relay_cmd_topic, 'button_press')
                    elif '"value":0' in m_decode or '"value": 0' in m_decode:
                        # Button released - also send toggle
                        print(f"Publishing to relay topic: {relay_cmd_topic}")
                        self.publish_to(relay_cmd_topic, 'button_release')
                else:
                    print("WARNING: Relay topic not set!")
            except Exception as e:
                print(f"Error handling button: {e}")
                pass

    def connect_to(self):
        # Init paho mqtt client class        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, self.clientname, clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log
        self.client.on_message = self.on_message
        self.client.username_pw_set(self.username, self.password)        
        print("Connecting to broker ", self.broker)        
        self.client.connect(self.broker, self.port)
    
    def disconnect_from(self):
        self.client.disconnect()                   
    
    def start_listening(self):        
        self.client.loop_start()        
    
    def stop_listening(self):        
        self.client.loop_stop()    
    
    def subscribe_to(self, topic):
        if CONNECTED:
            self.client.subscribe(topic)
        else:
            print("Can't subscribe. Connection should be established first")       
              
    def publish_to(self, topic, message):
        if CONNECTED:
            self.client.publish(topic, message)
            mainwin.sentDock.update_sent_log(topic, message)
        else:
            print("Can't publish. Connection should be established first")         
      

class ConnectionDock(QDockWidget):
    """Connection dock with broker settings"""
    def __init__(self, mc):
        QDockWidget.__init__(self)
        
        self.mc = mc
        self.mc.set_on_connected_to_form(self.on_connected)
        
        self.eConnectbtn = QPushButton("Connect/Listen", self)
        self.eConnectbtn.setToolTip("Click to connect and start listening")
        self.eConnectbtn.clicked.connect(self.on_button_connect_click)
        self.eConnectbtn.setStyleSheet("background-color: gray")
        
        self.eButtonTopic = QLineEdit()
        self.eButtonTopic.setText(button_topic)
        self.eButtonTopic.setPlaceholderText("Button topic")
        
        self.eDhtTopic = QLineEdit()
        self.eDhtTopic.setText(dht_topic)
        self.eDhtTopic.setPlaceholderText("DHT sensor topic")
        
        self.eRelayTopic = QLineEdit()
        self.eRelayTopic.setText("")
        self.eRelayTopic.setPlaceholderText("Paste relay topic here (from RELAY window)")

        formLayout = QFormLayout()
        formLayout.addRow("Connect", self.eConnectbtn)
        formLayout.addRow("Button Topic", self.eButtonTopic)
        formLayout.addRow("DHT Topic", self.eDhtTopic)
        formLayout.addRow("Relay Topic", self.eRelayTopic)

        widget = QWidget(self)
        widget.setLayout(formLayout)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)     
        self.setWindowTitle("Connect") 
        
    def on_connected(self):
        self.eConnectbtn.setStyleSheet("background-color: green")
        # Subscribe to all device topics
        self.mc.subscribe_to(self.eButtonTopic.text())
        self.mc.subscribe_to(self.eDhtTopic.text())
        if self.eRelayTopic.text().strip():
            self.mc.subscribe_to(self.eRelayTopic.text())
        # Subscribe to all topics to catch everything
        self.mc.subscribe_to('#')
    
    def get_relay_topic(self):
        return self.eRelayTopic.text().strip() if self.eRelayTopic.text().strip() else None
                    
    def on_button_connect_click(self):
        self.mc.set_broker(broker_ip)
        self.mc.set_port(int(broker_port))
        self.mc.set_clientName(clientname)
        self.mc.set_username(username)
        self.mc.set_password(password)        
        self.mc.connect_to()        
        self.mc.start_listening()


class SubscribeDock(QDockWidget):
    """Received messages display dock"""
    def __init__(self):
        QDockWidget.__init__(self)
        
        self.eMessageOutput = QTextEdit()
        self.eMessageOutput.setReadOnly(True)
        
        self.eClearBtn = QPushButton("Clear Received", self)
        self.eClearBtn.clicked.connect(self.clear_messages)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Received Messages:"))
        layout.addWidget(self.eMessageOutput)
        layout.addWidget(self.eClearBtn)

        widget = QWidget(self)
        widget.setLayout(layout)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)     
        self.setWindowTitle("Received Messages") 
        
    def update_mess_win(self, topic, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {topic}: {message}\n"
        cursor = self.eMessageOutput.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.insertText(formatted_msg)
        cursor.movePosition(QTextCursor.Start)
        
    def clear_messages(self):
        self.eMessageOutput.clear()


class SentDock(QDockWidget):
    """Sent messages display dock"""
    def __init__(self):
        QDockWidget.__init__(self)
        
        self.eMessageOutput = QTextEdit()
        self.eMessageOutput.setReadOnly(True)
        
        self.eClearBtn = QPushButton("Clear Sent", self)
        self.eClearBtn.clicked.connect(self.clear_messages)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Sent Messages:"))
        layout.addWidget(self.eMessageOutput)
        layout.addWidget(self.eClearBtn)

        widget = QWidget(self)
        widget.setLayout(layout)
        self.setTitleBarWidget(widget)
        self.setWidget(widget)     
        self.setWindowTitle("Sent Messages") 
        
    def update_sent_log(self, topic, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {topic}: {message}\n"
        cursor = self.eMessageOutput.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.insertText(formatted_msg)
        cursor.movePosition(QTextCursor.Start)
        
    def clear_messages(self):
        self.eMessageOutput.clear()


class GraphDock(QDockWidget):
    """Temperature and Humidity graph dock"""
    def __init__(self):
        QDockWidget.__init__(self)
        
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)
        
        self.temp_data = []
        self.hum_data = []
        self.time_data = []
        self.max_points = 50  # Keep last 50 data points
        
        self.ax1.set_title('Temperature (°C)')
        self.ax1.set_xlabel('Time')
        self.ax1.set_ylabel('°C')
        self.ax1.grid(True)
        
        self.ax2.set_title('Humidity (%)')
        self.ax2.set_xlabel('Time')
        self.ax2.set_ylabel('%')
        self.ax2.grid(True)
        
        self.figure.tight_layout()
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        
        widget = QWidget(self)
        widget.setLayout(layout)
        self.setWidget(widget)
        self.setWindowTitle("Temperature & Humidity")
        
    def add_data(self, temperature, humidity):
        current_time = datetime.datetime.now()
        
        self.time_data.append(current_time)
        self.temp_data.append(temperature)
        self.hum_data.append(humidity)
        
        # Keep only last max_points
        if len(self.time_data) > self.max_points:
            self.time_data = self.time_data[-self.max_points:]
            self.temp_data = self.temp_data[-self.max_points:]
            self.hum_data = self.hum_data[-self.max_points:]
        
        self.update_plot()
        
    def update_plot(self):
        self.ax1.clear()
        self.ax2.clear()
        
        if len(self.time_data) > 0:
            self.ax1.plot(self.time_data, self.temp_data, 'r-', linewidth=2)
            self.ax1.set_title('Temperature (°C)')
            self.ax1.set_ylabel('°C')
            self.ax1.grid(True)
            self.ax1.tick_params(axis='x', rotation=45)
            
            self.ax2.plot(self.time_data, self.hum_data, 'b-', linewidth=2)
            self.ax2.set_title('Humidity (%)')
            self.ax2.set_ylabel('%')
            self.ax2.grid(True)
            self.ax2.tick_params(axis='x', rotation=45)
        
        self.figure.tight_layout()
        self.canvas.draw()


class MainWindow(QMainWindow):
    
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
                
        # Init of Mqtt_client class
        self.mc = Mqtt_client()
        
        # general GUI settings
        self.setUnifiedTitleAndToolBarOnMac(True)

        # set up main window
        self.setGeometry(30, 100, 1000, 800)
        self.setWindowTitle('MQTT Client Listener')        

        # Init QDockWidget objects        
        self.connectionDock = ConnectionDock(self.mc)        
        self.subscribeDock = SubscribeDock()
        self.sentDock = SentDock()
        self.graphDock = GraphDock()
        
        self.addDockWidget(Qt.TopDockWidgetArea, self.connectionDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.subscribeDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sentDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.graphDock)
       

app = QApplication(sys.argv)
mainwin = MainWindow()
mainwin.show()
app.exec_()
