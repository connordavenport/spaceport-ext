from featurePreviewRoboFontExtension.source.lib import featurePreview

"""
test script to run featurePreview functions
"""

if __name__ == "__main__":

	f = featurePreview.FeatureFont(CurrentFont().naked())
	print(f.source)
	f.setFeatureState("liga", True)
	for gs in f.process("W a f f l e s".split(" ")): 

		print(gs.glyph.name)
		print(gs.advanceWidth)
		print(gs.alternates)