import math
import os
import time

import AppKit
import ezui
import merz
import yaml
from defcon import Font
from designspaceEditor.locationPreview import PreviewLocationFinder
from designspaceEditor.ui import DesignspaceEditorController
from drawBot.context.tools.drawBotbuiltins import remap
from fontParts.world import (
    CurrentFont,
    CurrentGlyph,
    CurrentLayer,
    OpenFont,
    #RGlyph,
    #RFont
)
from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)
from fontTools.misc import transform
from glyphNameFormatter.reader import N2n, n2N, n2u, u2n
from lib.fontObjects.doodleFont import DoodleFont
from lib.fontObjects.doodleGlyph import DoodleGlyph
from lib.fontObjects.doodleLayer import DoodleLayer
from lib.UI.spaceCenter import spaceInputScrollView as spaceInput
from lib.UI.spaceCenter.glyphSequenceEditText import (
    GlyphSequenceEditComboBox,
    currentGlyphKey,
    currentSelectionKey,
    groupsKey,
    newLineKey,
    splitText,
)
from lib.UI.spaceCenter.lineViewGlyphWrappers import GlyphRecord
from merz.errors import MerzError
from merz.tools.typesetter import HorizontalTypesetter
from mojo import events
from mojo.extensions import getExtensionDefault, setExtensionDefault

# from fontParts.fontshell.font import RFont as RFont # we need to do this because RFont from .world is a function
# from fontParts.fontshell.glyph import RGlyph as RGlyph # we need to do this because RGlyph from .world is a function
from mojo.roboFont import AllFonts, CurrentFont, RFont, RGlyph, internalFontClasses
from mojo.subscriber import (
    Coalescer,
    Subscriber,
    getRegisteredSubscriberEvents,
    registerRoboFontSubscriber,
    registerSubscriberEvent,
    unregisterRoboFontSubscriber,
)
from mojo.UI import GetFile, OpenGlyphWindow, getDefault, splitText
from ufoProcessor.ufoOperator import UFOOperator
from vanilla.vanillaBase import osVersion12_0, osVersionCurrent

"""
versioning
adds alpha to anything less than 0.1.0
adds beta to anything less than 1.0.0
"""
FALLBACK_VERSION = "0.0.0"
INFO_YAML = os.path.abspath(os.path.join(__file__, "../../../", "info.yaml"))
if os.path.exists(INFO_YAML):
    with open(INFO_YAML, mode="r") as file:
        info = yaml.safe_load(file)
else:
    info = dict(version=FALLBACK_VERSION)
EXTENSION_VERSION = info.get("version", FALLBACK_VERSION)
if int(EXTENSION_VERSION.split(".")[0]) < 1:
    if int(EXTENSION_VERSION.split(".")[1]) < 1:
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

DETACH_DATA:dict[str:int] = dict(width="fill",height=20, gravity="trailing")
DETACH_STACK:str          = "*HorizontalStack    @detachStack"

MATRIX_POS:tuple[int,int,int,int] = (0, -48, 0, 48)

CASES:list[str] = ["lower", "title", "upper", "default"]

CURSOR_SIZE = 30
CURSOR_IMAGE = AppKit.NSCursor.IBeamCursor().image()
CURSOR_IMAGE = CURSOR_IMAGE.resizeTo_(CURSOR_SIZE)
TYPING_CURSOR = CreateCursor(
    CURSOR_IMAGE,
    hotSpot=(CURSOR_SIZE/2, CURSOR_SIZE/2)
)
IBEAM_COLOR:tuple[float,float,float,float] = (0, 0.478, 1, 1)
ARROW_CURSOR = AppKit.NSCursor.arrowCursor()

class EZSequenceCombo(GlyphSequenceEditComboBox, ezui.tools.ParserMixIn):
    # https://github.com/typemytype/basicShapingRoboFontExtension/blob/47698796e1b45b074e6489b49c8b7b7ab7493bce/BasicShaping.roboFontExt/lib/CoreTextShaping.py#L167
    def __init__(
        self,
        *args,
        container=None,
        controller=None,
        descriptionData=None,
        identifier=None,
        callback=None,
        **kwargs
    ):
        ezui.tools.assignIdentifier(
            item=self,
            identifier=identifier,
            container=container
        )
        callback = ezui.tools.findCallback(
            callback=callback,
            identifier=identifier,
            container=container,
            controller=controller
        )
        super().__init__("auto", *args, callback=callback, **kwargs)

# we should move this to the __init__.py once we make one
try:
    ezui.tools.classes.registerClass("SequenceCombo", EZSequenceCombo)
except:
    pass

class InterpolationWarningWindow(ezui.WindowController):

    def build(self, parent, relative):

        self.relative = relative

        content = """
        * HorizontalStack                           @stack
        > * Image                                   @warningImage
        You must add a designspace file first!      @label
        ----------
        ( Manage Objects )                          @openDesignspaceButton
        """

        descriptionData = dict(
            stack=dict(
                distribution="fillEqually"
            ),
            label=dict(
                alignment="center",
            ),
            warningImage=dict(
                image=ezui.makeImage(
                    symbolName="exclamationmark.triangle",
                ),
                symbolConfiguration=dict(
                    scale="large",
                ),
            ),
            openDesignspaceButton=dict(
                width="fill"
            ),
        )
        self.w = ezui.EZPopUp(
            size=(200, 150),
            descriptionData=descriptionData,
            content=content,
            parent=parent,
            controller=self
        )

    def openDesignspaceButtonCallback(self, sender) -> None:
        window = self.relative.buildObjectsSheet()
        window.open()

    def started(self) -> None:
        self.w.open()


class MerzCollectionViewRGlyphItem(merz.collectionView.MerzCollectionViewItem):

    def __init__(self, *args, **kwargs) -> None:
        self._name:str                 = kwargs.get("name", "")
        self._font:DoodleFont          = kwargs.get("font")
        self._glyph:RGlyph             = kwargs.get("glyph")
        self._index:int                = kwargs.get("index", 0)
        self._onDisk:bool              = kwargs.get("onDisk", True)
        self._offset:float|int         = kwargs.get("italicOffset", 0)
        self._skewAngle:float|int      = kwargs.get("skewAngle", 0)
        self._scaler:float|int         = kwargs.get("scaler", 1)
        self._location:dict[str,float] = kwargs.get("location", {})
        self._selected:bool            = False
        self._isTyping:bool            = False
        self._selectedVisible:bool     = False

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

    def getSelected(self) -> bool:
        return self._selected

    def setSelected(self, value:bool=False) -> None:
        self._selected = value
        self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    selected = property(getSelected, setSelected)

    def getTypingItem(self) -> bool:
        return self._isTyping

    def setTypingItem(self, value:bool=False) -> None:
        self._isTyping = value
        layer = self.getLayer("glyphContainer").getSublayer("typingIndicator")
        layer.setVisible(value)
        if self._isTyping:
            sublayer = layer.getSublayer("typingIndicatorDrawing")
            sublayer.setFillColor(IBEAM_COLOR)
            with sublayer.propertyGroup(
                duration=.5,
                repeatCount="loop",
                reverse=True,
                timing="easeInEaseOut",
            ):
                sublayer.setFillColor((*IBEAM_COLOR[0:3], .1))

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

    def getSkewAngle(self) ->  int|float:
        return self._skewAngle

    def setSkewAngle(self, value:int|float) -> None:
        self._skewAngle = value

    skewAngle = property(getSkewAngle, setSkewAngle)

    def getScaler(self) ->  int|float:
        return self._scaler

    def setScaler(self, value:int|float) -> None:
        self._scaler = value

    scaler = property(getScaler, setScaler)

    def getLocation(self) ->  dict[str,float]:
        return self._location

    def setLocation(self, value:dict[str,float]) -> None:
        self._location = value

    location = property(getLocation, setLocation)


