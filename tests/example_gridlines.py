# EOmaps Example:  Customized gridlines

from eomaps import Maps

m = Maps(crs=Maps.CRS.Stereographic())
m.subplots_adjust(left=0.1, right=0.9, bottom=0.1, top=0.9)

m.add_feature.preset.ocean()
m.add_feature.preset.land()

# draw a regular 5 degree grid
m.add_gridlines(5, lw=0.25, alpha=0.5)
# draw a grid with 20 degree longitude spacing and add labels
g = m.add_gridlines((20, None), c="b", n=500)
g.add_labels(offset=10, fontsize=8, c="b")
# draw a grid with 20 degree latitude spacing, add labels and exclude the 10° tick
g = m.add_gridlines((None, 20), c="g", n=500)
g.add_labels(offset=10, fontsize=8, c="g", exclude=[10])
# explicitly highlight 10° lon/lat lines and add a label on one side of the map
g = m.add_gridlines(([-10], [10]), c="k", n=500, lw=2)
g.add_labels(where="W", fontsize=12, fontweight="bold")


# ----------------- first inset-map
mi = m.new_inset_map(xy=(45, 45), radius=10, inset_crs=Maps.CRS.Mollweide())
mi.add_feature.preset.ocean()
mi.add_feature.preset.land()

# draw a regular 1 degree grid
g = mi.add_gridlines((None, 1), c="g", lw=0.6)
# add some specific latitude gridlines and add labels
g = mi.add_gridlines((None, [40, 45, 50]), c="g", lw=2)
g.add_labels(where="EW", offset=7, fontsize=6, c="g")
# add some specific longitude gridlines and add labels
g = mi.add_gridlines(([40, 45, 50], None), c="b", lw=2)
g.add_labels(where="NS", offset=7, fontsize=6, c="b")


# ----------------- second inset-map
mi = m.new_inset_map(
    xy=(-10, 10), radius=10, inset_crs=4326, shape="rectangles", boundary=dict(ec="k")
)
mi.add_feature.preset.ocean()
mi.add_feature.preset.land()

# draw a regular 1 degree grid
g = mi.add_gridlines(1, lw=0.25)
# add some specific latitude gridlines and add labels
g = mi.add_gridlines((None, [5, 10, 15]), c="g", lw=2)
g.add_labels(where="E", offset=12, fontsize=6, c="g")
g.add_labels(where="W", offset=10, fontsize=6, c="g")
# add some specific longitude gridlines and add labels
g = mi.add_gridlines(([-15, -10, -5], None), c="b", lw=2)
g.add_labels(where="N", offset=7, fontsize=6, c="b")
g.add_labels(where="S", offset=10, fontsize=6, c="b")


m.apply_layout(
    {
        "figsize": [7.39, 4.8],
        "0_map": [0.025, 0.07698, 0.5625, 0.86602],
        "1_inset_map": [0.7, 0.53885, 0.225, 0.41681],
        "2_inset_map": [0.6625, 0.03849, 0.275, 0.42339],
    }
)
