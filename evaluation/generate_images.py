"""Regenerate the small, synthetic EvidenceLens evaluation images."""
from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT = Path(__file__).parent / "data" / "images"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Red-circle asset also used by prior live smoke checks. Deterministic pixels.
red = Image.new("RGB", (360, 240), "white")
ImageDraw.Draw(red).ellipse((120, 50, 240, 170), fill="red", outline="black", width=3)
red.save(OUTPUT / "red-circle.png", optimize=False)

# A second deliberately simple synthetic scene for visual variety.
scene = Image.new("RGB", (360, 240), "#dff2ff")
draw = ImageDraw.Draw(scene)
draw.rectangle((0, 174, 360, 240), fill="#a9d58e")
draw.ellipse((270, 28, 326, 84), fill="#ffd34e", outline="#d7a91f", width=2)
# Tree trunk and canopy are visibly separate, with an unambiguous brown trunk.
draw.rectangle((157, 126, 177, 196), fill="#8b5a36")
draw.polygon([(167, 55), (111, 147), (223, 147)], fill="#2f8753", outline="#216b40")
draw.polygon([(167, 78), (124, 158), (210, 158)], fill="#39965d", outline="#216b40")
scene.save(OUTPUT / "simple-landscape.png", optimize=False)
