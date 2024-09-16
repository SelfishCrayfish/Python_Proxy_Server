import tkinter as tk

from client_gui import ClientApp

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()
