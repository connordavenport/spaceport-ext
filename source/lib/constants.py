import yaml
import os
from mojo.UI import getDefault
from AppKit import NSCursor

from mojo.roboFont import CreateCursor

"""
versioning
adds alpha to anything less than 0.1.0
adds beta to anything less than 1.0.0
"""
FALLBACK_VERSION = "0.000"
INFO_YAML = os.path.abspath(os.path.join(__file__, "../../../", "info.yaml"))
if os.path.exists(INFO_YAML):
    with open(INFO_YAML, mode="r") as file:
        info = yaml.safe_load(file)
else:
    info = dict(version=FALLBACK_VERSION)
EXTENSION_VERSION = info.get("version", FALLBACK_VERSION)
major, minor_patch = EXTENSION_VERSION.split(".")
minor_patch = minor_patch.zfill(3)
if int(major) < 1:
    # pull only minor, ignore patch num
    if int(minor_patch[0]) < 1:
        EXTENSION_VERSION += "ɑ"
    else:
        EXTENSION_VERSION += "β"

BASE_DIR = os.path.dirname(__file__)
RESOURCES_PATH = os.path.abspath(os.path.join(BASE_DIR, "../", "resources"))

EXTENSION_KEY:str       = "com.connordavenport.spaceport"

CURRENTGLYPH_CHAR:str   = "/?"
SELECTEDGLYPHS_CHAR:str = "/!"
NEWLINE_CHAR:str        = "\\n"

ZOOM_WIDTH:str          = "arrow.left.and.right.square"
ZOOM_HEIGHT:str         = "arrow.up.and.down.square"
ADD_OBJECT:str          = "document"
KERNING:str             = "arrowtriangle.right.and.line.vertical.and.arrowtriangle.left"
INTERPOLATE:str         = "squareshape.split.2x2.dotted"
OPENTYPE:str            = "textformat.alt"
BEAM:str                = "ruler"

KERN_HEIGHT:int = 100

POS_KERN_COLOR:tuple[float,...] = (0.0, 0.0, 1.0)
NEG_KERN_COLOR:tuple[float,...] = (1.0, 0.0, 0.0)

ZOOM_IN_FACTOR:float = getDefault("zoomInFactor",.85)
ZOOM_OUT_FACTOR:float = getDefault("zoomOutFactor",1.15)

DESIGNSPACE_WIDTH = 300

MATRIX_POS:tuple[int,int,int,int] = (0, -48, 0, 48)

CASES:list[str] = ["lower", "title", "upper", "default"]

CURSOR_SIZE = 30
CURSOR_IMAGE = NSCursor.IBeamCursor().image()
CURSOR_IMAGE = CURSOR_IMAGE.resizeTo_(CURSOR_SIZE)
TYPING_CURSOR = CreateCursor(
    CURSOR_IMAGE,
    hotSpot=(CURSOR_SIZE/2, CURSOR_SIZE/2)
)

CURSOR_COLOR:tuple[float,float,float,float] = (1.0, 0.0, 0.0, 1.0)
SELECTION_COLOR:tuple[float,float,float,float] = (0.0, 0.0, 0.0, 0.1)
ARROW_CURSOR = NSCursor.arrowCursor()
KERNING_CURSOR = NSCursor.resizeLeftRightCursor()

POINT_SIZES:list[str,...]  = ["9", "10", "11", "12", "14", "18", "24", "36", "48", "72", "144", "288"]
LINE_HEIGHTS:list[str,...] = ["0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "2.0"]

ALL_MODES = "typing spacing kerning".split(" ")
REGISTERED = ['aalt', 'abvf', 'abvm', 'abvs', 'afrc', 'akhn', 'apkn', 'blwf', 'blwm', 'blws', 'calt', 'case', 'ccmp', 'cfar', 'chws', 'cjct', 'clig', 'cpct', 'cpsp', 'cswh', 'curs', 'cv01#99', 'c2pc', 'c2sc', 'dist', 'dlig', 'dnom', 'dtls', 'expt', 'falt', 'fin2', 'fin3', 'fina', 'flac', 'frac', 'fwid', 'half', 'haln', 'halt', 'hist', 'hkna', 'hlig', 'hngl', 'hojo', 'hwid', 'init', 'isol', 'ital', 'jalt', 'jp78', 'jp83', 'jp90', 'jp04', 'kern', 'lfbd', 'liga', 'ljmo', 'lnum', 'locl', 'ltra', 'ltrm', 'mark', 'med2', 'medi', 'mgrk', 'mkmk', 'mset', 'nalt', 'nlck', 'nukt', 'numr', 'onum', 'opbd', 'ordn', 'ornm', 'palt', 'pcap', 'pkna', 'pnum', 'pref', 'pres', 'pstf', 'psts', 'pwid', 'qwid', 'rand', 'rclt', 'rkrf', 'rlig', 'rphf', 'rtbd', 'rtla', 'rtlm', 'ruby', 'rvrn', 'salt', 'sinf', 'size', 'smcp', 'smpl', 'ss01#20', 'ssty', 'stch', 'subs', 'sups', 'swsh', 'titl', 'tjmo', 'tnam', 'tnum', 'trad', 'twid', 'unic', 'valt', 'vapk', 'vatu', 'vchw', 'vert', 'vhal', 'vjmo', 'vkna', 'vkrn', 'vpal', 'vrt2', 'vrtr', 'zero']
FEATURE_TAGS = []

# update feature tags with ranges
for t in REGISTERED:
    if "#" in t:
        pr  = t[:2]
        s,e = t[2:].split("#")
        ts  = [f"{pr}{i:0>2}" for i in range(int(s), int(e)+1)]
        FEATURE_TAGS.extend(ts)
    else:
        FEATURE_TAGS.append(t)

PREVIEW = "Preview Location"