import AppKit
from defcon import Font
from lib.UI.spaceCenter.glyphSequenceEditText import splitText,\
    currentGlyphKey, currentSelectionKey, newLineKey, groupsKey
from lib.fontObjects.doodleFont import DoodleFont
from lib.fontObjects.doodleLayer import DoodleLayer
from lib.fontObjects.doodleGlyph import DoodleGlyph

from lib.UI.spaceCenter import spaceInputScrollView as spaceInput
from lib.UI.spaceCenter.lineViewGlyphWrappers import  GlyphRecord

from mojo import events
from mojo.UI import *
from mojo.extensions import getExtensionDefault, setExtensionDefault
from fontParts.world import CurrentGlyph, CurrentLayer, CurrentFont
from mojo.roboFont import internalFontClasses
import ezui
import merz
from mojo.subscriber import Subscriber, registerCurrentGlyphSubscriber, unregisterCurrentGlyphSubscriber, registerSubscriberEvent, getRegisteredSubscriberEvents
from vanilla.vanillaBase import osVersionCurrent, osVersion12_0
from glyphNameFormatter.reader import n2u
import os
from fontTools.misc import transform
from fontTools.designspaceLib import (DesignSpaceDocument, AxisDescriptor,
                                      SourceDescriptor, InstanceDescriptor)
import math
from pprint import pprint
from designspaceEditor.ui import DesignspaceEditorController
from designspaceEditor.locationPreview import PreviewLocationFinder

import yaml

INFO_YAML = os.path.abspath(os.path.join( __file__, "../../../", "info.yaml"))
with open(INFO_YAML, mode="r") as file:
    info = yaml.safe_load(file)
EXTENSION_VERSION = info.get("version", "0.0.0")

# ---------
# Interface
# ---------
AXES = [
        "Weight",
        "Width",
        "Slant"
       ]


EXTENSION_KEY = "com.connordavenport.spaceport"

CURRENTGLYPH_CHAR = "/?"
NEWLINE_CHAR = "\\n"

EDIT_TEXT = "character.cursor.ibeam"
ADD_FONT = "document.badge.gearshape"
ADD_DESIGNSPACE = "squareshape.split.3x3"
SPACING = "arrow.left.and.right.text.vertical"
KERNING = "arrowtriangle.right.and.line.vertical.and.arrowtriangle.left"
INTERPOLATE = "squareshape.split.2x2.dotted"
VIEW_OPTIONS = "eye"
SHOW_METRICS = "character.magnify"
OPENTYPE = "textformat.alt"
BEAM = "ruler"

KERN_HEIGHT = 100

POS_KERN_COLOR = (0,0,1)
NEG_KERN_COLOR = (1,0,0)


class MerzCollectionViewRGlyphItem(merz.collectionView.MerzCollectionViewItem):

    def __init__(self, *args, **kwargs):
        self._name = kwargs.get("name")
        self._font = kwargs.get("font")
        self._glyph = kwargs.get("glyph")
        self._index = kwargs.get("index")
        self._onDisk = kwargs.get("onDisk")
        self._offset = kwargs.get("offset", 0)
        self._skewAngle = kwargs.get("skewAngle", 0)
        self._scaler = kwargs.get("scaler", 1)
        self._location = kwargs.get("location", {})
        self._selected = False
        self._selectedVisible = False

        super().__init__(*args, **kwargs)

    def getName(self) -> str:
        return self._name

    def setName(self, value:str):
        self._name = value

    name = property(getName, setName)

    def getGlyph(self) -> DoodleGlyph | RGlyph:
        return self._glyph

    def setGlyph(self, value:DoodleGlyph | RGlyph):
        self._glyph = value

    glyph = property(getGlyph, setGlyph)

    def getFont(self) -> DoodleFont:
        return self._font

    def setFont(self, value:DoodleFont):
        self._font = value

    font = property(getFont, setFont)

    def getSelected(self) -> bool:
        return self._selected

    def setSelected(self, value:bool=False):
        self._selected = value
        self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    selected = property(getSelected, setSelected)

    def getSelectedVisible(self) -> bool:
        return self._selectedVisible

    def setSelectedVisible(self, value:bool=False):
        # not the same as .visible, this only controls the view state not the selected state
        self._selectedVisible = value
        self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    selectedVisible = property(getSelectedVisible, setSelectedVisible)

    def getIndex(self) -> int:
        return self._index

    def setIndex(self, value:int=0):
        self._index = value

    index = property(getIndex, setIndex)

    def getOnDisk(self) -> bool:
        return self._onDisk

    def setOnDisk(self, value:bool=True):
        self._onDisk = value

    onDisk = property(getOnDisk, setOnDisk)

    def getOffset(self) -> int | float:
        return self._offset

    def setOffset(self, value:int | float):
        self._offset = value

    offset = property(getOffset, setOffset)

    def getSkewAngle(self) ->  int | float:
        return self._skewAngle

    def setSkewAngle(self, value: int | float):
        self._skewAngle = value

    skewAngle = property(getSkewAngle, setSkewAngle)

    def getScaler(self) ->  int | float:
        return self._scaler

    def setScaler(self, value: int | float):
        self._scaler = value

    scaler = property(getScaler, setScaler)

    def getLocation(self) ->  dict[str | float]:
        return self._location

    def setLocation(self, value: dict[str | float]):
        self._location = value

    location = property(getLocation, setLocation)



