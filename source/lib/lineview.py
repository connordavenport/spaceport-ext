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

BOTTOM_BAR = 28
BUTTON_HEIGHT = 25

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

def symbolImage(symbolName, color, flipped=False, pointSize=18.0, weight="light", scale="medium"):
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
            scale = scales.get(scale, AppKit.NSImageSymbolScaleMedium)

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
            weight = weights.get(weight, AppKit.NSFontWeightRegular)

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
                # dict(
                #     identifier="show_metrics",
                #     image=symbolImage(symbolName=SHOW_METRICS, color=(1,1,1,1), weight="regular"),
                #     text="Show Metrics",
                #     template=True,
                # ),
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

                # dict(
                #     identifier="invert_colors",
                #     image=symbolImage(symbolName="swirl.circle.righthalf.filled.inverse", color=(1,1,1,1), weight="regular"),
                #     text="invert colors",
                #     template=True,
                # ),
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
        self.w.getItem("collectionView").setBackgroundColor(AppKit.NSColor.whiteColor())

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
        self.te.setItemValue("textField", "Spaceport 123")
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
        collectionView = self.w.getItem("collectionView")
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
        collectionView.setLayoutProperties(
            scale=scale,
            lineHeight=lineHeight,
            alignment=alignment,
            inset=(inset, inset)
        )

    def invertColorsButtonCallback(self, sender):
        self.invert = self.v.getItemValue("invertColorsButton")
        foreground_color = [(0,0,0,1), (1,1,1,1)][self.invert]
        background_color = [AppKit.NSColor.whiteColor(), AppKit.NSColor.blackColor()][self.invert]

        self.w.getItem("collectionView").setBackgroundColor(background_color)
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


    def populateItems(self):
        collectionView = self.w.getItem("collectionView")
        font = self.font
        glyphs = self.glyphs
        items = []
        for glyph in self.glyphs:
            item = collectionView.makeItem()
            item.getCALayer().setGeometryFlipped_(True) # XXX Ugh. Yell at Tal about this.
            glyphContainer = merz.Base()
            item.appendLayer("glyphContainer", glyphContainer)

            # self.glyphMap
            
            glyphContainer.appendBaseSublayer(
                name="glyphMetrics",
                visible=True,
                acceptsHit=False,
            )
            filled = glyphContainer.appendPathSublayer(
                name="glyphFill",
                fillColor=self.foreground,
                visible=True,
                acceptsHit=True,
                # identifier=f"{glyph.name}@{font.path}"
            )
            filled.setInfoValue("glyph", glyph.name)
            filled.setInfoValue("font", font.path)

            glyphContainer.appendPathSublayer(
                name="glyphStroke",
                fillColor=None,
                strokeColor=self.foreground,
                strokeWidth=1,
                visible=True,
                acceptsHit=False,
            )
            glyphContainer.appendBaseSublayer(
                name="glyphPoints",
                visible=True,
                acceptsHit=False,
            )
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
                                imageSettings = dict(
                                    name="oval",
                                    size=(onCurve/2,onCurve/2),
                                    fillColor=(0, 0, 0, 1),
                                )
                            elif point.type == "curve":
                                imageSettings = dict(
                                    name="oval",
                                    size=(onCurve,onCurve),
                                    fillColor=(0, 0, 0, 1)
                                )
                            elif point.type == "qcurve":
                                imageSettings = dict(
                                    name="star",
                                    size=(onCurve,onCurve),
                                    fillColor=(0, 0, 0, 1),
                                    pointCount=8,
                                    inner=0.2,
                                    # outer=1.0
                                )
                            else:
                                # line, move
                                imageSettings = dict(
                                    name="rectangle",
                                    size=(onCurve,onCurve),
                                    fillColor=(0, 0, 0, 1)
                                )
                            x = point.x
                            y = point.y
                            glyphPointsLayer.appendSymbolSublayer(
                                position=(x, y),
                                imageSettings=imageSettings,
                                acceptsHits=False,
                            )
                    glyphPointsLayer.setVisible(self.showPoints)
            items.append(item)
        collectionView.set(items)


    def acceptsFirstResponder(self, sender):
        # necessary for accepting mouse events
        return True

    def acceptsMouseMoved(self, sender):
        # necessary for tracking mouse movement
        return True

    def magnifyWithEvent(self, sender, event):

        collectionView = self.w.getItem("collectionView")
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
        collectionView.setLayoutProperties(
            scale=scale,
            lineHeight=lineHeight
        )

        # self.populateItems()


    def destroy(self):
        # unregisterCurrentGlyphSubscriber(self)
        pass
        # print("debug::destroy")


    def mouseDown(self, view, event):
        container = self.w.getItem("collectionView").getMerzContainer()
        event = merz.unpackEvent(event)
        location = event["location"]
        location = self.w.getItem("collectionView").convertWindowCoordinateToViewCoordinate(
            point=location
        )
        point = container.convertViewCoordinateToLayerCoordinate(
            location,
            container
        )
        
        hits = container.findSublayersContainingPoint(
            point,
            onlyAcceptsHit=True,
            recurse=True
        )
        
        if hits:
            for hit in hits:
                glyph = hit.getInfoValue("glyph", None)
                if glyph:
                    hit.setStrokeWidth(2)
                    hit.setStrokeColor((1,0,0,1))
            
        
    def mouseMoved(self, view, event):
        pass
        # print("debug::mouseMoved")

    def mouseDragged(self, view, event):
        pass
        # print("debug::mouseDragged")

    def mouseUp(self, view, event):
        pass
        # print("debug::mouseUp")

    def subscribeToGlyphs(self):
        self.setAdjunctObjectsToObserve(set(self.glyphs))

    def unsubscribeFromGlyphs(self):
        self.clearObservedAdjunctObjects()

    def adjunctGlyphDidChangeMetrics(self, info):
        self.populateItems()

    def adjunctGlyphDidChangeOutline(self, info):
        self.populateItems()


registerCurrentGlyphSubscriber(Spaceport)

