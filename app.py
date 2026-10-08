"""SOWN Focus Manager: compact Windows-only grandMA2 focus monitor."""
import os, sys, time, queue, json, threading, logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
import customtkinter as ctk
from PIL import Image
from focus_engine import FocusEngine

ROOT=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"SOWNLighting"/"FocusManager"
ROOT.mkdir(parents=True,exist_ok=True)
CONF=ROOT/"settings.json"
LOG=ROOT/"focus_manager.log"
ASSET=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"assets"
def resource(filename): return ASSET/filename
def register_font():
    if sys.platform!="win32": return False
    try:
        import ctypes
        dll=ctypes.WinDLL("gdi32",use_last_error=True)
        f=dll.AddFontResourceExW
        f.argtypes=[ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_void_p]
        f.restype=ctypes.c_int
        return bool(f(str(resource("Poppins-Bold.ttf")),0x10,None))
    except Exception: return False

class App:
    BG="#09090B"; CARD="#17171B"; RED="#E53935"; WHITE="#F4F4F5"; GRAY="#92929D"
    def __init__(self):
        self.font="Poppins" if register_font() else "Segoe UI"
        self.events=queue.Queue(maxsize=300)
        self.settings={"monitor":True}
        try:self.settings.update(json.loads(CONF.read_text(encoding="utf-8")))
        except (OSError,ValueError,TypeError):pass
        self.settings["monitor"]=bool(self.settings.get("monitor",True))
        self.stop=threading.Event()
        self.count={"clicks":0,"verified":0,"attempts":0,"recovered":0}
        self.engine=FocusEngine()
        self.logger=logging.getLogger("SOWN")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            h=RotatingFileHandler(LOG,maxBytes=2000000,backupCount=3,encoding="utf-8")
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(h)
        ctk.set_appearance_mode("dark")
        self.root=ctk.CTk(fg_color=self.BG)
        self.root.title("SOWN Focus Manager")
        self.root.geometry("530x525")
        self.root.resizable(False,False)
        try:self.root.iconbitmap(str(resource("app.ico")))
        except Exception:pass
        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.tray=None
        self.draw()
        threading.Thread(target=self.watch,daemon=True).start()
        self.root.after(150,self.refresh)
        self.tray_start()
        self.report("START","Safe monitoring started")

    def report(self,kind,msg):
        self.logger.info("%s %s",kind,msg)
        try:self.events.put_nowait((time.strftime("%H:%M:%S"),kind,msg))
        except queue.Full:pass

    def draw(self):
        body=ctk.CTkFrame(self.root,fg_color="transparent")
        body.pack(fill="both",expand=True,padx=28,pady=24)
        row=ctk.CTkFrame(body,fg_color="transparent")
        row.pack(fill="x")
        try:
            pic=Image.open(resource("logo.jpg"))
            self.logo=ctk.CTkImage(light_image=pic,dark_image=pic,size=(100,88))
            ctk.CTkLabel(row,text="",image=self.logo,width=100).pack(side="left",padx=(0,15))
        except Exception:
            ctk.CTkLabel(row,text="SL",font=(self.font,26,"bold"),width=100,text_color=self.RED).pack(side="left")
        title=ctk.CTkFrame(row,fg_color="transparent")
        title.pack(side="left",fill="x",expand=True)
        ctk.CTkLabel(title,text="SOWN FOCUS",font=(self.font,23,"bold"),text_color=self.WHITE,anchor="w").pack(fill="x")
        ctk.CTkLabel(title,text="grandMA2  /  Focus Manager",font=(self.font,12,"bold"),text_color=self.GRAY,anchor="w").pack(fill="x")

        panel=ctk.CTkFrame(body,corner_radius=18,fg_color=self.CARD)
        panel.pack(fill="x",pady=(26,14))
        inside=ctk.CTkFrame(panel,fg_color="transparent")
        inside.pack(fill="x",padx=22,pady=20)
        self.status=ctk.CTkLabel(inside,text="",font=(self.font,16,"bold"),anchor="w")
        self.status.pack(fill="x",pady=(0,18))
        self.button=ctk.CTkButton(inside,text="",height=43,corner_radius=12,fg_color=self.RED,
            hover_color="#BA2926",font=(self.font,13,"bold"),command=self.toggle)
        self.button.pack(fill="x")
        stats=ctk.CTkFrame(body,fg_color="transparent")
        stats.pack(fill="x",pady=(4,15))
        self.values={}
        for i,(key,label) in enumerate((("clicks","MA2 CLICKS"),("verified","FOCUS OK"),("attempts","ATTEMPTS"),("recovered","RECOVERED"))):
            stats.grid_columnconfigure(i,weight=1,uniform="stat")
            cell=ctk.CTkFrame(stats,fg_color=self.CARD,corner_radius=14)
            cell.grid(row=0,column=i,sticky="nsew",padx=(0 if i==0 else 4,0 if i==3 else 4))
            val=ctk.CTkLabel(cell,text="0",font=(self.font,23,"bold"),text_color=self.WHITE)
            val.pack(pady=(14,0))
            ctk.CTkLabel(cell,text=label,font=(self.font,10,"bold"),text_color=self.GRAY).pack(pady=(0,13))
            self.values[key]=val
        footer=ctk.CTkFrame(body,fg_color="transparent")
        footer.pack(side="bottom",fill="x")
        self.activity=ctk.CTkLabel(footer,text="Ready",font=(self.font,11,"bold"),anchor="w",text_color=self.GRAY)
        self.activity.pack(fill="x",pady=(0,12))
        self.update_status()

    def update_status(self):
        active=self.settings["monitor"]
        self.status.configure(text="●  MONITORING" if active else "●  PAUSED",
            text_color="#4ADE80" if active else "#FBBF24")
        self.button.configure(text="PAUSE" if active else "RESUME")

    def toggle(self):
        self.settings["monitor"]=not self.settings["monitor"]
        try:CONF.write_text(json.dumps(self.settings),encoding="utf-8")
        except OSError:pass
        self.update_status()
        self.report("INFO","Monitoring "+("resumed" if self.settings["monitor"] else "paused"))

    def watch(self):
        previous=False
        while not self.stop.is_set():
            try:
                down=bool(self.engine.api.key(1)&0x8000)
                if self.settings["monitor"] and down and not previous:
                    target=self.engine.clicked_window()
                    if target and self.engine.is_ma2(target):
                        self.count["clicks"]+=1
                        if self.stop.wait(0.09):break
                        if self.settings["monitor"]:
                            result=self.engine.recover(target,"safe")
                            state=result["status"]
                            if state=="verified":self.count["verified"]+=1
                            if state in ("recovered","unresolved"):self.count["attempts"]+=1
                            if state=="recovered":self.count["recovered"]+=1
                            self.report("FOCUS",state+" target="+str(target))
                previous=down
            except Exception as ex:
                self.report("ERROR",repr(ex))
                self.stop.wait(0.5)
            self.stop.wait(0.02)

    def refresh(self):
        if self.stop.is_set():return
        for _ in range(60):
            try:timestamp,kind,msg=self.events.get_nowait()
            except queue.Empty:break
            self.activity.configure(text="["+timestamp+"]  "+kind+" · "+msg[:65])
        for key,widget in self.values.items():widget.configure(text=str(self.count[key]))
        self.root.after(150,self.refresh)

    def tray_start(self):
        try:
            import pystray
            ico=Image.open(resource("logo.jpg")).convert("RGBA")
            menu=pystray.Menu(
                pystray.MenuItem("Open",lambda *_:self.root.after(0,self.show)),
                pystray.MenuItem("Pause / Resume",lambda *_:self.root.after(0,self.toggle)),
                pystray.MenuItem("Exit",lambda *_:self.root.after(0,self.quit)))
            self.tray=pystray.Icon("SOWNFocus",ico,"SOWN Focus Manager",menu)
            threading.Thread(target=self.tray.run,daemon=True).start()
        except Exception as ex:self.report("WARN","Tray unavailable: "+repr(ex))
    def show(self):
        self.root.deiconify()
        self.root.lift()
    def close(self):
        if self.tray:self.root.withdraw()
        else:self.quit()
    def quit(self):
        self.stop.set()
        if self.tray:
            try:self.tray.stop()
            except Exception:pass
        self.root.destroy()

if __name__=="__main__":
    if sys.platform!="win32":raise SystemExit("Windows required")
    App().root.mainloop()
