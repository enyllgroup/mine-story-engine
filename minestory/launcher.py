"""Tiny native chooser; processing happens in a child process off the UI thread."""
from __future__ import annotations
import queue
import subprocess
import sys
import threading
from .util import ROOT

def launch():
    try:
        import tkinter as tk
        from tkinter import filedialog, ttk
        app = tk.Tk()
    except Exception as exc:
        raise RuntimeError("Launcher legado requer Python Tk e sessão gráfica. Para a rota atual use o Codex nesta conversa ou python -m minestory native --help") from exc
    app.title("MineStory — diagnóstico legado Blender")
    app.geometry("680x460")
    ttk.Label(app,text="Selecione sua narração finalizada",font=("sans",17)).pack(pady=18)
    quality = tk.StringVar(value="preview")
    ttk.Combobox(app,textvariable=quality,values=["preview","final"],state="readonly").pack()
    messages = queue.Queue()
    text = tk.Text(app,wrap="word",height=18)
    text.pack(fill="both",expand=True,padx=14,pady=14)
    def worker(path):
        proc = subprocess.Popen([sys.executable,"-m","minestory","produce",path,"--quality",quality.get(),"--legacy-blender"],
                                cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in proc.stdout:
            messages.put(line)
        proc.wait()
        messages.put(f"\nProcesso terminou com código {proc.returncode}\n")
        messages.put(None)
    def select():
        path = filedialog.askopenfilename(filetypes=[("Narração","*.mp3 *.wav *.m4a *.flac *.ogg"),("Todos","*")])
        if path:
            button.config(state="disabled")
            threading.Thread(target=worker,args=(path,),daemon=True).start()
    button = ttk.Button(app,text="Selecionar áudio e produzir",command=select)
    button.pack(pady=10)
    def poll():
        while not messages.empty():
            message = messages.get_nowait()
            if message is None:
                button.config(state="normal")
            else:
                text.insert("end",message)
                text.see("end")
        app.after(200,poll)
    poll()
    app.mainloop()
