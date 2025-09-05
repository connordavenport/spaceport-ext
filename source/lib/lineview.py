import AppKit
import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController
from lib.UI.spaceCenter.glyphSequenceEditText import splitText,\
    currentGlyphKey, currentSelectionKey, newLineKey, groupsKey
from mojo.canvas import CanvasGroup
from mojo import drawingTools as ctx
from mojo import events
from mojo.UI import *
from fontParts.world import CurrentGlyph, CurrentLayer, CurrentFont
from mojo.roboFont import OpenWindow
import ezui
import merz
from mojo.subscriber import Subscriber, registerCurrentGlyphSubscriber, unregisterCurrentGlyphSubscriber
from vanilla.vanillaBase import osVersionCurrent, osVersion12_0


# ---------
# Interface
# ---------
AXES = [
        "Weight",
        "Width",
        "Slant"
       ]


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

        self.foreground = (0,0,0,1)
        self.background = (1,1,1,1)

        self.font = CurrentFont()

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
            # size=(100,100),
            content=content,
            descriptionData=descriptionData,
            parent=self.w,
            behavior="transient",
            parentAlignment="right",
            controller=self
        )

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


        self.controlsStackCallback(None)
        self.displaySettingsButtonCallback(None)
        self.showMetricsButtonCallback(None)
        self.textFieldCallback(None)

    def started(self):
        self.w.open()

    def add_fontCallback(self, sender):
        pass

    def add_designspaceCallback(self, sender):
        pass

    def spacingCallback(self, sender):
        pass

    def kerningCallback(self, sender):
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
                holding.append(font[name])

            elif name == CURRENTGLYPH_CHAR:
                if CurrentGlyph() is not None:
                    holding.append(font[CurrentGlyph().name])

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
                #symbol.setBackgroundColor(foreground_color)
                location = symbol.getPosition()
                settings = symbol.getImageSettings()
                settings["fillColor"] = foreground_color
                symbol.setImageSettings(settings)
            # glyphPointsLayer.setFillColor(foreground_color)
            glyphPointsLayer.setVisible(self.showPoints)

        self.foreground = foreground_color
        self.background = background_color

    def showMetricsButtonCallback(self, sender):
        self.showMetrics = self.v.getItemValue("showMetricsButton")
        self.displaySettingsButtonCallback(None)

    def displaySettingsButtonCallback(self, sender):
        values = self.v.getItemValue("displaySettingsButton")
        self.showFill = 0 in values
        self.showStroke = 1 in values
        self.showPoints = 2 in values

        items = self.w.getItemValue("collectionView")
        for item in items:
            glyphContainer = item.getLayer("glyphContainer")

            glyphMetricsLayer = glyphContainer.getSublayer("glyphMetrics")
            glyphMetricsLayer.setVisible(self.showMetrics)

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
        font = self.font
        glyphs = self.glyphs
        items = []
        for glyph in self.glyphs:
            item = self.collectionView.makeItem(
                name=f"{glyph.name}@{font.path}",
                acceptsHit=True,
                )
            # item.setWidth(glyph.width)
            # item.setHeight(1000)
            item.getCALayer().setGeometryFlipped_(True) # XXX Ugh. Yell at Tal about this.
            glyphContainer = merz.Base()
            item.appendLayer("glyphContainer", glyphContainer)

            # self.glyphMap
            
            glyphContainer.appendBaseSublayer(
                name="glyphMetrics",
                visible=True,
            )
            filled = glyphContainer.appendPathSublayer(
                name="glyphFill",
                fillColor=self.foreground,
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
                position=(0,self.font.info.descender),
                size=(glyph.width, abs(self.font.info.descender) + self.font.info.ascender),
                cornerRadius=10,
                backgroundColor=(0,1,0,.2),
                visible=True
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

                        val = getattr(glyph, f"{side}Margin")
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
                            )
                    width = glyphMetricsLayer.appendTextLineSublayer(
                        text=str(glyph.width),
                        pointSize=7,
                        position=(round(glyph.width/2),round(depth/2)),
                        fillColor=(.2,.2,.2,1),
                        horizontalAlignment="center",
                        padding=(0,7),
                        )
                    glyphMetricsLayer.setVisible(self.showMetrics)


                selectionIndicatorLayer = glyphContainer.getSublayer("selectionIndicator")
                with selectionIndicatorLayer.propertyGroup():
                    if item in self.selectedItems:
                        selectionIndicatorLayer.setVisible(True)
                    else:
                        selectionIndicatorLayer.setVisible(False)
                
                glyphFillLayer = glyphContainer.getSublayer("glyphFill")
                with glyphFillLayer.propertyGroup():
                    glyphFillLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                    glyphFillLayer.setVisible(self.showFill)
                glyphStrokeLayer = glyphContainer.getSublayer("glyphStroke")
                with glyphStrokeLayer.propertyGroup():
                    glyphStrokeLayer.setPath(glyph.getRepresentation("merz.CGPath"))
                    glyphStrokeLayer.setVisible(self.showStroke)
                glyphPointsLayer = glyphContainer.getSublayer("glyphPoints")
                glyphPointsLayer.clearSublayers()
                onCurve = 3
                with glyphPointsLayer.propertyGroup():
                    for contour in glyph.contours:
                        for point in contour.points:
                            if point.type == "offcurve":
                                pass
                            else:
                                imageSettings = dict(
                                    name="oval",
                                    size=(onCurve,onCurve),
                                    fillColor=(0, 0, 0, 1)
                                )
                            x = point.x
                            y = point.y
                            glyphPointsLayer.appendSymbolSublayer(
                                position=(x, y),
                                imageSettings=imageSettings,
                                # acceptsHits=False,
                            )
                    glyphPointsLayer.setVisible(self.showPoints)
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
        pass
        # unregisterCurrentGlyphSubscriber(self)


    def _getItemAtEvent(self, position:tuple=(0,0)) -> merz.collectionView.MerzCollectionViewItem:
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
        self.container = self.container
        location = self.collectionView.getMerzView().convertWindowCoordinateToViewCoordinate(
            point=location
        )
        x, y = self.container.convertViewCoordinateToLayerCoordinate(
            location,
            self.container
        )
        return (x,y)


    def getFontFromPath(self, path:str) -> RFont:
        for f in AllFonts():
            if path == f.path:
                return f

    def getGlyphFromItem(self, item:merz.collectionView.MerzCollectionViewItem):
        parsed = self.parseItemName(item.getName())
        if parsed:
            glyphName, fontPath = parsed
            font = self.getFontFromPath(fontPath)
            return font[glyphName]


    def mouseDown(self,view,event):
        event = merz.unpackEvent(event)
        self.start = (x,y) = self._convertLocation(event)
        self.marqueeLayer.clearSublayers()
        hit = self._getItemAtEvent((x,y))
        selection = []

        selectedGlyph = None

        for temp_item in self.collectionView.get():
            if temp_item not in self.selectedItems:
                self.set_item_selection_status(temp_item,False)

        if hit:
            clickCount = event["clickCount"]
            parsed = self.parseItemName(hit.getName())
            if parsed:
                self.set_item_selection_status(hit,True)
                selectedGlyph = self.getGlyphFromItem(hit)

            if selectedGlyph:
                if AppKit.NSEvent.modifierFlags() & AppKit.NSShiftKeyMask:
                    # print("shift down, append")
                    self.selectedItems.append(hit)
                else:
                    # print("no mod, use only this")
                    self.selectedItems = [hit]
                    for temp_item in self.collectionView.get():
                        if temp_item not in self.selectedItems:
                            self.set_item_selection_status(temp_item,False)

                if clickCount == 2:
                    OpenGlyphWindow(ff[gn])
            else:
                # print("clearing selection")
                self.selectedItems = []
        else:
            # print("clearing selection")
            self.selectedItems = []

        if not self.selectedItems:
            for temp_item in self.collectionView.get():
                self.set_item_selection_status(temp_item,False)


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

                self.set_item_selection_status(item,True)

                glyph = self.getGlyphFromItem(item)
                                            
                if char in directions:
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

        # for item in self.selectedItems:
        #     self.set_item_selection_status(item,True)


    def set_item_selection_status(self, collection_item:merz.collectionView.MerzCollectionViewItem, bool=True):
        collection_item.getLayer("glyphContainer").getSublayer("selectionIndicator").setVisible(bool)

    def mouseMoved(self, view, event):
        pass
        # print("debug::mouseMoved")

    def mouseUp(self, view, event):
        # pass
        self.marqueeLayer.clearSublayers()
        # print("debug::mouseUp")

    def subscribeToGlyphs(self):
        self.setAdjunctObjectsToObserve(set(self.glyphs))

    def unsubscribeFromGlyphs(self):
        self.clearObservedAdjunctObjects()

    def adjunctGlyphDidChangeMetrics(self, info):
        self.populateItems(reload=True)

    def adjunctGlyphDidChangeOutline(self, info):
        self.populateItems(reload=True)


registerCurrentGlyphSubscriber(Spaceport)

