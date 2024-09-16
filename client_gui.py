import tkinter as tk
from tkinter import messagebox
from client_api import ClientAPI
import json


class ClientApp:
    def __init__(self, root, config_file='config.json'):
        self.root = root
        self.root.title("GUI")
        self.root.resizable(False, False)
        self.config_file = config_file
        self.server_ip = None
        self.server_port = None

        self.load_config()

        self.server_ip_label = tk.Label(root, text="Server IP address:")
        self.server_ip_label.grid(row=0, column=0, padx=5, pady=5)
        self.server_ip_entry = tk.Entry(root)
        self.server_ip_entry.grid(row=0, column=1, padx=5, pady=5)
        self.server_ip_entry.insert(0, self.server_ip)

        self.server_port_label = tk.Label(root, text="Server port:")
        self.server_port_label.grid(row=1, column=0, padx=5, pady=5)
        self.server_port_entry = tk.Entry(root)
        self.server_port_entry.grid(row=1, column=1, padx=5, pady=5)
        self.server_port_entry.insert(0, str(self.server_port))

        self.client_id_label = tk.Label(root, text="Client ID:")
        self.client_id_label.grid(row=2, column=0, padx=5, pady=5)
        self.client_id_entry = tk.Entry(root)
        self.client_id_entry.grid(row=2, column=1, padx=5, pady=5)

        self.add_client_button = tk.Button(root, text="Add a client", command=self.add_client)
        self.add_client_button.grid(row=3, columnspan=2, pady=10)

    def load_config(self):
        """
        Loads server config from JSON file
        Default ListenAddress: 127.0.0.1
        Default ListenPort: 1234
        """
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.server_ip = config.get("ListenAddresses", ["127.0.0.1"])[0]
                self.server_port = config.get("ListenPort", 1234)
                print(f"Server config loaded: IP={self.server_ip}, port={self.server_port}")
        except FileNotFoundError:
            print(f"Error: File {self.config_file} not found. Using default config...")
            self.server_ip = "127.0.0.1"
            self.server_port = 1234
        except json.JSONDecodeError:
            print("Error: Incorrect JSON formatting. Using default config...")
            self.server_ip = "127.0.0.1"
            self.server_port = 1234

    def client_id_input_field(self):
        """
        Retrieves client ID from input field
        """
        server_ip = self.server_ip_entry.get()
        server_port = int(self.server_port_entry.get())
        client_id = self.client_id_entry.get()

        if not client_id:
            messagebox.showerror("Error", "Client ID can't be empty!")
            return None

        return server_ip, server_port, client_id

    def add_client(self):
        """
        Creates a window for the client
        """
        details = self.client_id_input_field()
        if details:
            client_window = tk.Toplevel(self.root)
            client_window.resizable(False, False)
            ClientWindow(client_window, *details)


class ClientWindow:
    def __init__(self, root, server_ip, server_port, client_id):
        self.root = root
        self.client_id = client_id
        self.root.title(f"Client - {self.client_id}")
        self.client = None
        self.root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.disconnect_client)

        self.console_output = tk.Text(root, height=20, width=50, state=tk.DISABLED)
        self.console_output.grid(row=6, columnspan=2, padx=5, pady=5)

        self.client = ClientAPI(server_ip, server_port, self)
        self.client.start(client_id)

        self.topic_label = tk.Label(root, text="Topic:")
        self.topic_label.grid(row=0, column=0, padx=5, pady=5)
        self.topic_entry = tk.Entry(root)
        self.topic_entry.grid(row=0, column=1, padx=5, pady=5)

        self.add_topic_button = tk.Button(root, text="Register topic", command=self.register_topic)
        self.add_topic_button.grid(row=1, column=0, padx=5, pady=5)

        self.subscribe_button = tk.Button(root, text="Register subscription", command=self.register_subscription)
        self.subscribe_button.grid(row=1, column=1, padx=5, pady=5)

        self.withdraw_topic_button = tk.Button(root, text="Withdraw topic", command=self.withdraw_topic)
        self.withdraw_topic_button.grid(row=2, column=0, padx=5, pady=5)

        self.withdraw_subscription_button = tk.Button(root, text="Withdraw subscription",
                                                      command=self.withdraw_subscription)
        self.withdraw_subscription_button.grid(row=2, column=1, padx=5, pady=5)

        self.get_status_button = tk.Button(root, text="Server status", command=self.server_status)
        self.get_status_button.grid(row=3, columnspan=2, pady=5)

        self.message_label = tk.Label(root, text="Message:")
        self.message_label.grid(row=4, column=0, padx=5, pady=5)
        self.message_entry = tk.Entry(root)
        self.message_entry.grid(row=4, column=1, padx=5, pady=5)

        self.send_message_button = tk.Button(root, text="Send message", command=self.send_message)
        self.send_message_button.grid(row=5, columnspan=2, pady=10)

        self.clear_console_button = tk.Button(root, text="Clear console", command=self.clear_console)
        self.clear_console_button.grid(row=7, columnspan=2, pady=5)

        self.disconnect_button = tk.Button(root, text="Disconnect", command=self.disconnect_client)
        self.disconnect_button.grid(row=8, columnspan=2, pady=10)

    def register_topic(self):
        topic = self.topic_entry.get()
        if topic:
            self.client.register_producer(topic)
        else:
            self.log_to_console("Error: Topic name can't be empty!")

    def register_subscription(self):
        topic = self.topic_entry.get()
        if topic:
            self.client.register_subscriber(topic)
        else:
            self.log_to_console("Error: Topic name can't be empty!")

    def withdraw_topic(self):
        topic = self.topic_entry.get()
        if topic:
            self.client.withdraw_producer(topic)
        else:
            self.log_to_console("Error: Topic name can't be empty!")

    def withdraw_subscription(self):

        topic = self.topic_entry.get()
        if topic:
            self.client.withdraw_subscriber(topic)
        else:
            self.log_to_console("Error: Topic name can't be empty!")

    def server_status(self):
        self.client.get_server_status()

    def send_message(self):
        """
        Sends a message to registered topic
        """
        topic = self.topic_entry.get()
        message = self.message_entry.get()
        if topic and message:
            self.client.produce_message(topic, {"content": message})
        else:
            self.log_to_console("Error: Topic and message can't be empty!")

    def clear_console(self):
        self.console_output.config(state=tk.NORMAL)
        self.console_output.delete('1.0', tk.END)
        self.console_output.config(state=tk.DISABLED)

    def log_to_console(self, message):
        """
        Displays the message in console
        """
        self.console_output.config(state=tk.NORMAL)
        self.console_output.insert(tk.END, f"{message}\n")
        self.console_output.config(state=tk.DISABLED)

    def disconnect_client(self):
        """
        Disconnects client from server
        """
        self.client.stop()
        self.root.destroy()
