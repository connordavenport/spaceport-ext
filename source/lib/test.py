from featurePreviewLib.source.lib import featurePreview
import time
"""
test script to run featurePreview functions
"""

if __name__ == "__main__":

	start = time.time()
	f = featurePreview.FeatureFont(CurrentFont().naked())
	
	print(f.gsub.getFeatureList())

	f.setFeatureState("liga", True)
	for gs in f.process("W a f f l e s".split(" ")): 

		print(gs.glyph.name, end=" ")
		print(gs.advanceWidth, end=" ")
		print(gs.alternates, end=" ")

	print("\n")
	end = time.time()
	print(round(end-start, 3))

