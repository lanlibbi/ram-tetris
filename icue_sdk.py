"""Zugriff auf das Corsair-iCUE-SDK über ctypes.

Warum dieser Weg: iCUE selbst hat keine Kommandozeile, aber es liefert eine
Programmierschnittstelle als DLL mit, die einzelne LEDs setzen kann. Damit macht iCUE die
Hardware-Arbeit (inklusive der RAM-Riegel), und wir schicken nur Farben — kein zusätzlicher
Treiber, kein OpenRGB, keine Installation.

Die DLL kommt nicht von Corsair direkt auf die Platte, sondern mit Werkzeugen anderer
Mainboard-Hersteller. Auf diesem Rechner liegt sie im Gigabyte Control Center:
    C:\\Program Files\\GIGABYTE\\Control Center\\Lib\\MBStorage\\iCUESDK.x64_2019.dll

Zwei API-Generationen:
  * alt: CorsairPerformProtocolHandshake() — synchron, ein Aufruf
  * neu: CorsairConnect(callback, ctx) — Zustand kommt über den Callback, danach Geräte
Wir nehmen die alte Funktion, wenn die DLL sie anbietet, sonst die neue.
"""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import POINTER, Structure, byref, c_byte, c_char_p, c_int, c_ubyte, c_uint, c_void_p

STRING_M = 128

KANDIDATEN = [
    r"C:\Program Files\GIGABYTE\Control Center\Lib\MBStorage\iCUESDK.x64_2019.dll",
    r"C:\Program Files (x86)\GIGABYTE\Control Center\Lib\MBStorage\iCUESDK.x64_2019.dll",
    r"C:\Program Files\Corsair\Corsair iCUE5 Software\iCUESDK.x64_2019.dll",
    r"C:\Program Files\Corsair\CORSAIR iCUE 4 Software\iCUESDK.x64_2019.dll",
]

# Gerätetypen laut iCUESDK.h
CDT_MEMORY_MODULE = 0x0080
CDT_COOLER = 0x0100
CDT_MOTHERBOARD = 0x0200
CDT_GRAPHICS_CARD = 0x0400
CDT_MOUSEMAT = 0x0004
TYP_NAMEN = {
    0x0001: "Tastatur", 0x0002: "Maus", 0x0004: "Mauspad", 0x0008: "Headset",
    0x0020: "Lüfter-/LED-Controller", 0x0040: "LED-Controller", 0x0080: "Speichermodul",
    0x0100: "Kühler", 0x0200: "Mainboard", 0x0400: "Grafikkarte", 0x0800: "Touchbar",
}
FEHLER = {
    0: "Erfolg", 1: "nicht verbunden (iCUE läuft nicht oder SDK-Steuerung in iCUE aus)",
    2: "keine Kontrolle (anderer Client hat übernommen)", 3: "Protokoll unvereinbar",
    4: "ungültige Argumente", 5: "ungültige Operation", 6: "Gerät nicht gefunden",
    7: "nicht erlaubt",
}


class DeviceInfo(Structure):
    _fields_ = [
        ("type", c_int),
        ("id", ctypes.c_char * STRING_M),
        ("serial", ctypes.c_char * STRING_M),
        ("model", ctypes.c_char * STRING_M),
        ("ledCount", c_int),
        ("channelCount", c_int),
    ]


class LedColor(Structure):
    _fields_ = [
        ("id", c_uint),
        ("r", c_ubyte),
        ("g", c_ubyte),
        ("b", c_ubyte),
        ("a", c_ubyte),
    ]


class SessionStateChanged(Structure):
    """state (Enum als int) + Details; die Details brauchen wir nicht, nur Platz dafür."""
    _fields_ = [("state", c_int), ("details", c_byte * 512)]


class LedPosition(Structure):
    _fields_ = [("id", c_uint), ("cx", ctypes.c_double), ("cy", ctypes.c_double)]


class DeviceFilter(Structure):
    _fields_ = [("deviceTypeMask", c_int)]


