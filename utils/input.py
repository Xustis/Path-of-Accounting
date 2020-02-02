import time
from queue import Queue
from threading import Thread
from tkinter import TclError

import pyperclip

import os
from utils.config import STASHTAB_SCROLLING
if os.name == "nt" and STASHTAB_SCROLLING:
    import win32con
    import ctypes
    import atexit
    import sys
    from ctypes import *
    from ctypes.wintypes import DWORD, WPARAM, LPARAM, ULONG, POINT
    from multiprocessing import Process
    from win32gui import GetWindowText, GetForegroundWindow


is_keyboard_module_available = False
try:
    # This will raise error in case user is not running as root
    import keyboard

    keyboard.add_hotkey("x", lambda: print())
    keyboard.remove_hotkey("x")
    is_keyboard_module_available = True
except Exception:
    is_keyboard_module_available = False

is_pyinput_module_available = False
if not is_keyboard_module_available:
    try:
        # This will raise error if there is no display environment
        from pynput.keyboard import GlobalHotKeys, Controller, Key

        is_pyinput_module_available = True
    except Exception:
        is_pyinput_module_available = False


def get_clipboard():
    return pyperclip.paste()


class ClipboardWatcher(Thread):
    """
    Watches for changes in clipboard and calls callback.
    """

    def __init__(self, callback, should_process, pause=0.3):
        super(ClipboardWatcher, self).__init__()
        self.daemon = True
        self.callback = callback
        self.should_process = should_process
        self.pause = pause
        self.stopping = False
        # Clear the clipboard
        pyperclip.copy("")

    def run(self):
        prev = ""

        while not self.stopping:
            try:
                text = get_clipboard()

                if text != prev and self.should_process():
                    self.callback(text)

                prev = text
                time.sleep(self.pause)
            except (TclError, UnicodeDecodeError):  # ignore non-text clipboard contents
                continue
            except KeyboardInterrupt:
                break

    def stop(self):
        self.stopping = True


class HotkeyWatcher(Thread):
    """
    Watches for changes in hotkey queue and calls callbacks
    """

    def __init__(self, combination_to_function):
        super(HotkeyWatcher, self).__init__()
        self.daemon = True
        self.combination_to_function = combination_to_function
        self.stopping = False
        self.queue = Queue()

    def is_empty(self):
        return self.queue.unfinished_tasks == 0 and self.queue.qsize() == 0

    def push(self, hotkey):
        if self.is_empty():
            self.queue.put(hotkey)

    def run(self):
        while not self.stopping:
            try:
                hotkey = self.queue.get()
                self.combination_to_function[hotkey]()
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Do not fail
                print("Unexpected exception occurred while handling hotkey: " + str(e))

            self.queue.task_done()

    def stop(self):
        self.stopping = True


