import ezui  # ty:ignore[unresolved-import]
from typing import Any
import constants
from mojo.events import postEvent  # ty:ignore[unresolved-import]
from mojo.extensions import getExtensionDefault, setExtensionDefault  # noqa: F401  # ty:ignore[unresolved-import]
from AppKit import NSColor

class SpacePortSettingsController(ezui.WindowController):
    
    def build(self) -> None:

        self.detached = False
        content = """
        [ ] Blinking Cursor                @blinkingCursorButton     ? Use Blinking Cursor
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
            blinkingCursorButton=dict(
                value=False
            ),
            tintedBackgroundButton=dict(
                value=True,
            ),
            cursorStack=dict(
                distribution="fillEqually",
                alignment="leading",
            ),
            selectionStack=dict(
                distribution="fillEqually",
                alignment="leading",
            ),
            cursorColorWell=dict(
                color=constants.CURSOR_COLOR,
                height=20,
                width=80,
            ),
            selectionColorWell=dict(
                color=constants.SELECTION_COLOR,
                height=20,
                width=80,
            ),
            paddingInputField=dict(
                sizeStyle="small",
                valueType="integer",
                minValue=1,
                value=1,
                maxValue=10,
                # width=90,
            ),
        )

        self.w = ezui.EZWindow(
            size=(400, 100),
            title=f"{constants.EXTENSION_NAME} Settings",
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
        postEvent(constants.EVENT_KEY, name="tintedBackground", value=sender.get())

    def blinkingCursorButtonCallback(self, sender: Any) -> None:
        postEvent(constants.EVENT_KEY, name="cursorBlinking", value=sender.get())

    def cursorColorWellCallback(self, sender: Any) -> None:
        postEvent(constants.EVENT_KEY, name="cursorColor", value=sender.get())

    def selectionColorWellCallback(self, sender: Any) -> None:
        postEvent(constants.EVENT_KEY, name="selectionColor", value=sender.get())

    def paddingInputFieldCallback(self, sender: Any) -> None:
        postEvent(constants.EVENT_KEY, name="paddingMultiplier", value=sender.get())


if __name__ == "__main__":
    SpacePortSettingsController()
