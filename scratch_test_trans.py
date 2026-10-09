import os
os.environ["WEBVIEW2_DEFAULT_BACKGROUND_COLOR"] = "0"

import clr, time, ctypes, threading
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
from System.Windows.Forms import Form, Application, DockStyle, FormBorderStyle, FormStartPosition
from System.Drawing import Color, Point
clr.AddReference(r'C:\Users\coco\AppData\Roaming\Python\Python314\site-packages\webview\lib\Microsoft.Web.WebView2.WinForms.dll')
from Microsoft.Web.WebView2.WinForms import WebView2

class MARGINS(ctypes.Structure):
    _fields_ = [('l', ctypes.c_int), ('r', ctypes.c_int), ('t', ctypes.c_int), ('b', ctypes.c_int)]

f = Form()
f.Width = 700
f.Height = 360
f.FormBorderStyle = getattr(FormBorderStyle, 'None')
f.TopMost = True
f.StartPosition = FormStartPosition.Manual
f.Location = Point(500, 0)
f.BackColor = Color.Black

hwnd = f.Handle.ToInt64()
margins = MARGINS(-1, -1, -1, -1)
ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

wv = WebView2()
wv.Dock = DockStyle.Fill
wv.DefaultBackgroundColor = Color.Transparent
f.Controls.Add(wv)

def on_init(sender, args):
    wv.DefaultBackgroundColor = Color.Transparent
    html = '<!doctype html><html><body style="background:transparent;"><h1 style="color:red;">TEST</h1></body></html>'
    wv.NavigateToString(html)

wv.CoreWebView2InitializationCompleted += on_init

def check_pixel():
    time.sleep(2.0)
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hdc = user32.GetDC(0)
    pix = gdi32.GetPixel(hdc, 510, 10)
    user32.ReleaseDC(0, hdc)
    r = pix & 0xFF
    g = (pix >> 8) & 0xFF
    b = (pix >> 16) & 0xFF
    print(f'Pixel at (510, 10): RGB({r}, {g}, {b})')
    time.sleep(0.5)
    f.Close()

threading.Thread(target=check_pixel, daemon=True).start()
Application.Run(f)