def symbolImage(symbolName:str, color:tuple|AppKit.NSColor, flipped:bool=False, pointSize:float=18.0, weight:str="light", scale:str="medium") -> AppKit.NSImage:
    '''
    taken from designspace editor
    '''
    image = None
    if osVersionCurrent >= osVersion12_0:
        image = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbolName, "")
        # not all SF symbols are available on older systems
        if image is not None:
            if isinstance(color, tuple):
                color = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(*color)
            else:
                color = symbolColorMap[color]()

            pointSize = float(pointSize)

            scales = {
                "small": AppKit.NSImageSymbolScaleSmall,
                "medium": AppKit.NSImageSymbolScaleMedium,
                "large": AppKit.NSImageSymbolScaleLarge,
            }
            scale = scales.get(scale.lower(), AppKit.NSImageSymbolScaleMedium)

            weights = {
                "ultraLight": AppKit.NSFontWeightUltraLight,
                "thin":       AppKit.NSFontWeightThin,
                "light":      AppKit.NSFontWeightLight,
                "regular":    AppKit.NSFontWeightRegular,
                "medium":     AppKit.NSFontWeightMedium,
                "semibold":   AppKit.NSFontWeightSemibold,
                "bold":       AppKit.NSFontWeightBold,
                "heavy":      AppKit.NSFontWeightHeavy,
                "black":      AppKit.NSFontWeightBlack,
            }
            weight = weights.get(weight.lower(), AppKit.NSFontWeightRegular)

            # baseConfig = AppKit.NSImageSymbolConfiguration.configurationWithHierarchicalColor_(color)
            newConfig = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
                pointSize,
                weight,
                scale
            )
            # newConfig = AppKit.NSImageSymbolConfiguration.configurationWithScale_(scale)
            # configuration = baseConfig.configurationByApplyingConfiguration_(newConfig)
            image = image.imageWithSymbolConfiguration_(newConfig)
    if flipped and image:
        image.setFlipped_(True)
    return image


