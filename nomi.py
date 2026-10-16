import base64
import io
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat, ImageTk
# =====================================================================
# SECTION 1 - KONSTANTA DESAIN
# =====================================================================
DW, DH = 1080, 1920
CARD = (108, 228, 972, 1720)      # kartu kaca (x1, y1, x2, y2)
CARD_R = 70                       # lengkungan sudut kartu
ICON = (440, 147, 640, 347)       # logo aplikasi
ICON_R = 28
PILL_EMAIL = (147, 861, 927, 992)  # kolom email
PILL_PW = (147, 1071, 927, 1203)   # kolom password
BTN = (147, 1394, 927, 1546)       # tombol Continue
# Warna
RED = "#C83D3C"           # tulisan NOMI
GRAY = "#737373"          # subjudul
LINK = "#7CB9C6"          # link "Sudah punya akun? Login"
ERROR = "#C83D3C"
SUCCESS = "#2E9E7A"
PILL_RGB = (251, 242, 236)
BTN_COLORS = {"normal": (225, 94, 93), "hover": (212, 80, 80), "down": (196, 66, 66)}
# Titik warna gradient background: (kiri, tengah, kanan) pada 5 tinggi layar
XK = [50 / 1080, 0.5, 1030 / 1080]
YK = [50 / 1920, 500 / 1920, 960 / 1920, 1400 / 1920, 1870 / 1920]
GRID = [
    [(231, 164, 129), (200, 196, 186), (184, 210, 214)],
    [(240, 176, 133), (220, 188, 167), (199, 201, 201)],
    [(245, 201, 157), (232, 188, 165), (220, 175, 174)],
    [(246, 212, 174), (240, 171, 157), (234, 131, 140)],
    [(246, 210, 177), (243, 147, 142), (238, 97, 116)],
]
# =====================================================================
# SECTION 2 - FUNGSI GAMBAR (gradient, grain, bentuk membulat)
# =====================================================================
def interp(knots, vals, t):
    """Interpolasi linear antar titik. Dipakai untuk menghitung warna gradient."""
    if t <= knots[0]:
        return vals[0]
    if t >= knots[-1]:
        return vals[-1]
    for i in range(len(knots) - 1):
        if knots[i] <= t <= knots[i + 1]:
            f = (t - knots[i]) / (knots[i + 1] - knots[i])
            return tuple(a + (b - a) * f for a, b in zip(vals[i], vals[i + 1]))
