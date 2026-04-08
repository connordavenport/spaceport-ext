import yaml
import os
from mojo.UI import getDefault
from AppKit import NSCursor, NSImage
import plistlib
from mojo.roboFont import CreateCursor
import platform

"""
versioning
adds alpha to anything less than 0.1.0
adds beta to anything less than 1.0.0
"""
EXTENSION_NAME = "Spaceport"

WORKSPACE_WINDOW_IDENTIFIER = f"{EXTENSION_NAME} Window"

MACOS_VERSION: str = platform.mac_ver()[0]
if MACOS_VERSION.count(".") > 1:
    major, minor, superMinor = MACOS_VERSION.split(".", 2)
    MACOS_VERSION = ".".join((major, minor))
MACOS_VERSION: float = float(MACOS_VERSION)

FALLBACK_VERSION: str = "0.000"
INFO_YAML: str = os.path.abspath(os.path.join(__file__, "../../../", "info.yaml"))
INFO_PLST: str = os.path.abspath(os.path.join(__file__, "../../", "info.plist"))
if os.path.exists(INFO_YAML):
    # also if there is a yaml, this means we are in dev env
    with open(INFO_YAML, mode="r") as file:
        info = yaml.safe_load(file)
elif os.path.exists(INFO_PLST):
    # also check if there is a plist, this means we are in an extension
    with open(INFO_PLST, "rb") as file:
        info = plistlib.load(file)
else:
    # nothing found, fallback to 0.000
    info = dict(version=FALLBACK_VERSION)

EXTENSION_VERSION: str = info.get("version", FALLBACK_VERSION)
major, minor_patch = EXTENSION_VERSION.split(".")
minor_patch = minor_patch.zfill(3)
if int(major) < 1:
    # pull only minor, ignore patch num
    if int(minor_patch[0]) < 1:
        EXTENSION_VERSION += "ɑ"
    else:
        EXTENSION_VERSION += "β"

BASE_DIR: str = os.path.dirname(__file__)
RESOURCES_PATH: str = os.path.abspath(os.path.join(BASE_DIR, "../", "resources"))


KEY_PREFIX: str = "tools.programme"
EXTENSION_KEY: str = f"{KEY_PREFIX}.{EXTENSION_NAME.lower()}"
EVENT_KEY: str = f"{KEY_PREFIX}.{EXTENSION_NAME.lower()}.event.settingsChanged"

PLACEHOLDER_TEXT: list[str] = [i for i in EXTENSION_NAME]

TINTED_BACKGROUND: bool = True
CURSOR_BLINKING: bool = False

CURRENTGLYPH_CHAR: str = "/?"
SELECTEDGLYPHS_CHAR: str = "/!"
NEWLINE_CHAR: str = "\\n"

ZOOM_WIDTH: str = "arrow.left.and.right.square"
ZOOM_HEIGHT: str = "arrow.up.and.down.square"
ADD_OBJECT: str = "document"
OPENTYPE: str = "textformat.alt"
INTERPOLATE: str = "squareshape.split.2x2.dotted"
KERNING: str = "arrowtriangle.right.and.line.vertical.and.arrowtriangle.left"
BEAM: str = "ruler"

KERN_HEIGHT: int = 100
BUFFER: int = 75
DESIGNSPACE_WIDTH: int = 300
PADDING_MULTIPLIER: float = 1.0

POS_KERN_COLOR: tuple[float, float, float] = (0.0, 0.0, 1.0)
NEG_KERN_COLOR: tuple[float, float, float] = (1.0, 0.0, 0.0)

STATIC_COLOR: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.2)
INTERPO_COLOR: tuple[float, float, float, float] = (0.263, 0.667, 0.337, 1.0)
SOURCE_COLOR: tuple[float, float, float, float] = (0.914, 0.22, 0.106, 1.0)
INSTANCE_COLOR: tuple[float, float, float, float] = (0.149, 0.588, 0.824, 1.0)

