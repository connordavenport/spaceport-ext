import AppKit
from defcon import Font
from lib.UI.spaceCenter.glyphSequenceEditText import splitText,\
    currentGlyphKey, currentSelectionKey, newLineKey, groupsKey
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
import math

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
ADD_FONT = "plus"
ADD_DESIGNSPACE = "grid"
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

SOURCE_ICON = "􀀨"
INSTANCE_ICON = "􀀔"
STATIC_ICON = ""


class MerzCollectionViewRGlyphItem(merz.collectionView.MerzCollectionViewItem):

    def __init__(self, *args, **kwargs):
        self._font = kwargs.get("font")
        self._glyph = kwargs.get("glyph")
        self._index = kwargs.get("index")
        super().__init__(*args, **kwargs)

    # Dimensions

    def getGlyph(self):
        return self._glyph

    def setGlyph(self, value):
        self._glyph = value

    glyph = property(getGlyph, setGlyph)

    def getFont(self):
        return self._font

    def setFont(self, value):
        self._font = value

    font = property(getFont, setFont)

    def getSelected(self):
        return self._selected

    def setSelected(self, value):
        self._selected = value
        self.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(value)

    selected = property(getSelected, setSelected)


    def getIndex(self):
        return self._index

    def setIndex(self, value):
        self._index = value

    index = property(getIndex, setIndex)


    def getOnDisk(self):
        return self._onDisk

    def setOnDisk(self, value):
        self._onDisk = value

    onDisk = property(getOnDisk, setOnDisk)




