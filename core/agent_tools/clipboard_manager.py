import time
import ctypes
from ctypes import wintypes
from typing import Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# Configuration 64-bit des signatures ctypes Win32
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]


class ClipboardManager:
    """
    Gestionnaire natif du presse-papier Windows sans dépendance externe (Win32 API).
    Inspiré de CursorTouch/Windows-MCP pour l'automatisation système instantanée.
    Intègre les retries en cas de contention d'accès par d'autres applications.
    """
    @staticmethod
    def _open_clipboard(max_retries: int = 5, delay: float = 0.02) -> bool:
        """Tente d'ouvrir le presse-papier avec réessais en cas de verrouillage temporaire."""
        for _ in range(max_retries):
            if user32.OpenClipboard(None):
                return True
            time.sleep(delay)
        return False

    @staticmethod
    def get_text() -> str:
        """Récupère le texte actuellement présent dans le presse-papier Windows."""
        try:
            if not ClipboardManager._open_clipboard():
                return ""
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return ""
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return ""
                try:
                    return ctypes.wstring_at(ptr)
                finally:
                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        except Exception:
            return ""

    @staticmethod
    def set_text(text: str) -> bool:
        """Copie une chaîne de caractères dans le presse-papier Windows (CF_UNICODETEXT)."""
        if text is None:
            text = ""
        try:
            buf = ctypes.create_unicode_buffer(text)
            byte_len = ctypes.sizeof(buf)

            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_len)
            if not h_mem:
                return False

            ptr = kernel32.GlobalLock(h_mem)
            if not ptr:
                kernel32.GlobalFree(h_mem)
                return False

            ctypes.memmove(ptr, buf, byte_len)
            kernel32.GlobalUnlock(h_mem)

            if not ClipboardManager._open_clipboard():
                kernel32.GlobalFree(h_mem)
                return False

            try:
                user32.EmptyClipboard()
                res = user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                if not res:
                    kernel32.GlobalFree(h_mem)
                    return False
                return True
            finally:
                user32.CloseClipboard()
        except Exception:
            return False

    @staticmethod
    def clear() -> bool:
        """Efface le contenu du presse-papier."""
        try:
            if not ClipboardManager._open_clipboard():
                return False
            try:
                return bool(user32.EmptyClipboard())
            finally:
                user32.CloseClipboard()
        except Exception:
            return False
