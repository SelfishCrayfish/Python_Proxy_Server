import datetime
import socket
import threading
import json
import queue
import time


class Server:
    def __init__(self, config_file='config.json'):
        self.server_id = None
        self.address = None
        self.port = None
        self.timeout = None
        self.config_file = config_file
        self.load_config()
        self.server_socket = None
        self.topics = {}
        self.lock = threading.Lock()
        self.kko = queue.Queue()
        self.kkw = queue.Queue()
        self.callback_kkw = None

    def load_config(self):
        """
        Loads server config from JSON file.
        Default ServerID: default_server
        Default ListenAddress: 127.0.0.1
        Default ListenPort: 1234
        Default TimeOut: 3
        """
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.address = config.get("ListenAddresses", ["127.0.0.1"])[0]
                self.port = config.get("ListenPort", 1234)
                self.timeout = config.get("TimeOut", 3)
                self.server_id = config.get("ServerID", "default_server")
            print(f"Config loaded: host={self.address}, port={self.port}, timeout={self.timeout}")
        except FileNotFoundError:
            print(f"Error: File {self.config_file} not found. Using default config...")
            self.address = '127.0.0.1'
            self.port = 1234
            self.timeout = 3
            self.server_id = 'default_server'
        except json.JSONDecodeError:
            print("Error: Incorrect JSON formatting. Using default config...")
            self.address = '127.0.0.1'
            self.port = 1234
            self.timeout = 3
            self.server_id = 'default_server'

    def start(self):
        """
        Starts the server and waits for incoming clients
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.address, self.port))
        self.server_socket.listen(5)
        print(f"Server '{self.server_id}' listening on {self.address}:{self.port} with timeout of {self.timeout} seconds")

        self.register_kkw_callback(self.on_message_sent)

        threading.Thread(target=self.handle_outgoing_messages).start()
        threading.Thread(target=self.monitor_topics).start()

        try:
            while True:
                self.server_socket.settimeout(self.timeout)
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"Connected with {client_address}")
                    threading.Thread(target=self.handle_client, args=(client_socket,)).start()
                except TimeoutError:
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{current_time}] No new connections, server is waiting...")
                    continue
        except KeyboardInterrupt:
            print("Stopping server...")
        finally:
            self.server_socket.close()

    def monitor_topics(self):
        """
        Monitoring thread that handles KKO, topics and subscriptions
        """
        while True:
            if self.kko.empty():
                time.sleep(0.001)
                continue

            client_socket, data = self.kko.get()
            if not self.validate_kom(data):
                print(f"Validation unsuccesful: {data}")
                continue

            self.process_message(data, client_socket)
            print(data)
            self.kko.task_done()

    def validate_kom(self, data):
        """
        Validation of KOM, based specified format
        """
        try:
            required_keys = ["type", "id", "topic", "mode", "timestamp", "payload"]
            for key in required_keys:
                if key not in data:
                    return False

            datetime.datetime.fromisoformat(data["timestamp"])

            if data["type"] not in ["register", "withdraw", "message", "status"]:
                return False

            if data["mode"] not in ["producer", "subscriber"] and not data["type"] in ["status"]:
                return False

            return True
        except Exception as e:
            print(f"Validation failed: {e}")
            return False

    def register_kkw_callback(self, callback):
        """
        Registers callback, which will be called after each change in KKW
        """
        self.callback_kkw = callback

    def on_message_sent(self, client_socket, message):
        """
        Callback function called after each message sent to client
        Logs the message to log.txt file
        """
        log_entry = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Message to {client_socket.getpeername()}: {message}\n"

        try:
            with open("log.txt", "a") as log_file:
                log_file.write(log_entry)
        except IOError as e:
            print(f"Failed to write into log.txt: {e}")

    def handle_outgoing_messages(self):
        """
        Thread that processes messages from KKW
        """
        while True:
            if not self.kkw.empty():
                client_socket, message = self.kkw.get()
                try:
                    client_socket.send(message.encode('utf-8'))
                    if self.callback_kkw:
                        self.callback_kkw(client_socket, message)
                except Exception as e:
                    print(f"Failed to send the message: {e}")

    def handle_client(self, client_socket):
        """
        Processes clients' connections
        """
        try:
            while True:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                data = json.loads(message)

                self.kko.put((client_socket, data))

                threading.Thread(target=self.process_received_messages).start()

        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            self.handle_disconnection(client_socket)
            client_socket.close()

    def handle_disconnection(self, client_socket):
        """
        Handles client's disconnection. Deletes their subscriptions and/or topics, of which he was a producer
        """
        with self.lock:
            topics_to_remove = []
            for topic, info in list(self.topics.items()):
                if info["producer"] == client_socket:
                    print(f"Producer of topic {topic} disconnected. Deleting topic.")
                    topics_to_remove.append(topic)

                if client_socket in info["subscribers"]:
                    print(f"Subscriber of topic {topic} disconnected. Deleting subscription.")
                    self.topics[topic]["subscribers"].remove(client_socket)

            for topic in topics_to_remove:
                del self.topics[topic]
                print(f"Topic {topic} has been removed.")

    def process_received_messages(self):
        """
        Processes messages received from KKO
        """
        while not self.kko.empty():
            client_socket, data = self.kko.get()
            self.process_message(data, client_socket)

    def process_message(self, data, client_socket):
        """
        Processes messages from clients: register, withdraw, message, status
        """
        message_type = data.get("type")
        topic = data.get("topic")
        client_id = data.get("id")

        if message_type == "register" and data.get("mode") == "producer":
            with self.lock:
                if topic in self.topics:
                    if self.topics[topic]["producer"] == client_socket:
                        self.kkw.put((client_socket, f"You already are the producer of topic {topic}."))
                    else:
                        self.kkw.put((client_socket, f"Topic {topic} already exists."))
                else:
                    self.topics[topic] = {"producer": client_socket, "producer_id": client_id, "subscribers": []}
                    self.kkw.put((client_socket, f"New topic registered: {topic}"))

        elif message_type == "register" and data.get("mode") == "subscriber":
            with self.lock:
                if topic in self.topics:
                    if client_socket in self.topics[topic]["subscribers"]:
                        self.kkw.put((client_socket, f"You already are a subscriber of topic {topic}."))
                    else:
                        self.topics[topic]["subscribers"].append(client_socket)
                        self.kkw.put((client_socket, f"Subscribed to topic: {topic}"))
                else:
                    self.kkw.put((client_socket, f"Topic {topic} doesn't exist."))

        elif message_type == "withdraw" and data.get("mode") == "subscriber":
            with self.lock:
                if topic in self.topics:
                    if client_socket in self.topics[topic]["subscribers"]:
                        self.topics[topic]["subscribers"].remove(client_socket)
                        self.kkw.put((client_socket, f"Subscription of topic {topic} has been withdrawn."))
                    else:
                        self.kkw.put((client_socket, f"You are not a subscriber of topic {topic}."))
                else:
                    self.kkw.put((client_socket, f"Topic {topic} doesn't exist."))

        elif message_type == "withdraw" and data.get("mode") == "producer":
            with self.lock:
                if topic in self.topics:
                    if self.topics[topic]["producer"] == client_socket:
                        del self.topics[topic]
                        self.kkw.put((client_socket, f"Topic {topic} has been withdrawn."))
                    else:
                        self.kkw.put((client_socket, f"You are not a producer of topic {topic}."))
                else:
                    self.kkw.put((client_socket, f"Topic {topic} doesn't exist."))

        elif message_type == "message":
            payload = data.get("payload")
            with self.lock:
                if topic in self.topics:
                    if self.topics[topic]["producer"] == client_socket:
                        subscribers = self.topics[topic]["subscribers"]
                        for sub in subscribers:
                            try:
                                self.kkw.put((sub, json.dumps({"topic": topic, "payload": payload})))
                            except:
                                print(f"Failed to send message to a subscriber")
                    else:
                        self.kkw.put((client_socket, f"You are not a producer of topic {topic}."))
                else:
                    self.kkw.put((client_socket, f"Topic {topic} doesn't exist."))

        elif message_type == "status":
            with self.lock:
                topics_status = [{"topic": t, "id": self.topics[t]["producer_id"]} for t in self.topics]
                data["payload"] = topics_status
                self.kkw.put((client_socket, json.dumps(data)))
        else:
            self.kkw.put((client_socket, "Unknown message type."))


if __name__ == "__main__":
    server = Server(config_file="config.json")
    server.start()