class Keyboard:
    CLIPBOARD_HOTKEY = "<ctrl>+c"

    def __init__(self):
        self.combination_to_function = {}
        self.hotkey_watcher = None
        self.clipboard_watcher = None
        self.clipboard_callback = None

        # For Stashtab Scrolling
        self.enabled = False
        self.keyboard_hook = None
        self.mouse_hook = None
        self.ctrl_pressed = False

        if is_pyinput_module_available:
            self.controller = Controller()
            self.listener = None

    def add_hotkey(self, hotkey, fun):
        self.combination_to_function[hotkey] = fun

    def start(self):
        # Create hotkey watcher with all our hotkey callbacks
        self.hotkey_watcher = HotkeyWatcher(self.combination_to_function)
        self.clipboard_watcher = ClipboardWatcher(self.clipboard_callback, self.hotkey_watcher.is_empty)
        combination_to_queue = {}

        def to_watcher(watcher, hotkey):
            return lambda: watcher.push(hotkey)

        # Convert hotkey callbacks to proxy everything to hotkey watcher
        for h in self.combination_to_function:
            combination_to_queue[h] = to_watcher(self.hotkey_watcher, h)

        if is_keyboard_module_available:
            for h in combination_to_queue:
                keyboard.add_hotkey(h.replace("<", "").replace(">", ""), combination_to_queue[h])
        elif is_pyinput_module_available:
            self.listener = GlobalHotKeys(combination_to_queue)
            self.listener.daemon = True
            self.listener.start()

        if is_keyboard_module_available or is_pyinput_module_available:
            self.hotkey_watcher.start()

        self.clipboard_watcher.start()

    def wait(self):
        self.clipboard_watcher.join()

    def write(self, string):
        if is_keyboard_module_available:
            keyboard.write(string)
        elif is_pyinput_module_available:
            self.controller.type(string)

    def press_and_release(self, key):
        if is_keyboard_module_available:
            keyboard.press_and_release(key)
        elif is_pyinput_module_available:

            def safe_press(controller, k, press=True):
                try:
                    # Lazy way to try and convert special key to enum
                    k = Key[k]
                except Exception:
                    pass

                if press:
                    controller.press(k)
                else:
                    controller.release(k)

            keys = key.split("+")

            if len(keys) == 2:
                # Press first key, then second key, then release second key and finally release first key
                safe_press(self.controller, keys[0])
                safe_press(self.controller, keys[1])
                safe_press(self.controller, keys[1], False)
                safe_press(self.controller, keys[0], False)
            elif len(keys) == 1:
                safe_press(self.controller, keys[0])
                safe_press(self.controller, keys[0], False)

    
    def enable_hook(self, keyboard_callback, mouse_callback):
        if self.enabled:
            return
        self.enabled = True
        self.keyboard_hook = windll.user32.SetWindowsHookExA(win32con.WH_KEYBOARD_LL, keyboard_callback, windll.kernel32.GetModuleHandleW(None),0)
        self.mouse_hook = windll.user32.SetWindowsHookExA(win32con.WH_MOUSE_LL, mouse_callback, windll.kernel32.GetModuleHandleW(None),0)
        atexit.register(windll.user32.UnhookWindowsHookEx, self.keyboard_hook)
        atexit.register(windll.user32.UnhookWindowsHookEx, self.mouse_hook)
    def disable_hook(self):
        if not self.enabled:
            return
        self.enabled = False
        windll.user32.UnhookWindowsHookEx(self.keyboard_hook)
        windll.user32.UnhookWindowsHookEx(self.mouse_hook)
        self.keyboard_hook = None
        self.mouse_hook = None
    def run_stash_macro(self):
        while self.enabled:
            try:
                msg = ctypes.wintypes.MSG()
                windll.user32.GetMessageA(byref(msg), 0, 0, 0)
                windll.user32.TranslateMessage(msg)
                windll.user32.DispatchMessageA(msg)
            except:
                pass
        disable()


if os.name == "nt" and STASHTAB_SCROLLING:

    class KBDLLHOOKSTRUCT(Structure): _fields_=[('vkCode',DWORD),('scanCode',DWORD),('flags',DWORD),('time',DWORD),('dwExtraInfo',ULONG)]
    kb_macro = Keyboard()
    def keyboard_callback(ncode, wparam, lparam):
        if ncode < 0:
            return windll.user32.CallNextHookEx(kb_macro.keyboard_hook, ncode, wparam, lparam)
        if GetWindowText(GetForegroundWindow()) == "Path of Exile":
            key = KBDLLHOOKSTRUCT.from_address(lparam)
            if key.vkCode == win32con.VK_LCONTROL:
                if wparam == win32con.WM_KEYDOWN:
                    kb_macro.ctrl_pressed = True
                elif wparam == win32con.WM_KEYUP:
                    kb_macro.ctrl_pressed = False
        return windll.user32.CallNextHookEx(kb_macro.keyboard_hook, ncode, wparam, lparam)



    class MSLLHOOKSTRUCT(Structure): _fields_=[('pt',POINT),('mouseData',DWORD),('flags',DWORD),('time',DWORD),('dwExtraInfo',ULONG)]

    def mouse_callback(ncode, wparam, lparam):
        if ncode < 0:
            return windll.user32.CallNextHookEx(kb_macro.keyboard_hook, ncode, wparam, lparam)
        if kb_macro.ctrl_pressed and GetWindowText(GetForegroundWindow()) == "Path of Exile" and wparam == win32con.WM_MOUSEWHEEL:
            data = MSLLHOOKSTRUCT.from_address(lparam)
            a = ctypes.c_short(data.mouseData >> 16).value
            if a > 0: # up
                    kb_macro.press_and_release("left")
                    return 1
            elif a < 0: # down
                    kb_macro.press_and_release("right")
                    return 1 
        return windll.user32.CallNextHookEx(kb_macro.keyboard_hook, ncode, wparam, lparam)


    def setup():
        #                               (this, ncode, wparam, lparam)
        c_func = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, WPARAM, LPARAM)
        kc = c_func(keyboard_callback)
        mc = c_func(mouse_callback)
        kb_macro.enable_hook(kc,mc)
        kb_macro.run_stash_macro()

    
    p = Process(target=setup, args=())

def start_stash_scroll():
    if os.name == "nt" and STASHTAB_SCROLLING:
        p.daemon = True
        p.start()
def stop_stash_scroll():
    if os.name == "nt" and STASHTAB_SCROLLING:
        kb_macro.disable_hook()
        p.terminate()