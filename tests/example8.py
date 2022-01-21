# EOmaps example 8: Adding scalebars - what about distances?

from eomaps import Maps

m = Maps()
m.add_coastlines()

s1 = m.add_scalebar(
    -11,
    -50,
    scale=500000,
    scale_props=dict(n=10, width=5, colors=("k", ".25", ".5", ".75", ".95")),
    patch_props=dict(offsets=(1, 1.4, 1, 1), fc=(0.7, 0.8, 0.3, 1)),
    label_props=dict(offset=0.5, scale=1.4, every=5, weight="bold", family="Calibri"),
)

s2 = m.add_scalebar(
    46,
    53,
    scale=500000,
    scale_props=dict(n=6, width=3, colors=("k", "r")),
    patch_props=dict(fc="none", ec="r", lw=0.5, offsets=(1, 1, 1, 1)),
    label_props=dict(rotation=45, weight="bold", family="Impact"),
)

s3 = m.add_scalebar(
    -73,
    8,
    0,
    scale=500000,
    scale_props=dict(n=6, width=3, colors=("w", "r")),
    patch_props=dict(fc=".25", ec="k", lw=0.5, offsets=(1, 1, 1, 1)),
    label_props=dict(color="w", rotation=45, weight="bold", family="Impact"),
)

# it's also possible to update the properties of an existing scalebar
# via the setter-functions!
s4 = m.add_scalebar()
s4.set_position(-140, -55, 0)
s4.set_scale_props(scale=750000, n=10, width=4, colors=("k", "w"))
s4.set_patch_props(fc="none", ec="none", offsets=(1, 1.6, 1, 1))
s4.set_label_props(scale=1.5, offset=0.5, every=2, weight="bold", family="Courier New")

m.figure.f.set_figheight(6)
