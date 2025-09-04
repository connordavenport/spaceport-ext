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


PLUS = "plus"
ADD_DESIGNSPACE = "grid"
SPACING = "space"
KERNING = "arrowtriangle.right.and.line.vertical.and.arrowtriangle.left"
INTERPOLATE = "squareshape.split.2x2.dotted"

SETTINGS_CONTENT = """
*VerticalStack            @settings
> Toolbar Alignment:
> *VerticalStack          @controls
>> *HorizontalStack       @up_stack
>>> ({chevron.up})        @align_top_button
>> *HorizontalStack       @side_stack
>>>  ({chevron.left})     @align_left_button
>>>  ({chevron.right})    @align_right_button
>> *HorizontalStack       @down_stack
>>>  ({chevron.down})     @align_bottom_button
"""

CONTENT = """
* _REPLACE_Stack                        @stack
> ({xmark})                             @close_button
> -----
> ({move.3d})                           @designspace_button
> -----
> ({plus})                              @add_button  
> ({minus})                             @remove_button  
> ({square.and.arrow.down.on.square})   @load_button         
> ({arrow.up.arrow.down})               @reorder_button
> ({arrow.up.and.down.text.horizontal}) @one_line_button
> ({gearshape})                         @settings_button
"""

class Spaceport(ezui.WindowController):
        
    def build(self, posSize=None):

        self.alignment = "left"
        
        self.parent = CurrentSpaceCenterWindow()
        self.parentWindow = self.parent.window()


        x,y,w,h = self.parentWindow.getPosSize()

        if posSize is None:
            posSize = (x, y, 10, h+BOTTOM_BAR)
        
        self.rebuild(posSize=posSize, alignment="left")
        self.w.bind("close", self.windowCloseCallback)



    def rebuild(self, **kwargs):
        posSize = kwargs.get("posSize", (0,0,10,10))
        x,y,w,h = posSize
        alignment = kwargs.get("alignment", "left")

        stack = "Horizontal"
        distribution_type="auto"
        if alignment in ["left", "right"]:
            stack = "Vertical"
            # distribution_type = "equalSpacing"


        description_data = dict(
            stack=dict(
                alignment="center",
                distribution=distribution_type
            ),
            close_button = dict(
                # toolTip="close window",
                height=40,
            ),
            designspace_button = dict(
                # toolTip="navigate designspace",
                height=40,
            ),
            add_button = dict(
                # toolTip="add font",
                height=BUTTON_HEIGHT,
            ),  
            remove_button = dict(
                # toolTip="remove font",
                height=BUTTON_HEIGHT,
            ),  
            load_button = dict(
                # toolTip="import designspace",
                height=BUTTON_HEIGHT,
            ),  
            reorder_button = dict(
                # toolTip="reorder fonts",
                height=BUTTON_HEIGHT,
            ),
            one_line_button = dict(
                # toolTip="one line layout",
                height=BUTTON_HEIGHT,
            ),
            settings_button = dict(
                # toolTip="settings",
                height=BUTTON_HEIGHT,
            ),
        )

        self.w = ezui.EZPanel(
            size=(w,h),
            content=CONTENT.replace("_REPLACE_", stack),
            title="center of spacing",
            descriptionData=description_data,
            controller=self,
            # miniaturizable=False,
        )
        self.parentWindow.bind("resize", self.windowResized)

        settings_descriptionData = dict(
            settings = dict(
                distribution="equalCentering"
            ),
            controls = dict(
                distribution="equalCentering",
                width = 60,
            ),
            up_stack = dict(
                distribution="equalCentering"
            ),
            side_stack = dict(
                distribution="equalCentering"
            ),
            down_stack = dict(
                distribution="equalCentering"
            ),
            align_left_button = dict(
                height=10,
                width=20,
            ),
            align_right_button = dict(
                height=10,
                width=20,
            ),
            align_top_button = dict(
                height=10,
                width=20,
            ),
            align_bottom_button = dict(
                height=10,
                width=20,
            ),
        )
        self.settings_popover = ezui.EZPopover(
            size=(100,100),
            content=SETTINGS_CONTENT,
            descriptionData=settings_descriptionData,
            parent=self.w,
            behavior="semitransient",
            # parentAlignment="left",
            controller=self
        )

        self.nsWindow = self.w.getNSWindow()
        self.nsWindow.setTitlebarAppearsTransparent_(True)
        self.nsWindow.setTitleVisibility_(AppKit.NSWindowTitleHidden)
        self.nsWindow.setHasShadow_(False)

        mask = self.nsWindow.styleMask()
        mask = AppKit.NSTitledWindowMask | AppKit.NSWindowStyleMaskFullSizeContentView
        self.nsWindow.setStyleMask_(mask)
        self.nsWindow.setMovable_(False)

        self.w.open()

        self.wd = self.w.getPosSize()[2]

        self.nsWindow.setFrameOrigin_((x-self.w.getPosSize()[2], self.parentWindow.getNSWindow().frameOrigin().y))
        self.parentWindow.getNSWindow().addChildWindow_ordered_(self.nsWindow, AppKit.NSWindowAbove)
        


    def designspace_buttonCallback(self, sender):
        # self.ds_pop.open()
        DesignspaceExplorerController(self.w)


    def align_left_buttonCallback(self, sender):
        self.w.close()
        self.alignment = "left"
        self.rebuild(alignment=self.alignment)
        # self.w.open()
        self.windowResized(None)

    def align_right_buttonCallback(self, sender):
        self.w.close()
        self.alignment = "right"
        self.rebuild(alignment=self.alignment)
        # self.w.open()
        self.windowResized(None)

    def align_top_buttonCallback(self, sender):
        self.w.close()
        self.alignment = "top"
        self.rebuild(alignment=self.alignment)
        # self.w.open()
        self.windowResized(None)

    def align_bottom_buttonCallback(self, sender):
        self.w.close()
        self.alignment = "bottom"
        self.rebuild(alignment=self.alignment)
        # self.w.open()
        self.windowResized(None)

    def settings_buttonCallback(self, sender):
        self.settings_popover.open()

    def close_buttonCallback(self, sender):
        self.w.close()

    def windowCloseCallback(self, sender):
        # events.removeObserver(self, "currentGlyphChanged")
        self.parentWindow.unbind("resize", self.windowResized)
        # self.endGlyphObservation()

    def windowResized(self, sender):
        if hasattr(self, "w"):
            xx,yy,ww,hh = self.parentWindow.getPosSize()
            y = self.parentWindow.getNSWindow().frameOrigin().y
            if self.alignment in "left right".split(" "):
                w,h = (10, hh)
                x = xx - self.wd
                if self.alignment == "right": x = (ww + xx)
                h += BOTTOM_BAR

            else:
                w,h = (0, 10)
                x = xx
                if self.alignment == "top":
                    y = (hh + y) + 88
                else:
                    y -= 10
                # y += BOTTOM_BAR


            self.w.setPosSize((1,1,w,h), animate=False)
            self.w.getNSWindow().setFrameOrigin_((x, y))