def symbolImage(symbolName:str, color:tuple|AppKit.NSColor, flipped:bool=False, pointSize:float=18.0, weight:str="light", scale:str="medium") -> AppKit.NSImage:
    '''
    taken from designspace editors
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

    def build(self):

        # self._unwrappedItems = []

        self.selectedItems = []

        self.foreground     = (0, 0, 0, 1)
        self.background     = (1, 1, 1, 1)
        self.selectionColor = (0.58, 0.22, 1, 1)

        self.showKerning = False
        self.multiline = True
        self.openSources = False
        self.viewSources = True
        self.viewInstances = False
        self.showBeam = True


        self.font = CurrentFont()
        self.fonts = {f.path:(f==CurrentFont(),f) for f in AllFonts()}

        self.designspaces = {dsp.path:dsp for dsp in AllDesignspaces()}
        self.designspace = None

        self.beamPosition = int(self.font.info.xHeight / 2)

        toolbar = dict(
            autosaveName="demoToolbar",
            allowCustomization=True,
            contents=[
                dict(
                    identifier="edit_text",
                    image=symbolImage(symbolName=EDIT_TEXT, color=(1,1,1,1), weight="regular"),
                    text="Edit Text",
                    template=True,
                ),
                dict(
                    identifier="add_font",
                    image=symbolImage(symbolName=ADD_FONT, color=(1,1,1,1), weight="regular"),
                    text="Add Font",
                    template=True,
                ),
                dict(
                    identifier="add_designspace",
                    image=symbolImage(symbolName=ADD_DESIGNSPACE, color=(1,1,1,1), weight="regular"),
                    text="Add Designspace",
                    template=True,
                ),
                dict(
                    identifier="spacing",
                    image=symbolImage(symbolName=SPACING, color=(1,1,1,1), weight="regular"),
                    text="Spacing",
                    template=True,
                ),
                dict(
                    identifier="kerning",
                    image=symbolImage(symbolName=KERNING, color=(1,1,1,1), weight="regular"),
                    text="Kerning",
                    template=True,
                ),
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
                    identifier="view_options",
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
        descriptionData = dict(
            collectionView=dict(
                height="fill",
                width="fill",
                delegate=self,
            )
        )
        self.w = ezui.EZWindow(
            title="Spaceport",
            toolbar=toolbar,
            content=content,
            descriptionData=descriptionData,
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

        self.marqueeLayer = self.container.appendRectangleSublayer(
            position=(100,100),
            size=(1000,1000),
            fillColor=(0,1,0,.1),
            strokeColor=(0,1,0,1),
            strokeWidth=1
        )

        # self.marqueeLayer = self.container.appendRectangleSublayer()

        # for item in self.w.getItemValues():
        #     if "Field" in item:
        #         ii = self.w.getItem(item)
        #         try:
        #             ii.hide(True)
        #         except:
        #             pass

        content = """
        Beam:
        * HorizontalStack
        > [X]                                                         @showBeamButton
        > --X------                                                   @beamPositionSlider
        Multiline:                                                 
        [X]                                                           @multilineButton
        Show Kerning:                                                 @showKerningLabel
        [ ]                                                           @showKerningButton
        Show Metrics:
        ( Off | On )                                                  @showMetricsButton
        Invert Colors:
        ( {circle.dashed} | {circle.fill} )                           @invertColorsButton
        Fill Options:
        (( {circle.fill} | {circle} | {circle.hexagonpath} ))         @displaySettingsButton
        Text Alignment:
        ( {text.alignleft} | {text.aligncenter} | {text.alignright} ) @alignmentSegmentButton
        """

        descriptionData = dict(
            showBeamButton=dict(
                value=True,
            ),
            beamPositionSlider=dict(
                minValue=0,
                maxValue=self.font.info.unitsPerEm,
                value=int(self.font.info.xHeight/2)
            ),
            showKerningButton=dict(
                # hide=False,
            ),
            showMetricsButton=dict(
                selected=1
            ),
            displaySettingsButton=dict(
                selected=[0]
            ),
            alignmentSegmentButton=dict(
                selected=0
            ),
        )

        self.glyphMap = {}

        self.v = ezui.EZPopover(
            size=(100,100),
            content=content,
            descriptionData=descriptionData,
            parent=self.w,
            behavior="transient",
            parentAlignment="right",
            controller=self
        )

        self.v.getItem("showKerningButton").show(False)
        self.v.getItem("showKerningLabel").show(False)

        content = """
        * HorizontalStack       @controlsStack
        > [__](±)               @pointSizeField
        > [__](±)               @lineHeightField
        > *GlyphSequence        @textField
        """

        descriptionData = dict(
            textField=dict(
                width="fill",
                font=self.font
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
            descriptionData=descriptionData,
            parent=self.w,
            behavior="transient",
            parentAlignment="bottom",
            controller=self
        )
        self.te.setItemValue("textField", "SPACEPORT")
        #contentViewController
        self.v.getItem("invertColorsButton").set(0)
        self.invertColorsButtonCallback(self.v.getItem("invertColorsButton"))

        # nsTableView = self.af.getItem("fontsTable")._table.getNSTableView()
        # nsTableColumn = nsTableView.tableColumns()[0]
        # nsTableHeaderCell = nsTableColumn.headerCell()
        # nsTableHeaderCell.setImage_(
        #     ezui.makeImage(
        #     symbolName="eye.circle.fill",
        #     template=True
        #     )
        # )
        
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
        

    def started(self):
        self.w.open()

    def build_fonts_sheet(self):
        content_fonts = """
        |------------------|
        | use    | path    | @fontsTable
        |--------|---------|
        | []     | a.ufo   |
        |        |         |
        |------------------|
        """
        descriptionData_fonts = dict(
            fontsTable=dict(
                items=[
                    dict(
                        will_use=use,
                        name=os.path.basename(path),
                        ) for (path, (use, font)) in self.fonts.items()
                    ],
                columnDescriptions=[
                    dict(
                        identifier="will_use",
                        title="􀘨",
                        width=35,
                        editable=True,
                        cellDescription=dict(
                            cellType="Checkbox",
                            )
                        ),
                    dict(
                        identifier="name",
                        title="Name"
                    )
                ]
            ),
        )

        self.w.af = ezui.EZSheet(
            size=(400, 300),
            content=content_fonts,
            descriptionData=descriptionData_fonts,
            parent=self.w,
            controller=self
        )

    def build_designspace_sheet(self):
        content_dsps = """
        |---------|
        | path    |            @designspaceTable
        |---------|
        | a.dsp   |
        |         |
        |---------|
        * HorizontalStack
        > [ ] Open Sources     @openSourcesCheckbox  
        > [ ] View Sources     @viewSourcesCheckbox
        > [ ] View Instances   @viewInstancesCheckbox
        """
        descriptionData_dsps = dict(
            designspaceTable=dict(
                items=[
                    dict(
                        name=os.path.basename(path),
                        ) for (path, (obj)) in self.designspaces.items()
                    ],
                columnDescriptions=[
                    dict(
                        identifier="name",
                        title="Name"
                    )
                ],
                allowsMultipleSelection=False,
            ),
            openSourcesCheckbox=dict(
                value=self.openSources
            ),
            viewSourcesCheckbox=dict(
                value=self.viewSources
            ),
            viewInstancesCheckbox=dict(
                value=self.viewInstances
            ),
        )

        self.w.dsp = ezui.EZSheet(
            size=(400, 300),
            content=content_dsps,
            descriptionData=descriptionData_dsps,
            parent=self.w,
            controller=self
        )

        table=self.w.dsp.getItem("designspaceTable")
        selection_index = None
        if self.designspace:
            for ii, (path,obj) in enumerate(self.designspaces.items()):
                if obj == self.designspace:
                    selection_index = ii
        if selection_index != None:
            table.setSelectedIndexes([selection_index])


    def designspaceTableSelectionCallback(self, sender):
        index = sender.getSelectedIndexes()
        if index:
            self.openSources = self.w.dsp.getItemValue("openSourcesCheckbox")
            self.viewSources = self.w.dsp.getItemValue("viewSourcesCheckbox")
            self.viewInstances = self.w.dsp.getItemValue("viewInstancesCheckbox")

            index = index[0]
            path  = list(self.designspaces.keys())[index]
            obj = self.designspaces[path]
            self.designspace = obj
            self.fonts = {}
            if self.viewSources:
                for source,loc_data in obj.getFonts():
                    source.lib["descriptor"]  = "source"
                    source.lib["location"]    = loc_data                    
                    self.fonts[source.path]   = (True,source)
            if self.viewInstances:
                for instance in obj.instances:
                    inst = Font()
                    inst.lib["descriptor"]    = "instance"
                    inst.lib["location"]      = instance.designLocation
                    self.fonts[instance.path] = (True,inst)
        self.populateItems()


    def fontsTableEditCallback(self, sender):
        index = sender.getEditedIndex()
        new   = sender.getEditedItem()["will_use"]
        path  = list(self.fonts.keys())[index]
        use,font = self.fonts[path]
        self.fonts[path] = (new, font)
        self.populateItems()

    def add_fontCallback(self, sender):
        self.build_fonts_sheet()
        self.w.af.open()
        
    def addRemoveButtonAddCallback(self, sender):
        file = GetFile(fileTypes=["ufoz", "ufo"])
        if file:
            opened = OpenFont(file)
            opened = SFont(file)

            self.fonts[file] = (True, opened)
            
            self.w.af.close()
            # need to close the window first and then add item
            table = self.w.af.getItem("fontsTable")
            item = table.makeItem(
                use=True,
                name=os.path.basename(file)
            )
            table.appendItems([item])

    def addRemoveButtonRemoveCallback(self, sender):
        table = self.w.af.getItem("fontsTable")
        if len(table.selectedItems()) != 1:
            table.removeSelectedItems()

    def add_designspaceCallback(self, sender):
        self.build_designspace_sheet()
        self.w.dsp.open()

    def spacingCallback(self, sender):
        pass

    def kerningCallback(self, sender):
        pass

    def opentypeCallback(self, sender):
        pass

    def interpolateCallback(self, sender):
        pass

    def view_optionsCallback(self,sender):
        self.v.open()

    def edit_textCallback(self, sender):
        self.te.open()
        subwindow = self.te.getNSWindow().contentViewController().view().window()
        subwindow.makeFirstResponder_(self.te.getItem("textField").getNSTextField())

    def currentGlyphDidSetGlyph(self, info):
        self.textFieldCallback(None)

    def textFieldCallback(self, sender):
        self.unsubscribeFromGlyphs()
        self.glyphNames = self.te.getItemValue("textField")
        font = self.font
        holding = []
        for name in self.glyphNames:
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
        scale = pointSize / self.font.info.unitsPerEm
        lineHeight = self.font.info.unitsPerEm * lineHeight * scale
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
        self.displaySettingsButtonCallback(None)
        self.populateItems()

    def showBeamButtonCallback(self, sender):
        self.showBeam = self.v.getItemValue("showBeamButton")
        self.displaySettingsButtonCallback(None)
        self.populateItems()
        '''
        glyph1, glyph2
        glyph1.beamRightMargin + glyph2.beamLeftMargin 
        '''

    def showKerningButtonCallback(self, sender):
        self.showKerning = self.v.getItemValue("showKerningButton")
        self.displaySettingsButtonCallback(None)
        self.populateItems()

    def displaySettingsButtonCallback(self, sender):
        values = self.v.getItemValue("displaySettingsButton")
        self.showFill = 0 in values
        self.showStroke = 1 in values
        self.showPoints = 2 in values

        self.beamPosition = self.v.getItemValue("beamPositionSlider")
        self.showBeam   = self.v.getItemValue("showBeamButton")

        items = self.w.getItemValue("collectionView")
        for item in items:
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


    def parseItemName(self, name:str) -> str:
        if name:
            if "@" not in name:
                return None
            glyphName,fontPath = name.split("@")
            glyphName.strip(" ")
            fontPath.strip(" ")
            return (glyphName, fontPath)
        else:
            return None


    def populateItems(self, reload=False):
        # font = self.font
        # glyphs = self.glyphs\

        # print(dir(self.collectionView.merzDocumentViewClass))
        items = []

        for path,(use,font) in self.fonts.items():
            if use:
                
                if font.lib.get("descriptor") == "instance":
                    self.designspace.makeOneInfo(font.lib.get("location")).extractInfo(font.info)

                off = font.lib.get('com.typemytype.robofont.italicSlantOffset', 0)
                for index, glyph in enumerate(self.glyphs):
                    on_disk = True
                    if font.lib.get("descriptor") == "instance":
                        mathGlyph = self.designspace.makeOneGlyph(glyph, font.lib.get("location"), decomposeComponents=True)
                        if mathGlyph is not None:
                            glyph = internalFontClasses.createGlyphObject()
                            mathGlyph.extractGlyph(glyph)
                            on_disk = False
                    else:
                        glyph = font[glyph]

                    if not isinstance(glyph, RGlyph):
                        glyph = RGlyph(glyph)

                    # item = self.collectionView.makeItem(
                    #     name=f"{glyph.name}@{font.path}",
                    #     acceptsHit=True,
                    #     )

                    # print(font[glyph.name])
                    item = MerzCollectionViewRGlyphItem(
                        name=glyph.name,
                        acceptsHit=True,
                        glyph=glyph,
                        font=font,
                        index=index,
                        onDisk=on_disk,
                    )
                    # item.setWidth(glyph.width)
                    # item.setHeight(1000)
                    item.getCALayer().setGeometryFlipped_(True) # XXX Ugh. Yell at Tal about this.
                    glyphContainer = merz.Base()
                    item.appendLayer("glyphContainer", glyphContainer)


                    glyphContainer.appendBaseSublayer(
                        name="descriptorIndicator",
                        visible=True,
                    )
                    # self.glyphMap
                    
                    glyphContainer.appendBaseSublayer(
                        name="glyphMetrics",
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
                        # identifier=f"{glyph.name}@{font.path}"
                    )
                    # filled.setInfoValue("glyph", glyph.name)
                    # filled.setInfoValue("font", font.path)

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
                        item.setHeight(font.info.unitsPerEm)


                        glyphContainer = item.getLayer("glyphContainer")
                        glyphContainer.addTranslationTransformation(
                            value=(0, -font.info.descender),
                            name="descender"
                        )

                        icon = ""
                        if font.lib.get("descriptor") == "source":
                            icon = SOURCE_ICON
                        elif font.lib.get("descriptor") == "instance":
                            icon = INSTANCE_ICON

                        descriptorIndicatorLayer = glyphContainer.getSublayer("descriptorIndicator")
                        with descriptorIndicatorLayer.propertyGroup():
                            if item.index == 0:
                                descriptorIndicatorLayer.appendTextLineSublayer(
                                    text=icon,
                                    pointSize=8,
                                    position=(-100,0),
                                    fillColor=(0,0,1,1),
                                    horizontalAlignment="center",
                                )

                        glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")
                        # 
                        # 
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
                                        text=str(val),
                                        pointSize=7,
                                        position=(start[0],round(depth/2)),
                                        fillColor=(.2,.2,.2,1),
                                        horizontalAlignment=side,
                                        padding=(5,0),
                                        )
                                line = glyphMetricsLayer.appendLineSublayer(
                                    startPoint=start,
                                    endPoint=end,
                                    strokeWidth=1,
                                    strokeColor=(.2,.2,.2,1),
                                    strokeCap="round"
                                    )
                                line.addSkewTransformation(-getattr(font.info, "italicAngle", 0))
                            width = glyphMetricsLayer.appendTextLineSublayer(
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
                                position=(0,font.info.descender),
                                size=(glyph.width, abs(font.info.descender) + font.info.ascender),
                                fillColor=(0,1,0,.2),
                                # visible=True
                            )
                            selectionIndicatorLayer.addSublayerSkewTransformation((-font.info.italicAngle))
                            
                            if item in self.selectedItems:
                                selectionIndicatorLayer.setVisible(True)
                            else:
                                selectionIndicatorLayer.setVisible(False)
                        
                        glyphFillLayer = glyphContainer.getSublayer("glyphFill")
                        with glyphFillLayer.propertyGroup():
                            glyphFillLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                            glyphFillLayer.addTranslationTransformation((-font.lib.get("com.typemytype.robofont.italicSlantOffset", 0), 0), "translate")
                            glyphFillLayer.setVisible(self.showFill)
                        glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
                        with glyphStrokeLayer.propertyGroup():
                            glyphStrokeLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                            glyphStrokeLayer.addTranslationTransformation((-font.lib.get("com.typemytype.robofont.italicSlantOffset", 0), 0), "translate")
                            glyphStrokeLayer.setVisible(self.showStroke)
                        glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
                        glyphPointsLayer.clearSublayers()
                        onCurve = 3
                        with glyphPointsLayer.propertyGroup():
                            for contour in glyph.contours:
                                for point in contour.points:
                                    if point.type != "offcurve":
                                        imageSettings = dict(
                                            name="oval",
                                            size=(onCurve,onCurve),
                                            fillColor=(0, 0, 0, 1)
                                        )
                                        x = point.x
                                        y = point.y
                                        glyphPointsLayer.appendSymbolSublayer(
                                            position=(x-off, y),
                                            imageSettings=imageSettings,
                                        )
                            glyphPointsLayer.setVisible(self.showPoints)

                        beamIndicatorLayer = glyphContainer.getSublayer("beamIndicator")
                        beamIntersectSize = 120
                        with beamIndicatorLayer.propertyGroup():
                            try:
                                next_glyph = self.glyphs[index+1]
                            except IndexError:
                                next_glyph = None

                            right = glyph.getRayRightMargin(self.beamPosition, font.info.italicAngle) or 0
                            left = glyph.getRayLeftMargin(self.beamPosition, font.info.italicAngle) or 0

                            aa = font.info.italicAngle
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

                            if index == 0:
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

                                if font.lib.get("descriptor") == "instance":
                                    mathGlyph = self.designspace.makeOneGlyph(next_glyph, font.lib.get("location"), decomposeComponents=True)
                                    if mathGlyph is not None:
                                        glyph = internalFontClasses.createGlyphObject()
                                        mathGlyph.extractGlyph(glyph)
                                        next = RGlyph(glyph)
                                else:
                                    next = font[next_glyph]

                                other_left = next.getRayLeftMargin(self.beamPosition, font.info.italicAngle) or 0

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
                                # beamIndicatorLayer.appendOvalSublayer(
                                #     position=(glyph.width + left, self.beamPosition),
                                #     size=(beamIntersectSize,beamIntersectSize),
                                #     anchor=(.5,.5),
                                #     fillColor=(1,.2,0,1)
                                # )
                            beamIndicatorLayer.setVisible(self.showBeam)
                    if index+1 == len(self.glyphs):
                        if self.multiline:
                            item.setForceBreakAfter(True)
                        else:
                            item.setForceBreakAfter(False)
                    items.append(item)

        self.collectionView.set(items)


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
            factor = 0.9
        else:
            factor = 1.1
            
        pointSize *= factor
        scale = pointSize / self.font.info.unitsPerEm
        lineHeight = self.font.info.unitsPerEm * lineHeight * scale

        self.te.setItemValue("pointSizeField", pointSize)
        self.collectionView.setLayoutProperties(
            scale=scale,
            lineHeight=lineHeight
        )
        # self.populateItems()


    def destroy(self):
        setExtensionDefault(EXTENSION_KEY + ".main_prefs", self.w.getItemValues())
        setExtensionDefault(EXTENSION_KEY + ".view_prefs", self.v.getItemValues())
        input_dict = self.te.getItemValues()
        input_dict['textField'] = ''.join([chr(n2u(glyph)) for glyph in input_dict['textField']])
        setExtensionDefault(EXTENSION_KEY + ".input_prefs", input_dict)

        # unregisterCurrentGlyphSubscriber(self)

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
                    OpenGlyphWindow(selectedGlyph)
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

        for temp_item in self.collectionView.get():
            layer = temp_item.getLayer("glyphContainer").getSublayer("glyphFill")
            if temp_item.font == selectedFont:
                layer.setFillColor((*self.selectionColor[0:3],.5))
                layer.setStrokeColor(self.selectionColor)
                layer.setStrokeWidth(1)
                temp_item.selected = False
            else:
                layer.setFillColor(self.foreground)
                layer.setStrokeColor(None)
                layer.setStrokeWidth(None)
            


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

        # self.marqueeLayer.setPosition(p)
        # self.marqueeLayer.setSize(s)

        # pos = marquee.getPosition()
        # sz = marquee.getSize()
        # x,y,w,h = pos[0],pos[1],sz[0],sz[1]


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

    def mouseMoved(self, view, event):
        pass
        # print("debug::mouseMoved")

    def mouseUp(self, view, event):
        # pass
        self.marqueeLayer.clearSublayers()
        # print("debug::mouseUp")

    def subscribeToGlyphs(self):
        glyphs = []
        for font in self.fonts:
            ff = [f for f in AllFonts() if font == f.path][0]
            glyphs.extend(list(set([ff[glyph] for glyph in self.glyphs])))
        self.setAdjunctObjectsToObserve(glyphs)

    def unsubscribeFromGlyphs(self):
        self.clearObservedAdjunctObjects()

    def adjunctGlyphDidChangeMetrics(self, info):
        self.populateItems(reload=True)

    def adjunctGlyphDidChangeOutline(self, info):
        self.populateItems(reload=True)


#registerCurrentGlyphSubscriber(Spaceport)
if __name__ == "__main__":
    Spaceport()