class Spaceport(Subscriber, ezui.WindowController):

    debug = True

    def build(self) -> None:

        self.__cache:list[MerzCollectionViewRGlyphItem] = []

        self.selectedItems:list[MerzCollectionViewRGlyphItem] = []

        self.case:str = "default"

        self.foreground:tuple[float,...] = (0, 0, 0, 1)
        self.background:tuple[float,...] = (1, 1, 1, 1)

        self.showKerning:bool           = False
        self.showMetrics:bool           = False
        self.showLabel:bool             = True
        self.multiline:bool             = True
        self.openSources:bool           = False
        self.viewSources:bool           = False # for testing its false
        self.viewInstances:bool         = False
        self.showBeam:bool              = True
        self.designspaceController:bool = True

        self.sortingSettings:list[int] = []
        self.weightSort:int = 1
        self.widthSort:int  = 1
        self.italicSort:int = 1

        self.viewDesignspace:bool = False

        self.typing:bool   = False
        self.detached:bool = False

        self.typingIndex:int|None = None
        self.typingFont:DoodleFont|None=None

        self.currentGlyph:RGlyph                     = CurrentGlyph()
        self.font:RFont                              = CurrentFont()
        self.fonts:dict[str,tuple[bool,RFont]]       = dict()
        self._fontFolder:dict[str,tuple[bool,RFont]] = dict()
        self.glyphs:list[str,...]                    = []
        self.holdingGlyphs:list[str,...]             = []
        self.rawGlyphList:list[str,...]              = []

        for f in AllFonts():
            f.lib["descriptor"] = ""
            self.fonts[f.path] = (f==CurrentFont(), f)

        self.internalPreview:bool = False
        self.designspaces:dict[str,tuple[bool,UFOOperator]] = dict()
        self.operator:UFOOperator|DesignspaceEditorController|None = None

        self.xAxis:str|None = None
        self.yAxis:str|None = None

        self.x:float = 0.0
        self.y:float = 0.0

        # add type hints
        self.sources:list[DoodleFontType]       = []
        self.instances:list[InstanceDescriptor] = []

        self.pointSize:float|int  = 30
        self.scale:float|int      = 1
        self.lineHeight:float|int = round(30 * 1.2)

        self.zoomCoalescer:Coalescer = Coalescer(
            callback=self.zoomEnded,
            delay=.1,
            subscriptionKey=None,
            coalescerKey=None,
        )

        self.typingCoalescer:Coalescer = Coalescer(
            callback=self.subscribeToGlyphs,
            delay=.5,
            subscriptionKey=None,
            coalescerKey=None,
        )

        self.beamPosition:float = int(getattr(getattr(self.font, "info", None), "xHeight", 500) / 2)
        self.upm:int = int(getattr(getattr(self.font, "info", None), "unitsPerEm", 1000))

        toolbar = dict(
            autosaveName="demoToolbar",
            allowCustomization=True,
            contents=[
                dict(
                    identifier="addObjects",
                    image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, f"{ADD_OBJECT}.svg"), template=True),
                    text="Objects",
                    template=True,
                ),
                # dict(
                #     identifier="kerning",
                #     image=ezui.makeImage(imagePath=os.path.join(RESOURCES_f"{PATH, KERNING}.svg"), template=True),
                #     text="Kerning",
                #     template=True,
                # ),

                dict(
                    identifier="opentype",
                    image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, f"{OPENTYPE}.svg"), template=True),
                    text="OpenType",
                    template=True,
                ),
                dict(
                    identifier="interpolate",
                    image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, f"{INTERPOLATE}.svg"), template=True),
                    text="Interpolate",
                    template=True,
                ),
            ]
        )

        content = """
        * VerticalStack
        > --------------
        > * HorizontalStack                 @controlsStack
        >> ---X--- [__](±)                  @pointSizeInputField
        >> ---X--- [__](±)                  @lineHeightField
        >> ---------------
        >> * HorizontalStack
        >>> *GlyphSequence                  @leadingTextField
        >>> *Image                          @trailingLeadingImage
        >>> *GlyphSequence                  @trailingTextField
        >> ({arrow.left.and.right.square})  @zoomToWidth
        >> ({arrow.up.and.down.square})     @zoomToHeight
        >> ({gearshape})                    @viewOptions
        """
        for i in range(4):
            content += f"""
            > --------            @line{i}
            """
        content += """
        >* MerzCollectionView               @collectionView
        """
        numberFieldWidth = 40

        fontToLoad = self.font or internalFontClasses.createFontObject()
        if isinstance(fontToLoad, RFont):
            fontToLoad = fontToLoad.naked()

        descriptionData = dict(
            collectionView=dict(
                height="fill",
                width="fill",
                delegate=self,
            ),
            leadingTextField=dict(
                width=40,
                font=fontToLoad,
            ),
            trailingTextField=dict(
                width=40,
                font=fontToLoad,
            ),
            textField=dict(
                width="fill",
                font=fontToLoad,
                items=getDefault('spaceCenterInputSamples', []),
            ),
            controlsStack=dict(
                margins=(10,0,10,0)
            ),
            pointSizeInputField=dict(
                valueType="integer",
                textFieldWidth=numberFieldWidth,
                minValue=20,
                value=150,
                maxValue=500,
                valueIncrement=5,
                width=160,
            ),
            lineHeightField=dict(
                textFieldWidth=numberFieldWidth,
                valueType="float",
                minValue=0.5,
                value=1.0,
                maxValue=2.0,
                valueIncrement=0.1,
                width=140,
            ),

            trailingLeadingImage=dict(
                image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, "leading.trailing.svg"), template=True),
                symbolConfiguration=dict(
                    scale="large",
                )
            ),

            zoomToWidth=dict(
                image=ezui.makeImage(symbolName=ZOOM_WIDTH, imagePath=os.path.join(RESOURCES_PATH, f"{ZOOM_WIDTH}.svg"), template=True),
                symbolConfiguration=dict(
                    scale="large",
                )
            ),
            zoomToHeight=dict(
                image=ezui.makeImage(symbolName=ZOOM_HEIGHT, imagePath=os.path.join(RESOURCES_PATH, f"{ZOOM_HEIGHT}.svg"), template=True),
                symbolConfiguration=dict(
                    scale="large",
                )
            ),
        )

        self.w = ezui.EZWindow(
            title=f"Spaceport v{EXTENSION_VERSION}",
            toolbar=toolbar,
            content=content,
            descriptionData=descriptionData,
            controller=self,
            margins=0,
            size=(1000, 500),
            minSize=(400, 200),
        )
        # resize only the slider
        self.w.getItem("pointSizeInputField")._slider._setSizeStyle("small")

        self.styleWindowButtons(self.w)

        for i in range(4):
            item = f"line{i}"
            self.w.getItem(item).show(False)

        self.collectionView = self.w.getItem("collectionView")
        self.container = self.collectionView.getMerzContainer()
        self.collectionView.setBackgroundColor(AppKit.NSColor.whiteColor())
        self.w.matrix = spaceInput.SpaceInputScrollView(MATRIX_POS)
        self.matrixPosition:int = 0

        self.buildSettingsPopover()

        #contentViewController
        self.viewSettingsWindow.getItem("invertColorsButton").set(0)
        self.invertColorsButtonCallback(self.viewSettingsWindow.getItem("invertColorsButton"))

        viewPrefs = getExtensionDefault(EXTENSION_KEY + ".view_prefs", fallback=self.viewSettingsWindow.getItemValues())
        try: self.viewSettingsWindow.setItemValues(viewPrefs)
        except (AttributeError, KeyError): pass

        windowSettings = self.w.getItemValues()
        for name,field in windowSettings.items():
            if name.lower().endswith("textfield"):
                cleanedInput = []
                for glyph in field:
                    if glyph in [CURRENTGLYPH_CHAR, SELECTEDGLYPHS_CHAR]:
                        cleanedInput.append(glyph)
                    else:
                        try:
                            cleanedInput.append(chr(n2u(glyph)))
                        except:
                            pass
                windowSettings[name] = ''.join(cleanedInput)

        mainPrefs = getExtensionDefault(EXTENSION_KEY + ".main_prefs", fallback=windowSettings)
        try: self.w.setItemValues(mainPrefs)
        except (AttributeError, KeyError): pass

        holding = getExtensionDefault(EXTENSION_KEY + ".text", [])
        if holding:
            self.holdingGlyphs = holding

        self.controlsStackCallback(None)
        self.displaySettingsButtonCallback(None)
        self.showMetricsButtonCallback(None)
        #self.showKerningButtonCallback(None)
        self.textFieldCallback(None)

        if not self.fonts:
            window = self.buildObjectsSheet()
            if window: window.open()

    def started(self) -> None:
        self.w.open()


    def buildSettingsPopover(self, open:bool=False) -> None:
        self.detached = False
        content = DETACH_STACK
        content += """
        > ({arrow.up.right.circle})                                   @detachSettingsButton

        [X] Multiline                                                 @multilineButton
        [ ] Show Label                                                @showLabelButton
        [ ] Show Kerning                                              @showKerningButton
        [X] Show Metrics                                              @showMetricsButton
        [ ] Show Control Glyphs                                       @showControlGlyphsButton
        -----
        [X] Show Space Matrix                                         @showSpaceMatrixButton
        * HorizontalStack
        > ({arrow.trianglehead.swap})                                 @moveSpaceMatrixButton
        > Matrix Position
        Beam:
        * HorizontalStack
        > [X]                                                         @showBeamButton
        > --X------                                                   @beamPositionSlider
        -----
        Invert Colors:
        ( {circle.dashed} | {circle.fill} )                           @invertColorsButton
        Glyph Drawing Options:
        (( Fill | Stroke ))                                           @displaySettingsButton
        -----
        Sorting Order:
        ( Fonts | Line | Glyph )                                      @sortingButton
        -----
        Text Formatting:
        ( {characters.lowercase} | {textformat.characters} | {characters.uppercase} | None ) @textFormattingButton
        -----
        Horizontal Text Alignment:
        ( {text.alignleft} | {text.aligncenter} | {text.alignright} ) @horzAlignmentSegmentButton
        Vertical Text Alignment (BETA):
        ( {align.vertical.top} | {align.vertical.center} | {align.vertical.bottom} ) @vertAlignmentSegmentButton
        """

        descriptionData = dict(
            textFormattingButton=dict(
                selected=CASES.index(self.case)
            ),
            detachSettingsButton=DETACH_DATA,
            showBeamButton=dict(
                value=True,
            ),
            beamPositionSlider=dict(
                minValue=0,
                maxValue=self.upm,
                value=self.beamPosition
            ),
            showKerningButton=dict(
                # hide=False,
            ),
            showMetricsButton=dict(
                value=True
            ),
            showLabelButton=dict(
                value=True
            ),
            displaySettingsButton=dict(
                selected=[0]
            ),
            horzAlignmentSegmentButton=dict(
                selected=0
            ),
            vertAlignmentSegmentButton=dict(
                selected=0
            ),
            showSpaceMatrixButton=dict(
                value=True,
            ),
            moveSpaceMatrixButton=dict(
                height=20,
                width=13,
            ),
        )

        self.glyphMap = {}
        parent = self.w.getItem("viewOptions")
        self.viewSettingsWindow = ezui.EZPopover(
            size=(100,100),
            content=content,
            descriptionData=descriptionData,
            parent=parent,
            # behavior="transient",
            # parentAlignment="right",
            controller=self
        )
        self.viewSettingsWindow.getItem("showKerningButton").show(False)

        # disable while we work on the functions
        self.viewSettingsWindow.getItem("sortingButton").enable(False)
        self.viewSettingsWindow.getItem("showControlGlyphsButton").enable(False)
        self.viewSettingsWindow.getItem("vertAlignmentSegmentButton").enable(False)

        self.styleWindowButtons(self.viewSettingsWindow)

        if open: self.viewSettingsWindow.open()


    # designspace editor notifcations
    designspaceEditorPreviewLocationDidChangeDelay = 0.01
    def designspaceEditorPreviewLocationDidChange(self, notification) -> None:
        if self.designspaceController or self.internalPreview:
            selectedFonts = list(set([i.font for i in self.selectedItems if not i.onDisk]))
            if len(selectedFonts) == 1:
                pass
            elif not selectedFonts:
                if not self.fonts.get("Preview Location")[0]:
                    self.fontTableEditCallback(None) # turn on preview location
                # grab out dummy instance
                # selectedFonts = [list(self.fonts.values())[0][-1]]
                selectedFonts = [self.fonts.get("Preview Location")[-1]]

            for item in self.collectionView.get():
                if item.font == selectedFonts[0]:
                    self.updateItem(item, updatedLocation=notification["location"])
        self.collectionView.set(self.w.getItemValue("collectionView")) # i think that this is the only external-way to reload the view
        self.collectionView._documentView.set(self.w.getItemValue("collectionView"))


    def designspaceEditorInstancesDidChangeSelection(self, notification) -> None:
        if self.designspaceController:
            operator = notification["designspace"]
            self.instances = notification["selectedItems"]
            self.designspaceSettingsChanged(
                    object=operator,
                    sources=self.sources,
                    instances=self.instances
            )


    def designspaceEditorSourcesDidChangeSelection(self, notification) -> None:
        if self.designspaceController:
            operator = notification["designspace"]
            sources = notification["selectedItems"]
            reformated = []
            fs = operator.getFonts()
            locations = [s.designLocation for s in sources]
            for (ff,ll) in fs:
                if ll in locations:
                    reformated.append((ff,ll))
            self.sources = reformated
            self.designspaceSettingsChanged(
                    object=operator,
                    sources=self.sources,
                    instances=self.instances
            )


    def openSourcesCheckboxCallback(self, sender) -> None:
        self.openSources = sender.get()


    def designspaceSettingsButtonCallback(self, sender) -> None:
        self.viewSources           = 0 in sender.get()
        self.viewInstances         = 1 in sender.get()
        self.designspaceController = 2 in sender.get()
        self.designspaceSettingsChanged()


    def vertAlignmentSegmentButtonCallback(self, sender) -> None:
        m = "top center bottom".split(" ")
        position = m[sender.get()]
        collection = self.collectionView
        typesetter = collection._documentView._typesetter
        # firstYPos = typesetter.getItemPosition(0)[1]
        lineHeight = self.w.getItemValues()["lineHeightField"]
        pointSize = self.w.getItemValues()["pointSizeInputField"]

        __,(__,containerHeight) = collection.getNSScrollView().bounds()
        availableHeight = (len(typesetter.getLines())-1) * (lineHeight * pointSize)

        # print(typesetter._lineHeight, (lineHeight * pointSize) * (1/self.scale))

        if availableHeight < containerHeight:
            if position == "top":
                offset = 0
            elif position == "center":
                offset = ((containerHeight - availableHeight) / 2)
            else:
                offset = (containerHeight)

            typesetterScale = 1 / self.scale
            offset *= typesetterScale

            for i, item in enumerate(collection.get()):
                typeitem = typesetter[i]
                x,y = typesetter.getItemPosition(i)
                typeitem.setPosition((x,y+offset))


    def textFormattingButtonCallback(self, sender) -> None:
        self.case = CASES[sender.get()]
        self.textFieldCallback(None)


    def showSpaceMatrixButtonCallback(self, sender) -> None:
        if self.matrixPosition == 1:
            for i in range(4):
                item = f"line{i}"
                self.w.getItem(item).show(sender.get())
        self.w.matrix.show(sender.get())


    def moveSpaceMatrixButtonCallback(self, sender) -> None:
        if self.w.matrix.isVisible():
            if self.matrixPosition == 0:
                self.matrixPosition = 1
                x,y,w,h = MATRIX_POS
                pos = (x,40,w,h)
                show = True
            else:
                self.matrixPosition = 0
                pos = MATRIX_POS
                show = False

            self.w.matrix.setPosSize(pos, False)
            for i in range(4):
                item = f"line{i}"
                self.w.getItem(item).show(show)


    def styleWindowButtons(self, window:ezui.windows.window.EZWindow | ezui.windows.popover.EZPopover) -> None:
        for name, item in window.getItems().items():
            if isinstance(item, ezui.items.segmentButton.SegmentButton):
                item.getNSSegmentedButton().setSegmentStyle_(AppKit.NSSegmentStyleRoundRect)

    def buildObjectsSheet(self) -> None:

        if not self.designspaces:
            self.designspaces = {dsp.path:(False, dsp) for dsp in AllDesignspaces()}

        content = """
        *HorizontalStack
        > * Box                                                            @fontBox = VerticalStack
        >> !!!Fonts
        >> * HorizontalStack                                               @fontStack
        >>> ((( Refresh Order | Add All Open Fonts )))                     @addAndReorderButton
        >>> *Image                                                         @sortImage
        >>> (( Weight | Width | Italic))                                   @sortFontListButton
        >> |-files----|                                                    @fontTable
        >> |          |
        >> |----------|
        >> (+-)                                                            @fontTableAddRemoveButton
        > * Box                                                            @designspaceBox = VerticalStack
        >> !!!Designspaces
        >> (( View Sources | View Instances | DSE Controller ))            @designspaceSettingsButton
        >> |-files----|                                                    @designspaceTable
        >> |          |
        >> |----------|
        >> (+-)                                                            @designspaceTableAddRemoveButton
        """

        descriptionData = dict(
            fontStack=dict(
                alignment="center",
                ),
            contents=dict(
                displayMode="text",
                allowCustomization=True,
                toolbarStyle="preference"
            ),
            fontBox=dict(
                width=400,
            ),
            designspaceBox=dict(
                width=400,
            ),
            sortImage=dict(
                image=ezui.makeImage(
                    symbolName="point.topright.arrow.triangle.backward.to.point.bottomleft.scurvepath.fill",
                    template=True,
                )
            ),
            sortFontListButton=dict(
                segmentDescriptions=[
                    dict(
                        # text="Weight",
                        image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, "sort.weight.svg"), template=True),
                    ),
                    dict(
                        # text="Width",
                        image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, "sort.width.svg"), template=True),
                    ),
                    dict(
                        # text="Italic",
                        image=ezui.makeImage(imagePath=os.path.join(RESOURCES_PATH, "sort.italic.svg"), template=True),
                    ),
                ]
            ),
            fontTable=dict(
                height=200,
                items=[
                    dict(use=use,path=path) for (path, (use, font)) in self.fonts.items()
                ],
                itemType="dict",
                acceptedDropFileTypes=[".ufo", ".ufoz", ".ufox"],
                allowsDropBetweenRows=True,
                allowsInternalDropReordering=True,
                showColumnTitles=True,
                enableDelete=True,
                alternatingRowColors=True,
                columnDescriptions=[
                    dict(
                        editable=True,
                        width=50,
                        identifier="use",
                        title="Display",
                        cellDescription=dict(
                            cellType="Checkbox"
                        )
                    ),
                    dict(
                        identifier="path",
                        title="UFO",
                        cellClassArguments=dict(
                            showFullPath=False
                    )),

                ]
            ),
            designspaceTable=dict(
                height=200,
                items=[
                    dict(use=use,path=path) for (path, (use, dsp)) in self.designspaces.items()
                ],
                itemType="dict",
                acceptedDropFileTypes=[".designspace"],
                allowsMultipleSelection=False,
                allowsDropBetweenRows=True,
                allowsDragOut=False,
                showColumnTitles=True,
                alternatingRowColors=True,
                columnDescriptions=[
                  dict(
                        editable=True,
                        width=50,
                        identifier="use",
                        title="Display",
                        cellDescription=dict(
                            cellType="Checkbox"
                        )
                    ),
                    dict(
                        identifier="path",
                        title="Designspace"
                    ),
                ]
            ),
        )

        self.w.objw = ezui.EZSheet(
            autosaveName="objectController",
            size="auto",
            content=content,
            descriptionData=descriptionData,
            parent=self.w,
            controller=self
        )


        self.styleWindowButtons(self.w.objw)
        # get current values
        vs = 0 if self.viewSources else None
        vi = 1 if self.viewInstances else None
        dc = 2 if self.designspaceController else None

        self.w.objw.getItem("designspaceSettingsButton").set([vs,vi,dc])

        self.w.objw.getItem("sortFontListButton").set(self.sortingSettings)


        indexes = [ii for ii,(i,obj) in enumerate(self.fonts.items()) if obj[0]]
        self.w.objw.getItem("fontTable").setSelectedIndexes(indexes)

        table=self.w.objw.getItem("designspaceTable")
        selectionIndex = None
        if self.operator:
            for ii, (path,(use, obj)) in enumerate(self.designspaces.items()):
                if obj == self.operator:
                    selectionIndex = ii
        if selectionIndex != None:
            table.setSelectedIndexes([selectionIndex])
        return self.w.objw

    def openAllFontsButtonCallback(self) -> None:
        current = self.fonts.keys()
        for f in AllFonts():
            if f.path not in current:
                self.fonts[f.path] = (False, f)
        self.fonts = {path:(True,font) for path,(view,font) in self.fonts.items()}
        self.w.objw.getItem("fontTable").set(dict(use=use,path=path) for (path, (use, font)) in self.fonts.items())
        self.populateItems()


    def fontTableAddRemoveButtonAddCallback(self, sender) -> None:
        table = self.w.objw.getItem("fontTable")
        files = GetFile(allowsMultipleSelection=True, fileTypes=["ufo", "ufoz"])
        if files:
            for file in files:
                item = table.makeItem(
                    use=True,
                    path=file
                )
                table.appendItems([item])
                obj = OpenFont(file,True)
                self.fonts[file] = (True, obj)


    def fontTableAddRemoveButtonRemoveCallback(self, sender) -> None:
        table = self.w.objw.getItem("fontTable")
        table.removeSelectedItems()


    def designspaceTableAddRemoveButtonAddCallback(self, sender) -> None:
        table = self.w.objw.getItem("designspaceTable")
        files = GetFile(allowsMultipleSelection=True, fileTypes=["designspace"])
        if files:
            for file in files:
                item = table.makeItem(
                    use=False,
                    path=file
                )
                table.appendItems([item])
                obj = DesignspaceEditorController(file)
                operator = obj.operator
                self.designspaces[file] = (False,operator)


    def designspaceTableAddRemoveButtonRemoveCallback(self, sender) -> None:
        table = self.w.objw.getItem("designspaceTable")
        table.removeSelectedItems()


    def designspaceSettingsChanged(self, **kwargs) -> None:
        obj = kwargs.get("object", self.operator)
        reset = kwargs.get("reset", False)

        openFonts = {f.path:f for f in AllFonts()}
        if reset:
            self.fonts = self._fontFolder
        else:
            if obj:
                sources = kwargs.get("sources", obj.getFonts())
                instances = kwargs.get("instances", obj.instances)
                # remove designspace items
                fontsDict = list(self.fonts.items())
                for _path, (_view, _font) in fontsDict:
                    # if _view:
                    if _path in [p.path for (p,_) in self.sources]:
                        del self.fonts[_path]
                        self._fontFolder[_path] = (_view, _font)

                # temporarily disable font previews when changing sources

                preview = self.fonts.get("Preview Location")
                for path, (view, font) in self.fonts.items():
                    self.fonts[path] = (False, font)

                if "Preview Location" not in self.fonts.keys():
                    # create a temporary instance that we can interpolate on if no fonts are selected
                    temp = internalFontClasses.createFontObject()
                    temp.info.familyName = "Preview Location"
                    temp.lib["descriptor"] = "instance"
                    temp.lib["location"]   = obj.findDefault().designLocation
                    obj.makeOneInfo(temp.lib["location"]).extractInfo(temp.info)

                    libMutator = obj.getLibEntryMutator(obj.getLocationType(temp.lib["location"])[2])
                    if libMutator:
                        lib = libMutator.makeInstance(temp.lib["location"])
                        temp.lib["com.typemytype.robofont.italicSlantOffset"] = lib.get("com.typemytype.robofont.italicSlantOffset", 0)

                    items = list(self.fonts.items())
                    items.insert(0, ('Preview Location', (False, temp)))
                    self.fonts = dict(items)

                if self.viewSources:
                    for source,locationData in sources:

                        if source.path in openFonts.keys():
                            source = openFonts.get(source.path)

                        source.lib["descriptor"] = "source"
                        source.lib["location"]   = locationData
                        self.fonts[source.path]  = (True,source)

                if self.viewInstances:
                    for instance in instances:
                        inst = internalFontClasses.createFontObject()
                        inst.lib["descriptor"] = "instance"
                        inst.lib["location"]   = instance.designLocation
                        obj.makeOneInfo(instance.designLocation).extractInfo(inst.info)

                        libMutator = obj.getLibEntryMutator(obj.getLocationType(instance.designLocation)[2])
                        if libMutator:
                            lib = libMutator.makeInstance(instance.designLocation)
                            inst.lib["com.typemytype.robofont.italicSlantOffset"] = lib.get("com.typemytype.robofont.italicSlantOffset", 0)

                        self.fonts[instance.path] = (True,inst)

                if preview:
                    self.fonts["Preview Location"] = preview


        if not self.font and self.fonts:
            self.setMainFont(obj, True)
        try:
            self.w.objw.getItem("fontTable").set(dict(use=use,path=path) for (path, (use, font)) in self.fonts.items())
        except AttributeError:
            pass
        self.populateItems()


    def designspaceTableEditCallback(self, sender) -> None:
        index = sender.getEditedIndex()
        path  = list(self.designspaces.keys())[index]
        obj = self.designspaces[path][-1]
        self.operator = obj
        self.sources = obj.getFonts()
        self.instances = obj.instances
        view = [item["use"] for item in sender.get() if item["path"] == path][0]

        self.designspaces[path] = (view, obj)
        self.designspaceSettingsChanged(
                                        object=obj,
                                        sources=self.sources,
                                        instances=self.instances,
                                        reset=False if view else True
        )

        self.textFieldCallback(None)
        #self.w.objw.getItem("fontTable").set(dict(use=use,path=path) for (path, (use, font)) in self.fonts.items())
        self.populateItems()


    def setMainFont(self, operator=None, setText=False) -> None:
        if operator:
            self.font = operator.getFonts()[0][0]
        else:
            self.font = list(self.fonts.values())[1][-1]
        self.upm = self.font.info.unitsPerEm
        if setText:
            for name,item in self.w.get().items():
                if "textfield" in name.lower():
                    self.w.getItem(name).setFont(self.font)


    def designspaceTableCreateItemsForDroppedPathsCallback(self, sender, paths) -> list:
        operators = []
        operator = None
        for path in paths:
            controller = DesignspaceEditorController(path)
            operator = controller.operator
            self.designspaces[path] = (False,operator)
            item = dict(
                use=False,
                path=path,
            )
            operators.append(item)
        if operator: self.setMainFont(operator, True)
        return operators


    def addObjectsCallback(self, sender) -> None:
        window = self.buildObjectsSheet()
        window.open()


    def addAndReorderButtonCallback(self, sender) -> None:
        if sender.get() == 0:
            self.refreshOrderButtonCallback()
        else:
            self.openAllFontsButtonCallback()


    def refreshOrderButtonCallback(self) -> None:
        reordered = [item["path"] for item in self.w.objw.getItemValue("fontTable")]
        if reordered != list(self.fonts.keys()):
            self.fonts = {item["path"]:(item["use"],self.fonts[item["path"]][1]) for item in self.w.objw.getItemValue("fontTable")}
            self.populateItems()


    def sortFontListButtonCallback(self, sender) -> None:
        """
        allows you to sort all the fonts by weight, width, and italic states
        holding shift when you select a new item will reverse its value in the
        overall list. e.g.
        default:
        compressed - wide
        roman - italic
        light - dark

        with shift down:
        dark -  light
        etc.
        """
        sortKeys = "weight width italic".split(" ")
        recentSender = list(set(sender.get()) - set(self.sortingSettings))

        weight = 0 in sender.get()
        width  = 1 in sender.get()
        italic = 2 in sender.get()

        if recentSender:
            newIndex = recentSender[0]
            newItem  = sortKeys[newIndex]
            if AppKit.NSEvent.modifierFlags() & AppKit.NSShiftKeyMask:
                holding = getattr(self, f"{newItem}Sort")
                setattr(self, f"{newItem}Sort", -holding)

        sortedFonts = sorted(self.fonts, key=lambda key: (-self.fonts[key][1].info.openTypeOS2WidthClass * self.widthSort if width else 5, -self.fonts[key][1].info.italicAngle * self.italicSort if italic else 0, self.fonts[key][1].info.openTypeOS2WeightClass * self.weightSort if weight else 400))
        orderedDict = {path:self.fonts.get(path) for path in sortedFonts}

        self.sortingSettings = sender.get()

        self.fonts = orderedDict
        self.w.objw.getItem("fontTable").set(dict(use=use,path=path) for (path, (use, font)) in self.fonts.items())
        self.populateItems()


    def fontTableEditCallback(self, sender) -> None:
        if sender:
            new   = sender.getEditedItem()["use"]
            path  = list(self.fonts.keys())[sender.getEditedIndex()]
        else:
            new = True
            path = "Preview Location"
        use,font = self.fonts[path]
        self.fonts[path] = (new, font)
        self.textFieldCallback(None)


    def fontTableCreateItemsForDroppedPathsCallback(self, sender, paths) -> list[dict]:
        fonts = []
        _temp = list(self.fonts.keys())
        for path in paths:
            opened = OpenFont(path, self.w.objw.getItemValue("openFontWithUIButton"))
            self.fonts[path] = (False, opened)
            item = dict(
                use=False,
                path=path,
            )
            fonts.append(item)
        self.setMainFont()
        return fonts


    def fontTableButtonsAddCallback(self, sender) -> None:
        file = GetFile(fileTypes=["ufoz", "ufo", "ufox"])
        if file:
            opened = OpenFont(file)
            self.fonts[file] = (True, opened)
            self.w.objw.getItem("fontTable").close()
        self.populateItems()


    def fontTableDeleteCallback(self, sender) -> None:
        if len(sender.get()) > 1:
            items = sender.getSelectedIndexes()
            for it in items:
                ir = list(self.fonts.keys())[it]
                del self.fonts[ir]
            sender.removeSelection()


    def addDesignspaceCallback(self, sender) -> None:
        window = self.buildObjectsSheet()
        window.open()


    def spacingCallback(self, sender) -> None:
        pass


    def kerningCallback(self, sender) -> None:
        pass


    def opentypeCallback(self, sender) -> None:
        pass


    def interpolateCallback(self, sender) -> None:
        # pass
        # modified from DSE
        #x,y,w,h = self.w.getPosSize()
        #ww = w+(DESIGNSPACE_WIDTH/2) if self.viewDesignspace else w-(DESIGNSPACE_WIDTH/2)
        #self.w.setPosSize((x,y,ww,h))
        #self.w.getItem("designspaceNav").show(self.viewDesignspace)
        # self.w.resizeToFitContent()

        try:
            if not self.detatched:
                self.viewSettingsWindow.close()
        except: pass

        self.viewDesignspace = not self.viewDesignspace
        axes = "x"
        interpolatable = []
        if self.operator:
            content = ""
            descriptionData = dict(
                designspaceNav=dict(
                    height=300,
                    width=300,
                    delegate=self,
                    backgroundColor=(1,1,1,1)
                ),
            )

            for axisDescriptor in self.operator.axes:
                value = axisDescriptor.default
                if hasattr(axisDescriptor, "values"):
                    # discrete axis
                    content += """
                    *HorizontalStack
                    > {axisDescriptor.name}:
                    > ( ...)    @{axisDescriptor.name}
                    """
                    descriptionData[axisDescriptor.name] = dict(
                        items=[str(value) for value in axisDescriptor.values],
                    )
                else:
                    interpolatable.append(axisDescriptor.name)

            content += """
            * HorizontalStack   @axisSelectors
            """
            content += """
            > x-axis:
            > ( ...)            @xAxisSelection
            """
            if len(interpolatable) > 1:
                axes += "y"
                content += """
                > y-axis:
                > ( ...)        @yAxisSelection
            """

            content += """
            * MerzView          @designspaceNav
            """

            for i,a in enumerate(axes):
                idd = f"{a}AxisSelection"
                descriptionData[idd] = dict(
                    items=interpolatable,
                    selected=i
                )
                if a == "x":
                    self.xAxis = interpolatable[i]
                elif a == "y":
                    self.yAxis = interpolatable[i]

            descriptionData["axisSelectors"] = dict(
                distribution="fillEqually"
            )

            self.interpolationWindow = ezui.EZPopover(
                content=content,
                descriptionData=descriptionData,
                size="auto",
                parent=self.w,
                parentAlignment="right",
                controller=self
            )
            self.interpolationWindow.open()
        else:
            InterpolationWarningWindow(self.w, self)


    def detachSettingsButtonCallback(self, sender) -> None:
        self.viewSettingsWindow.getNSPopover().detach()
        self.viewSettingsWindow.getItem("detachSettingsButton").show(False)
        self.detached = True


    def viewOptionsCallback(self,sender) -> None:
        self.viewSettingsWindow.close()
        try: self.interpolationWindow.close()
        except: pass
        self.buildSettingsPopover(open=True)


    def yAxisSelectionCallback(self, sender) -> None:
        self.yAxis = self.interpolatable[sender.get()]
        self._convertViewLocationToDesignspaceLocation((self.x,self.y))


    def xAxisSelectionCallback(self, sender) -> None:
        self.xAxis = self.interpolatable[sender.get()]
        self._convertViewLocationToDesignspaceLocation((self.x,self.y))


    def contentCallback(self, sender) -> None:
        """
        this is linked as several callbacks so we have to
        make sure its only running for the designspace navigation
        popover and adjust then.
        """
        if isinstance(sender.get(), dict):
            if "xAxisSelection" in sender.get().keys():
                self._convertViewLocationToDesignspaceLocation((self.x,self.y))


    @property
    def interpolatable(self) -> list:
        return [axisDescriptor.name for axisDescriptor in self.operator.axes if not hasattr(axisDescriptor, "values")]


    def roboFontDidSwitchCurrentGlyph(self, info) -> None:
        # print(info["glyph"].name, CurrentGlyph().name)
        infoGlyph = info["glyph"]
        if infoGlyph is not None and self.currentGlyph is not None:
            if infoGlyph.name != self.currentGlyph.name:
                self.textFieldCallback(None)
        self.currentGlyph = CurrentGlyph()


    def leadingTextFieldCallback(self, sender) -> None:
        self.textFieldCallback(None)


    def trailingTextFieldCallback(self, sender) -> None:
        self.textFieldCallback(None)


    def validateGlyphNames(self, glyphNames:list[str]) -> list[str | None]:
        validated = []
        previous = None
        for index, glyphName in enumerate(glyphNames):
            name = glyphName
            selected = CurrentFont().selectedGlyphNames if CurrentFont() else  []
            if glyphName == SELECTEDGLYPHS_CHAR:
                if selected:
                    validated.extend(selected)
            else:
                if glyphName in self.font.keys():
                    name = glyphName
                elif glyphName == CURRENTGLYPH_CHAR:
                    if CurrentGlyph() is not None:
                        name = CurrentGlyph().name
                    else:
                        if selected:
                            name = selected[0]
                # modify case
                if self.case == "upper":
                    name = n2N(name)
                elif self.case == "lower":
                    name = N2n(name)
                elif self.case == "title":
                    if previous in "space period comma semicolon".split(" ") or index == 0:
                        name = n2N(name)
                    else:
                        name = N2n(name)
                else:
                    name = name
                validated.append(name)
            previous = name
        return validated


    def mergeTextList(self, glyphList:list[str,...]) -> list[str,...]:
        output = []
        index = 0

        while index < len(glyphList):
            if glyphList[index] == 'slash':
                slashed = '/'
                startIndex = index
                index += 1

                charsCollected = []
                while index < len(glyphList) and glyphList[index] not in ['space', 'slash']:
                    charsCollected.append(glyphList[index])
                    slashed += glyphList[index]
                    index += 1
                skipFollowingSpace = False
                if slashed == '/question':
                    output.append('/?')
                    skipFollowingSpace = True
                elif slashed == '/exclam':
                    output.append('/!')
                    skipFollowingSpace = True
                elif slashed == '/':
                    output.append('/')
                else:
                    glyphName = slashed[1:]

                    if glyphName in self.font.keys():
                        output.append(glyphName)
                        skipFollowingSpace = True
                    else:
                        output.append('slash')
                        output.extend(charsCollected)

                if index < len(glyphList) and glyphList[index] == 'space' and skipFollowingSpace:
                    index += 1
            elif glyphList[index] == 'space':
                output.append('space')
                index += 1
            else:
                output.append(glyphList[index])
                index += 1
        return output


    def combineText(self, glyphList:list[str,...]) -> str:
        # the opposite of mojo.UI's `splitText()`
        output = ""
        for glyphName in glyphList:
            if glyphName in [CURRENTGLYPH_CHAR,SELECTEDGLYPHS_CHAR]:
                output += f"{glyphName} "
            else:
                uu = n2u(glyphName)
                if uu:
                    cc = chr(uu)
                    if cc:
                        output += cc
                    else:
                        output += f"/{glyphName} "
                else:
                    output += f"/{glyphName} "
        return output

    def textFieldCallback(self, sender) -> None:
        self.typingCoalescer.restart()
        self.unsubscribeFromGlyphs()
        if self.font:
            raw = self.holdingGlyphs
            glyphNames = self.validateGlyphNames(self.mergeTextList(raw))
            self.rawGlyphList = raw

            font = self.font
            holding = []
            pre = self.validateGlyphNames(self.w.getItemValue("leadingTextField"))
            pst = self.validateGlyphNames(self.w.getItemValue("trailingTextField"))
            if font:
                for index,name in enumerate(glyphNames):
                    if name in font.keys():
                        holding.extend(pre)
                        holding.append(name)
                        holding.extend(pst)
            self.glyphs = holding
            self.populateItems()
            self.scale = self.w.getItemValue("pointSizeInputField") / self.upm

    def horzAlignmentSegmentButtonCallback(self, sender) -> None:
        self.controlsStackCallback(None)


    def controlsStackCallback(self, sender) -> None:
        windowSettings = self.w.getItemValues()
        viewSettings = self.viewSettingsWindow.getItemValues()

        pointSize = windowSettings["pointSizeInputField"]
        lineHeight = windowSettings["lineHeightField"]
        alignment = ("left", "center", "right")[viewSettings["horzAlignmentSegmentButton"]]
        scale = pointSize / self.upm
        lineHeight = self.upm * lineHeight * scale
        inset = pointSize * 0.2
        minInset = 10
        maxInset = 30
        if inset < minInset:
            inset = minInset
        elif inset > maxInset:
            inset = maxInset
        self.collectionView.setLayoutProperties(
            scale=scale,
            lineHeight=lineHeight,
            alignment=alignment,
            inset=(inset, inset)
        )

    def invertColorsButtonCallback(self, sender) -> None:
        self.invert = self.viewSettingsWindow.getItemValue("invertColorsButton")
        foregroundColor = [(0,0,0,1), (1,1,1,1)][self.invert]
        backgroundColor = [AppKit.NSColor.whiteColor(), AppKit.NSColor.blackColor()][self.invert]

        self.collectionView.setBackgroundColor(backgroundColor)
        items = self.w.getItemValue("collectionView")
        for item in items:
            glyphContainer = item.getLayer("glyphContainer")
            glyphFillLayer = glyphContainer.getSublayer("glyphFill")
            glyphFillLayer.setFillColor(foregroundColor)
            glyphFillLayer.setVisible(self.showFill)

            glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
            if self.showStroke:
                if self.invert:
                    glyphStrokeLayer.setStrokeWidth(.7)
                else:
                    glyphStrokeLayer.setStrokeWidth(1)

                glyphFillLayer.setFillColor((*foregroundColor[:3], .2))
            else:
                glyphFillLayer.setFillColor(foregroundColor)

            glyphStrokeLayer.setStrokeColor(foregroundColor)
            glyphStrokeLayer.setVisible(self.showStroke)

        self.foreground = foregroundColor
        self.background = backgroundColor


    def showMetricsButtonCallback(self, sender) -> None:
        self.showMetrics = self.viewSettingsWindow.getItemValue("showMetricsButton")
        self.displaySettingsButtonCallback(None)


    def showLabelButtonCallback(self, sender) -> None:
        self.showLabel = self.viewSettingsWindow.getItemValue("showLabelButton")
        self.displaySettingsButtonCallback(None)


    def multilineButtonCallback(self, sender) -> None:
        self.multiline = self.viewSettingsWindow.getItemValue("multilineButton")
        self.w.getItem("zoomToWidth").enable(self.multiline)
        self.displaySettingsButtonCallback(None)
        self.populateItems()


    def beamPositionSliderCallback(self, sender) -> None:
        self.beamPosition = sender.get()
        self.displaySettingsButtonCallback(None, onlyBeam=True)


    def showBeamButtonCallback(self, sender) -> None:
        self.showBeam = self.viewSettingsWindow.getItemValue("showBeamButton")
        self.displaySettingsButtonCallback(None, onlyBeam=True)


    def showKerningButtonCallback(self, sender) -> None:
        self.showKerning = self.viewSettingsWindow.getItemValue("showKerningButton")
        self.displaySettingsButtonCallback(None)
        self.populateItems()

    def NSColor2RGBA(self, color:AppKit.NSColor):
        try:
            reColor = (
                color.redComponent(),
                color.greenComponent(),
                color.blueComponent(),
                color.alphaComponent()
            )
        except ValueError:
            rgb = color.colorUsingColorSpace_(AppKit.NSColorSpace.genericRGBColorSpace())
            r = rgb.redComponent()
            g = rgb.greenComponent()
            b = rgb.blueComponent()
            a = rgb.alphaComponent()
            reColor = (r,g,b,a)
        return reColor


    def displaySettingsButtonCallback(self, sender, onlyBeam=False, previewState=False) -> None:
        values = self.viewSettingsWindow.getItemValue("displaySettingsButton")
        self.showFill      = 0 in values
        self.showStroke    = 1 in values
        self.showPoints    = 2 in values

        self.beamPosition  = self.viewSettingsWindow.getItemValue("beamPositionSlider")
        self.showBeam      = self.viewSettingsWindow.getItemValue("showBeamButton")

        showBeam = self.showBeam
        showMetrics = self.showMetrics
        showLabel = self.showLabel
        showKerning = self.showKerning
        showBeam = self.showBeam
        showFill = self.showFill
        showStroke = self.showStroke
        background = self.NSColor2RGBA(self.background)

        if previewState:
            showMetrics = showLabel = showKerning = showBeam = showStroke = showBeam = False
            showFill = True
            r,g,b,a = background
            colorComp = .9 if r == 1 else .1
            background = (colorComp,colorComp,colorComp,a)
        self.collectionView.setBackgroundColor(AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(*background))

        items = self.w.getItemValue("collectionView")
        for item in items:
            if onlyBeam:
                self.beamController(item)
                self.w.matrix.setShowBeam(showBeam)
                self.w.matrix.setBeamPosition(self.beamPosition)
            else:
                glyphContainer = item.getLayer("glyphContainer")

                glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")
                glyphMetricsLayer.setVisible(showMetrics)

                labelLayer = glyphContainer.getSublayer("descriptorIndicator")
                labelLayer.setVisible(showLabel)

                kernIndicatorLayer = glyphContainer.getSublayer("kernIndicator")
                kernIndicatorLayer.setVisible(showKerning)

                beamIndicatorLayer = glyphContainer.getSublayer("beamIndicator")
                beamIndicatorLayer.setVisible(showBeam)

                glyphFillLayer = glyphContainer.getSublayer("glyphFill")
                glyphFillLayer.setVisible(showFill)
                if showStroke:
                    glyphFillLayer.setFillColor((*self.foreground[:3], .2))
                else:
                    glyphFillLayer.setFillColor(self.foreground)

                glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
                glyphStrokeLayer.setVisible(showStroke)

                typingIndicatorLayer = glyphContainer.getSublayer("typingIndicator")
                typingIndicatorLayer.setVisible(False)
                item.typing = False
                # glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
                # glyphPointsLayer.setVisible(self.showPoints)


    # @functools.cache
    def buildItem(self, **kwargs) -> MerzCollectionViewRGlyphItem:
        name = kwargs.get("name")
        glyph = kwargs.get("glyph")
        font = kwargs.get("font")
        index = kwargs.get("index")
        onDisk = kwargs.get("onDisk")
        skewAngle = kwargs.get("skewAngle")
        off = kwargs.get("italicOffset")
        location = kwargs.get("location", {})
        # location = {_l[0]:_l[1] for _l in location}

        item = MerzCollectionViewRGlyphItem(
            name=name,
            acceptsHit=True,
            glyph=glyph,
            font=font,
            index=index,
            onDisk=onDisk,
            skewAngle=skewAngle,
            italicOffset=off,
            scaler=(self.upm/1000),
            location=location,
        )

        item.setHeight(self.upm)
        item.getCALayer().setGeometryFlipped_(True) # XXX Ugh. Yell at Tal about this.
        glyphContainer = merz.Base()
        item.appendLayer("glyphContainer", glyphContainer)

        glyphContainer.appendBaseSublayer(
            name="descriptorIndicator",
            visible=True,
        )

        glyphContainer.appendBaseSublayer(
            name="glyphMetrics",
            visible=True,
        )

        glyphContainer.appendBaseSublayer(
            name="reorderIndicator",
            visible=True,
        )

        if self.showStroke:
            foreground = (*self.foreground[:3], .2)
        else:
            foreground = self.foreground

        filled = glyphContainer.appendPathSublayer(
            name="glyphFill",
            fillColor=foreground,
            visible=True,
        )
        glyphContainer.appendPathSublayer(
            name="glyphStroke",
            fillColor=None,
            strokeColor=self.foreground,
            strokeWidth=1,
            visible=True,
        )
        # glyphContainer.appendBaseSublayer(
        #     name="glyphPoints",
        #     visible=True,
        # )

        glyphContainer.appendBaseSublayer(
            name="selectionIndicator",
        )
        glyphContainer.appendBaseSublayer(
            name="typingIndicator",
        )
        glyphContainer.appendBaseSublayer(
            name="kernIndicator",
            position=(0, 0),
            size=(0, 0),
            cornerRadius=3,
            backgroundColor=(1,0,0,.3),
            visible=True
        )

        glyphContainer.appendBaseSublayer(
            name="beamIndicator",
            visible=True,
        )
        # item.appendLayer("selectionIndicator", selectionLayer)

        with item.propertyGroup():
            item.setWidth(glyph.width)
            item.setHeight(self.upm)

            glyphContainer = item.getLayer("glyphContainer")
            glyphContainer.addTranslationTransformation(
                value=(0, -font.info.descender),
                name="descender"
            )

            locationData  = ""
            formatted = [f'{axis}:{value}' for axis,value in location.items()]
            if font.lib.get("descriptor") == "source":
                locationData += f' s: {" ".join(formatted)}'
            elif font.lib.get("descriptor") == "instance":
                locationData += f' i: {" ".join(formatted)}'
            else:
                locationData += f"    {os.path.basename(item.font.path)}"

            descriptorIndicatorLayer = glyphContainer.getSublayer("descriptorIndicator")
            with descriptorIndicatorLayer.propertyGroup():
                if item.index == 0:
                    descriptorIndicatorLayer.appendTextLineSublayer(
                        font="SFMono-Regular",
                        text=locationData,
                        pointSize=8,
                        position=(-50,-200*item.scaler),
                        fillColor=(*self.foreground[0:3], .5),
                        horizontalAlignment="left",
                        verticalAlignment="center",
                        anchor=(.5,.5)
                    )
                descriptorIndicatorLayer.setVisible(self.showLabel)

            glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")

            depth = -75
            with glyphMetricsLayer.propertyGroup():
                for side in ["left", "right"]:
                    if side == "left":
                        start = (0,0)
                        end = (0, depth)
                    else:
                        start = (glyph.width,0)
                        end = (glyph.width, depth)

                    val = round(getattr(glyph, f"angled{side.title()}Margin"))
                    if val:
                        margin = glyphMetricsLayer.appendTextLineSublayer(
                            name=f"glyph{side.title()}MetricsValueSublayer",
                            text=str(val),
                            pointSize=7,
                            position=(start[0],round(depth/2)),
                            fillColor=(.2,.2,.2,1),
                            horizontalAlignment=side,
                            padding=(5,0),
                            )
                    line = glyphMetricsLayer.appendLineSublayer(
                        name=f"glyphMetrics{side.title()}LinesSublayer",
                        startPoint=start,
                        endPoint=end,
                        strokeWidth=1,
                        strokeColor=(.2,.2,.2,1),
                        strokeCap="round"
                        )
                    line.addSkewTransformation(-skewAngle)
                width = glyphMetricsLayer.appendTextLineSublayer(
                    name="glyphWidthSublayer",
                    text=str(glyph.width),
                    pointSize=7,
                    position=(round(glyph.width/2),round(depth/2)),
                    fillColor=(.2,.2,.2,1),
                    horizontalAlignment="center",
                    padding=(0,7),
                    )
                glyphMetricsLayer.setVisible(self.showMetrics)

            kernIndicatorLayer = glyphContainer.getSublayer("kernIndicator")
            with kernIndicatorLayer.propertyGroup():

                kern = 0
                try:
                    nextGlyph = self.glyphs[index+1]
                    kern = font.kerning.find((glyph.name, nextGlyph))
                except IndexError:
                    kern = 0
                if not self.showKerning:
                    kern = 0

                if kern:
                    item.setXAdvance(kern)
                    kernIndicatorLayer.setVisible(True)

                    kernColor = POS_KERN_COLOR if kern > 0 else NEG_KERN_COLOR
                    kernIndicatorLayer.appendTextLineSublayer(
                        text=str(kern),
                        pointSize=7,
                        position=((abs(kern)/2), 0),
                        fillColor=(*kernColor,1),
                        horizontalAlignment="center",
                        )

                    x = (glyph.width+kern) if kern < 0 else glyph.width
                    kernIndicatorLayer.setBackgroundColor((*kernColor, .2))
                    kernIndicatorLayer.setSize((abs(kern), abs(font.info.descender) + font.info.ascender))
                    kernIndicatorLayer.setPosition((x, font.info.descender))
                    kernIndicatorLayer.setVisible(self.showKerning)
                else:
                    kernIndicatorLayer.setVisible(False)

            selectionIndicatorLayer = glyphContainer.getSublayer("selectionIndicator")
            with selectionIndicatorLayer.propertyGroup():

                selectionIndicatorLayer.appendRectangleSublayer(
                    name="selectionIndicatorDrawing",
                    position=(0,font.info.descender),
                    size=(glyph.width, abs(font.info.descender) + font.info.ascender),
                    fillColor=(0,1,0,.2),
                )
                selectionIndicatorLayer.addSublayerSkewTransformation((-skewAngle))

                if item in self.selectedItems:
                    selectionIndicatorLayer.setVisible(True)
                else:
                    selectionIndicatorLayer.setVisible(False)

            glyphFillLayer = glyphContainer.getSublayer("glyphFill")
            with glyphFillLayer.propertyGroup():
                glyphFillLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                glyphFillLayer.addTranslationTransformation((-off, 0), "translate")
                glyphFillLayer.setVisible(self.showFill)
            glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
            with glyphStrokeLayer.propertyGroup():
                glyphStrokeLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                glyphStrokeLayer.addTranslationTransformation((-off, 0), "translate")
                glyphStrokeLayer.setVisible(self.showStroke)

            typingIndicatorLayer = glyphContainer.getSublayer("typingIndicator")
            with typingIndicatorLayer.propertyGroup():

                typingIndicatorLayer.appendRectangleSublayer(
                    name="typingIndicatorDrawing",
                    position=(glyph.width-20,font.info.descender),
                    size=(40, abs(font.info.descender) + font.info.ascender),
                    fillColor=(IBEAM_COLOR),
                    cornerRadius=20,
                )
            typingIndicatorLayer.addSublayerSkewTransformation((-skewAngle))
            typingIndicatorLayer.setVisible(False)

            self.beamController(item)

        if index+1 == len(self.glyphs):
            if self.multiline:
                item.setForceBreakAfter(True)
            else:
                item.setForceBreakAfter(False)
        return item


    def updateItem(self, item:MerzCollectionViewRGlyphItem, **kwargs) -> None:
        """
        a faster alternative to rebuilding glyphs everytime
        """
        glyphContainer = item.getLayer("glyphContainer")
        glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")

        glyph = item.glyph
        font = item.font
        loc = kwargs.get("updatedLocation")

        # print(self.operator, loc)
        if loc:
            item.location = loc
            # infoMutator = self.operator.makeOneInfo(loc)
            # item.skewAngle = infoMutator.italicAngle
            item.font.info.italicAngle = item.skewAngle
            item.font.lib["location"] = loc

            libMutator = self.operator.getLibEntryMutator(self.operator.getLocationType(loc)[2])
            if libMutator:
                lib = libMutator.makeInstance(loc)
                item.offset = lib.get("com.typemytype.robofont.italicSlantOffset", 0)
                item.font.lib["com.typemytype.robofont.italicSlantOffset"] = item.offset

            mathGlyph = self.operator.makeOneGlyph(item.name, loc, decomposeComponents=True)
            if mathGlyph is not None:
                glyph = internalFontClasses.createGlyphObject()
                glyph = RGlyph(mathGlyph.extractGlyph(glyph))
                item.glyph = glyph

                descriptionLayer = glyphContainer.getSublayer("descriptorIndicator")
                with descriptionLayer.propertyGroup():
                    descriptionLayer.clearSublayers()
                    if item.index == 0:
                        formatted = [f"{axis}:{round(value,3)}" for axis,value in loc.items()]
                        descriptionLayer.appendTextLineSublayer(
                            text=f" 􀤒 {' '.join(formatted)}",
                            font="SFMono-Regular",
                            pointSize=8,
                            position=(-50,-200*item.scaler),
                            fillColor=(0.5819, 0.2157, 1.0, 1.0),
                            horizontalAlignment="left",
                            verticalAlignment="center",
                            anchor=(.5,.5),
                        )
        skewAngle = item.skewAngle
        item.setWidth(glyph.width)

        depth = -75
        with glyphMetricsLayer.propertyGroup():
            for side in ["left", "right"]:
                if side == "left":
                    start = (0,0)
                    end = (0, depth)
                else:
                    start = (glyph.width,0)
                    end = (glyph.width, depth)

                val = round(getattr(glyph, f"angled{side.title()}Margin"))
                if val:
                    margin = glyphMetricsLayer.getSublayer(f"glyph{side.title()}MetricsValueSublayer")
                    if margin:
                        margin.setText(str(val))
                        margin.setPosition((start[0],round(depth/2)))

                line = glyphMetricsLayer.getSublayer(f"glyphMetrics{side.title()}LinesSublayer")
                line.setStartPoint(start)
                line.setEndPoint(end)

            wd = glyphMetricsLayer.getSublayer("glyphWidthSublayer")
            if wd:
                wd.setText(str(glyph.width))
                wd.setPosition((round(glyph.width/2),round(depth/2)))

        glyphFillLayer = glyphContainer.getSublayer("glyphFill")
        #with glyphFillLayer.propertyGroup():    # for some reason this wont work inside a property group
        try: glyphFillLayer.removeTransformation("translate")
        except MerzError: pass
        glyphFillLayer.addTranslationTransformation((-item.offset, 0), "translate")
        glyphFillLayer.setPath(glyph.getRepresentation("merz.CGPath"))

        glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
        #with glyphStrokeLayer.propertyGroup():    # for some reason this wont work inside a property group
        try: glyphStrokeLayer.removeTransformation("translate")
        except MerzError: pass
        glyphStrokeLayer.addTranslationTransformation((-item.offset, 0), "translate")
        glyphStrokeLayer.setPath(glyph.getRepresentation("merz.CGPath"))

        # glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
        # glyphPointsLayer.clearSublayers()
        # onCurve = 20 * item.scaler

        # with glyphPointsLayer.propertyGroup():
        #     for contour in glyph.contours:
        #         for point in contour.points:
        #             if point.type != "offcurve":
        #                 x = point.x
        #                 y = point.y
        #                 glyphPointsLayer.appendOvalSublayer(
        #                     position=(x-item.offset, y),
        #                     size=(onCurve,onCurve),
        #                     anchor=(.5,.5),
        #                     fillColor=(0, 0, 0, 1),
        #                 )
        #     glyphPointsLayer.setVisible(self.showPoints)

        self.beamController(item)

        selection = glyphContainer.getSublayer("selectionIndicator").getSublayer("selectionIndicatorDrawing")
        selection.setPosition((0,font.info.descender))
        selection.setSize((glyph.width, abs(font.info.descender) + font.info.ascender))
                # if switching from roman <> italic, we need to update the selection indicator skew
        if kwargs.get("updatedLocation"):
            try: selection.removeTransformation("skew")
            except MerzError: pass
            if item.skewAngle: selection.addSublayerSkewTransformation((-item.skewAngle))


    def populateItems(self, reload:bool=False) -> None:
        items = []
        _glyphRecords = []

        for fontIndex, (path,(use,font)) in enumerate(self.fonts.items()):
            if use:
                scaler = font.info.unitsPerEm/1000
                for index, glyph in enumerate(self.glyphs):
                    item = None
                    if self.__cache:
                        if len(self.__cache) >= index+1:
                            hold = self.__cache[index]
                            if hold == glyph:
                                itemHolder = [_item
                                               for _item in self.w.getItemValue("collectionView")
                                               if font == _item.font
                                               and
                                               glyph == _item.glyph.name
                                               and
                                               index == _item.index
                                              ]
                                if itemHolder:
                                    item = itemHolder[0]
                                    if index+1 == len(self.glyphs):
                                        if self.multiline:
                                            item.setForceBreakAfter(True)
                                        else:
                                            item.setForceBreakAfter(False)
                                    else:
                                        item.setForceBreakAfter(False)

                    if not item:
                        onDisk = True
                        skewAngle = getattr(font.info, "italicAngle") or 0
                        off = font.lib.get("com.typemytype.robofont.italicSlantOffset", 0)
                        if font.lib.get("descriptor") == "instance":
                            _temp = glyph
                            location = font.lib.get("location")
                            mathGlyph = self.operator.makeOneGlyph(glyph, location, decomposeComponents=True)
                            if mathGlyph is not None:
                                glyph = internalFontClasses.createGlyphObject()
                                # glyph.font = font
                                mathGlyph.extractGlyph(glyph)
                                glyph = font.insertGlyph(glyph, name=_temp)
                                onDisk = False
                        else:
                            if glyph in font.keys():
                                glyph = font[glyph]

                        if isinstance(glyph, str):
                            capScale = font.info.capHeight / 750
                            glyph = RGlyph()
                            glyph.readGlyphFromString('<?xml version="1.0" encoding="UTF-8"?><glyph name="IGNORE" format="2"><advance width="893"/><outline><contour><point x="117" y="703" type="curve" smooth="yes"/><point x="79" y="664"/><point x="70" y="612"/><point x="70" y="542" type="curve" smooth="yes"/><point x="70" y="535" type="line"/><point x="127" y="535" type="line"/><point x="127" y="544" type="line" smooth="yes"/><point x="127" y="592"/><point x="133" y="636"/><point x="158" y="661" type="curve" smooth="yes"/><point x="183" y="687"/><point x="228" y="694"/><point x="276" y="694" type="curve" smooth="yes"/><point x="287" y="694" type="line"/><point x="287" y="750" type="line"/><point x="278" y="750" type="line" smooth="yes"/><point x="209" y="750"/><point x="156" y="741"/></contour><contour><point x="338" y="694" type="line"/><point x="554" y="694" type="line"/><point x="554" y="750" type="line"/><point x="338" y="750" type="line"/></contour><contour><point x="776" y="703" type="curve" smooth="yes"/><point x="737" y="742"/><point x="684" y="750"/><point x="613" y="750" type="curve" smooth="yes"/><point x="606" y="750" type="line"/><point x="606" y="694" type="line"/><point x="618" y="694" type="line" smooth="yes"/><point x="665" y="694"/><point x="709" y="686"/><point x="734" y="661" type="curve" smooth="yes"/><point x="760" y="636"/><point x="766" y="593"/><point x="766" y="546" type="curve" smooth="yes"/><point x="766" y="535" type="line"/><point x="823" y="535" type="line"/><point x="823" y="540" type="line" smooth="yes"/><point x="823" y="612"/><point x="814" y="665"/></contour><contour><point x="766" y="266" type="line"/><point x="823" y="266" type="line"/><point x="823" y="483" type="line"/><point x="766" y="483" type="line"/></contour><contour><point x="776" y="47" type="curve" smooth="yes"/><point x="814" y="86"/><point x="823" y="138"/><point x="823" y="210" type="curve" smooth="yes"/><point x="823" y="215" type="line"/><point x="766" y="215" type="line"/><point x="766" y="204" type="line" smooth="yes"/><point x="766" y="158"/><point x="759" y="114"/><point x="734" y="89" type="curve" smooth="yes"/><point x="709" y="64"/><point x="665" y="57"/><point x="618" y="57" type="curve" smooth="yes"/><point x="606" y="57" type="line"/><point x="606" y="0" type="line"/><point x="613" y="0" type="line" smooth="yes"/><point x="684" y="0"/><point x="737" y="9"/></contour><contour><point x="338" y="0" type="line"/><point x="554" y="0" type="line"/><point x="554" y="57" type="line"/><point x="338" y="57" type="line"/></contour><contour><point x="117" y="47" type="curve" smooth="yes"/><point x="156" y="9"/><point x="209" y="0"/><point x="280" y="0" type="curve" smooth="yes"/><point x="287" y="0" type="line"/><point x="287" y="57" type="line"/><point x="274" y="57" type="line" smooth="yes"/><point x="228" y="57"/><point x="184" y="64"/><point x="158" y="89" type="curve" smooth="yes"/><point x="133" y="114"/><point x="127" y="158"/><point x="127" y="204" type="curve" smooth="yes"/><point x="127" y="215" type="line"/><point x="70" y="215" type="line"/><point x="70" y="210" type="line" smooth="yes"/><point x="70" y="138"/><point x="78" y="86"/></contour><contour><point x="70" y="266" type="line"/><point x="127" y="266" type="line"/><point x="127" y="483" type="line"/><point x="70" y="483" type="line"/></contour><contour><point x="438" y="291" type="curve" smooth="yes"/><point x="456" y="291"/><point x="467" y="302"/><point x="467" y="316" type="curve" smooth="yes"/><point x="467" y="319"/><point x="467" y="321"/><point x="467" y="323" type="curve" smooth="yes"/><point x="467" y="347"/><point x="480" y="362"/><point x="510" y="382" type="curve" smooth="yes"/><point x="550" y="410"/><point x="577" y="434"/><point x="577" y="480" type="curve" smooth="yes"/><point x="577" y="546"/><point x="519" y="583"/><point x="450" y="583" type="curve" smooth="yes"/><point x="381" y="583"/><point x="335" y="548"/><point x="325" y="509" type="curve" smooth="yes"/><point x="324" y="503"/><point x="323" y="495"/><point x="323" y="489" type="curve" smooth="yes"/><point x="323" y="473"/><point x="335" y="464"/><point x="347" y="464" type="curve" smooth="yes"/><point x="360" y="464"/><point x="368" y="470"/><point x="373" y="479" type="curve" smooth="yes"/><point x="379" y="488" type="line"/><point x="391" y="515"/><point x="415" y="534"/><point x="448" y="534" type="curve" smooth="yes"/><point x="489" y="534"/><point x="515" y="512"/><point x="515" y="478" type="curve" smooth="yes"/><point x="515" y="449"/><point x="498" y="435"/><point x="461" y="409" type="curve" smooth="yes"/><point x="430" y="387"/><point x="410" y="365"/><point x="410" y="327" type="curve" smooth="yes"/><point x="410" y="324"/><point x="410" y="321"/><point x="410" y="319" type="curve" smooth="yes"/><point x="410" y="300"/><point x="420" y="291"/></contour><contour><point x="437" y="170" type="curve" smooth="yes"/><point x="459" y="170"/><point x="478" y="188"/><point x="478" y="210" type="curve" smooth="yes"/><point x="478" y="232"/><point x="460" y="249"/><point x="437" y="249" type="curve" smooth="yes"/><point x="415" y="249"/><point x="397" y="232"/><point x="397" y="210" type="curve" smooth="yes"/><point x="397" y="188"/><point x="415" y="170"/></contour></outline></glyph>')
                            glyph.scaleBy(capScale)
                            glyph.width *= capScale

                        if not isinstance(glyph, RGlyph):
                            glyph = RGlyph(glyph)

                        item = self.buildItem(
                                        name=glyph.name,
                                        glyph=glyph,
                                        font=font,
                                        index=index,
                                        onDisk=onDisk,
                                        skewAngle=skewAngle,
                                        italicOffset=off,
                                        location=font.lib.get("location", {}),
                                        scaler=scaler,
                                )

                    if fontIndex == 0:
                        _glyphRecords.append(GlyphRecord(item.glyph.naked()))
                    items.append(item)

        self.__cache = self.glyphs
        self.collectionView.set(items)

        items = self.w.getItemValue("collectionView")
        for item in items:
            self.beamController(item)

        self.w.matrix.set(_glyphRecords)
        self.displaySettingsButtonCallback(None, previewState=self.typing)


    def beamController(self, item:MerzCollectionViewRGlyphItem) -> None:
        glyph = item.glyph
        font = item.font
        beamIndicatorLayer = item.getLayer("glyphContainer").getSublayer("beamIndicator")
        beamIndicatorLayer.clearSublayers()

        if self.collectionView.get():
            # beamIndicatorLayer.addTranslationTransformation(value=(-off,0))
            beamIntersectSize = 30 * item.scaler

            with beamIndicatorLayer.propertyGroup():
                try:
                    next = [ii for ii in self.collectionView.get() if item.font == ii.font][item.index+1].glyph
                except IndexError:
                    next = None

                previous = None
                try:
                    previous = [ii for ii in self.collectionView.get() if item.font == ii.font][item.index-1].glyph
                except IndexError:
                    previous = None

                right = glyph.getRayRightMargin(self.beamPosition, item.skewAngle) or 0
                left = glyph.getRayLeftMargin(self.beamPosition, item.skewAngle) or 0

                isEmpty = not glyph.contours and not glyph.components

                if font.info.familyName == "Preview Location":
                    right += item.offset
                    left -= item.offset

                aa = item.skewAngle
                if aa:
                    aa *= -1
                else:
                    aa = 0
                x = y = math.radians(aa)
                matrix = transform.Identity.skew(x=x, y=y)
                t = transform.Transform()
                oX, oY = (0,0)
                t = t.translate( oX,  oY)
                t = t.transform(matrix)
                t = t.translate(-oX, -oY)
                tt = tuple(t)
                ot = transform.Transform(*tt)
                transformed,_ = ot.transformPoint((0, self.beamPosition))

                if item.index == 0:
                    if self.multiline:
                        beamIndicatorLayer.appendOvalSublayer(
                            position=(-(beamIntersectSize*2), self.beamPosition),
                            size=(beamIntersectSize*2,beamIntersectSize*2),
                            anchor=(.5,.5),
                            fillColor=(1,.2,0,1),
                            horizontalAlignment="right",
                            acceptsHit=True,
                        )
                    beamIndicatorLayer.appendLineSublayer(
                        startPoint=(-beamIntersectSize*2, self.beamPosition),
                        endPoint=(left+transformed, self.beamPosition),
                        strokeColor=(1,.2,0,.4),
                        strokeWidth=1,
                    )

                if not isEmpty:
                    # left side
                    beamIndicatorLayer.appendOvalSublayer(
                        position=(left+transformed, self.beamPosition),
                        size=(beamIntersectSize,beamIntersectSize),
                        anchor=(.5,.5),
                        fillColor=(1,.2,0,1)
                    )

                    # right side
                    beamIndicatorLayer.appendOvalSublayer(
                        position=((glyph.width - right)+transformed, self.beamPosition),
                        size=(beamIntersectSize,beamIntersectSize),
                        anchor=(.5,.5),
                        fillColor=(1,.2,0,1)
                    )

                # through glyph line

                if isEmpty and previous:
                    left = previous.getRayLeftMargin(self.beamPosition, item.skewAngle) or 0
                    left -= previous.width

                beamIndicatorLayer.appendLineSublayer(
                    startPoint=(left+transformed, self.beamPosition),
                    endPoint=((glyph.width - right)+transformed, self.beamPosition),
                    strokeColor=(1,.2,0,.4),
                    strokeWidth=1,
                    )

                if next is not None:
                    if next.contours or next.components:
                        nextLeft = next.getRayLeftMargin(self.beamPosition, item.skewAngle) or 0
                        if font.info.familyName == "Preview Location":
                            nextLeft -= item.offset

                        if not isEmpty:
                            beamIndicatorLayer.appendLineSublayer(
                                startPoint=((glyph.width - right)+transformed, self.beamPosition),
                                endPoint=((glyph.width + nextLeft)+transformed, self.beamPosition),
                                strokeColor=(1,.2,0,1),
                                strokeWidth=1,
                            )
                            if nextLeft:
                                beamIndicatorLayer.appendTextLineSublayer(
                                    text=str(round(right + nextLeft)),
                                    font="SFMono-Regular",
                                    position=((glyph.width - right) + ((right + nextLeft)/2)+transformed, self.beamPosition),
                                    fillColor=(1,.2,0,1),
                                    pointSize=10,
                                    backgroundColor=(1,.2,0,.2),
                                    cornerRadius=5,
                                    horizontalAlignment="center",
                                    verticalAlignment="bottom",
                                    padding=(3,1),
                                )

                        else:
                            beamIndicatorLayer.appendLineSublayer(
                                startPoint=((glyph.width - right)+transformed, self.beamPosition),
                                endPoint=((glyph.width + nextLeft)+transformed, self.beamPosition),
                                strokeColor=(1,.2,0,.4),
                                strokeWidth=1,
                            )

                beamIndicatorLayer.setVisible(self.showBeam)


    def acceptsFirstResponder(self, sender) -> bool:
        # necessary for accepting mouse events
        return True

    def acceptsMouseMoved(self, sender) -> bool:
        # necessary for tracking mouse movement
        return True

    def zoomCoalescerManager(self) -> None:
        self.zoomCoalescer.restart()

    # def magnifyWithEvent(self, sender, event) -> None:
    #     self.zoomCoalescerManager()
    #     self.zoom(delta=event.magnification())

    # def windowDidResize(self, sender):
    #     print(self.collectionView._documentView._view.enclosingScrollView())

    def zoom(self, direction:str="out", delta:float=None, scale:float=None, option:bool=False) -> None:

        values = self.w.getItemValues()
        pointSize = values["pointSizeInputField"]
        lineHeight = values["lineHeightField"]
        if scale:
            self.pointSize = self.upm * scale
            self.scale = scale
        else:
            if delta:
                if delta < 0:
                    factor = ZOOM_IN_FACTOR
                else:
                    factor = ZOOM_OUT_FACTOR
                pointSize *= factor
            else:
                factor = 5 if option else 15
                if direction == "in":
                    pass
                else:
                    factor *= -1
                pointSize += factor

            self.pointSize = max(pointSize, 10)
            self.scale = pointSize / self.upm

        self.lineHeight = self.upm * lineHeight * self.scale

        self.w.setItemValue("pointSizeInputField", self.pointSize)

        typesetter = self.collectionView._documentView._typesetter

        ### thanks tal, you're the BEST
        self.collectionView.getMerzContainer().setContainerScale(self.scale)
        typesetterScale = 1 / self.scale
        x, y = self.collectionView._documentView._inset
        x *= typesetterScale
        y *= typesetterScale
        typesetter.setPosition((x, y))
        typesetter.setLineHeight(self.lineHeight * typesetterScale)

        origin, (width, height) = self.collectionView._documentView._view.frame()
        insetX, insetY = typesetter.getPosition()

        (documentX, documentY), (documentWidth, documentHeight) = self.collectionView._documentView._view.visibleRect()
        typesetterX = documentX * typesetterScale
        typesetterY = documentY * typesetterScale
        typesetterWidth = documentWidth * typesetterScale
        typesetterHeight = documentHeight * typesetterScale
        indexes = typesetter.getItemIndexesInRect((
            typesetterX,
            typesetterY,
            typesetterWidth,
            typesetterHeight
        ))
        items = []
        maxLineWidth = width * typesetterScale
        maxLineWidth -= insetX * 2
        typesetter.setMaxLineWidth(maxLineWidth)
        typesetter.breakLines()

        for index in indexes:
            try:
                ira = typesetter[index]
                ira.setPosition(typesetter.getItemPosition(index))
            except:
                pass
        ###
        if scale: self.zoomEnded(None)


    def zoomEnded(self, coalescer:Coalescer) -> None:
        self.collectionView.setLayoutProperties(
            scale=self.scale,
            lineHeight=self.lineHeight
        )

    def zoomToWidthCallback(self, sender) -> None:
        self.zoomCoalescerManager()
        self._zoomToFit("width")

    def zoomToHeightCallback(self, sender) -> None:
        self.zoomCoalescerManager()
        self._zoomToFit("height")

    def _zoomToFit(self, direction:str) -> None:
        if self.multiline:
            collection = self.collectionView
            typesetter = collection._documentView._typesetter
            __,(containerWidth, containerHeight) = collection.getNSScrollView().bounds()
            availableHeight = len([1 for use, font in self.fonts.values() if use]) * typesetter.getLineHeight() * 1.1

            mm = {}
            for ii in self.collectionView.get():
                v = mm.get(ii.font.path,0)
                v += ii.glyph.width
                mm[ii.font.path] = v
            availableWidth = max(list(mm.values())) * 1.1

            xScale = containerWidth/availableWidth
            yScale = containerHeight/availableHeight
            if direction == "width":
                scale = xScale
            elif direction == "height":
                scale = yScale

            if scale == 1.0:
                return

            self.zoom(scale=scale)


    def destroy(self) -> None:
        #setExtensionDefault(EXTENSION_KEY + ".main_prefs", self.w.getItemValues())
        TYPING_CURSOR.pop()
        setExtensionDefault(EXTENSION_KEY + ".view_prefs", self.viewSettingsWindow.getItemValues())
        setExtensionDefault(EXTENSION_KEY + ".text", self.holdingGlyphs)

        windowSettings = self.w.getItemValues()
        for name,field in windowSettings.items():
            if name.lower().endswith("textfield"):
                cleanedInput = []
                for glyph in field:
                    if glyph == CURRENTGLYPH_CHAR:
                        cleanedInput.append("/?")
                    elif glyph == SELECTEDGLYPHS_CHAR:
                        cleanedInput.append("/!")
                    else:
                        try:
                            cleanedInput.append(chr(n2u(glyph)))
                        except:
                            pass
                windowSettings[name] = ''.join(cleanedInput)
        if "collectionView" in windowSettings.keys(): del windowSettings['collectionView']

        if self.detached:
            self.viewSettingsWindow.close()
        setExtensionDefault(EXTENSION_KEY + ".main_prefs", windowSettings)
        self.clearObservedAdjunctObjects()
        self.zoomCoalescer.stop()
        self.typingCoalescer.stop()


    def _getItemAtEvent(self, position:tuple[float,float]=(0.0,0.0)) -> MerzCollectionViewRGlyphItem | None:
        x,y = position
        if self.typing:
            hits = self.container.findSublayersIntersectedByRect(
                (x-100,y-25,100,50),
                onlyAcceptsHit=True,
                recurse=False
            )
        else:
            hits = self.container.findSublayersContainingPoint(
                (x, y),
                onlyAcceptsHit=True,
                recurse=False
            )
        if not hits:
            return None
        hit = hits[0]
        return hit


    def _convertLocation(self, event:dict, view:ezui.views.merzView.MerzView | merz.collectionView.MerzCollectionDocumentView) -> tuple[float, float]:
        location = event["location"]
        view = view if view else self.collectionView.getMerzView()
        location = view.convertWindowCoordinateToViewCoordinate(
            point=location
        )
        x, y = view.getMerzContainer().convertViewCoordinateToLayerCoordinate(
            location,
            view.getMerzContainer()
        )
        return (x,y)


    def mouseDown(self, view, event) -> None:

        if isinstance(view, ezui.views.merzView.MerzView):
            # working with designspace navigator
            pass

        elif isinstance(view, merz.collectionView.MerzCollectionDocumentView):
            # working with glyph record view
            event = merz.unpackEvent(event)
            self.start = (x,y) = self._convertLocation(event, view)
            hit = self._getItemAtEvent((x,y))
            selection = []

            selectedGlyph = None
            selectedFont = None
            multiFontSelect = False

            for temporary in self.collectionView.get():
                if temporary not in self.selectedItems:
                    temporary.selected = False

            if hit:
                clickCount = event["clickCount"]
                parsed = hit.glyph
                if parsed is not None and parsed.name != "IGNORE":
                    if not self.typing:
                        hit.selected = True
                        # selectedGlyph = self.getGlyphFromItem(hit)
                        selectedGlyph = parsed

                        if event["modifiers"] == ["command"]:
                            selectedFont = hit.font

                        elif event["modifiers"] == ["option"]:
                            multiFontSelect = True

                        if AppKit.NSEvent.modifierFlags() & AppKit.NSShiftKeyMask:
                            # print("shift down, append")
                            self.selectedItems.append(hit)
                        else:
                            # print("no mod, use only this")
                            self.selectedItems = [hit]
                            for temporary in self.collectionView.get():
                                if temporary not in self.selectedItems:
                                    temporary.selected = False
                        if clickCount == 2:
                            try:
                                OpenGlyphWindow(selectedGlyph)
                            except:
                                selectedGlyph.copyToPasteboard()

                    else:
                        self.typingIndex = hit.index
                        self.typingFont  = hit.font
                        selectedGlyph    = hit.glyph
                        self.selectedItems = [hit]
                else:
                    self.selectedItems = []
            else:
                self.selectedItems = []


            if not self.selectedItems:
                for temporary in self.collectionView.get():
                    temporary.selected = False

            if self.typing:
                self.setTypingItem()

            if multiFontSelect:
                for temporary in self.collectionView.get():
                    if temporary.index == hit.index:
                        self.selectedItems.append(temporary)
                        temporary.selected = True

            # only set the matrix for one font at a time, the selected one.
            if len(set([hits.glyph.font for hits in self.selectedItems])) == 1 and selectedGlyph:
                records = [GlyphRecord(item.glyph.naked()) for item in self.collectionView.get() if item.glyph.font == selectedGlyph.font]
                self.w.matrix.set(records)

            elif multiFontSelect:
                records = [GlyphRecord(item.glyph.naked()) for item in self.selectedItems]
                self.w.matrix.set(records)


    def mouseDragged(self, view, event) -> None:
        if isinstance(view, ezui.views.merzView.MerzView):
            self.internalPreview = True
            self.hoverItem = None
            self.wasDragging = True
            container = view.getMerzContainer()

            container.clearSublayers()

            event = merz.unpackEvent(event)
            x, y = self._convertLocation(event,view)

            container.appendLineSublayer(
                startPoint=(x,0),
                endPoint=(x,1000),
                strokeColor=(0,0,0,.2),
                strokeWidth=1,
                )
            container.appendLineSublayer(
                startPoint=(0,y),
                endPoint=(1000,y),
                strokeColor=(0,0,0,.2),
                strokeWidth=1,
                )

            container.appendOvalSublayer(
                position=(x,y),
                size=(10,10),
                anchor=(.5,.5),
                fillColor=(0.2,0.2,0.2,1),
                strokeColor=(0,0,0,1),
                strokeWidth=1,
            )

            self._convertViewLocationToDesignspaceLocation((x,y))
            self.x = x
            self.y = y


    @property
    def currentLocation(self) -> dict[str, float]:
        location = self.interpolationWindow.getItemValues()
        if "xAxisSelection" in location.keys():
            del location["xAxisSelection"]
        for axisDescriptor in self.operator.axes:
            if hasattr(axisDescriptor, "values"):
                index = location[axisDescriptor.name]
                location[axisDescriptor.name] = axisDescriptor.values[index]
        return location


    def _convertViewLocationToDesignspaceLocation(self, position:tuple[float, float]):
        x,y = position
        location = self.currentLocation
        desc = [a for a in self.operator.axes if a.name == self.xAxis][0]
        minimum, default, maximum = self.operator.getAxisExtremes(desc)
        nx = remap(x, 0, 300, minimum, maximum, True)
        location[self.xAxis] = nx
        if self.yAxis:
            desc = [a for a in self.operator.axes if a.name == self.yAxis][0]
            minimum, default, maximum = self.operator.getAxisExtremes(desc)
            ny = remap(y, 0, 300, minimum, maximum, True)
            location[self.yAxis] = ny
        self.designspaceEditorPreviewLocationDidChange(dict(location=location))


    def keyDown(self, view, event) -> None:
        rawEvent = event
        rawChar  = rawEvent.characters()
        deleting = adding = False

        event = merz.unpackEvent(event)
        mods  = event["modifiers"]
        char  = event["character"]

        rawGlyphName = u2n(ord(rawChar))
        directions = "left right up down".split(" ")

        fontList = [f for p,(u,f) in self.fonts.items() if u]

        if not self.typing:
            if char in directions:
                for item in self.selectedItems:
                    item.selected = True
                    # glyph = self.getGlyphFromItem(item)
                    glyph = item.glyph

                    if item.onDisk:
                        with glyph.undo(f"Change spacing of {glyph.name}"):
                            if "shift" in mods and "command" in mods:
                                spacingUnit = 100
                            elif "shift" in mods:
                                spacingUnit = 10
                            else:
                                spacingUnit = 1
                            if glyph.bounds:
                                if "option" in mods and char == "right":
                                    glyph.leftMargin += spacingUnit
                                elif "option" in mods and char == "left":
                                    glyph.leftMargin -= spacingUnit
                                elif char == "right":
                                    glyph.rightMargin += spacingUnit
                                elif char == "left":
                                    glyph.rightMargin -= spacingUnit
                                elif char == "up":
                                    glyph.rightMargin += spacingUnit
                                    glyph.leftMargin  += spacingUnit
                                elif char == "down":
                                    glyph.rightMargin -= spacingUnit
                                    glyph.leftMargin  -= spacingUnit
                                else:
                                    pass
                            else:
                                if char == "right":
                                    glyph.width += spacingUnit
                                elif char == "left":
                                    glyph.width -= spacingUnit

            else:
                # allow for undoing
                if self.command:
                    if char.lower() == "z":
                        for toUndo in self.selectedItems:
                            glyph = toUndo.glyph
                            manager = AppKit.NSApp().getUndoManagerForGlyph_(glyph.asDefcon())
                            manager.undo()
                    elif char.lower() == "t":
                        # set the text field as active
                        #self.w.getNSWindow().makeFirstResponder_(self.w.getItem("textField").getNSTextField())
                        self.toggleTypingState()
                        return

                    elif char == ";":
                        self.addObjectsCallback(None)
                    elif char == "=":
                        # zoom in
                        self.zoomCoalescerManager()
                        self.zoom(direction="in", option=AppKit.NSEvent.modifierFlags() & AppKit.NSAlternateKeyMask)
                    elif char == "-":
                        # zoom out
                        self.zoomCoalescerManager()
                        self.zoom(direction="out", option=AppKit.NSEvent.modifierFlags() & AppKit.NSAlternateKeyMask)

                if mods == []:
                    if char.lower() == "b":
                        self.showBeam = not self.showBeam
                        self.viewSettingsWindow.setItemValue("showBeamButton", self.showBeam)
                        self.w.matrix.setShowBeam(self.showBeam)
                        items = self.w.getItemValue("collectionView")
                        for item in items:
                            self.beamController(item)

                    elif char == getDefault("glyphViewZoomInKey", "z"):
                        # zoom in
                        self.zoomCoalescerManager()
                        self.zoom(direction="in")
                    elif char == getDefault("glyphViewZoomOutKey", "x"):
                        # zoom out
                        self.zoomCoalescerManager()
                        self.zoom(direction="out")
        else:
            if rawEvent.keyCode() == 51:
                # print(f"deleting {self.glyphs[self.typingIndex]} @ {self.typingIndex}")
                deleting = True
                if self.command:
                    self.typingIndex = 0
                    self.rawGlyphList = []
                else:
                    if self.typingIndex < len(self.holdingGlyphs):
                        self.rawGlyphList.pop(self.typingIndex)
                self.holdingGlyphs = self.rawGlyphList

            if rawGlyphName:
                adding = True
                self.rawGlyphList.insert(self.typingIndex + 1, rawGlyphName)
                self.holdingGlyphs = self.rawGlyphList

            if self.command:
                if char.lower() == "t":
                    self.toggleTypingState()
                    return

            if char in directions:
                if char == "left":
                    if self.command:
                        self.typingIndex = 0
                    else:
                        if self.typingIndex > 0:
                            self.typingIndex += -1
                elif char == "right":
                    if self.command:
                        self.typingIndex = len(self.holdingGlyphs)-1
                    else:
                        if self.typingIndex < len(self.holdingGlyphs)-1:
                            self.typingIndex += 1
                elif char == "up":
                    if self.typingFont != fontList[0]:
                        self.typingFont = fontList[fontList.index(self.typingFont)-1]
                elif char == "down":
                    if self.typingFont != fontList[-1]:
                        self.typingFont = fontList[fontList.index(self.typingFont)+1]
            if deleting:
                if self.typingIndex > 0:
                    self.typingIndex += -1
            if adding:
                if self.typingIndex < len(self.holdingGlyphs)-1:
                    self.typingIndex += 1

            if adding or deleting:
                self.textFieldCallback(None)

            self.setTypingItem()

            # records = [GlyphRecord(item.glyph.naked()) for item in self.collectionView.get() if item.glyph.font == self.typingFont]
            # self.w.matrix.set(records)
            # self.w.setItemValue(
            #     "textField",
            #     self.combineText(self.holdingGlyphs)
            # )

    @property
    def command(self) -> bool:
        return AppKit.NSEvent.modifierFlags() & AppKit.NSCommandKeyMask

    def getMergedIndexFromRawIndex(self, rawIndex):
        if not self.holdingGlyphs:
            return 0

        currentRawIndex = 0
        mergedIndex = 0

        while currentRawIndex < rawIndex and currentRawIndex < len(self.holdingGlyphs):
            if self.holdingGlyphs[currentRawIndex] == 'slash':
                slashStr = '/'
                startRawIndex = currentRawIndex
                currentRawIndex += 1

                charsCollected = []
                while currentRawIndex < len(self.holdingGlyphs) and self.holdingGlyphs[currentRawIndex] not in ['space', 'slash']:
                    charsCollected.append(self.holdingGlyphs[currentRawIndex])
                    slashStr += self.holdingGlyphs[currentRawIndex]
                    currentRawIndex += 1

                skipFollowingSpace = False

                if slashStr in ['/question', '/exclam', '/']:
                    skipFollowingSpace = True
                else:
                    glyphName = slashStr[1:]
                    if glyphName in self.font.keys():
                        skipFollowingSpace = True
                    else:
                        if startRawIndex < rawIndex:
                            mergedIndex += 1 + len(charsCollected)
                        continue

                if currentRawIndex < len(self.holdingGlyphs) and self.holdingGlyphs[currentRawIndex] == 'space' and skipFollowingSpace:
                    currentRawIndex += 1

                mergedIndex += 1

            elif self.holdingGlyphs[currentRawIndex] == 'space':
                currentRawIndex += 1
                mergedIndex += 1
            else:
                currentRawIndex += 1
                mergedIndex += 1

        return mergedIndex


    def toggleTypingState(self):
        if self.fonts:
            self.typing = not self.typing
            self.typingFont = list(self.fonts.values())[0][-1]
            if self.typing:
                cursor = TYPING_CURSOR
            else:
                cursor = ARROW_CURSOR
            scrollView = self.collectionView.getNSScrollView()
            scrollView.setDocumentCursor_(cursor)
            self.displaySettingsButtonCallback(None, previewState=self.typing)
            if self.typing:
                if self.typingIndex is None:
                    self.typingIndex = len(self.holdingGlyphs)-1
                self.setTypingItem()


    def setTypingItem(self):
        # set where the typing cursor is
        index = self.getMergedIndexFromRawIndex(self.typingIndex)
        for item in self.collectionView.get():
            item.typing = False
            if item.font == self.typingFont:
                if item.index == index:
                    item.typing = True
                else:
                    item.typing = False


    def mouseMoved(self, view, event) -> None:
        pass
        # print("debug::mouseMoved")


    def mouseUp(self, view, event) -> None:
        pass
        # print("debug::mouseUp")


    def subscribeToGlyphs(self, coalescer:Coalescer) -> None:
        glyphs = []
        for (__, obj) in self.fonts.values():
            try:
                glyphs.extend(list(set([obj[glyph] for glyph in self.glyphs])))
            except:
                pass
        self.setAdjunctObjectsToObserve(glyphs)


    def unsubscribeFromGlyphs(self) -> None:
        self.clearObservedAdjunctObjects()


    def adjunctGlyphDidChangeMetrics(self, info) -> None:
        # print(info["glyph"])
        selectedMatrixItem = self.w.matrix._inputView.getSelected() or RGlyph()
        if info["glyph"].name != selectedMatrixItem.name:
            self.w.matrix._glyphWidthChanged(info)
        items = self.w.getItemValue("collectionView")
        for item in items:
            if item.glyph == info["glyph"]:
                self.updateItem(item)
        self.collectionView.set(self.w.getItemValue("collectionView")) # i think that this is the only external-way to reload the view


    def adjunctGlyphDidChangeOutline(self, info) -> None:
        selectedMatrixItem = self.w.matrix._inputView.getSelected() or RGlyph()
        if info["glyph"].name != selectedMatrixItem.name:
            self.w.matrix._glyphChanged(info)
        items = self.w.getItemValue("collectionView")
        for item in items:
            if item.glyph == info["glyph"]:
                self.updateItem(item)
        self.collectionView.set(self.w.getItemValue("collectionView")) # i think that this is the only external-way to reload the view


if __name__ == "__main__":
    registerRoboFontSubscriber(Spaceport)
