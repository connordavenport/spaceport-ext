from AppKit import NSEvent, NSShiftKeyMask, NSCommandKeyMask, NSAlternateKeyMask, NSFunctionKeyMask
from mojo.roboFont import AllFonts

# ----------------------------------------------------------
# Taken from DrawBot builtins, dont require import for these
# ----------------------------------------------------------
def norm(value:float, start:float, stop:float) -> float:
    """
    Return the interpolation factor (between 0 and 1) of a `value` between `start` and `stop`.
    """
    return (value - start) / (stop - start)


def lerp(start:float, stop:float, factor:float) -> float:
    """
    Return an interpolated value between `start` and `stop` using interpolation factor `factor`.
    """
    return start + (stop - start) * factor


def remap(value:float, start1:float, stop1:float, start2:float, stop2:float, clamp:bool=False) -> float:
    """
    Re-maps a number from one range to another.
    """
    factor = norm(value, start1, stop1)
    if clamp:
        if factor < 0:
            factor = 0
        elif factor > 1:
            factor = 1
    return lerp(start2, stop2, factor)
# ----------------------------------------------------------
# ----------------------------------------------------------
# ----------------------------------------------------------

def fontIsOpen(path:str) -> bool:
    isOpen = False
    openPaths = [f.path for f in AllFonts()]
    if path in openPaths:
        isOpen = True
    return isOpen


# @property
def shift() -> bool:
    return NSEvent.modifierFlags() & NSShiftKeyMask


# @property
def command() -> bool:
    return NSEvent.modifierFlags() & NSCommandKeyMask


# @property
def option() -> bool:
    return NSEvent.modifierFlags() & NSAlternateKeyMask


# @property
def function() -> bool:
    return NSEvent.modifierFlags() & NSFunctionKeyMask