class Spaceport(Subscriber, ezui.WindowController):

    debug = True

    def build(self):

        self._cache_ = []

        self.selectedItems = []

        self.foreground     = (0, 0, 0, 1)
        self.background     = (1, 1, 1, 1)

        self.showKerning = False
        self.multiline = True
        self.openSources = False
        self.viewSources = True
        self.viewInstances = False
        self.showBeam = True
        self.designspaceController = True


        self.font   = CurrentFont()
        self.fonts  = dict()
        self.glyphs = []

        self._fontFolder = {}


        for f in AllFonts():
            f.lib["descriptor"] = ""
            self.fonts[f.path] = (f==CurrentFont(), f)

        self.internalPreview = False
        self.designspaces = dict()
        self.operator = None

        self.sources   = []
        self.instances = []

        self.beamPosition = int(getattr(getattr(self.font, "info", None), "xHeight", 500) / 2)
        self.upm = int(getattr(getattr(self.font, "info", None), "unitsPerEm", 1000))

        toolbar = dict(
            autosaveName="demoToolbar",
            allowCustomization=True,
            contents=[
                dict(
                    identifier="editText",
                    image=symbolImage(symbolName=EDIT_TEXT, color=(1,1,1,1), weight="regular"),
                    text="Edit Text",
                    template=True,
                ),
                dict(
                    identifier="addObjects",
                    image=symbolImage(symbolName=ADD_FONT, color=(1,1,1,1), weight="regular"),
                    text="Objects",
                    template=True,
                ),
                # dict(
                #     identifier="addDesignspace",
                #     image=symbolImage(symbolName=ADD_DESIGNSPACE, color=(1,1,1,1), weight="light"),
                #     text="Designspace",
                #     template=True,
                # ),
                # dict(
                #     identifier="spacing",
                #     image=symbolImage(symbolName=SPACING, color=(1,1,1,1), weight="regular"),
                #     text="Spacing",
                #     template=True,
                # ),
                # dict(
                #     identifier="kerning",
                #     image=symbolImage(symbolName=KERNING, color=(1,1,1,1), weight="regular"),
                #     text="Kerning",
                #     template=True,
                # ),
                dict(
                    identifier="opentype",
                    image=symbolImage(symbolName=OPENTYPE, color=(1,1,1,1), weight="regular"),
                    text="OpenType",
                    template=True,
                ),
                dict(
                    identifier="interpolate",
                    image=symbolImage(symbolName=INTERPOLATE, color=(1,1,1,1), weight="regular"),
                    text="Interpolate",
                    template=True,
                ), 

                dict(
                    identifier="viewOptions",
                    image=symbolImage(symbolName=VIEW_OPTIONS, color=(1,1,1,1), weight="regular"),
                    text="View Options",
                    template=True,
                ),
            ]
        )

        content = """
        * MerzCollectionView    @collectionView
        """
        numberFieldWidth = 40
        description_data = dict(
            collectionView=dict(
                height="fill",
                width="fill",
                delegate=self,
            )
        )
        self.w = ezui.EZWindow(
            title=f"Spaceport v{EXTENSION_VERSION}",
            toolbar=toolbar,
            content=content,
            descriptionData=description_data,
            controller=self,
            margins=0,
            size=(1000, 500),
            minSize=(400, 200),
        )

        self.collectionView = self.w.getItem("collectionView")
        self.container = self.collectionView.getMerzContainer()
        self.marqueeLayer = self.container.appendRectangleSublayer()
        self.marquee = None
        self.collectionView.setBackgroundColor(AppKit.NSColor.whiteColor())
        self.marqueeLayer = self.container.appendBaseSublayer()
        self.w.matrix = spaceInput.SpaceInputScrollView((0, -48, 0, 48))


        content = """
        Beam:
        * HorizontalStack
        > [X]                                                         @showBeamButton
        > --X------                                                   @beamPositionSlider
        [X] Multiline                                                 @multilineButton
        [ ] Show Kerning                                              @showKerningButton
        [X] Show Metrics                                              @showMetricsButton
        [X] Show Space Matrix                                         @showSpaceMatrixButton
        -----
        Invert Colors:
        ( {circle.dashed} | {circle.fill} )                           @invertColorsButton
        Fill Options:
        (( {circle.fill} | {circle} | {circle.hexagonpath} ))         @displaySettingsButton
        Text Alignment:
        ( {text.alignleft} | {text.aligncenter} | {text.alignright} ) @alignmentSegmentButton
        """

        description_data = dict(
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
            displaySettingsButton=dict(
                selected=[0]
            ),
            alignmentSegmentButton=dict(
                selected=0
            ),
            showSpaceMatrixButton=dict(
                value=True,
            ),
        )

        self.glyphMap = {}

        self.v = ezui.EZPopover(
            size=(100,100),
            content=content,
            descriptionData=description_data,
            parent=self.w,
            behavior="transient",
            parentAlignment="right",
            controller=self
        )

        self.v.getItem("showKerningButton").show(False)

        content = """
        * HorizontalStack       @controlsStack
        > [__](±)               @pointSizeField
        > [__](±)               @lineHeightField
        > *GlyphSequence        @textField
        """

        description_data = dict(
            textField=dict(
                width="fill",
                font=self.font or internalFontClasses.createFontObject(),
            ),
            pointSizeField=dict(
                textFieldWidth=numberFieldWidth,
                minValue=20,
                value=150,
                maxValue=500,
                valueIncrement=10,
            ),
            lineHeightField=dict(
                textFieldWidth=numberFieldWidth,
                valueType="float",
                minValue=0.5,
                value=1.0,
                maxValue=2.0,
                valueIncrement=0.1
            ),
        )

        self.te = ezui.EZPopover(
            size=(self.w.getPosSize()[2], 40),
            content=content,
            descriptionData=description_data,
            parent=self.w,
            behavior="transient",
            parentAlignment="bottom",
            controller=self
        )
        self.te.setItemValue("textField", "SPACEPORT")
        #contentViewController
        self.v.getItem("invertColorsButton").set(0)
        self.invertColorsButtonCallback(self.v.getItem("invertColorsButton"))
        
        # main_prefs = getExtensionDefault(EXTENSION_KEY + ".main_prefs", fallback=self.w.getItemValues())
        # try: self.w.setItemValues(main_prefs)
        # except (AttributeError, KeyError): pass

        view_prefs = getExtensionDefault(EXTENSION_KEY + ".view_prefs", fallback=self.v.getItemValues())
        try: self.v.setItemValues(view_prefs)
        except (AttributeError, KeyError): pass

        __ = self.te.getItemValues()
        if isinstance(__["textField"], list): __["textField"] = ''.join([chr(n2u(glyph)) for glyph in __['textField']])
        
        input_prefs = getExtensionDefault(EXTENSION_KEY + ".input_prefs", fallback=__)
        try: self.te.setItemValues(input_prefs)
        except (AttributeError, KeyError): pass

        self.controlsStackCallback(None)
        self.displaySettingsButtonCallback(None)
        self.showMetricsButtonCallback(None)
        #self.showKerningButtonCallback(None)
        self.textFieldCallback(None)

        if not self.fonts and not self.designspaces:
            window = self.build_objects_sheet()
            window.open()

    def started(self):
        self.w.open()


    # designspace editor notifcations
    designspaceEditorPreviewLocationDidChangeDelay = 0.01

    def designspaceEditorPreviewLocationDidChange(self, notification):
        if self.designspaceController or self.internalPreview:
            selectedFonts = list(set([i.font for i in self.selectedItems if not i.onDisk]))
            if len(selectedFonts) == 1:
                pass
            elif not selectedFonts:
                if not list(self.fonts.values())[0][0]:
                    self.fontTableEditCallback(None) # turn on preview location
                # grab out dummy instance
                selectedFonts = [list(self.fonts.values())[0][-1]]

            for item in self.collectionView.get():
                if item.font == selectedFonts[0]:
                    self.updateItem(item, updated_location=notification["location"])
        self.collectionView.set(self.w.getItemValue("collectionView")) # i think that this is the only external-way to reload the view


    def designspaceEditorInstancesDidChangeSelection(self, notification):
        if self.designspaceController:
            operator = notification["designspace"]
            self.instances = notification["selectedItems"]
            self.designspaceSettingsChanged(
                    object=operator,
                    sources=self.sources,
                    instances=self.instances
            )


    def designspaceEditorSourcesDidChangeSelection(self, notification):
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


    def openSourcesCheckboxCallback(self, sender):
        self.openSources = sender.get()


    def DSSettingsButtonCallback(self, sender):
        self.viewSources           = 0 in sender.get()
        self.viewInstances         = 1 in sender.get()
        self.designspaceController = 2 in sender.get()
        self.designspaceSettingsChanged()
        

    def showSpaceMatrixButtonCallback(self, sender):
        self.w.matrix.show(sender.get())
        

    def build_objects_sheet(self):

        if not self.designspaces:
            self.designspaces = {dsp.path:(False, dsp) for dsp in AllDesignspaces()}

        content = """
        = ToolbarTabs
        * ToolbarTab:                                                      @fontTab
        > * Box                                                            @fontBox = HorizontalStack
        >> ( Refresh Order )                                               @refreshOrderButton
        >> ( Add All Open Fonts )                                          @openAllFontsButton
        >> [X] Open Font Interface                                         @openFontWithUIButton
        > |-files----|                                                     @fontTable
        > |          |  
        > |----------|  
        * ToolbarTab:                                                      @designspaceTab
        > * Box                                                            @designspaceBox = HorizontalStack
        >> ((  X View Sources X | View Instances | X DSE Controller X ))   @DSSettingsButton
        # >> [ ]                                                           @viewSourcesCheckbox
        # >> View Sources                                                  @viewSourcesText
        # >> [ ]                                                           @viewInstancesCheckbox
        # >> View Instances                                                @viewInstancesText
        # >> [ ]                                                           @useDesignspaceController
        # >> DSE Controller                                                @useDesignspaceText
        > |-files----|                                                     @designspaceTable
        > |          |
        > |----------|
        """

        description_data = dict(
            contents=dict(
                displayMode="text",
                allowCustomization=True,
                toolbarStyle="preference"
            ),
            fontTab=dict(
                identifier="fontTab",
                image=symbolImage(symbolName="dot.square", color=(1,1,1,1), weight="regular"),
                text="Fonts",
                template=True,
            ),
            designspaceTab=dict(
                identifier="designspaceTab",
                image=symbolImage(symbolName="arrow.up.left.and.down.right.and.arrow.up.right.and.down.left", color=(1,1,1,1), weight="regular"),
                text="Designspaces",
                template=True,
            ),
            fontBox=dict(
                height=50
            ),
            designspaceBox=dict(
                height=50
            ),
            fontTable=dict(
                items=[
                    dict(use=use,path=path) for (path, (use, font)) in self.fonts.items()
                ],
                itemType="dict",
                acceptedDropFileTypes=[".ufo", ".ufoz"],
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
            size=(500,500),
            content=content,
            descriptionData=description_data,
            parent=self.w,
            controller=self
        )

        indexes = [ii for ii,(i,obj) in enumerate(self.fonts.items()) if obj[0]]
        self.w.objw.getItem("fontTable").setSelectedIndexes(indexes)

        table=self.w.objw.getItem("designspaceTable")
        selection_index = None
        if self.operator:
            for ii, (path,(use, obj)) in enumerate(self.designspaces.items()):
                if obj == self.operator:
                    selection_index = ii
        if selection_index != None:
            table.setSelectedIndexes([selection_index])
        return self.w.objw

    def openAllFontsButtonCallback(self, sender):
        current = self.fonts.keys()
        for f in AllFonts():
            if f.path not in current:
                self.fonts[f.path] = (False, f)
        self.fonts = {path:(True,font) for path,(view,font) in self.fonts.items()}
        self.w.objw.getItem("fontTable").set(dict(use=use,path=path) for (path, (use, font)) in self.fonts.items())                
        self.populateItems()

        
    def designspaceSettingsChanged(self, **kwargs):
        obj = kwargs.get("object", self.operator)
        reset = kwargs.get("reset", False)
        if reset:
            self.fonts = self._fontFolder
        else:
            if obj:
                sources = kwargs.get("sources", obj.getFonts())
                instances = kwargs.get("instances", obj.instances)
                # remove designspace items
                fonts_dict = list(self.fonts.items())
                for _path, (_view, _font) in fonts_dict:
                    # if _view:    

                    if _path in [p.path for (p,_) in self.sources]:
                        del self.fonts[_path]
                        self._fontFolder[_path] = (_view, _font)

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
                    for source,loc_data in sources:
                        source.lib["descriptor"] = "source"
                        source.lib["location"]   = loc_data                    
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
                        
        if not self.font and self.fonts:
            self.setMainFont()

        self.w.objw.getItem("fontTable").set(dict(use=use,path=path) for (path, (use, font)) in self.fonts.items())                
        self.populateItems()



    def designspaceTableEditCallback(self, sender):
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


    def setMainFont(self, operator=None, setText=False):
        if operator:
            self.font = operator.getFonts()[0][0]
        else:
            self.font = list(self.fonts.values())[1][-1]
        self.upm = self.font.info.unitsPerEm
        if setText: self.te.getItem("textField").setFont(self.font)


    def designspaceTableCreateItemsForDroppedPathsCallback(self, sender, paths):
        operators = []
        for path in paths:
            controller = DesignspaceEditorController(path)
            operator = controller.operator
            self.designspaces[path] = (False,operator)
            item = dict(
                use=False,
                path=path,
            )
            operators.append(item)
            
        self.setMainFont(operator, True)
        return operators


    def addObjectsCallback(self, sender):
        self.build_objects_sheet()
        self.w.objw.open()


    def refreshOrderButtonCallback(self, sender):
        reordered = [item["path"] for item in self.w.objw.getItemValue("fontTable")]
        if reordered != list(self.fonts.keys()):
            self.fonts = {item["path"]:(item["use"],self.fonts[item["path"]][1]) for item in self.w.objw.getItemValue("fontTable")}
            self.populateItems()


    def fontTableEditCallback(self, sender):
        if sender:
            index = sender.getEditedIndex()
            new   = sender.getEditedItem()["use"]
        else:
            index = 0
            new = True

        path  = list(self.fonts.keys())[index]
        use,font = self.fonts[path]
        self.fonts[path] = (new, font)
        #self.populateItems()
        self.textFieldCallback(None)



    def fontTableCreateItemsForDroppedPathsCallback(self, sender, paths):
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


    def fontTableButtonsAddCallback(self, sender):
        file = GetFile(fileTypes=["ufoz", "ufo"])
        if file:
            opened = OpenFont(file)
            self.fonts[file] = (True, opened)
            self.w.objw.getItem("fontTable").close()
        self.populateItems()


    def fontTableDeleteCallback(self, sender):
        if len(sender.get()) > 1:
            items = sender.getSelectedIndexes()
            for it in items:
                ir = list(self.fonts.keys())[it]
                del self.fonts[ir]
            sender.removeSelection()


    def addDesignspaceCallback(self, sender):
        self.build_objects_sheet()
        self.w.objw.open()


    def spacingCallback(self, sender):
        pass


    def kerningCallback(self, sender):
        pass


    def opentypeCallback(self, sender):
        pass


    def interpolateCallback(self, sender):
        pass
        # # modified from DSE
        # if self.operator:
        #     content = """
        #     = TwoColumnForm
        #     """
        #     descriptionData = dict(
        #         content=dict(
        #             itemColumnWidth=200
        #         ),
        #     )
        #     for axisDescriptor in self.operator.axes:
        #         value = axisDescriptor.default
        #         if hasattr(axisDescriptor, "values"):
        #             # discrete axis
        #             content += f"""
        #             : {axisDescriptor.name}:
        #             ( ...)         @{axisDescriptor.name}
        #             """
        #             descriptionData[axisDescriptor.name] = dict(
        #                 items=[str(value) for value in axisDescriptor.values]
        #             )
        #         else:
        #             content += f"""
        #             : {axisDescriptor.name}:
        #             ---X--- [__]     @{axisDescriptor.name}
        #             """
        #             minimum, default, maximum = self.operator.getAxisExtremes(axisDescriptor)
        #             descriptionData[axisDescriptor.name] = dict(
        #                 minValue=minimum,
        #                 maxValue=maximum,
        #                 value=value
        #             )

        #     content += """
        #     =====
        #     ( Add as Instance )   @addAsInstance
        #     """
        #     self.vp = ezui.EZPopover(
        #         content=content,
        #         descriptionData=descriptionData,
        #         parent=self.w,
        #         parentAlignment="bottom",
        #         behavior="transient",
        #         size="auto",
        #         controller=self
        #     )

        #     self.vp.open()


    # def contentCallback(self, sender):
    #     self.internalPreview = True
    #     self.operator.setPreviewLocation(location=sender.get())


    def viewOptionsCallback(self,sender):
        self.v.open()


    def editTextCallback(self, sender):
        self.te.open()
        subwindow = self.te.getNSWindow().contentViewController().view().window()
        subwindow.makeFirstResponder_(self.te.getItem("textField").getNSTextField())


    def currentGlyphDidSetGlyph(self, info):
        self.textFieldCallback(None)


    def textFieldCallback(self, sender):
        self.unsubscribeFromGlyphs()
        glyphNames = self.te.getItemValue("textField")
        font = self.font
        holding = []
        if font:
            for name in glyphNames:
                if name in font.keys():
                    holding.append(name)

                elif name == CURRENTGLYPH_CHAR:
                    if CurrentGlyph() is not None:
                        holding.append(CurrentGlyph().name)

        self.glyphs = holding
        self.subscribeToGlyphs()
        self.populateItems()


    def alignmentSegmentButtonCallback(self, sender):
        self.controlsStackCallback(None)


    def controlsStackCallback(self, sender):
        values = self.te.getItemValues()
        al_vals = self.v.getItemValues()

        pointSize = values["pointSizeField"]
        lineHeight = values["lineHeightField"]
        alignment = ("left", "center", "right")[al_vals["alignmentSegmentButton"]]
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

    def invertColorsButtonCallback(self, sender):
        self.invert = self.v.getItemValue("invertColorsButton")
        foreground_color = [(0,0,0,1), (1,1,1,1)][self.invert]
        background_color = [AppKit.NSColor.whiteColor(), AppKit.NSColor.blackColor()][self.invert]

        self.collectionView.setBackgroundColor(background_color)
        items = self.w.getItemValue("collectionView")
        for item in items:
            glyphContainer = item.getLayer("glyphContainer")
            glyphFillLayer = glyphContainer.getSublayer("glyphFill")
            glyphFillLayer.setFillColor(foreground_color)
            glyphFillLayer.setVisible(self.showFill)
                
            glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
            if self.showStroke:
                if self.invert:
                    glyphStrokeLayer.setStrokeWidth(.7)
                else:
                    glyphStrokeLayer.setStrokeWidth(1)

                glyphFillLayer.setFillColor((*foreground_color[:3], .2))
            else:
                glyphFillLayer.setFillColor(foreground_color)

            glyphStrokeLayer.setStrokeColor(foreground_color)
            glyphStrokeLayer.setVisible(self.showStroke)
            glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")

            for symbol in glyphPointsLayer.getSublayers():
                location = symbol.getPosition()
                settings = symbol.getImageSettings()
                settings["fillColor"] = foreground_color
                symbol.setImageSettings(settings)
            glyphPointsLayer.setVisible(self.showPoints)
        self.foreground = foreground_color
        self.background = background_color


    def showMetricsButtonCallback(self, sender):
        self.showMetrics = self.v.getItemValue("showMetricsButton")
        self.displaySettingsButtonCallback(None)


    def multilineButtonCallback(self, sender):
        self.multiline = self.v.getItemValue("multilineButton")
        self.displaySettingsButtonCallback(None)
        self.populateItems()


    def beamPositionSliderCallback(self, sender):
        self.beamPosition = sender.get()
        self.displaySettingsButtonCallback(None, onlyBeam=True)


    def showBeamButtonCallback(self, sender):
        self.showBeam = self.v.getItemValue("showBeamButton")
        self.displaySettingsButtonCallback(None, onlyBeam=True)


    def showKerningButtonCallback(self, sender):
        self.showKerning = self.v.getItemValue("showKerningButton")
        self.displaySettingsButtonCallback(None)
        self.populateItems()


    def displaySettingsButtonCallback(self, sender, onlyBeam=False):
        values = self.v.getItemValue("displaySettingsButton")
        self.showFill      = 0 in values
        self.showStroke    = 1 in values
        self.showPoints    = 2 in values

        self.beamPosition  = self.v.getItemValue("beamPositionSlider")
        self.showBeam      = self.v.getItemValue("showBeamButton")

        items = self.w.getItemValue("collectionView")
        for item in items:

            if onlyBeam:
                self.beamController(item)
                self.w.matrix.setShowBeam(self.showBeam)
                self.w.matrix.setBeamPosition(self.beamPosition)
            else:
                glyphContainer = item.getLayer("glyphContainer")

                glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")
                glyphMetricsLayer.setVisible(self.showMetrics)

                kernIndicatorLayer = glyphContainer.getSublayer("kernIndicator")
                kernIndicatorLayer.setVisible(self.showKerning)

                beamIndicatorLayer = glyphContainer.getSublayer("beamIndicator")
                beamIndicatorLayer.setVisible(self.showBeam)

                glyphFillLayer = glyphContainer.getSublayer("glyphFill")
                glyphFillLayer.setVisible(self.showFill)
                if self.showStroke:
                    glyphFillLayer.setFillColor((*self.foreground[:3], .2))
                else:
                    glyphFillLayer.setFillColor(self.foreground)

                glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
                glyphStrokeLayer.setVisible(self.showStroke)
                glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
                glyphPointsLayer.setVisible(self.showPoints)


    def buildItem(self, **kwargs) -> MerzCollectionViewRGlyphItem:
        name = kwargs.get("name")
        glyph = kwargs.get("glyph")
        font = kwargs.get("font")
        index = kwargs.get("index")
        onDisk = kwargs.get("onDisk")
        skewAngle = kwargs.get("skewAngle")
        off = kwargs.get("italicOffset")
        location = kwargs.get("location", {})

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
        glyphContainer.appendBaseSublayer(
            name="glyphPoints",
            visible=True,
        )

        glyphContainer.appendBaseSublayer(
            name="selectionIndicator",
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

            location_data  = ""
            formatted = [f'{axis}:{value}' for axis,value in location.items()]
            if font.lib.get("descriptor") == "source":
                location_data += f' s: {" ".join(formatted)}'
            elif font.lib.get("descriptor") == "instance":
                location_data += f' i: {" ".join(formatted)}'
            else:
                location_data += f"    {os.path.basename(item.font.path)}"

            descriptorIndicatorLayer = glyphContainer.getSublayer("descriptorIndicator")
            with descriptorIndicatorLayer.propertyGroup():
                if item.index == 0:
                    descriptorIndicatorLayer.appendTextLineSublayer(
                        font="SFMono-Regular",
                        text=location_data,
                        pointSize=8,
                        position=(-50,-200*item.scaler),
                        fillColor=(*self.foreground[0:3], .5),
                        horizontalAlignment="left",
                        verticalAlignment="center",
                        anchor=(.5,.5)
                    )

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
                    next_glyph = self.glyphs[index+1]
                    kern = font.kerning.find((glyph.name, next_glyph))
                except IndexError:
                    kern = 0

                if not self.showKerning:
                    kern = 0

                if kern:
                    item.setXAdvance(kern)
                    kernIndicatorLayer.setVisible(True)

                    kern_color = POS_KERN_COLOR if kern > 0 else NEG_KERN_COLOR
                    kernIndicatorLayer.appendTextLineSublayer(
                        text=str(kern),
                        pointSize=7,
                        position=((abs(kern)/2), 0),
                        fillColor=(*kern_color,1),
                        horizontalAlignment="center",
                        # padding=(0,0),
                        )

                    x = (glyph.width+kern) if kern < 0 else glyph.width
                    kernIndicatorLayer.setBackgroundColor((*kern_color, .2))
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
            glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
            glyphPointsLayer.clearSublayers()
            onCurve = 20 * item.scaler
            with glyphPointsLayer.propertyGroup():
                for contour in glyph.contours:
                    for point in contour.points:
                        if point.type != "offcurve":
                            x = point.x
                            y = point.y
                            glyphPointsLayer.appendOvalSublayer(
                                position=(x-off, y),
                                size=(onCurve,onCurve),
                                anchor=(.5,.5),
                                fillColor=(0, 0, 0, 1),
                            )
                glyphPointsLayer.setVisible(self.showPoints)
                self.beamController(item)

        if index+1 == len(self.glyphs):
            if self.multiline:
                item.setForceBreakAfter(True)
            else:
                item.setForceBreakAfter(False)
        return item


    def updateItem(self, item:MerzCollectionViewRGlyphItem, **kwargs):
        """
        a faster alternative to rebuilding glyphs everytime
        """
        glyphContainer = item.getLayer("glyphContainer")
        glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")

        glyph = item.glyph
        font = item.font
        loc = kwargs.get("updated_location")
        if loc:
            item.location = loc
            infoMutator = self.operator.makeOneInfo(loc)
            item.skewAngle = infoMutator.italicAngle
            item.font.info.italicAngle = item.skewAngle

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
                
                loc_layer = glyphContainer.getSublayer("descriptorIndicator")
                with loc_layer.propertyGroup():
                    loc_layer.clearSublayers()
                    if item.index == 0:
                        formatted = [f"{axis}:{round(value,3)}" for axis,value in loc.items()]
                        loc_layer.appendTextLineSublayer(
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
                    margin.setText(str(val))
                    margin.setPosition((start[0],round(depth/2)))

                line = glyphMetricsLayer.getSublayer(f"glyphMetrics{side.title()}LinesSublayer")
                line.setStartPoint(start)
                line.setEndPoint(end)

            wd = glyphMetricsLayer.getSublayer("glyphWidthSublayer")
            wd.setText(str(glyph.width))
            wd.setPosition((round(glyph.width/2),round(depth/2)))

        glyphFillLayer = glyphContainer.getSublayer("glyphFill")
        #with glyphFillLayer.propertyGroup():    # for some reason this wont work inside a property group
        try: glyphFillLayer.removeTransformation("translate")
        except: pass
        glyphFillLayer.addTranslationTransformation((-item.offset, 0), "translate")
        glyphFillLayer.setPath(glyph.getRepresentation("merz.CGPath"))

        glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
        #with glyphStrokeLayer.propertyGroup():    # for some reason this wont work inside a property group
        try: glyphStrokeLayer.removeTransformation("translate")
        except: pass
        glyphStrokeLayer.addTranslationTransformation((-item.offset, 0), "translate")
        glyphStrokeLayer.setPath(glyph.getRepresentation("merz.CGPath"))

        glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
        glyphPointsLayer.clearSublayers()
        onCurve = 20 * item.scaler
        
        with glyphPointsLayer.propertyGroup():
            for contour in glyph.contours:
                for point in contour.points:
                    if point.type != "offcurve":
                        x = point.x
                        y = point.y
                        glyphPointsLayer.appendOvalSublayer(
                            position=(x-item.offset, y),
                            size=(onCurve,onCurve),
                            anchor=(.5,.5),
                            fillColor=(0, 0, 0, 1),
                        )
            glyphPointsLayer.setVisible(self.showPoints)

        self.beamController(item)

        selection = glyphContainer.getSublayer("selectionIndicator").getSublayer("selectionIndicatorDrawing")
        selection.setPosition((0,font.info.descender))
        selection.setSize((glyph.width, abs(font.info.descender) + font.info.ascender))
                # if switching from roman <> italic, we need to update the selection indicator skew
        if kwargs.get("updated_location"):
            try: selection.removeTransformation("skew")
            except: pass
            if item.skewAngle: selection.addSublayerSkewTransformation((-item.skewAngle))


    def populateItems(self, reload:bool=False):
        items = []
        _glyphRecords = []
        
        for font_index, (path,(use,font)) in enumerate(self.fonts.items()):
            if use:
                for index, glyph in enumerate(self.glyphs):
                    item = None
                    if self._cache_:
                        if len(self._cache_) > index+1:
                            hold = self._cache_[index]
                            if hold == glyph:
                                item_holder = [_item
                                               for _item in self.w.getItemValue("collectionView")
                                               if font == _item.font
                                               and
                                               glyph == _item.glyph.name
                                               and
                                               index == _item.index
                                              ]
                                if item_holder:
                                    item = item_holder[0]
                                    if index+1 == len(self.glyphs):
                                        if self.multiline:
                                            item.setForceBreakAfter(True)
                                        else:
                                            item.setForceBreakAfter(False)

                    if not item:
                        on_disk = True
                        skewAngle = getattr(font.info, "italicAngle") or 0
                        off = font.lib.get("com.typemytype.robofont.italicSlantOffset", 0)
                        if font.lib.get("descriptor") == "instance":
                            _temp = glyph
                            mathGlyph = self.operator.makeOneGlyph(glyph, font.lib.get("location"), decomposeComponents=True)
                            if mathGlyph is not None:
                                glyph = internalFontClasses.createGlyphObject()
                                # glyph.font = font
                                mathGlyph.extractGlyph(glyph)
                                glyph = font.insertGlyph(glyph, name=_temp)
                                on_disk = False
                        else:
                            glyph = font[glyph]

                        if not isinstance(glyph, RGlyph):
                            glyph = RGlyph(glyph)

                        item = self.buildItem(
                                        name=glyph.name,
                                        glyph=glyph,
                                        font=font,
                                        index=index,
                                        onDisk=on_disk,
                                        skewAngle=skewAngle,
                                        italicOffset=off,
                                        location=font.lib.get("location", {})
                                )

                    if font_index == 0:
                        _glyphRecords.append(GlyphRecord(item.glyph.naked()))

                    items.append(item)

        self._cache_ = self.glyphs
        self.collectionView.set(items)

        items = self.w.getItemValue("collectionView")
        for item in items:
            self.beamController(item)
            
        self.w.matrix.set(_glyphRecords)


    def beamController(self, item:MerzCollectionViewRGlyphItem):

        glyph = item.glyph
        font = item.font
        beamIndicatorLayer = item.getLayer("glyphContainer").getSublayer("beamIndicator")
        beamIndicatorLayer.clearSublayers()
        # beamIndicatorLayer.addTranslationTransformation(value=(-off,0))
        beamIntersectSize = 30 * item.scaler

        with beamIndicatorLayer.propertyGroup():
            try:
                next_glyph = [ii for ii in self.collectionView.get() if item.font == ii.font][item.index+1].glyph
            except IndexError:
                next_glyph = None

            right = glyph.getRayRightMargin(self.beamPosition, item.skewAngle) or 0
            left = glyph.getRayLeftMargin(self.beamPosition, item.skewAngle) or 0

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
            trans = tuple(t)
            ot = transform.Transform(*trans)
            
            tp,_ = ot.transformPoint((0, self.beamPosition))

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
                    endPoint=(left+tp, self.beamPosition),
                    strokeColor=(1,.2,0,.4),
                    strokeWidth=1,
                )

            beamIndicatorLayer.appendOvalSublayer(
                position=(left+tp, self.beamPosition),
                size=(beamIntersectSize,beamIntersectSize),
                anchor=(.5,.5),
                fillColor=(1,.2,0,1)
            )

            beamIndicatorLayer.appendOvalSublayer(
                position=((glyph.width - right)+tp, self.beamPosition),
                size=(beamIntersectSize,beamIntersectSize),
                anchor=(.5,.5),
                fillColor=(1,.2,0,1)
            )

            beamIndicatorLayer.appendLineSublayer(
                startPoint=(left+tp, self.beamPosition),
                endPoint=((glyph.width - right)+tp, self.beamPosition),
                strokeColor=(1,.2,0,.4),
                strokeWidth=1,
                )
            if next_glyph:
                # if font.lib.get("descriptor") == "instance":
                #     mathGlyph = self.operator.makeOneGlyph(next_glyph, item.location, decomposeComponents=True)
                #     if mathGlyph is not None:
                #         glyph = internalFontClasses.createGlyphObject()
                #         mathGlyph.extractGlyph(glyph)
                #         next = RGlyph(glyph)
                # else:
                #     next = font[next_glyph]

                other_left = next_glyph.getRayLeftMargin(self.beamPosition, item.skewAngle) or 0

                if font.info.familyName == "Preview Location":
                    other_left -= item.offset

                beamIndicatorLayer.appendLineSublayer(
                    startPoint=((glyph.width - right)+tp, self.beamPosition),
                    endPoint=((glyph.width + other_left)+tp, self.beamPosition),
                    strokeColor=(1,.2,0,1),
                    strokeWidth=1,
                )

                if other_left:
                    beamIndicatorLayer.appendTextLineSublayer(
                        text=str(round(right + other_left)),
                        font="SFMono-Regular",
                        position=((glyph.width - right) + ((right + other_left)/2)+tp, self.beamPosition),
                        fillColor=(1,.2,0,1),
                        pointSize=10,
                        backgroundColor=(1,.2,0,.2),
                        cornerRadius=5,
                        horizontalAlignment="center",
                        verticalAlignment="bottom",
                        padding=(3,1),
                    )

            beamIndicatorLayer.setVisible(self.showBeam)


    def acceptsFirstResponder(self, sender):
        # necessary for accepting mouse events
        return True

    def acceptsMouseMoved(self, sender):
        # necessary for tracking mouse movement
        return True

    def magnifyWithEvent(self, sender, event):
        values = self.te.getItemValues()
        pointSize = values["pointSizeField"]
        lineHeight = values["lineHeightField"]
        minScale = 0.1
        maxScale = 3.0
        magnificationDelta = event.magnification()
        if magnificationDelta < 0:
            factor = 0.85
        else:
            factor = 1.15
        pointSize *= factor
        scale = pointSize / self.upm
        lineHeight = self.upm * lineHeight * scale

        self.te.setItemValue("pointSizeField", pointSize)
        self.collectionView.setLayoutProperties(
            scale=scale,
            lineHeight=lineHeight
        )


    def destroy(self):
        setExtensionDefault(EXTENSION_KEY + ".main_prefs", self.w.getItemValues())
        setExtensionDefault(EXTENSION_KEY + ".view_prefs", self.v.getItemValues())
        input_dict = self.te.getItemValues()
        input_dict['textField'] = ''.join([chr(n2u(glyph)) for glyph in input_dict['textField']])
        setExtensionDefault(EXTENSION_KEY + ".input_prefs", input_dict)
        self.clearObservedAdjunctObjects()


    def _getItemAtEvent(self, position:tuple=(0,0)) -> MerzCollectionViewRGlyphItem:
        x,y = position
        hits = self.container.findSublayersContainingPoint(
            (x, y),
            onlyAcceptsHit=True,
            recurse=False
        )
        if not hits:
            return None
        hit = hits[0]
        return hit


    def _convertLocation(self, event:dict) -> tuple:
        location = event["location"]
        location = self.collectionView.getMerzView().convertWindowCoordinateToViewCoordinate(
            point=location
        )
        x, y = self.container.convertViewCoordinateToLayerCoordinate(
            location,
            self.container
        )
        return (x,y)


    def mouseDown(self,view,event):
        event = merz.unpackEvent(event)
        self.start = (x,y) = self._convertLocation(event)
        self.marqueeLayer.clearSublayers()
        hit = self._getItemAtEvent((x,y))
        selection = []

        selectedGlyph = None
        selectedFont = None
        multiFontSelect = False

        for temp_item in self.collectionView.get():
            if temp_item not in self.selectedItems:
                temp_item.selected = False

        if hit:
            clickCount = event["clickCount"]
            parsed = hit.glyph
            if parsed:
                hit.selected = True
                # selectedGlyph = self.getGlyphFromItem(hit)
                selectedGlyph = parsed

            if selectedGlyph:

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
                    for temp_item in self.collectionView.get():
                        if temp_item not in self.selectedItems:
                            temp_item.selected = False

                if clickCount == 2:
                    try:
                        OpenGlyphWindow(selectedGlyph)
                    except:
                        selectedGlyph.copyToPasteboard()
            else:
                # print("clearing selection")
                self.selectedItems = []
        else:
            # print("clearing selection")
            self.selectedItems = []

        if not self.selectedItems:
            for temp_item in self.collectionView.get():
                temp_item.selected = False

        if multiFontSelect:
            for temp_item in self.collectionView.get():
                if temp_item.index == hit.index:
                    self.selectedItems.append(temp_item)
                    temp_item.selected = True

        # only set the matrix for one font at a time, the selected one.
        if len(set([hits.glyph.font for hits in self.selectedItems])) == 1:
            records = [GlyphRecord(item.glyph.naked()) for item in self.collectionView.get() if item.glyph.font == selectedGlyph.font]
            self.w.matrix.set(records)

        elif multiFontSelect:
            records = [GlyphRecord(item.glyph.naked()) for item in self.selectedItems]
            self.w.matrix.set(records)



    def mouseDragged(self,view,event):
        self.hoverItem = None
        self.wasDragging = True
        # self.container.clearSublayers()

        event = merz.unpackEvent(event)
        x, y = self._convertLocation(event)

        ox,oy = self.start
        shift = True if AppKit.NSEvent.modifierFlags() & AppKit.NSShiftKeyMask else False
        
        if x > ox and y < oy:
            p = (ox,y)
            s = (ox-x,oy-y)
            
        elif x > ox and y > oy:
            p = (ox,oy)
            s = (x-ox, y-oy)
            
        elif x < ox and y > oy:
            p = (x,oy)
            s = (ox-x, oy-y)
            
        elif x < ox and y < oy:
            p = (x,y)
            s = (x-ox, y-oy)
        else:
            return


    def keyDown(self, view, event):

        directions = "left right up down".split(" ")
        event = merz.unpackEvent(event)

        mods = event["modifiers"]
        char = event["character"]
        repeat = event["isKeyRepeat"]

        if char in directions:
            for item in self.selectedItems:

                item.selected = True

                # glyph = self.getGlyphFromItem(item)
                glyph = item.glyph
                                            
                if item.onDisk:
                    with glyph.undo(f"Change spacing of {glyph.name}"):
                        if "shift" in mods and "command" in mods:
                            spacing_unit = 100
                        elif "shift" in mods:
                            spacing_unit = 10
                        else:
                            spacing_unit = 1
                        if glyph.bounds:
                            if "option" in mods and char == "right":
                                glyph.leftMargin += spacing_unit
                            elif "option" in mods and char == "left":
                                glyph.leftMargin -= spacing_unit
                            elif char == "right":
                                glyph.rightMargin += spacing_unit
                            elif char == "left":
                                glyph.rightMargin -= spacing_unit
                            elif char == "up":
                                glyph.rightMargin += spacing_unit
                                glyph.leftMargin  += spacing_unit
                            elif char == "down":
                                glyph.rightMargin -= spacing_unit
                                glyph.leftMargin  -= spacing_unit
                            else:
                                pass
                        else:
                            if char == "right":
                                glyph.width += spacing_unit
                            elif char == "left":
                                glyph.width -= spacing_unit

        else:
            # allow for undoing
            if AppKit.NSEvent.modifierFlags() & AppKit.NSCommandKeyMask:
                if char.lower() == "z":
                    for to_undo in self.selectedItems:
                        glyph = to_undo.glyph
                        manager = AppKit.NSApp().getUndoManagerForGlyph_(glyph.asDefcon())
                        manager.undo()
                elif char.lower() == "t":
                    self.te.open()

            if mods == []:
                if char.lower() == "b":
                    self.showBeam = not self.showBeam
                    self.v.setItemValue("showBeamButton", self.showBeam)

                    self.w.matrix.setShowBeam(self.showBeam)

                    items = self.w.getItemValue("collectionView")
                    for item in items:
                        self.beamController(item)


    def mouseMoved(self, view, event):
        pass
        # print("debug::mouseMoved")


    def mouseUp(self, view, event):
        pass
        # print("debug::mouseUp")


    def subscribeToGlyphs(self):
        glyphs = []
        for (__, obj) in self.fonts.values():
            try:
                glyphs.extend(list(set([obj[glyph] for glyph in self.glyphs])))
            except:
                pass
        self.setAdjunctObjectsToObserve(glyphs)


    def unsubscribeFromGlyphs(self):
        self.clearObservedAdjunctObjects()


    def adjunctGlyphDidChangeMetrics(self, info):
        self.w.matrix._glyphWidthChanged(info)
        items = self.w.getItemValue("collectionView")
        for item in items:
            if item.glyph == info["glyph"]:
                self.updateItem(item)
        self.collectionView.set(self.w.getItemValue("collectionView")) # i think that this is the only external-way to reload the view


    def adjunctGlyphDidChangeOutline(self, info):
        self.w.matrix._glyphChanged(info)
        items = self.w.getItemValue("collectionView")
        for item in items:
            if item.glyph == info["glyph"]:
                self.updateItem(item)
        self.collectionView.set(self.w.getItemValue("collectionView")) # i think that this is the only external-way to reload the view



#registerCurrentGlyphSubscriber(Spaceport)
if __name__ == "__main__":
    Spaceport()


