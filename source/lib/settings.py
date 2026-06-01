import ezui  # ty:ignore[unresolved-import]
from typing import Any
import constants as defaults
from mojo.events import postEvent  # ty:ignore[unresolved-import]
from mojo.extensions import getExtensionDefault, setExtensionDefault  # noqa: F401  # ty:ignore[unresolved-import]
from AppKit import NSColor, NSApp

class SpacePortSettingsController(ezui.WindowController):
    
    def loadDefaults(self) -> None:

        self.tintedBackground: bool = getExtensionDefault( defaults.EXTENSION_KEY + ".tintedBackground", defaults.TINTED_BACKGROUND)
        self.cursorBlinking: bool = getExtensionDefault( defaults.EXTENSION_KEY + ".cursorBlinking", defaults.CURSOR_BLINKING)
        self.cursorColor: tuple[float, float, float, float] = getExtensionDefault( defaults.EXTENSION_KEY + ".cursorColor", defaults.CURSOR_COLOR)
        self.selectionColor: tuple[float, float, float, float] = getExtensionDefault( defaults.EXTENSION_KEY + ".selectionColor", defaults.SELECTION_COLOR)
        self.paddingMultiplier: float = getExtensionDefault( defaults.EXTENSION_KEY + ".paddingMultiplier", defaults.PADDING_MULTIPLIER)
        self.glyphTextShortcut: str = getExtensionDefault( defaults.EXTENSION_KEY + ".glyphTextShortcut", defaults.GLYPH_TEXT_SHORTCUT)
        self.textTextShortcut: str = getExtensionDefault( defaults.EXTENSION_KEY + ".textTextShortcut", defaults.TEXT_TEXT_SHORTCUT)

    def build(self) -> None:

        self.loadDefaults()

        content = f"""
        [ ] Blinking Cursor                 @cursorBlinkingButton     ? Use Blinking Cursor
        * HorizontalStack                   @cursorStack                                 
        > Cursor Color: 
        > * ColorWell                       @cursorColorWell          ? Cursor Color
        -------
        [ ] Tinted Typing Background        @tintedBackgroundButton   ? Use Tinted Background in Typing View
        -------
        * HorizontalStack                   @selectionStack
        > Selection Color: 
        > * ColorWell                       @selectionColorWell       ? Glyph Selection Color
        -------
        Add Glyph Keys: ⌘ + [_ {self.glyphTextShortcut} _]         @glyphTextField           ? Add Glyph Shortcut
        Sample Text Keys: ⌘ + [_ {self.textTextShortcut} _]        @textTextField            ? Sample Text Shortcut    

        # * Box                               @warningBox = VerticalStack
        # > * HorizontalStack                 @warningStack
        # >> * Image                          @warningImage
        # > (Revert Settings)                 @revertButton             ? Revert Extension Settings to Default, Please Restart Spaceport
        """

        descriptionData = dict(
           cursorStack=dict(
                distribution="fillEqually",
                alignment="leading",
            ),
            shortcutsStack=dict(
                distribution="fillEqually",
                alignment="leading",
            ),
            selectionStack=dict(
                distribution="fillEqually",
                alignment="leading",
            ),
            cursorBlinkingButton=dict(
                value=self.cursorBlinking
            ),
            tintedBackgroundButton=dict(
                value=self.tintedBackground,
            ),
            cursorColorWell=dict(
                color=self.cursorColor,
                height=20,
                width=80,
            ),
            selectionColorWell=dict(
                color=self.selectionColor,
                height=20,
                width=80,
            ),
            paddingInputField=dict(
                sizeStyle="small",
                valueType="integer",
                minValue=1,
                value=self.paddingMultiplier,
                maxValue=10,
                # width=90,
            ),
            warningStack=dict(
                distribution="fill",
                alignment="leading",
                margins=(30, 30)
            ),
            warningImage=dict(
                image=ezui.makeImage(
                    symbolName="exclamationmark.triangle",
                ),
                symbolConfiguration=dict(
                    scale="large",
                    renderingMode="palette",
                    colors=[(1,0,0,1)]
                ),
            ),

            revertButton=dict(
                width=200,
            ),
            warningBox=dict(
                backgroundColor=(1,0,0,.2),
                borderColor=(1,0,0,1),
                cornerRadius=10,
            ),
        )

        self.w = ezui.EZWindow(
            size=(400, 100),
            title=f"{defaults.EXTENSION_NAME} Settings",
            content=content,
            descriptionData=descriptionData,
            controller=self,
        )
        # ns = self.w.getItem("paddingInputField")._textField.getNSTextField()
        # ns.setBordered_(False)
        # ns.setBackgroundColor_(NSColor.clearColor())
        # ns.setFocusRingType_(1)
        self.w.getNSWindow().setInitialFirstResponder_(self.w.getItem("cursorStack").getNSStackView())


    def started(self) -> None:
        self.w.open()
        
    def tintedBackgroundButtonCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="tintedBackground", value=sender.get())

    def cursorBlinkingButtonCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="cursorBlinking", value=bool(sender.get()))

    def cursorColorWellCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="cursorColor", value=sender.get())

    def selectionColorWellCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="selectionColor", value=sender.get())

    def glyphTextFieldCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="glyphTextShortcut", value=sender.get())

    def textTextFieldCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="textTextShortcut", value=sender.get())


    # def paddingInputFieldCallback(self, sender: Any) -> None:
    #     postEvent(defaults.EVENT_KEY, name="paddingMultiplier", value=sender.get())

    def revertButtonCallback(self, sender) -> None:
        extDefs = NSApp().extensionDefaults()
        for key in list(extDefs):
            if key.startswith(defaults.EXTENSION_KEY):
                del extDefs[key]
        
        self.w.setItemValue("cursorBlinkingButton", defaults.CURSOR_BLINKING)   
        self.w.setItemValue("cursorColorWell", defaults.CURSOR_COLOR)        
        self.w.setItemValue("tintedBackgroundButton", defaults.TINTED_BACKGROUND) 
        self.w.setItemValue("selectionColorWell", defaults.SELECTION_COLOR)     
        self.w.setItemValue("glyphTextField", defaults.GLYPH_TEXT_SHORTCUT)
        self.w.setItemValue("textTextField", defaults.TEXT_TEXT_SHORTCUT)
        # self.w.setItemValue("paddingInputField", defaults.PADDING_MULTIPLIER)      



if __name__ == "__main__":
    SpacePortSettingsController()
