"""Conservative Windows focus recovery for grandMA2 onPC."""
import ctypes as C
from ctypes import wintypes as W
import sys,time
TARGET_EXE="gma2onpc.exe"
GA_ROOT=2
PROCESS_QUERY_LIMITED_INFORMATION=0x1000
class GUIThreadInfo(C.Structure):
    _fields_=[("cbSize",W.DWORD),("flags",W.DWORD),("hwndActive",W.HWND),("hwndFocus",W.HWND),("hwndCapture",W.HWND),("hwndMenuOwner",W.HWND),("hwndMoveSize",W.HWND),("hwndCaret",W.HWND),("rcCaret",W.RECT)]
class WinAPI:
    def __init__(self):
        if sys.platform!="win32":raise RuntimeError("Windows required")
        u=C.WinDLL("user32",use_last_error=True)
        k=C.WinDLL("kernel32",use_last_error=True)
        def bind(lib,name,args,ret):
            fn=getattr(lib,name);fn.argtypes=args;fn.restype=ret;return fn
        self.foreground=bind(u,"GetForegroundWindow",[],W.HWND)
        self.ancestor=bind(u,"GetAncestor",[W.HWND,W.UINT],W.HWND)
        self.from_point=bind(u,"WindowFromPoint",[W.POINT],W.HWND)
        self.cursor=bind(u,"GetCursorPos",[C.POINTER(W.POINT)],W.BOOL)
        self.key=bind(u,"GetAsyncKeyState",[C.c_int],W.SHORT)
        self.thread_pid=bind(u,"GetWindowThreadProcessId",[W.HWND,C.POINTER(W.DWORD)],W.DWORD)
        self.gui=bind(u,"GetGUIThreadInfo",[W.DWORD,C.POINTER(GUIThreadInfo)],W.BOOL)
        self.set_foreground=bind(u,"SetForegroundWindow",[W.HWND],W.BOOL)
        self.attach=bind(u,"AttachThreadInput",[W.DWORD,W.DWORD,W.BOOL],W.BOOL)
        self.current_tid=bind(k,"GetCurrentThreadId",[],W.DWORD)
        self.open_process=bind(k,"OpenProcess",[W.DWORD,W.BOOL,W.DWORD],W.HANDLE)
        self.image_name=bind(k,"QueryFullProcessImageNameW",[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)],W.BOOL)
        self.close_handle=bind(k,"CloseHandle",[W.HANDLE],W.BOOL)
        self.is_window=bind(u,"IsWindow",[W.HWND],W.BOOL)
class FocusEngine:
    def __init__(self,api=None):
        self.api=api or WinAPI()
        self.cache={}
    def root(self,hwnd):
        return int(self.api.ancestor(hwnd,GA_ROOT) or hwnd or 0)
    def tid_pid(self,hwnd):
        pid=W.DWORD()
        tid=self.api.thread_pid(hwnd,C.byref(pid)) if hwnd else 0
        return int(tid),int(pid.value)
    def process_name(self,pid):
        if not pid:return ""
        now=time.monotonic()
        cached=self.cache.get(pid)
        if cached and now-cached[0]<3:return cached[1]
        name=""
        handle=self.api.open_process(PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
        if handle:
            try:
                buf=C.create_unicode_buffer(32768)
                size=W.DWORD(len(buf))
                if self.api.image_name(handle,0,buf,C.byref(size)):
                    name=buf.value.rsplit("\\",1)[-1].lower()
            finally:self.api.close_handle(handle)
        self.cache[pid]=(now,name)
        return name
    def is_ma2(self,hwnd):
        return self.process_name(self.tid_pid(hwnd)[1])==TARGET_EXE
    def snapshot(self,target):
        fg=int(self.api.foreground() or 0)
        tid,_=self.tid_pid(fg)
        info=GUIThreadInfo();info.cbSize=C.sizeof(info)
        good=bool(tid and self.api.gui(tid,C.byref(info)))
        return {"foreground":fg,"focus":int(info.hwndFocus or 0) if good else 0,"active":int(info.hwndActive or 0) if good else 0,"target":int(target)}
    def verify(self,snap):
        return bool(self.is_ma2(snap["foreground"]) and snap["focus"] and self.is_ma2(snap["focus"]))
    def recover(self,clicked,mode="safe"):
        clicked=self.root(clicked)
        before=self.snapshot(clicked)
        if not self.is_ma2(clicked):return {"status":"ignored","before":before}
        if self.verify(before):return {"status":"verified","before":before}
        if mode=="observe":return {"status":"observed","before":before}
        if not self.api.is_window(clicked):return {"status":"window_closed","before":before}
        current=int(self.api.current_tid())
        target_tid,_=self.tid_pid(clicked)
        fg_tid,_=self.tid_pid(before["foreground"])
        attached=[]
        try:
            for tid in dict.fromkeys((target_tid,fg_tid)):
                if tid and tid!=current and self.api.attach(current,tid,True):attached.append(tid)
            called=bool(self.api.set_foreground(clicked))
            after=self.snapshot(clicked)
            return {"status":"recovered" if self.verify(after) else "unresolved","called":called,"before":before,"after":after}
        finally:
            for tid in reversed(attached):self.api.attach(current,tid,False)
    def clicked_window(self):
        pt=W.POINT()
        if not self.api.cursor(C.byref(pt)):return 0
        return self.root(self.api.from_point(pt))