class Sdk:
    def __init__(self, pfad: str | None = None):
        self.pfad = pfad or next((p for p in KANDIDATEN if os.path.exists(p)), None)
        if not self.pfad:
            raise SystemExit("iCUE-SDK-DLL nicht gefunden. Gesucht:\n  " + "\n  ".join(KANDIDATEN))
        self.dll = ctypes.CDLL(self.pfad)
        self._signaturen()
        self.verbunden = False
        self._letzte_id = b""

    # -- Signaturen setzen, soweit die DLL die Funktionen anbietet -------------
    def _signaturen(self) -> None:
        d = self.dll
        self.hat = {n: hasattr(d, n) for n in (
            "CorsairPerformProtocolHandshake", "CorsairConnect", "CorsairGetDeviceCount",
            "CorsairGetDevices", "CorsairGetDeviceInfo", "CorsairSetLedColors",
            "CorsairSetLedColorsBuffer",
            "CorsairSetLedColorsFlushBufferAsync", "CorsairGetLedPositions", "CorsairRequestControl",
            "CorsairReleaseControl", "CorsairSetLayerPriority")}

        if self.hat["CorsairGetDeviceCount"]:
            d.CorsairGetDeviceCount.restype = c_int
            d.CorsairGetDeviceCount.argtypes = []
        if self.hat["CorsairGetDevices"]:
            d.CorsairGetDevices.restype = c_int
            d.CorsairGetDevices.argtypes = [POINTER(DeviceFilter), c_int, POINTER(DeviceInfo), POINTER(c_int)]
        if self.hat["CorsairGetDeviceInfo"]:
            d.CorsairGetDeviceInfo.restype = c_int
            d.CorsairGetDeviceInfo.argtypes = [c_char_p, POINTER(DeviceInfo)]
        if self.hat["CorsairSetLedColors"]:
            d.CorsairSetLedColors.restype = c_int
            d.CorsairSetLedColors.argtypes = [c_char_p, c_int, POINTER(LedColor)]
        if self.hat["CorsairSetLedColorsBuffer"]:
            d.CorsairSetLedColorsBuffer.restype = c_int
            d.CorsairSetLedColorsBuffer.argtypes = [c_char_p, c_int, POINTER(LedColor)]
        if self.hat["CorsairSetLedColorsFlushBufferAsync"]:
            d.CorsairSetLedColorsFlushBufferAsync.restype = c_int
            d.CorsairSetLedColorsFlushBufferAsync.argtypes = []
        if self.hat["CorsairGetLedPositions"]:
            d.CorsairGetLedPositions.restype = c_int
            d.CorsairGetLedPositions.argtypes = [c_char_p, c_int, POINTER(LedPosition), POINTER(c_int)]
        if self.hat["CorsairRequestControl"]:
            d.CorsairRequestControl.restype = c_int
            d.CorsairRequestControl.argtypes = [c_char_p, c_int]
        if self.hat["CorsairSetLayerPriority"]:
            d.CorsairSetLayerPriority.restype = c_int
            d.CorsairSetLayerPriority.argtypes = [c_uint]

    # -- Verbindung ------------------------------------------------------------
    def verbinde(self) -> str:
        if self.hat.get("CorsairPerformProtocolHandshake"):
            code = self.dll.CorsairPerformProtocolHandshake()
            self.verbunden = code == 0
            return f"Handshake: {FEHLER.get(code, code)}"
        if self.hat.get("CorsairConnect"):
            zustand = {"wert": None}

            def rueckruf(_ctx, ereignis):              # noqa: ANN001
                # ereignis zeigt auf CorsairSessionStateChanged: erstes Feld ist der Zustand
                try:
                    zustand["wert"] = ereignis.contents.state
                except Exception:
                    zustand["wert"] = None

            handler = ctypes.CFUNCTYPE(None, c_void_p, POINTER(SessionStateChanged))(rueckruf)
            self.dll.CorsairConnect.restype = c_int
            self.dll.CorsairConnect.argtypes = [ctypes.c_void_p, c_void_p]
            code = self.dll.CorsairConnect(handler, None)
            self._handler = handler            # Referenz halten, sonst sammelt Python ihn ein
            for _ in range(60):
                if zustand["wert"] == 6:       # CSS_Connected
                    break
                time.sleep(0.1)
            self.verbunden = (code == 0 and zustand["wert"] == 6)
            return f"CorsairConnect: {FEHLER.get(code, code)}, Zustand {zustand['wert']}"
        return "keine Verbindungsfunktion gefunden"

    # -- Geräte ----------------------------------------------------------------
    def geraete(self) -> list[dict]:
        roh: list[DeviceInfo] = []
        if self.hat.get("CorsairGetDevices"):
            filter_ = DeviceFilter(0xFFFFFFFF)      # alle Typen
            max_ = 32
            feld = (DeviceInfo * max_)()
            groesse = c_int(0)
            code = self.dll.CorsairGetDevices(byref(filter_), max_, feld, byref(groesse))
            if code != 0:
                raise RuntimeError(f"CorsairGetDevices: {FEHLER.get(code, code)}")
            roh = [feld[i] for i in range(min(groesse.value, max_))]
        else:
            anzahl = self.dll.CorsairGetDeviceCount()
            for i in range(anzahl):
                info = DeviceInfo()
                if self.dll.CorsairGetDeviceInfo(i, byref(info)) == 0:
                    roh.append(info)
        liste = []
        for i, info in enumerate(roh):
            liste.append({
                "index": i,
                "id": info.id.decode("utf-8", "replace"),
                "typ": info.type,
                "typ_name": TYP_NAMEN.get(info.type, f"unbekannt ({info.type:#x})"),
                "modell": info.model.decode("utf-8", "replace"),
                "leds": info.ledCount,
                "kanaele": info.channelCount,
            })
        return liste

    def positionen(self, geraet: dict) -> list[dict]:
        """LED-Kennungen mit Koordinaten (bei Speichermodulen in Millimetern)."""
        if not self.hat.get("CorsairGetLedPositions"):
            return []
        max_ = max(geraet["leds"], 1) * 2
        feld = (LedPosition * max_)()
        groesse = c_int(0)
        code = self.dll.CorsairGetLedPositions(geraet["id"].encode(), max_, feld, byref(groesse))
        if code != 0:
            return []
        return [{"id": feld[i].id, "x": feld[i].cx, "y": feld[i].cy}
                for i in range(min(groesse.value, max_))]

    def kontrolle(self, geraet: dict, exklusiv: bool = True) -> str:
        if not self.hat.get("CorsairRequestControl"):
            return "keine Kontrollfunktion"
        self._letzte_id = geraet["id"].encode()
        code = self.dll.CorsairRequestControl(self._letzte_id, 1 if exklusiv else 0)
        return FEHLER.get(code, str(code))

    def freigeben(self, geraet: dict) -> None:
        if self.hat.get("CorsairReleaseControl"):
            self.dll.CorsairReleaseControl(geraet["id"].encode())

    def setze_farben_raw(self, farben: list[tuple[int, tuple[int, int, int]]]) -> int:
        """Farben als (LED-Kennung, (r,g,b)) — für Geräte mit beliebiger Geometrie."""
        n = len(farben)
        if not n:
            return 0
        puffer = (LedColor * n)()
        for i, (kennung, (r, g, b)) in enumerate(farben):
            puffer[i] = LedColor(kennung, r, g, b, 255)
        kennung_bytes = self._letzte_id
        if self.hat.get("CorsairSetLedColorsBuffer") and self.hat.get("CorsairSetLedColorsFlushBufferAsync"):
            code = self.dll.CorsairSetLedColorsBuffer(kennung_bytes, n, puffer)
            if code == 0:
                self.dll.CorsairSetLedColorsFlushBufferAsync()
            return code
        return self.dll.CorsairSetLedColors(kennung_bytes, n, puffer)

    def setze_farben(self, geraet: dict, farben: list[tuple[int, int, int]]) -> int:
        """Setzt die LEDs 0..n-1 der Reihe nach. Gibt den SDK-Fehlercode zurück."""
        n = min(len(farben), geraet["leds"])
        puffer = (LedColor * n)()
        for i in range(n):
            r, g, b = farben[i]
            puffer[i] = LedColor(i, r, g, b, 255)
        if self.hat.get("CorsairSetLedColorsBuffer") and self.hat.get("CorsairSetLedColorsFlushBufferAsync"):
            code = self.dll.CorsairSetLedColorsBuffer(geraet["id"].encode(), n, puffer)
            if code == 0:
                self.dll.CorsairSetLedColorsFlushBufferAsync()
            return code
        return self.dll.CorsairSetLedColors(geraet["id"].encode(), n, puffer)
