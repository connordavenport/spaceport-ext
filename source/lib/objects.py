from inspect import Attribute
import constants
import ezui
import merz
import AppKit
from lib.fontObjects.doodleFont import DoodleFont
from lib.fontObjects.doodleGlyph import DoodleGlyph
from lib.fontObjects.doodleLayer import DoodleLayer
from mojo.roboFont import AllFonts, CurrentFont, RFont, RGlyph, internalFontClasses
from mojo.UI import inDarkMode
from fontTools.fontBuilder import FontBuilder
from typing import BinaryIO
import io
from featurePreviewLib.source.lib import featurePreview


class FeatureButtonClass(ezui.items.pushButton.PushButton):

    states = {
        "default":AppKit.NSColor.grayColor(),
        "on":AppKit.NSColor.greenColor(),
        "off":AppKit.NSColor.redColor(),
    }

    def __init__(self,
            tag="",
            state=list(states.keys())[0],
            keyEquivalent=None,
            keyEquivalentModifiers=None,
            sizeStyle="regular",
            callback=None,
            toolTip=None,
            identifier=None,
            container=None,
            controller=None,
            descriptionData={}
        ):

        self._callback = ezui.tools.findCallback(
            callback=callback,
            identifier=identifier,
            container=container,
            controller=controller
        )

        self._state = state
        if tag not in constants.FEATURE_TAGS:
            if len(tag) <= 4:
                tag = f'{tag:+<4}'.upper()
            elif len(tag) > 4:
                tag = tag[0:4].upper()
            else:
                tag = "____" # raise error?
        self._tag = tag

        super().__init__(
            text=tag,
            sizeStyle=sizeStyle,
            callback=self._internalCallback,
        )

        ezui.tools.assignIdentifier(
            item=self,
            identifier=identifier,
            container=container
        )

        self.setButtonColor(self.states["default"])
        self.getNSButton().setFont_(AppKit.NSFont.monospacedSystemFontOfSize_weight_(12.0, 0))
        self.getNSButton().setBezelStyle_(AppKit.NSBezelStyleRecessed)
        self.getNSButton().setCornerRadius_(5)

        
    def setButtonColor(self, color:AppKit.NSColor):
        textColor = AppKit.NSColor.blackColor() if inDarkMode() else AppKit.NSColor.whiteColor()
        attrTxt = AppKit.NSAttributedString.alloc().initWithString_attributes_(
            self._tag, 
            {
                AppKit.NSForegroundColorAttributeName : textColor
            }
        )
        self.getNSButton().setBackgroundColor_(color)
        self.getNSButton().setAttributedTitle_(attrTxt)


    def _internalCallback(self, sender):
        stateKeys = list(self.states.keys())
        try:
            self._state = stateKeys[stateKeys.index(self._state)+1] 
        except IndexError:
            self._state = stateKeys[0]
            
        stateColor = self.states.get(self._state, AppKit.NSColor.clearColor())
        self.setButtonColor(color=stateColor)

        if self._callback is not None:
            self._callback(self)

    @property
    def tag(self):
        return self._tag

    def _getState(self) -> str:
        return self._state

    def _setState(self, value:str):
        self._state = value
        self.setButtonColor(self.states[self._state])

    state = property(_getState, _setState)
    

try: 
    ezui.tools.classes.registerClass("FeatureToggleButton", FeatureButtonClass)
except:
    pass


