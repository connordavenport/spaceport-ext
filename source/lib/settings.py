import ezui  # ty:ignore[unresolved-import]
from typing import Any
import constants
from mojo.events import postEvent  # ty:ignore[unresolved-import]

class SpacePortSettingsController(ezui.WindowController):
    
    def build(self) -> None:

        self.detached = False
        content = """
        !!!! Spaceport Misc. Settings
        * Box                                                           @cursorBox = VerticalStack
        > [ ] Blinking Cursor                                           @blinkingCursorButton                        ? Use Blinking Cursor
        > * HorizontalStack                                             @cursorStack                                 
        >> Cursor Color: 
        >> * ColorWell                                                  @cursorColorWell                             ? Cursor Color
        > [ ] Tinted Typing Background                                  @tintedBackgroundButton                      ? Use Tinted Background in Typing View
        > * HorizontalStack                                             @selectionStack
        >> Selection Color: 
        >> * ColorWell                                                  @selectionColorWell                          ? Glyph Selection Color
        """

        descriptionData = dict(
            blinkingCursorButton=dict(
                value=False
            ),
            tintedBackgroundButton=dict(
                value=False,
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
        )

        self.w = ezui.EZWindow(
            # size=(100, 100),
            content=content,
            descriptionData=descriptionData,
            controller=self,
        )


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



if __name__ == "__main__":
    SpacePortSettingsController()
