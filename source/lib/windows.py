import constants
import ezui
from typing import Any, Optional
from mojo.UI import getDefault
from lib.UI.spaceCenter.glyphSequenceEditText import splitText

class GlyphFinderPalette(ezui.WindowController):

    def build(self, parent:ezui.EZWindow, relative:Any) -> None:
        self.relative = relative
        self.parent   = parent
        content = """
        [__]                               @glyphFinderTextField
        ( X Starts With X | Contains )     @matchingSegmentedButton
        |-----------------|                @glyphFinderTable
        |                 |
        |-----------------|
        """
        footer = """
        (Insert)                           @insertGlyphButton         ? Insert Glyph into View
        """
        self.glyphMap = {"CurrentGlyph":"/?", "CurrentSelection":"/!",}
        glyphNames = list(self.glyphMap.keys())
        glyphNames.extend(self.relative.font.glyphOrder)
        data = dict(
            matchingSegmentedButton=dict(
                width=200,
            ),
            glyphFinderTextField=dict(
                placeholder="Glyph Name",
                width=200,
            ),
            glyphFinderTable=dict(
                allowsMultipleSelection=False,
                alternatingRowColors=True,
                width=200,
                height=100,
                items=glyphNames
            )
        )
        self.w = ezui.EZPopUp(
            content=content,
            parent=parent,
            footer=footer,
            controller=self,
            descriptionData=data,
            parentOffset=(-100, 0)
        )

        self.w.setDefaultButton(self.w.getItem("insertGlyphButton"))

        ns = self.w.getItem("glyphFinderTextField").getNSTextField()
        ns.setFocusRingType_(1)


    def insertGlyphCallback(self, input:str) -> None:
        if input:
            returnedItem = input[0]
            if returnedItem in self.glyphMap.keys():
                returnedItem = self.glyphMap.get(returnedItem)
            self.relative.holdingGlyphs.insert(self.relative.typingIndex, returnedItem)
            if returnedItem == "/!":
                self.relative.typingIndex += len(self.relative.currentSelection)
            else:
                self.relative.typingIndex += 1
            self.relative.setTypingItem()
            self.relative.updateCharacterString()
            self.w.close()


    def insertGlyphButtonCallback(self, sender:Any) -> None:
        selected = self.w.getItem("glyphFinderTable").getSelectedItems()
        self.insertGlyphCallback(selected)


    def glyphFinderTableDoubleClickCallback(self, sender:Any) -> None:
        selected = sender.getSelectedItems()
        self.insertGlyphCallback(selected)


    def glyphFinderTextFieldCallback(self, sender:Any) -> None:
        hit = sender.get()
        if self.w.getItemValue("matchingSegmentedButton") == 0:
            accepts = sorted([g for g in self.relative.font.glyphOrder if g.startswith(hit)])
        else:
            accepts = sorted([g for g in self.relative.font.glyphOrder if hit in g])

        accepts.extend(list(self.glyphMap.keys()))
        # accepts.extend(sorted([g for g in self.relative.font.glyphOrder if hit in g and g not in accepts]))
        self.w.getItem("glyphFinderTable").set(accepts)
        if accepts: self.w.getItem("glyphFinderTable").setSelectedIndexes([0])


    def started(self) -> None:
        self.w.open()


class HistoryPalette(ezui.WindowController):

    def build(self, parent:ezui.EZWindow, relative:Any) -> None:
        self.relative = relative
        self.parent   = parent
        content = """
        |-----------------|                @historyTable   ? User SpaceCenter Input
        |                 |
        |-----------------|
        """
        footer = """
        (Insert)                           @setInputButton ? Insert String into View
        """
        self.inputText = getDefault("spaceCenterInputSamples")
        data = dict(
            historyTable=dict(
                allowsMultipleSelection=False,
                alternatingRowColors=True,
                width=300,
                height=100,
                items=self.inputText
            )
        )
        self.w = ezui.EZPopUp(
            content=content,
            parent=parent,
            footer=footer,
            controller=self,
            descriptionData=data,
            parentOffset=(-100, 0)
        )

        self.w.setDefaultButton(self.w.getItem("setInputButton"))
        if self.inputText:
            self.w.getNSWindow().makeKeyAndOrderFront_(None)
            self.w.getItem("historyTable").setSelectedIndexes([0])


    def applyInputCallback(self, input:str) -> None:
        if input:
            returnedItem = input[0]
            self.relative.holdingGlyphs = splitText(returnedItem, self.relative.font.getCharacterMapping())
            self.relative.typingIndex = len(returnedItem)
            self.relative.setTypingItem()
            self.relative.updateCharacterString()
            self.w.close()


    def setInputButtonCallback(self, sender:Any) -> None:
        selected = self.w.getItem("historyTable").getSelectedItems()
        self.applyInputCallback(selected)


    def historyTableDoubleClickCallback(self, sender:Any) -> None:
        selected = sender.getSelectedItems()
        self.applyInputCallback(selected)


    def started(self) -> None:
        self.w.open()


class InterpolationWarningWindow(ezui.WindowController):

    def build(self, parent:ezui.EZWindow, relative:Any) -> None:

        self.relative = relative

        content = """
        * HorizontalStack                           @stack
        > * Image                                   @warningImage
        You must add a designspace file first!      @label
        ----------
        ( Manage Objects )                          @openDesignspaceButton  ? Open Objects Sheet
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

    def openDesignspaceButtonCallback(self, sender:Any) -> None:
        window = self.relative.buildObjectsSheet()
        window.open()

    def started(self) -> None:
        self.w.open()