class MerzCollectionViewRGlyphItem(merz.collectionView.MerzCollectionViewItem):

    def __init__(self, *args, **kwargs) -> None:
        self._name:str                    = kwargs.get("name", "")
        self._font:DoodleFont             = kwargs.get("font")
        # self._layer:DoodleFont          = self._font.layers.defaultLayer.name or "foreground"
        self._glyph:RGlyph                = kwargs.get("glyph")
        self._index:int                   = kwargs.get("index", 0)
        self._onDisk:bool                 = kwargs.get("onDisk", True)
        self._offset:float|int            = kwargs.get("italicOffset", 0)
        self._skewAngle:float|int         = kwargs.get("skewAngle", 0)
        self._scaler:float|int            = kwargs.get("scaler", 1)
        self._location:dict[str,float]    = kwargs.get("location", {})
        self._selected:bool               = False
        self._selectedPair:tuple|None     = None
        self._pairPart                    = None
        self._isTyping:bool               = False
        self._kerning:bool                = False
        self._selectedVisible:bool        = False

        self._selectionColor:tuple[float] = kwargs.get("selectionColor", constants.SELECTION_COLOR)
        self._cursorColor:tuple[float]    = kwargs.get("cursorColor", constants.CURSOR_COLOR)
        self._cursorBlinking:bool         = kwargs.get("cursorBlinking", False)

        super().__init__(*args, **kwargs)


    def getName(self) -> str:
        return self._name

    def setName(self, value:str) -> None:
        self._name = value

    name = property(getName, setName)

    def getGlyph(self) -> DoodleGlyph | RGlyph:
        return self._glyph

    def setGlyph(self, value:DoodleGlyph | RGlyph) -> None:
        self._glyph = value

    glyph = property(getGlyph, setGlyph)

    def getFont(self) -> DoodleFont:
        return self._font

    def setFont(self, value:DoodleFont) -> None:
        self._font = value

    font = property(getFont, setFont)

    # # we use layer to actually draw
    # def getLayer(self) -> DoodleLayer:
    #     return self._layer

    # def setLayer(self, value:str|DoodleLayer) -> None:
    #     if isinstance(value, str):
    #         name = value
    #     elif isinstance(value, DoodleLayer):
    #         name = value.name
    #     else:
    #         return

    #     if name in self._font.layerOrder:
    #         self._layer = self._font.layers[name]

    # layer = property(getLayer, setLayer)

    def getSelected(self) -> bool:
        return self._selected

    def setSelected(self, value:bool=False) -> None:
        self._selected = value
        if self.kerning:
            self.getLayer("glyphContainer").getSublayer("kernSelectionIndicator").setVisible(value)
        else:
            self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    selected = property(getSelected, setSelected)

    def getKerning(self) -> bool:
        return self._kerning

    def setKerning(self, value:bool=False) -> None:
        self._kerning = value
        #self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    kerning = property(getKerning, setKerning)

    def getPairPart(self) -> bool:
        return self._pairPart

    def setPairPart(self, value) -> None:
        self._pairPart = value

    pairPart = property(getPairPart, setPairPart)

    @property
    def selectedPair(self) -> tuple|None:
        return (self._name, self.pairPart.name)

    def getSelectionColor(self) -> tuple[float]:
        return self._selectionColor

    def setSelectionColor(self, value:tuple[float]) -> None:
        self._selectionColor = value
        item = self.getLayer("glyphContainer").getSublayer("selectionIndicator").getSublayer("selectionIndicatorDrawing")
        if item: item.setFillColor(value)

    selectionColor = property(getSelectionColor, setSelectionColor)

    def getCursorColor(self) -> tuple[float]:
        return self._cursorColor

    def setCursorColor(self, value:tuple[float]) -> None:
        self._cursorColor = value
        self.typing = self._isTyping # we need to reset typing to change color in view

    cursorColor = property(getCursorColor, setCursorColor)

    def getBlinkingCursor(self) -> bool:
        return self._cursorBlinking

    def setBlinkingCursor(self, value:bool=False) -> None:
        self._cursorBlinking = value
        self.typing = self._isTyping # we need to reset typing to change color in view

    cursorBlinking = property(getBlinkingCursor, setBlinkingCursor)

    def getTypingItem(self) -> bool:
        return self._isTyping

    def setTypingItem(self, value:bool=False) -> None:
        self._isTyping = value
        layer = self.getLayer("glyphContainer").getSublayer("typingIndicator")
        layer.setVisible(value)
        if self._isTyping:
            sublayer = layer.getSublayer("typingIndicatorDrawing")
            sublayer.setStrokeColor(self.cursorColor)
            with sublayer.propertyGroup(
                duration=.5,
                repeatCount="loop",
                reverse=True,
                timing="easeInEaseOut",
            ):
                alpha = .1 if self.cursorBlinking else self.cursorColor[-1]
                sublayer.setStrokeColor((*self.cursorColor[0:3], alpha))
                
    typing = property(getTypingItem, setTypingItem)

    def getSelectedVisible(self) -> bool:
        return self._selectedVisible

    def setSelectedVisible(self, value:bool=False) -> None:
        # not the same as .visible, this only controls the view state not the selected state
        self._selectedVisible = value
        self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    selectedVisible = property(getSelectedVisible, setSelectedVisible)

    def getIndex(self) -> int:
        try:
            return int(self._index)
        except:
            return 0

    def setIndex(self, value:int=0) -> None:
        self._index = value

    index = property(getIndex, setIndex)

    def getOnDisk(self) -> bool:
        return self._onDisk

    def setOnDisk(self, value:bool=True) -> None:
        self._onDisk = value

    onDisk = property(getOnDisk, setOnDisk)

    def getOffset(self) -> int|float:
        return self._offset

    def setOffset(self, value:int|float) -> None:
        self._offset = value

    offset = property(getOffset, setOffset)

    def getSkewAngle(self) -> int|float:
        return self._skewAngle

    def setSkewAngle(self, value:int|float) -> None:
        self._skewAngle = value

    skewAngle = property(getSkewAngle, setSkewAngle)

    def getScaler(self) -> int|float:
        return self._scaler

    def setScaler(self, value:int|float) -> None:
        self._scaler = value

    scaler = property(getScaler, setScaler)

    def getLocation(self) -> dict[str,float]:
        return self._location

    def setLocation(self, value:dict[str,float]) -> None:
        self._location = value

    location = property(getLocation, setLocation)


