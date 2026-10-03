"""Stack the reference frame above a render: python3 scripts/compare.py render.png out.png"""
import sys
from PIL import Image
r = Image.open("reference/reference_frame.png").convert("RGB")
a = Image.open(sys.argv[1]).convert("RGB")
W = 960
r = r.resize((W, int(W * r.height / r.width)))
a = a.resize((W, int(W * a.height / a.width)))
s = Image.new("RGB", (W, r.height + a.height + 8))
s.paste(r, (0, 0)); s.paste(a, (0, r.height + 8)); s.save(sys.argv[2])
