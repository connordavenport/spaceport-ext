import ezui  # ty:ignore[unresolved-import]
from typing import Any
import constants as defaults
from mojo.events import postEvent  # ty:ignore[unresolved-import]
from mojo.extensions import getExtensionDefault, setExtensionDefault  # noqa: F401  # ty:ignore[unresolved-import]
from AppKit import NSColor

class SpacePortSettingsController(ezui.WindowController):
    
    def loadDefaults(self) -> None:

        self.tintedBackground: bool = getExtensionDefault( defaults.EXTENSION_KEY + ".tintedBackground", defaults.TINTED_BACKGROUND)
        self.cursorBlinking: bool = getExtensionDefault( defaults.EXTENSION_KEY + ".cursorBlinking", defaults.CURSOR_BLINKING)
        self.cursorColor: tuple[float, float, float, float] = getExtensionDefault( defaults.EXTENSION_KEY + ".cursorColor", defaults.CURSOR_COLOR)
        self.selectionColor: tuple[float, float, float, float] = getExtensionDefault( defaults.EXTENSION_KEY + ".selectionColor", defaults.CURSOR_COLOR)
        self.paddingMultiplier: float = getExtensionDefault( defaults.EXTENSION_KEY + ".paddingMultiplier", defaults.PADDING_MULTIPLIER)


    def build(self) -> None:

        self.loadDefaults()

        content = """
        [ ] Blinking Cursor                 @cursorBlinkingButton     ? Use Blinking Cursor
        * HorizontalStack                   @cursorStack                                 
        > Cursor Color: 
        > * ColorWell                       @cursorColorWell          ? Cursor Color
        -------
         [ ] Tinted Typing Background       @tintedBackgroundButton   ? Use Tinted Background in Typing View
        -------
        * HorizontalStack                   @selectionStack
        > Selection Color: 
        > * ColorWell                       @selectionColorWell       ? Glyph Selection Color
        -------
        * HorizontalStack
        > Top Padding:                         
        > ---X--- [__](±)                   @paddingInputField        ? Top Padding Offset (Relative Scaler)
        """

        descriptionData = dict(
           cursorStack=dict(
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
        )

        self.w = ezui.EZWindow(
            size=(400, 100),
            title=f"{defaults.EXTENSION_NAME} Settings",
            content=content,
            descriptionData=descriptionData,
            controller=self,
        )
        ns = self.w.getItem("paddingInputField")._textField.getNSTextField()
        ns.setBordered_(False)
        ns.setBackgroundColor_(NSColor.clearColor())
        ns.setFocusRingType_(1)
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

    def paddingInputFieldCallback(self, sender: Any) -> None:
        postEvent(defaults.EVENT_KEY, name="paddingMultiplier", value=sender.get())


if __name__ == "__main__":
    SpacePortSettingsController()
