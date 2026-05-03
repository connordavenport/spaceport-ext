<!-- ![Static Badge](https://img.shields.io/badge/unpublished-blue?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBlbmFibGUtYmFja2dyb3VuZD0ibmV3IDAgMCA2NCA2NCIgaWQ9InVuaTJCMjQiIHdpZHRoPSI3NSIgaGVpZ2h0PSI2OSIgdmVyc2lvbj0iMS4xIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIj48cGF0aCB0cmFuc2Zvcm09InNjYWxlKDEgLTEpIHRyYW5zbGF0ZSgwLCAtNjkpIiBkPSJNNDAgNjlDNTkgNjkgNzUgNTUgNzUgMzdDNzUgMTYgNTYgMCAzNSAwQzE2IDAgMCAxNSAwIDMyQzAgNTMgMTggNjkgNDAgNjlaTTUxIDE2TDQ3IDI3QzQ1IDMyIDQ3IDM2IDUyIDM5TDMyIDU4QzMxIDU5IDMwIDU5IDI5IDU4TDIzIDMwQzMwIDMwIDMzIDI4IDM0IDI0TDM3IDEyWk00NCAzMEwzNSAyOEMzMyAzMSAyOCAzMiAyNiAzMkwzMSA1Nkw0OCAzOUM0NiAzNyA0MyAzNCA0NCAzMFpNMzYgNDNDMzQgNDMgMzMgNDIgMzMgNDBDMzMgMzcgMzUgMzUgMzcgMzVDMzggMzUgMzkgMzYgMzkgMzhDMzkgNDAgMzggNDMgMzYgNDNaIi8%2BPC9zdmc%2B&logoColor=white&label=Mechanic&labelColor=FFFFFF&color=purple&link=https%3A%2F%2Frobofontmechanic.com%2F%23connor-davenport)
![Dynamic YAML Badge](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fconnordavenport%2FBezierSurgeon%2Frefs%2Fheads%2Fmaster%2Finfo.yaml&query=%24.version&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyBlbmFibGUtYmFja2dyb3VuZD0ibmV3IDAgMCA2NCA2NCIgaWQ9InVuaTJCMjQiIHdpZHRoPSI3NSIgaGVpZ2h0PSI2OSIgdmVyc2lvbj0iMS4xIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIj48cGF0aCB0cmFuc2Zvcm09InNjYWxlKDEgLTEpIHRyYW5zbGF0ZSgwLCAtNjkpIiBkPSJNNDAgNjlDNTkgNjkgNzUgNTUgNzUgMzdDNzUgMTYgNTYgMCAzNSAwQzE2IDAgMCAxNSAwIDMyQzAgNTMgMTggNjkgNDAgNjlaTTUxIDE2TDQ3IDI3QzQ1IDMyIDQ3IDM2IDUyIDM5TDMyIDU4QzMxIDU5IDMwIDU5IDI5IDU4TDIzIDMwQzMwIDMwIDMzIDI4IDM0IDI0TDM3IDEyWk00NCAzMEwzNSAyOEMzMyAzMSAyOCAzMiAyNiAzMkwzMSA1Nkw0OCAzOUM0NiAzNyA0MyAzNCA0NCAzMFpNMzYgNDNDMzQgNDMgMzMgNDIgMzMgNDBDMzMgMzcgMzUgMzUgMzcgMzVDMzggMzUgMzkgMzYgMzkgMzhDMzkgNDAgMzggNDMgMzYgNDNaIi8%2BPC9zdmc%2B&label=Ext.%20Version&labelColor=white)
![GitHub commit activity](https://img.shields.io/github/commit-activity/w/connordavenport/BezierSurgeon?logo=GitHub&logoColor=black&labelColor=white) -->
# Spaceport

>"A spaceport is a site where spacecraft are tested, launched, sheltered and maintained.
The Spaceport extension is a place where multiple, unrelated UFOs can be spaced, kerned and interpolated concurrently."

##### Spaceport is currently in beta development.

![UI Image](./images/ui_default.png)

## User Interface - Main Window

- 1 : State Toggler
	- Type: Typing state, enter text and edit strings
	- Space: Edit spacing
	- Kern: Edit Kerning

- 2 : Point Size
 
- 3 : Line Height
 
- 4 : Fit Text
	- To Width
	- To Height
 
- 5 : Text Alignment
 
- 6 : Character Ordering
 
- 7 : (Un)sync Text Strings
 
- 8 : Leading and Trailing Text Field
 
- 9 : Controllers
	- Objects Controller:
		- Add and manage UFOs and Designspaces
 	- OpenType Features Controller
 	- Interpolation Controller

- 10 : Settings Window
 
- 11 : Space Matrix


## Key Controls

### Spacing

Arrow Keys: `← → ↓ ↑`
Spaceport allows you to modify glyph(s) spacing via the arrow keys, optionally with modifiers to change the increments.
With at least one selected item, you can edit the spacing. If more than one item is selected, it will apply the delta globally to those glyphs.

`shift + command = 100` 
`shift = 10`
`default = 1`

`up` and `down` arrows control the glyphs' width, adding or subtracting the delta, respectively.

`left` and `right` arrow controls the glyphs' margins, if `option` is pressed, the `leftMargin` will be edited. `right` arrow will add the delta, while `left` will subtract the delta.

### Other Events

`command z` Call and apply the selected glyphs' undo manager stack

`command t` Toggle between _Typing_ and _Spacing_ modes

`command ;` Open objects manager sheet

`command +` Zoom in

`command -` Zoom out
                    
`b` Toggle beam visibility

`m` Toggle metrics visibility

`l` Toggle label visibility

`l` Toggle apply kerning

##### The following keys are extracted from the users' preferences

`glyphViewZoomInKey` Zoom in `e.g. z`

`glyphViewZoomInKey` Zoom out `e.g. x`

## Typing

![Typing](https://github.com/user-attachments/assets/66227df7-7202-4aa8-94a6-ab05d944d43b)

## Kerning

![Kerning](https://github.com/user-attachments/assets/9e6d560f-d957-4531-9237-bb39627f43bb)

## Mouse Controls

When selecting a glyph inside the Spaceport view there are several modifiers available.

`shift` will allow for multi-glyph selection

`option` selects the current glyph in all fonts that are activated

_Note: `shift` and `option` are not able to be combined!_

Double clicking a single item will open a `DoodleGlyphWindow` for that glyph.

### Objects Manager

![Objects Sheets](./images/ui_objects.png)

Tabs:  `Fonts`  `Designspaces`

#### `Fonts`

`Font List` A list with all fonts, can be (de)activated with checkbox

`Refresh Order` Update the font order (font list can be dragged to reorder)

`Add All Open Fonts` Add all open fonts to the font list

`Open Font Interface` Show fonts' interface when opening new font object

#### `Designspaces`

`Designspace List` A list with all designspaces, can be (de)activated with checkbox, but only one can be used a time

`View Sources` Add all designspace sources to the font list

`View Instances` Add all designspace instances to the font list (metrics can not be edited) (interpolation value can be edited)

`DSE Controller` Allow DesignspaceEditor to control the interpolation values, display selected instances, or selected sources


### Interpolation Controller

![Interpolation](https://github.com/user-attachments/assets/418416cd-2cc0-43c0-9046-90fb97ef0cfc)

If there is an activated designspace, the interpolation controller will generate a UI to control all available axes in the operator. Discrete axes can be accessed through popup buttons while continuous axes can be controlled 2 at a time through an interactive 2-dimensional view.

Continuous axes can be switched using the x and/or y axes popovers and dragging your mouse within the view. The mouse location is remapped into the axes' minimum and maximum.

### Credits

Developed by Connor Davenport

Designed by Vincent Chan and Connor Davenport

Sponsored by Vincent Chan

