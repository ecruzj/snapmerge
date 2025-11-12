from __future__ import annotations
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

class LogConsole(ScrolledText):
    """A simple text console to append log lines."""

    def append(self, text: str) -> None:
        self.configure(state="normal")
        self.insert(tk.END, text + "\n")
        self.see(tk.END)
        self.configure(state="disabled")