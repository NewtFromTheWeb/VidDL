import tkinter as tk

root = tk.Tk()
root.title("Test GUI")
root.geometry("200x100")

label = tk.Label(root, text="Hello, GUI!")
label.pack(pady=20)

root.mainloop()