TYPE_COLOR_MAP = {
    "static": STATIC_COLOR,
    "preview": INTERPO_COLOR,
    "source": SOURCE_COLOR,
    "instance": INSTANCE_COLOR,
}

ZOOM_IN_FACTOR: float = getDefault("zoomInFactor", 0.85)
ZOOM_OUT_FACTOR: float = getDefault("zoomOutFactor", 1.15)

MATRIX_POS_BOTTOM: tuple[int, int, int, int] = (0, -48, 0, 48)
MATRIX_POS_TOP: tuple[int, int, int, int] = (0, 40, 0, 48)

CASES: list[str] = ["lower", "title", "upper", "default"]

CURSOR_SIZE: int = 30
CURSOR_IMAGE = NSCursor.IBeamCursor().image()
CURSOR_IMAGE = CURSOR_IMAGE.resizeTo_(CURSOR_SIZE)

TYPING_CURSOR: NSImage = CreateCursor(
    CURSOR_IMAGE, hotSpot=(CURSOR_SIZE / 2, CURSOR_SIZE / 2)
)

ARROW_CURSOR: NSImage = NSCursor.arrowCursor()
KERNING_CURSOR: NSImage = NSCursor.resizeLeftRightCursor()

CURSOR_COLOR: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0)
SELECTION_COLOR: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.1)


POINT_SIZES: list[str] = [
    "9",
    "10",
    "11",
    "12",
    "14",
    "18",
    "24",
    "36",
    "48",
    "72",
    "144",
    "288",
]
LINE_HEIGHTS: list[str] = [
    "0.5",
    "0.6",
    "0.7",
    "0.8",
    "0.9",
    "1.0",
    "1.1",
    "1.2",
    "1.3",
    "1.4",
    "1.5",
    "1.6",
    "1.7",
    "1.8",
    "1.9",
    "2.0",
]

ALL_MODES: list[str] = ["typing", "spacing", "kerning"]
REGISTERED: list[str] = [ "aalt", "abvf", "abvm", "abvs", "afrc", "akhn", "apkn", "blwf", "blwm", "blws", "calt", "case", "ccmp", "cfar", "chws", "cjct", "clig", "cpct", "cpsp", "cswh", "curs", "cv01#99", "c2pc", "c2sc", "dist", "dlig", "dnom", "dtls", "expt", "falt", "fin2", "fin3", "fina", "flac", "frac", "fwid", "half", "haln", "halt", "hist", "hkna", "hlig", "hngl", "hojo", "hwid", "init", "isol", "ital", "jalt", "jp78", "jp83", "jp90", "jp04", "kern", "lfbd", "liga", "ljmo", "lnum", "locl", "ltra", "ltrm", "mark", "med2", "medi", "mgrk", "mkmk", "mset", "nalt", "nlck", "nukt", "numr", "onum", "opbd", "ordn", "ornm", "palt", "pcap", "pkna", "pnum", "pref", "pres", "pstf", "psts", "pwid", "qwid", "rand", "rclt", "rkrf", "rlig", "rphf", "rtbd", "rtla", "rtlm", "ruby", "rvrn", "salt", "sinf", "size", "smcp", "smpl", "ss01#20", "ssty", "stch", "subs", "sups", "swsh", "titl", "tjmo", "tnam", "tnum", "trad", "twid", "unic", "valt", "vapk", "vatu", "vchw", "vert", "vhal", "vjmo", "vkna", "vkrn", "vpal", "vrt2", "vrtr", "zero"]
FEATURE_TAGS: list[str] = []

# update feature tags with ranges
for t in REGISTERED:
    if "#" in t:
        pr = t[:2]
        s, e = t[2:].split("#")
        ts = [f"{pr}{i:0>2}" for i in range(int(s), int(e) + 1)]
        FEATURE_TAGS.extend(ts)
    else:
        FEATURE_TAGS.append(t)

PREVIEW: str = "Preview Location"
