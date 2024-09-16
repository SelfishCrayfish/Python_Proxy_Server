import socket
import json
import threading
from datetime import datetime


class ClientAPI:
    def __init__(self, server_ip, server_port, client_window):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_window = client_window
        self.socket = None
        self.connected = False
        self.client_id = None

    def get_timestamp(self):
        """
        Returns current time based on format ISO 8601.
        """
        return datetime.utcnow().isoformat() + "Z"

    def start(self, client_id):
        """
        Establishes connection with server
        """
        self.client_id = client_id
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            self.connected = True
            self.client_window.log_to_console(
                f"Connected to server {self.server_ip}:{self.server_port} as {self.client_id}")

            threading.Thread(target=self.listen_for_messages).start()
        except Exception as e:
            self.client_window.log_to_console(f"Connection error: {e}")

    def listen_for_messages(self):
        """
        Listens for messages from the server
        """
        while self.connected:
            try:
                response = self.socket.recv(1024).decode('utf-8')
                if response:
                    if response.startswith("{"):
                        data = json.loads(response)
                        topic = data.get("topic")
                        message = data.get("payload")
                        if topic and message and topic != "logs":
                            self.client_window.log_to_console(f"Message received on topic: {topic}: {message}")
                        elif data.get("type") == "status":
                            self.display_status(data)
                    else:
                        self.client_window.log_to_console(response)
            except Exception as e:
                if self.connected:
                    self.client_window.log_to_console(f"Failed to receive the message: {e}")
                self.connected = False

    def register_producer(self, topic_name):
        message = {
            "type": "register",
            "id": self.client_id,
            "topic": topic_name,
            "mode": "producer",
            "timestamp": self.get_timestamp(),
            "payload": {}
        }
        self.send_message(message)

    def register_subscriber(self, topic_name):
        message = {
            "type": "register",
            "id": self.client_id,
            "topic": topic_name,
            "mode": "subscriber",
            "timestamp": self.get_timestamp(),
            "payload": {}
        }
        self.send_message(message)

    def produce_message(self, topic_name, payload):
        message = {
            "type": "message",
            "id": self.client_id,
            "topic": topic_name,
            "mode": "producer",
            "timestamp": self.get_timestamp(),
            "payload": payload
        }
        self.send_message(message)

    def withdraw_producer(self, topic_name):
        message = {
            "type": "withdraw",
            "id": self.client_id,
            "topic": topic_name,
            "mode": "producer",
            "timestamp": self.get_timestamp(),
            "payload": {}
        }
        self.send_message(message)

    def withdraw_subscriber(self, topic_name):
        message = {
            "type": "withdraw",
            "id": self.client_id,
            "topic": topic_name,
            "mode": "subscriber",
            "timestamp": self.get_timestamp(),
            "payload": {}
        }
        self.send_message(message)

    def get_server_status(self):
        message = {
            "type": "status",
            "id": self.client_id,
            "topic": "logs",
            "mode": "",
            "timestamp": self.get_timestamp(),
            "payload": {}
        }
        self.send_message(message)

    def send_message(self, message):
        """
        Sends a message to the server
        """
        try:
            self.socket.send(json.dumps(message).encode('utf-8'))
        except Exception as e:
            self.client_window.log_to_console(f"Failed to send a message: {e}")

    def display_status(self, data):
        message = data["payload"]
        self.client_window.log_to_console(f"Server status: {json.dumps(message, indent=4)}")

    def stop(self):
        """
        Closes connection to server
        """
        if self.connected:
            self.connected = False
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                self.socket.close()