def make_gradient(w, h):
    """Buat gradient 4 sudut (oranye, biru, krem, merah muda) lalu diperhalus."""
    cw, ch = max(2, w // 6), max(2, h // 6)
    img = Image.new("RGB", (cw, ch))
    px = img.load()
    for y in range(ch):
        v = y / (ch - 1)
        for x in range(cw):
            u = x / (cw - 1)
            rows = [interp(XK, row, u) for row in GRID]
            px[x, y] = tuple(int(round(c)) for c in interp(YK, rows, v))
    return img.resize((w, h), Image.BICUBIC)
def add_grain(img, sigma):
    """Tambah efek 'noise' halus supaya terlihat seperti foto (grainy)."""
    noise = Image.effect_noise(img.size, sigma)
    noise = Image.merge("RGB", (noise, noise, noise))
    return ImageChops.add(img, noise, 1.0, -128)
def rr_mask(w, h, r):
    """Mask persegi membulat yang halus (anti-aliasing lewat supersampling 4x)."""
    ss = 4
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)
def hex_color(rgb):
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb)
# =====================================================================
# SECTION 3 - KELAS UTAMA: LoginScreen
# =====================================================================
class LoginScreen:
    def __init__(self, root, on_success=None):
        self.root = root
        self.on_success = on_success or self.default_success
        self.mode = "signup"          # "signup" atau "login"
        self.press_target = None
        # ---- ukuran jendela menyesuaikan tinggi layar ----
        sh = root.winfo_screenheight()
        sw = root.winfo_screenwidth()
        self.S = max(0.3, min(0.42, (sh - 120) / DH))
        self.W, self.H = round(DW * self.S), round(DH * self.S)
        root.title("Nomi")
        root.resizable(False, False)
        root.geometry(f"{self.W}x{self.H}+{(sw - self.W) // 2}+{max(0, (sh - self.H) // 2 - 30)}")
        # ---- pilih font ----
        installed = set(tkfont.families())
        self.family = next((f for f in ("Montserrat", "Poppins", "Plus Jakarta Sans",
                                        "Segoe UI", "Helvetica") if f in installed), "Helvetica")
        self.fonts = []               # simpan referensi font supaya tidak dihapus Python
        # ---- canvas + background ----
        self.canvas = tk.Canvas(root, width=self.W, height=self.H, highlightthickness=0, bd=0)
        self.canvas.pack()
        bg, self.entry_bg = self.build_background()
        self.bg_img = ImageTk.PhotoImage(bg)
        self.canvas.create_image(0, 0, image=self.bg_img, anchor="nw")
        self.draw_static_text()
        self.draw_title()
        self.draw_link()
        self.build_entries()
        self.build_button()
        self.msg = self.canvas.create_text(self.d(540), self.d(1300), text="", width=self.d(720),
                                           font=self.font(30, "bold"), fill=ERROR, justify="center")
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Leave>", self.on_leave)
        root.bind("<Return>", lambda e: self.submit())
        self.email.focus_set()
    # ---------- helper ukuran ----------
    def d(self, v):
        """Ubah ukuran desain (1080x1920) menjadi piksel layar."""
        return int(round(v * self.S))
    def box(self, b):
        return tuple(self.d(v) for v in b)
    def font(self, px, weight="normal"):
        f = tkfont.Font(family=self.family, size=-max(6, self.d(px)), weight=weight)
        self.fonts.append(f)
        return f
    def fit_font(self, text, px, weight, target):
        """Font yang ukurannya disesuaikan agar lebar teks = target (lebar di foto)."""
        f = self.font(px, weight)
        w = f.measure(text)
        if w > 0:
            size = max(6, int(round(abs(int(f.cget("size"))) * self.d(target) / w)))
            f = tkfont.Font(family=self.family, size=-size, weight=weight)
            self.fonts.append(f)
        return f
    # ---------- background kaca + gradient ----------
    def build_background(self):
        W, H = self.W, self.H
        bg = add_grain(make_gradient(W, H), 13)
        # kartu kaca: gradient dicampur 55% putih
        x1, y1, x2, y2 = self.box(CARD)
        w, h = x2 - x1, y2 - y1
        glass = Image.blend(bg.crop((x1, y1, x2, y2)), Image.new("RGB", (w, h), (255, 255, 255)), 0.55)
        bg.paste(glass, (x1, y1), rr_mask(w, h, self.d(CARD_R)))
        # bayangan logo
        ix1, iy1, ix2, iy2 = self.box(ICON)
        shadow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(shadow).rounded_rectangle(
            (ix1 + self.d(6), iy1 + self.d(14), ix2 - self.d(6), iy2 + self.d(10)),
            self.d(ICON_R), fill=110)
        shadow = shadow.filter(ImageFilter.GaussianBlur(self.d(10)))
        bg.paste((70, 45, 45), (0, 0, W, H), shadow)
        # logo (dibaca dari data base64 di bawah file)
        logo = Image.open(io.BytesIO(base64.b64decode(LOGO_B64))).convert("RGB")
        logo = logo.resize((ix2 - ix1, iy2 - iy1), Image.LANCZOS)
        bg.paste(logo, (ix1, iy1), rr_mask(ix2 - ix1, iy2 - iy1, self.d(ICON_R)))
        # dua kolom input berbentuk pil
        entry_bg = {}
        for key, b in (("email", PILL_EMAIL), ("pw", PILL_PW)):
            x1, y1, x2, y2 = self.box(b)
            w, h = x2 - x1, y2 - y1
            pill = Image.blend(bg.crop((x1, y1, x2, y2)), Image.new("RGB", (w, h), PILL_RGB), 0.93)
            bg.paste(pill, (x1, y1), rr_mask(w, h, h // 2))
            mean = ImageStat.Stat(bg.crop((x1 + h // 2, y1 + h // 4, x2 - h // 2, y2 - h // 4))).mean
            entry_bg[key] = hex_color(mean)   # warna Entry = warna pil di bawahnya
        return bg, entry_bg
    # ---------- teks ----------
    def spaced(self, text, x, y, font, target, fill, anchor="center", tag=None):
        """Tulis teks huruf per huruf dengan jarak antar huruf (letter-spacing)."""
        widths = [font.measure(ch) for ch in text]
        n = len(text)
        gap = (self.d(target) - sum(widths)) / (n - 1) if n > 1 else 0
        gap = max(-self.d(4), min(self.d(40), gap))
        total = sum(widths) + gap * (n - 1)
        left = x - total / 2 if anchor == "center" else x
        cx = left
        for ch, w in zip(text, widths):
            self.canvas.create_text(cx, y, text=ch, font=font, fill=fill, anchor="w", tags=tag)
            cx += w + gap
        return left, total
    def draw_static_text(self):
        c = self.canvas
        self.spaced("NOMI", self.d(540), self.d(455), self.font(120, "bold"), 392, RED)
        head = "Find people who get you"
        c.create_text(self.d(538), self.d(556), text=head, fill="#000000",
                      font=self.fit_font(head, 46, "bold", 596))
        f = self.font(28)
        self.spaced("Temukan orang yang dengan selera & minat", self.d(538), self.d(606), f, 695, GRAY)
        self.spaced("yang serupa.", self.d(538), self.d(638), f, 201, GRAY)
        self.spaced("Email", self.d(192), self.d(839), self.font(27), 76, "#000000", anchor="left")
        self.spaced("Password", self.d(182), self.d(1049), self.font(27), 180,
                    "#000000", anchor="left")
    def draw_title(self):
        self.canvas.delete("title")
        text = "Sign up" if self.mode == "signup" else "Login"
        self.canvas.create_text(self.d(537), self.d(760), text=text, fill="#000000", tags="title",
                                font=self.fit_font(text, 48, "bold", 26 * len(text)))
    def draw_link(self):
        self.canvas.delete("link")
        text = ("Sudah punya akun? Login" if self.mode == "signup"
                else "Belum punya akun? Sign up")
        y = self.d(1582)
        left, total = self.spaced(text, self.d(537), y, self.font(28), 16.3 * len(text), LINK, tag="link")
        self.canvas.create_line(left, y + self.d(16), left + total, y + self.d(16),
                                fill=LINK, width=max(1, self.d(2)), tags="link")
    # ---------- kolom input & tombol ----------
    def build_entries(self):
        self.email = self.make_entry(PILL_EMAIL, "email")
        self.pw = self.make_entry(PILL_PW, "pw", show="•")
    def make_entry(self, b, key, show=""):
        x1, y1, x2, y2 = self.box(b)
        e = tk.Entry(self.canvas, font=self.font(34), bd=0, relief="flat", highlightthickness=0,
                     bg=self.entry_bg[key], fg="#222222", insertbackground="#222222", show=show)
        self.canvas.create_window((x1 + x2) // 2, (y1 + y2) // 2, window=e,
                                  width=(x2 - x1) - self.d(120), height=self.d(70))
        return e
    def build_button(self):
        x1, y1, x2, y2 = self.box(BTN)
        w, h = x2 - x1, y2 - y1
        self.btn_imgs = {}
        for name, rgb in BTN_COLORS.items():
            img = Image.new("RGBA", (w, h), rgb + (255,))
            img.putalpha(rr_mask(w, h, h // 2))
            self.btn_imgs[name] = ImageTk.PhotoImage(img)
        self.btn_box = (x1, y1, x2, y2)
        self.btn_item = self.canvas.create_image(x1, y1, image=self.btn_imgs["normal"], anchor="nw")
        text = "Continue"
        self.canvas.create_text(self.d(537), self.d(1470), text=text, fill="#FFFFFF",
                                font=self.fit_font(text, 48, "bold", 218))
    # ---------- interaksi mouse ----------
    @staticmethod
    def inside(x, y, b):
        return b[0] <= x <= b[2] and b[1] <= y <= b[3]
    def hit(self, e):
        if self.inside(e.x, e.y, self.btn_box):
            return "btn"
        return None
    def set_btn(self, state):
        self.canvas.itemconfig(self.btn_item, image=self.btn_imgs[state])
    def on_motion(self, e):
        t = self.hit(e)
        self.canvas.config(cursor="hand2" if t else "")
        if self.press_target is None:
            self.set_btn("hover" if t == "btn" else "normal")
    def on_leave(self, e):
        self.canvas.config(cursor="")
        self.set_btn("normal")
    def on_press(self, e):
        self.press_target = self.hit(e)
        if self.press_target == "btn":
            self.set_btn("down")
    def on_release(self, e):
        t, started = self.hit(e), self.press_target
        self.press_target = None
        self.set_btn("hover" if t == "btn" else "normal")
        if t == started == "btn":       # tombol hanya aktif jika ditekan & dilepas di tempat sama
            self.submit()
    # ---------- logika ----------
    def show_msg(self, text, color=ERROR):
        self.canvas.itemconfig(self.msg, text=text, fill=color)
    def submit(self):
        email, pw = self.email.get().strip(), self.pw.get()
        self.show_msg("")
        self.on_success(email, self.mode)
    def default_success(self, email, mode):
        """Ganti fungsi ini untuk pindah ke halaman berikutnya (Profil / Homepage)."""
        aksi = "Akun dibuat" if mode == "signup" else "Berhasil masuk"
        self.show_msg(f"{aksi}! Lanjut ke halaman berikutnya.", SUCCESS)
# =====================================================================
# SECTION 4 - DATA LOGO (base64) + MAIN
# =====================================================================
LOGO_B64 = "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"
import math
# =====================================================================
# KONSTANTA - semua koordinat memakai piksel PDF desain (819 x 1456)
# =====================================================================
K = 1080 / 819                       # PDF px -> ukuran desain 1080 px
CARD_P = (82, 173, 737, 1304)        # kartu kaca (sama dengan halaman login)
CORAL = (225, 94, 93)
DARKRED = (200, 58, 58)
TEAL = (122, 184, 196)
ORANGE = (251, 155, 100)
WHITE = (255, 255, 255)
CREAM = (252, 244, 225)
DISC_GRID = [[(243, 196, 162), (224, 216, 202), (214, 226, 222)],
             [(236, 216, 186), (232, 214, 196), (236, 186, 182)],
             [(232, 226, 202), (240, 192, 182), (222, 152, 166)]]
MATCH_GRID = [[(176, 186, 216), (236, 128, 108), (246, 150, 112)],
              [(222, 115, 100), (232, 108, 98), (240, 125, 100)],
              [(226, 96, 96), (225, 92, 92), (228, 100, 98)],
              [(232, 110, 100), (232, 105, 95), (236, 120, 105)],
              [(246, 176, 24), (245, 165, 60), (242, 176, 152)]]
PROFILES = [
    dict(name="Aryo, 67", match="86% match", score=86, quote="\u201cGod is number one.\u201d",
         cols=((122, 177, 188), (125, 178, 187), (165, 196, 192), (238, 196, 168)),
         tags=[[("Action", 113, 241), ("Coffee", 264, 409), ("Dog", 430, 555), ("Pop", 578, 723)],
               [("Childfree", 113, 294), ("Games", 343, 486), ("Photography", 520, 712)]]),
    dict(name="Angel, 50", match="64% match", score=64,
         quote="\u201cWork life balance as independent woman.\u201d",
         cols=((210, 95, 85), (218, 115, 100), (214, 135, 120), (245, 165, 130)),
         tags=[[("Korean Drama", 113, 318), ("Matcha", 341, 486), ("Turtle", 520, 684)],
               [("Feminism", 113, 294), ("Gym", 343, 486), ("Painting", 520, 701)]]),
    dict(name="Kareen, 19", match="83% match", score=83,
         quote="\u201cLiving a life of bliss.\u201d",
         cols=((252, 160, 108), (248, 185, 145), (240, 180, 140), (245, 218, 205)),
         tags=[[("Drama", 113, 241), ("Chocolate", 264, 409), ("Dog", 430, 555), ("RnB", 578, 723)],
               [("Travel", 113, 294), ("Slow living", 343, 520), ("Pop", 554, 712)]]),
]
QUIZ = [  # (judul, x teks, y teks, lebar teks, jenis ikon, [(label, x1, y1, x2, y2), ...])
    ("What your hobby?", 146, 278, 247, "hobby", [
        ("Film", 114, 308, 295, 364), ("Food & Drink", 305, 308, 487, 364), ("Music", 497, 308, 678, 364),
        ("Games", 114, 380, 295, 436), ("Study", 305, 380, 487, 436), ("Books", 497, 380, 678, 436),
        ("Travel", 215, 451, 396, 507), ("Art", 411, 451, 592, 507)]),
    ("Pets", 155, 546, 59, "pets", [
        ("Dog", 117, 577, 298, 633), ("Cat", 319, 577, 500, 633), ("Fish", 521, 577, 702, 633),
        ("Horse", 223, 648, 404, 704), ("Reptile", 430, 648, 611, 704)]),
    ("Lifestyle", 164, 751, 119, "life", [
        ("Fashion", 123, 781, 304, 837), ("Sport", 323, 781, 504, 837), ("Healthy", 523, 781, 704, 837),
        ("Slow Living", 222, 853, 404, 909), ("Active", 424, 852, 605, 908)]),
    ("Values", 167, 963, 91, "values", [
        ("Feminism", 124, 1001, 305, 1057), ("Social Politic", 324, 1001, 505, 1057),
        ("Mental Health", 524, 1001, 705, 1057), ("Childfree", 122, 1081, 303, 1137),
        ("Animal Welfare", 324, 1081, 514, 1137), ("Human Rights", 524, 1081, 705, 1137)]),
]
# =====================================================================
# FUNGSI GAMBAR TAMBAHAN
# =====================================================================
def smooth(rows, W, H):
    """Gradient halus dari grid warna kecil."""
    h, w = len(rows), len(rows[0])
    im = Image.new("RGB", (w, h))
    im.putdata([c for r in rows for c in r])
    return im.resize((W, H), Image.BICUBIC)
def tilt(c, w, h, n=24):
    """Gradient diagonal dari 4 sudut: (kiri-atas, kanan-atas, kiri-bawah, kanan-bawah)."""
    im = Image.new("RGB", (n, n))
    px = im.load()
    for y in range(n):
        v = y / (n - 1)
        for x in range(n):
            u = x / (n - 1)
            px[x, y] = tuple(int(c[0][i] * (1 - u) * (1 - v) + c[1][i] * u * (1 - v) +
                                 c[2][i] * (1 - u) * v + c[3][i] * u * v) for i in range(3))
    return im.resize((w, h), Image.BICUBIC)
def drop_shadow(img, dx, dy, blur, op):
    a = img.getchannel("A").point(lambda v: int(v * op))
    a = ImageChops.offset(a, int(dx), int(dy)).filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", img.size, (50, 30, 30, 255))
    sh.putalpha(a)
    return Image.alpha_composite(sh, img)
def over(base, *layers):
    base = base.convert("RGBA")
    for lay in layers:
        base = Image.alpha_composite(base, lay)
    return base
def heart(cx, cy, s, n=80):
    return [(cx + s * 16 * math.sin(t) ** 3,
             cy - s * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
            for t in (2 * math.pi * i / n for i in range(n))]
def sparkle(cx, cy, r):
    q = r * 0.25
    return [(cx, cy - r), (cx + q, cy - q), (cx + r, cy), (cx + q, cy + q),
            (cx, cy + r), (cx - q, cy + q), (cx - r, cy), (cx - q, cy - q)]
class Painter:
    """Kanvas gambar anti-aliasing (supersampling 3x). Koordinat = piksel PDF desain."""
    def __init__(self, W, H, k, ss=3):
        self.W, self.H, self.k, self.ss, self.f = W, H, k, ss, k * ss
        self.im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
        self.dr = ImageDraw.Draw(self.im)
    def pt(self, p):
        return (p[0] * self.f, p[1] * self.f)
    def bx(self, b):
        return tuple(v * self.f for v in b)
    def circle(self, cx, cy, r, fill=None, outline=None, w=0):
        self.dr.ellipse(self.bx((cx - r, cy - r, cx + r, cy + r)), fill=fill, outline=outline,
                        width=int(w * self.f))
    def ellipse(self, b, fill):
        self.dr.ellipse(self.bx(b), fill=fill)
    def rrect(self, b, r, fill):
        self.dr.rounded_rectangle(self.bx(b), r * self.f, fill=fill)
    def poly(self, pts, fill):
        self.dr.polygon([self.pt(p) for p in pts], fill=fill)
    def polyline(self, pts, w, fill, closed=False):
        pp = [self.pt(p) for p in pts]
        if closed:
            pp.append(pp[0])
        self.dr.line(pp, fill=fill, width=max(1, int(w * self.f)), joint="curve")
    def line(self, a, b, w, fill):
        self.dr.line([self.pt(a), self.pt(b)], fill=fill, width=max(1, int(w * self.f)))
        for p in (a, b):
            self.circle(p[0], p[1], w / 2, fill)
    def capsule(self, a, b, w, fill, outline=None, ow=0):
        if outline:
            self.line(a, b, w + 2 * ow, outline)
        self.line(a, b, w, fill)
    def dome(self, cx, base, rx, ry, fill):
        self.poly([(cx + rx * math.cos(i * math.pi / 60), base - ry * math.sin(i * math.pi / 60))
                   for i in range(61)], fill)
    def ellipse_in_circle(self, eb, c, fill):
        m1 = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(m1).ellipse(self.bx(eb), fill=255)
        m2 = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(m2).ellipse(self.bx((c[0] - c[2], c[1] - c[2], c[0] + c[2], c[1] + c[2])), fill=255)
        self.im.paste(Image.new("RGBA", self.im.size, fill), (0, 0), ImageChops.multiply(m1, m2))
    def person(self, cx, head_y, head_r, body_top, clip, fill):
        self.circle(cx, head_y, head_r, fill)
        self.ellipse_in_circle((cx - clip[2] * 0.82, body_top, cx + clip[2] * 0.82, body_top + clip[2] * 1.5),
                               clip, fill)
    def render(self, shadow=None):
        out = self.im.resize((self.W, self.H), Image.LANCZOS)
        if shadow:
            dx, dy, blur, op = shadow
            out = drop_shadow(out, dx * self.k, dy * self.k, blur * self.k, op)
        return out
# =====================================================================
# KELAS DASAR SEMUA HALAMAN
# =====================================================================
class Screen:
    def __init__(self, app):
        self.app, self.root = app, app.root
        self.S, self.W, self.H, self.family = app.S, app.W, app.H, app.family
        self.k = self.S * K
        self.fonts, self.imgs, self.hot, self.press = [], [], [], None
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H, highlightthickness=0, bd=0)
        self.canvas.pack()
        c = self.canvas
        c.bind("<Motion>", self.on_motion)
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Leave>", lambda e: (c.config(cursor=""), self.refresh(None)))
    # ---- helper ukuran / font / gambar ----
    def q(self, v):
        return int(round(v * self.k))
    def bx(self, b):
        return tuple(self.q(v) for v in b)
    def font(self, px, weight="normal", slant="roman", underline=False):
        f = tkfont.Font(family=self.family, size=-max(6, self.q(px)), weight=weight, slant=slant,
                        underline=underline)
        self.fonts.append(f)
        return f
    def fit(self, text, px, weight, target, slant="roman"):
        f = self.font(px, weight, slant)
        w = f.measure(text)
        if w > 0:
            size = max(6, int(round(abs(int(f.cget("size"))) * self.q(target) / w)))
            f = tkfont.Font(family=self.family, size=-size, weight=weight, slant=slant)
            self.fonts.append(f)
        return f
    def keep(self, img):
        ph = ImageTk.PhotoImage(img)
        self.imgs.append(ph)
        return ph
    def t(self, x, y, text, font, fill="#000000", anchor="center", tags=(), width=0):
        return self.canvas.create_text(self.q(x), self.q(y), text=text, font=font, fill=fill,
                                       anchor=anchor, tags=tags, width=self.q(width) if width else 0,
                                       justify="center")
    def put(self, img, tags=()):
        return self.canvas.create_image(0, 0, image=self.keep(img), anchor="nw", tags=tags)
    # ---- latar kaca (sama dengan halaman login) ----
    def glass_bg(self):
        bg = add_grain(make_gradient(self.W, self.H), 13)
        x1, y1, x2, y2 = self.bx(CARD_P)
        w, h = x2 - x1, y2 - y1
        glass = Image.blend(bg.crop((x1, y1, x2, y2)), Image.new("RGB", (w, h), WHITE), 0.55)
        bg.paste(glass, (x1, y1), rr_mask(w, h, self.q(53)))
        return bg
    def pill(self, bg, b, alpha=0.93):
        x1, y1, x2, y2 = self.bx(b)
        w, h = x2 - x1, y2 - y1
        pl = Image.blend(bg.crop((x1, y1, x2, y2)), Image.new("RGB", (w, h), PILL_RGB), alpha)
        bg.paste(pl, (x1, y1), rr_mask(w, h, h // 2))
        mean = ImageStat.Stat(bg.crop((x1 + h // 2, y1 + h // 4, x2 - h // 2, y2 - h // 4))).mean
        return hex_color(mean)
    def entry(self, b, color, show=""):
        x1, y1, x2, y2 = self.bx(b)
        e = tk.Entry(self.canvas, font=self.font(25), bd=0, relief="flat", highlightthickness=0,
                     bg=color, fg="#222222", insertbackground="#222222", show=show)
        self.canvas.create_window((x1 + x2) // 2, (y1 + y2) // 2, window=e,
                                  width=(x2 - x1) - self.q(60), height=self.q(52))
        return e
    def button(self, b, cb, text="Continue"):
        x1, y1, x2, y2 = self.bx(b)
        w, h = x2 - x1, y2 - y1
        imgs = {}
        for n, rgb in BTN_COLORS.items():
            im = Image.new("RGBA", (w, h), rgb + (255,))
            im.putalpha(rr_mask(w, h, h // 2))
            imgs[n] = self.keep(im)
        item = self.canvas.create_image(x1, y1, image=imgs["normal"], anchor="nw")
        self.t((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, text, self.fit(text, 30, "bold", 166), "#FFFFFF")
        self.hot.append(dict(box=(x1, y1, x2, y2), cb=cb, imgs=imgs, item=item))
    def add_hot(self, b, cb):
        self.hot.append(dict(box=self.bx(b), cb=cb))
    # ---- interaksi mouse ----
    def hit(self, e):
        for t in reversed(self.hot):
            b = t["box"]
            if b[0] <= e.x <= b[2] and b[1] <= e.y <= b[3]:
                return t
        return None
    def refresh(self, h):
        for t in self.hot:
            if t.get("imgs"):
                st = "down" if self.press is t else ("hover" if h is t and self.press is None else "normal")
                self.canvas.itemconfig(t["item"], image=t["imgs"][st])
    def on_motion(self, e):
        h = self.hit(e)
        self.canvas.config(cursor="hand2" if h else "")
        self.refresh(h)
    def on_press(self, e):
        self.press = self.hit(e)
        self.refresh(self.press)
    def on_release(self, e):
        h, p = self.hit(e), self.press
        self.press = None
        self.refresh(h)
        if p is not None and h is p:
            p["cb"]()
# =====================================================================
# HALAMAN 2 - USER PROFIL
# =====================================================================
class ProfileScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        self.gender = None
        bg = self.glass_bg()
        boxes = {"user": (114, 488, 705, 571), "nomi": (114, 614, 705, 697),
                 "age": (114, 739, 331, 807), "gender": (361, 739, 685, 807),
                 "email": (114, 865, 705, 948), "phone": (114, 999, 705, 1082)}
        col = {key: self.pill(bg, b) for key, b in boxes.items()}
        # avatar, kamera, panah dropdown
        p = Painter(self.W, self.H, self.k)
        p.circle(409.5, 205, 122.5, WHITE)
        p.circle(410, 205, 95, ORANGE)
        p.circle(410, 205, 85, WHITE)
        p.circle(410, 181, 32.5, ORANGE)
        p.ellipse_in_circle((340, 228, 480, 380), (410, 205, 85), ORANGE)
        p.poly([(619, 766), (653, 766), (636, 789)], (200, 61, 60))
        self.put(over(bg, p.render()).convert("RGB"))
        c = self.canvas
        lab = self.font(20)
        for text, x, y in (("Username", 134, 467), ("Nomi ID", 129, 600), ("Age", 133, 719),
                           ("Gender", 384, 724), ("Email", 132, 847), ("Phone number", 125, 985)):
            self.t(x, y, text, lab, anchor="w")
        self.t(410, 368, "User Profil", self.fit("User Profil", 36, "bold", 219))
        self.ent = {"user": self.entry(boxes["user"], col["user"]), "nomi": self.entry(boxes["nomi"], col["nomi"]),
                    "age": self.entry(boxes["age"], col["age"]),
                    "email": self.entry(boxes["email"], col["email"]),
                    "phone": self.entry(boxes["phone"], col["phone"])}
        self.ent["email"].insert(0, app.data.get("email", ""))
        self.gen_txt = self.t(384, 773, "", self.font(21), anchor="w")
        self.msg = self.t(409, 1105, "", self.font(15, "bold"), ERROR, width=590)
        self.button((114, 1128, 705, 1243), self.submit)
        self.add_hot(boxes["gender"], lambda: self.drop(
            boxes["gender"], ["Female", "Male", "Non-binary", "Prefer not to say"], "gender"))
        self.root.bind("<Return>", lambda e: self.submit())
        self.ent["user"].focus_set()
    def drop(self, b, items, which):
        m = tk.Menu(self.root, tearoff=0, font=self.font(18))
        for i, it in enumerate(items):
            m.add_command(label=str(it), columnbreak=(which == "age" and i > 0 and i % 12 == 0),
                          command=lambda v=it: self.choose(which, v))
        x1, y1, x2, y2 = self.bx(b)
        m.tk_popup(self.canvas.winfo_rootx() + x1, self.canvas.winfo_rooty() + y2)
    def choose(self, which, v):
        self.gender = v
        self.canvas.itemconfig(self.gen_txt, text=v if len(v) < 12 else "Prefer not...")
    def submit(self):
        # Ambil isi semua kolom; kolom boleh dibiarkan kosong.
        e = {k: v.get().strip() for k, v in self.ent.items()}
        # Simpan data profil lalu lanjut ke halaman kuis.
        self.app.data.update(username=e["user"], nomi_id=e["nomi"], age=e["age"], gender=self.gender,
                             email=e["email"], phone=e["phone"])
        self.app.go(QuizScreen)
# =====================================================================
# HALAMAN 3 - TASTE QUIZ
# =====================================================================
class QuizScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        bg = self.glass_bg()
        for _, _, _, _, _, chips in QUIZ:
            for _, x1, y1, x2, y2 in chips:
                self.pill(bg, (x1, y1, x2, y2), 0.8)
        p = Painter(self.W, self.H, self.k)
        black = (0, 0, 0)
        # ikon judul section
        for i in range(6):
            a = i * math.pi / 3
            p.circle(129 + 8 * math.cos(a), 278 + 8 * math.sin(a), 5, None, black, 1.6)
        p.circle(129, 278, 4.5, None, black, 1.6)
        for cx, cy in ((129, 553), (142, 541)):
            p.ellipse((cx - 5.5, cy + 1, cx + 5.5, cy + 9), black)
            for dx, dy in ((-6.5, -3), (-2.2, -7.5), (2.2, -7.5), (6.5, -3)):
                p.circle(cx + dx, cy + dy, 2.4, black)
        p.polyline(heart(142, 751, 1.0), 1.8, black, True)
        p.polyline([(127, 752), (134, 752), (138, 745), (142, 758), (146, 749), (150, 752), (157, 752)], 1.6, black)
        p.polyline(sparkle(150, 963, 15), 1.8, black, True)
        p.polyline(sparkle(160, 976, 7), 1.6, black, True)
        self.put(over(bg, p.render()).convert("RGB"))
        self.t(390, 212, "Taste Quiz", self.fit("Taste Quiz", 36, "bold", 216))
        self.selected = set()
        cache, cf = {}, self.font(20)
        for title, tx, ty, tw, _, chips in QUIZ:
            self.t(tx, ty, title, self.fit(title, 24, "bold", tw), anchor="w")
            for label, x1, y1, x2, y2 in chips:
                bx = self.bx((x1, y1, x2, y2))
                w, h = bx[2] - bx[0], bx[3] - bx[1]
                if (w, h) not in cache:
                    im = Image.new("RGBA", (w, h), CORAL + (255,))
                    im.putalpha(rr_mask(w, h, h // 2))
                    cache[(w, h)] = self.keep(im)
                sel = self.canvas.create_image(bx[0], bx[1], image=cache[(w, h)], anchor="nw", state="hidden")
                txt = self.t((x1 + x2) / 2, (y1 + y2) / 2, label, cf)
                self.add_hot((x1, y1, x2, y2), lambda l=label, s=sel, t=txt: self.toggle(l, s, t))
        self.button((114, 1166, 705, 1281), self.submit)
    def toggle(self, label, sel, txt):
        if label in self.selected:
            self.selected.discard(label)
            self.canvas.itemconfig(sel, state="hidden")
            self.canvas.itemconfig(txt, fill="#000000")
        else:
            self.selected.add(label)
            self.canvas.itemconfig(sel, state="normal")
            self.canvas.itemconfig(txt, fill="#FFFFFF")
    def submit(self):
        self.app.data["tastes"] = sorted(self.selected)
        self.app.go(DiscoverScreen, 0)
# =====================================================================
# HALAMAN 4 - DISCOVER (Dengan Gesture Swipe Mouse/Touch)
# =====================================================================
class DiscoverScreen(Screen):
    def __init__(self, app, idx=0):
        super().__init__(app)
        self.idx, self.busy, self.cards = idx % len(PROFILES), False, {}
        self.drag_start_y = 0
        self.is_dragging = False
        self.put(add_grain(smooth(DISC_GRID, self.W, self.H), 8))
        self.card_item = self.canvas.create_image(0, 0, anchor="nw", tags="card")
        self.chrome_item = self.put(self.chrome())
        self.show_card()
        self.t(410, 72, "Discover", self.fit("Discover", 44, "bold", 258), "#FFFFFF")
        nf = lambda s, w: self.fit(s, 21, "bold", w)
        self.t(143, 1387, "Match", nf("Match", 77), "#FFFFFF")
        self.t(415, 1387, "Discover", nf("Discover", 109), "#FFFFFF")
        self.t(672, 1387, "Chat", nf("Chat", 58), "#FFFFFF")
        self.add_hot((199, 1103, 359, 1263), lambda: self.swipe(False))
        self.add_hot((477, 1103, 637, 1263), lambda: self.swipe(True))
        # Bind event swipe keyboard & mouse/touch
        for key, like in (("<Left>", False), ("<Down>", False), ("<Right>", True), ("<Up>", True)):
            self.root.bind(key, lambda e, l=like: self.swipe(l))
        # Event gesture swipe mouse drag (Swipe ke Atas = Match, Swipe ke Bawah = Pass)
        self.canvas.bind("<ButtonPress-1>", self.start_drag, add="+")
        self.canvas.bind("<B1-Motion>", self.on_drag, add="+")
        self.canvas.bind("<ButtonRelease-1>", self.end_drag, add="+")
    def start_drag(self, e):
        if not self.busy:
            self.drag_start_y = e.y
            self.is_dragging = True
    def on_drag(self, e):
        if self.is_dragging and not self.busy:
            dy = e.y - self.drag_start_y
            self.canvas.coords("card", 0, dy)
    def end_drag(self, e):
        if self.is_dragging and not self.busy:
            self.is_dragging = False
            dy = e.y - self.drag_start_y
            threshold = self.q(60)
            if dy < -threshold:
                self.swipe(True)     # Swipe ke atas -> Connect/Match
            elif dy > threshold:
                self.swipe(False)    # Swipe ke bawah -> Pass
            else:
                self.canvas.coords("card", 0, 0)
    # ---- lapisan depan: top bar, tombol, navigasi ----
    def chrome(self):
        W, H, k = self.W, self.H, self.k
        top = Painter(W, H, k)
        top.rrect((-10, -10, 830, 141), 0, CORAL + (255,))
        # gear
        pts = []
        for i in range(8 * 12):
            a = 2 * math.pi * i / 96
            pts.append((74 + (35 if 2 <= i % 12 <= 5 else 27) * math.cos(a),
                        73 + (35 if 2 <= i % 12 <= 5 else 27) * math.sin(a)))
        top.poly(pts, WHITE)
        top.circle(74, 73, 13, CORAL)
        # ikon profil
        top.circle(764, 74, 34, None, WHITE, 4.5)
        top.circle(764, 62, 12, WHITE)
        top.ellipse_in_circle((738, 82, 790, 140), (764, 74, 31), WHITE)
        nav = Painter(W, H, k)
        nav.rrect((47, 1284, 771, 1419), 67, CORAL)
        b1, b2 = Painter(W, H, k), Painter(W, H, k)
        b1.circle(279, 1183, 80, DARKRED)
        b2.circle(557, 1183, 80, TEAL)
        # lingkaran tengah (Discover) bergradient
        cc = Painter(W, H, k)
        cc.circle(412, 1352, 83, WHITE)
        alpha = cc.render().getchannel("A")
        x1, y1, x2, y2 = self.bx((329, 1269, 495, 1435))
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        grad.paste(tilt(((122, 184, 196), (122, 184, 196), (140, 188, 190), (214, 196, 160)),
                        x2 - x1, y2 - y1), (x1, y1))
        grad.putalpha(alpha)
        center = drop_shadow(grad, 0, self.q(7), self.q(8), 0.35)
        ic = Painter(W, H, k)
        ic.line((243, 1147), (315, 1220), 18, WHITE)
        ic.line((315, 1147), (243, 1220), 18, WHITE)
        ic.rrect((507, 1177, 534, 1229), 5, WHITE)
        ic.rrect((540, 1181, 607, 1231), 13, WHITE)
        ic.poly([(548, 1184), (553, 1152), (566, 1132), (580, 1137), (576, 1176)], WHITE)
        ic.line((549, 1199), (598, 1199), 2, TEAL)
        ic.line((549, 1213), (596, 1213), 2, TEAL)
        shadowed = ic.render((0, 5, 3, 0.45))
        nv = Painter(W, H, k)
        nv.poly(heart(141, 1330, 2.7), WHITE)
        for a, b in (((118, 1336), (142, 1362)), ((126, 1328), (154, 1354)), ((134, 1320), (160, 1346))):
            nv.line(a, b, 3, CORAL)
        nv.circle(400, 1326, 26, None, WHITE, 7)
        nv.line((420, 1347), (440, 1367), 8, WHITE)
        nv.poly(sparkle(425, 1306, 18), WHITE)
        nv.ellipse((633, 1303, 711, 1358), WHITE)
        nv.poly([(648, 1350), (640, 1372), (676, 1355)], WHITE)
        for dx in (-16, 0, 16):
            nv.circle(672 + dx, 1331, 5.5, CORAL)
        return over(Image.new("RGBA", (W, H), (0, 0, 0, 0)),
                    top.render(), nav.render((0, 6, 7, 0.3)),
                    b1.render((3, 8, 8, 0.35)), b2.render((3, 8, 8, 0.35)),
                    center, shadowed, nv.render())
    # ---- kartu profil ----
    def card_img(self, i):
        if i in self.cards:
            return self.cards[i]
        pf, (W, H, k) = PROFILES[i], (self.W, self.H, self.k)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        x1, y1, x2, y2 = self.bx((52, 232, 767, 1078))
        w, h = x2 - x1, y2 - y1
        body = tilt(pf["cols"], w, h).convert("RGBA")
        body.putalpha(rr_mask(w, h, self.q(75)))
        layer.paste(body, (x1, y1))
        layer = drop_shadow(layer, 0, self.q(6), self.q(9), 0.35)
        px2, py2 = self.bx((767, 656))[0], self.bx((767, 656))[1]
        pw, ph = px2 - x1, py2 - y1
        photo = tilt((pf["cols"][0], pf["cols"][1], pf["cols"][0], pf["cols"][1]), pw, ph)
        layer.paste(photo, (x1, y1), rr_mask(pw, ph, self.q(75)))
        gap = photo.getpixel((min(pw - 1, self.q(405) - x1), min(ph - 1, self.q(413) - y1)))
        p = Painter(W, H, k)
        p.dome(405, 656, 163, 156, WHITE)
        p.circle(405, 413, 103, gap)
        p.circle(405, 413, 89, WHITE)
        for row, (ya, yb) in zip(pf["tags"], ((756, 812), (826, 882))):
            for _, a, b in row:
                p.rrect((a, ya, b, yb), 28, (255, 255, 255, 150))
        pill = Painter(W, H, k)
        pill.rrect((82, 251, 319, 311), 30, WHITE)
        self.cards[i] = self.keep(over(layer, p.render(), pill.render((0, 5, 6, 0.35))))
        return self.cards[i]
    def show_card(self):
        pf = PROFILES[self.idx]
        c = self.canvas
        c.delete("ctext")
        c.itemconfig(self.card_item, image=self.card_img(self.idx))
        c.coords(self.card_item, 0, 0)
        tg = ("card", "ctext")
        self.t(200, 281, pf["match"], self.fit(pf["match"], 27, "bold", 172), "#C83D3C", tags=tg)
        self.t(410, 693, pf["name"], self.fit(pf["name"], 40, "bold", 24.1 * len(pf["name"])), tags=tg)
        tf = self.font(20)
        for row, (ya, yb) in zip(pf["tags"], ((756, 812), (826, 882))):
            for text, a, b in row:
                self.t((a + b) / 2, (ya + yb) / 2, text, tf, tags=tg)
        self.t(417, 945, pf["quote"], self.font(21, slant="italic"), tags=tg)
        c.tag_lower("ctext", self.chrome_item)
    def swipe(self, like):
        if self.busy:
            return
        self.busy = True
        dy = self.q(-72 if like else 72)
        def step(i=0):
            if i < 10:
                self.canvas.move("card", 0, dy)
                self.root.after(14, lambda: step(i + 1))
            else:
                nxt = (self.idx + 1) % len(PROFILES)
                if like and PROFILES[self.idx]["score"] >= 80:
                    self.app.go(MatchScreen, nxt)
                else:
                    self.idx, self.busy = nxt, False
                    self.show_card()
        step()
# =====================================================================
# HALAMAN 5 - MATCH!! (Kembali Presisi Sesuai Kode Asli)
# =====================================================================
class MatchScreen(Screen):
    def __init__(self, app, nxt=0):
        super().__init__(app)
        self.nxt = nxt
        W, H = self.W, self.H
        bg = add_grain(smooth(MATCH_GRID, W, H), 3)
        yel, tea, red = (255, 222, 115), (125, 185, 198), CORAL
        p = Painter(W, H, self.k)
        p.circle(208, 587, 127, yel)
        p.person(208, 556, 43, 618, (208, 587, 115), WHITE)
        p.circle(615, 763, 123, tea)
        p.person(615, 735, 41, 794, (615, 763, 115), WHITE)
        h = Painter(W, H, self.k)
        h.circle(462, 650, 102, CREAM)
        h.poly([(246, 650), (268, 610), (305, 590), (345, 588), (400, 610), (470, 680), (535, 735),
                (525, 780), (445, 832), (395, 800), (330, 760), (280, 735)], CREAM)
        for a, b in (((431, 768), (485, 826)), ((462, 746), (518, 798)), ((492, 722), (528, 768))):
            h.capsule(a, b, 26, CREAM, red, 3)
        for a, b in (((272, 762), (318, 716)), ((296, 800), (340, 752)),
                     ((330, 826), (372, 785)), ((364, 848), (405, 812))):
            h.capsule(a, b, 30, CREAM, red, 3.5)
        h.polyline([(300, 677), (340, 673), (380, 661), (408, 644), (440, 651), (470, 640), (484, 614)], 4, red)
        h.line((424, 650), (532, 742), 3.5, red)
        self.put(over(bg, p.render(), h.render()).convert("RGB"))
        self.t(410, 897, "Match!!", self.fit("Match!!", 50, "bold", 215), "#FFFFFF")
        self.hot.append(dict(box=(0, 0, self.W, self.H), cb=self.back))
        self.root.bind("<Return>", lambda e: self.back())
    def back(self):
        self.app.go(DiscoverScreen, self.nxt)
# =====================================================================
# KONTROLER APLIKASI
# =====================================================================
class App:
    def __init__(self, root):
        self.root, self.data = root, {}
        self.cur = LoginScreen(root, on_success=self.on_login)
        self.S, self.W, self.H, self.family = self.cur.S, self.cur.W, self.cur.H, self.cur.family
    def on_login(self, email, mode):
        self.data["email"] = email
        self.go(DiscoverScreen, 0) if mode == "login" else self.go(ProfileScreen)
    def go(self, cls, *args):
        for key in ("<Return>", "<Left>", "<Right>", "<Up>", "<Down>"):
            self.root.unbind(key)
        self.cur.canvas.destroy()
        self.cur = cls(self, *args)
def main():
    try:  # Windows: tampilan tajam di layar HiDPI
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
if __name__ == "__main__":
    main()