class FontItem(object):
    # custom item so we can store more attributes with fonts we are using
    def __init__(self, **kwargs) -> None:
        self._path:str            = kwargs.get("path")
        self._use:bool            = kwargs.get("use")
        self._font:DoodleFont     = kwargs.get("font")
        if isinstance(self._font, RFont): self._font = self._font.naked()
        self._layer:DoodleLayer   = kwargs.get("layer", self._font.layers.defaultLayer)
        self._text:str|None       = None
        self._localText:bool      = False
        self._gsub:list[str]  = []

        self._featureFont         = None

        try:
            self._featureFont = featurePreview.FeatureFont(self._font)
            self._gsub = self._featureFont.gsub.getFeatureList()
            # self._gpos = self._featureFont.gpos.getFeatureList()
            self._gpos = [] # we are ignore gpos lookups for now, handle kerning on UFO level
        except:
            self._gsub = []
            self._gpos = []


    ## ---- Taken from FontParts to use on Doodle objects ----
    def findGlyph(self, glyphName):
        groupNames = self._findGlyph(glyphName)
        groupNames = [groupName for groupName in groupNames]
        return groupNames

    def _findGlyph(self, glyphName):
        found = []
        for key, groupList in self._font.groups.items():
            if glyphName in groupList:
                found.append(key)
        return found
    ## -------------------------------------------------------


    def smartSet(self, pair:tuple[str,str], value:float, exceptionType="find", debug=False):
        
        '''
        pair must be a tuple, its contents can be a glyphName or a group's name
        value must be an integer, why would you even kern on fractions....
        exceptionType is the level of searching the function will do
            None : use the top level group or glyph names, no exceptions
            g2G  : glyph to Group exception
            g2g  : glyph to glyph exception
            G2g  : Group to glyph exception
        '''
        l,r = pair
        if not isinstance(l,str) and isinstance(r,str):
            return

        if exceptionType in ["find", "g2G", "g2g", "G2g"]:
            pass
        else:
            exceptionType = "find"
                
        if "public.kern1" in l:
            if l not in self._font.groups.keys():
                return
            leftGroup = l
        else:
            if l not in self._font.keys():
                return
            leftGlyph = l
            leftGroup = l
            for gs in self.findGlyph(l):
                if "public.kern1" in gs:
                    leftGroup = gs
            
        if "public.kern2" in r:
            if r not in self._font.groups.keys():
                return
            rightGroup = r
        else:
            if r not in self._font.keys():
                return
                
            rightGlyph = r
            rightGroup = r
            for gs in self.findGlyph(r):
                if "public.kern2" in gs:
                    rightGroup = gs

        if exceptionType == "find":
            kp = (leftGroup, rightGroup)
        elif exceptionType == "g2G":
            kp = (leftGlyph, rightGroup)
        elif exceptionType == "g2g":
            kp = (leftGlyph, rightGlyph)
        elif exceptionType == "G2g":
            kp = (leftGroup, rightGlyph)
        else:
            raise TypeError("exception type unknown") 
        

        if debug:
            print(kp, value)
        else:
            self._font.kerning[kp] = value


    def deleteKern(self, pair:tuple[str,str], exceptionType="find", debug=False):
        
        '''
        pair must be a tuple, its contents can be a glyphName or a group's name
        value must be an integer, why would you even kern on fractions....
        exceptionType is the level of searching the function will do
            None : use the top level group or glyph names, no exceptions
            g2G  : glyph to Group exception
            g2g  : glyph to glyph exception
            G2g  : Group to glyph exception
        '''
        l,r = pair
        if not isinstance(l,str) and isinstance(r,str):
            return

        if exceptionType in ["find", "g2G", "g2g", "G2g"]:
            pass
        else:
            exceptionType = "find"
                
        if "public.kern1" in l:
            if l not in self._font.groups.keys():
                return
            leftGroup = l
        else:
            if l not in self._font.keys():
                return
            leftGlyph = l
            leftGroup = l
            for gs in self.findGlyph(l):
                if "public.kern1" in gs:
                    leftGroup = gs
            
        if "public.kern2" in r:
            if r not in self._font.groups.keys():
                return
            rightGroup = r
        else:
            if r not in self._font.keys():
                return
                
            rightGlyph = r
            rightGroup = r
            for gs in self.findGlyph(r):
                if "public.kern2" in gs:
                    rightGroup = gs

        if exceptionType == "find":
            kp = (leftGroup, rightGroup)
        elif exceptionType == "g2G":
            kp = (leftGlyph, rightGroup)
        elif exceptionType == "g2g":
            kp = (leftGlyph, rightGlyph)
        elif exceptionType == "G2g":
            kp = (leftGroup, rightGlyph)
        else:
            raise TypeError("exception type unknown") 
        

        if debug:
            print(kp, value)
        else:
            del self._font.kerning[kp]


    def getPath(self) -> str:
        return self._path

    def setPath(self, value:str) -> None:
        self._path = value

    path = property(getPath, setPath)

    def getUse(self) -> bool:
        return self._use

    def setUse(self, value:bool) -> None:
        self._use = value

    use = property(getUse, setUse)

    def getFont(self) -> str:
        return self._font

    def setFont(self, value:DoodleFont) -> None:
        if self._layer.name not in value.layerOrder:
            self._layer = value.layers.defaultLayer
        self._font = value

    font = property(getFont, setFont)

    # we use layer to actually draw
    def getLayer(self) -> DoodleLayer:
        return self._layer

    def setLayer(self, value:str|DoodleLayer) -> None:
        if isinstance(value, str):
            name = value
        elif isinstance(value, DoodleLayer):
            name = value.name

        if name in self._font.layers.layerOrder:
            self._layer = self._font.layers[name]

    layer = property(getLayer, setLayer)

    def getText(self) -> str|None:
        return self._text

    def setText(self, value:str|None) -> None:
        self._text = value

    text = property(getText, setText)

    def getLocalText(self) -> bool:
        return self._localText

    def setLocalText(self, value:bool) -> None:
        self._localText = value

    localText = property(getLocalText, setLocalText)