class DesignspaceExplorerController(ezui.WindowController):

    debug = True
    fillColor = (1, 0, 0, .25)
    brushRadius = 40

    def build(self, parent):
        content = """
        *VerticalStack

        > *HorizontalStack @axis_controls

        >> 􀄾 X-Axis       @x_axis_text
        >> (X ...)         @x_axis_button

        >> 􀑹 Y-Axis        @y_axis_text
        >> (Y ...)         @y_axis_button

        > * MerzView    @merz_view
        """

        descriptionData = dict(
            axis_controls=dict(
                distribution="equalSpacing"
            ),
            x_axis_button=dict(
                items=AXES,
                selected=0,
            ),
            y_axis_button=dict(
                items=AXES,
                selected=1,

            ),
            merz_view=dict(
                backgroundColor=(1, 1, 1, 1),
                delegate=self
            )
        )

        self.mouse_offset = 30
        self.w = ezui.EZPopover(
            content=content,
            parent=parent,
            descriptionData=descriptionData,
            size=(500, 500),
            controller=self,
            parentAlignment="left",
        )

        container = self.w.getItem("merz_view").getMerzContainer()
        self.pointerLayer = container.appendOvalSublayer(
            position=(0, 0),
            anchor=(.5, .5),
            size=(10,10),
            strokeColor=(0,0,0,.2),
            strokeWidth=2,
            fillColor=(0,0,0,.2)
        )
        self.brushLayer = container.appendBaseSublayer()


        font = AppKit.NSFont.monospacedSystemFontOfSize_weight_(12.0, 0)
        for item in self.w.getItems():
            ii = self.w.getItem(item)
            if isinstance(ii, ezui.items.label.Label):
                ii.getNSTextField().setFont_(font)


    def started(self):
        self.w.open()

    def acceptsFirstResponder(self, sender):
        # necessary for accepting mouse events
        return True

    def acceptsMouseMoved(self, sender):
        # necessary for tracking mouse movement
        return True

    def destroy(self):
        container = self.w.getItem("merz_view").getMerzContainer()
        container.clearSublayers()

    def mouseMoved(self, view, event):
        x, y = event.locationInWindow()
        self.pointerLayer.setPosition((x-self.mouse_offset, y-self.mouse_offset))

    def mouseDragged(self, view, event):
        x, y = event.locationInWindow()
        self.brushLayer.clearSublayers()
        self.pointerLayer.setStrokeColor((0,0,0,1))
        self.pointerLayer.setPosition((x-self.mouse_offset, y-self.mouse_offset))

        self.brushLayer.appendLineSublayer(
           startPoint=(0, y-self.mouse_offset),
           endPoint=(500, y-self.mouse_offset),
           strokeWidth=2,
           strokeColor=(0, 0, 0, .1)
        )
        self.brushLayer.appendLineSublayer(
           startPoint=(x-self.mouse_offset, 0),
           endPoint=(x-self.mouse_offset, 500),
           strokeWidth=2,
           strokeColor=(0, 0, 0, .1)
        )

        self.w.getItem("x_axis_text").set(f"􀄾 X-Axis {(round(x)):4}")
        self.w.getItem("y_axis_text").set(f"􀑹 Y-Axis {(round(y)):4}")

    def mouseUp(self, view, event):
        self.pointerLayer.setStrokeColor((0,0,0,.2))
        self.brushLayer.clearSublayers()


if __name__ == "__main__":
    Spaceport()



