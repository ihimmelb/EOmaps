import matplotlib as mpl

mpl.rcParams["toolbar"] = "None"

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.font_manager import FontProperties

import unittest
from types import SimpleNamespace

import pandas as pd
import numpy as np

from eomaps import Maps, MapsGrid


class TestBasicPlotting(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(
            np.linspace(-19000000, 19000000, 50), np.linspace(-19000000, 19000000, 50)
        )
        x, y = x.ravel(), y.ravel()

        self.data = pd.DataFrame(dict(x=x, y=y, value=y - x))

    def test_simple_map(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=4326)
        m.plot_map()
        plt.close(m.figure.f)

        # -------------------------------------

        m = Maps()
        m.set_data_specs(data=self.data, xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(
            plot_crs=4326,
            title="asdf",
            label="bsdf",
            histbins=100,
            density=True,
            cpos="ur",
            cpos_radius=1,
        )
        m.plot_map()
        plt.close(m.figure.f)

    def test_simple_plot_shapes(self):
        usedata = self.data.sample(500)

        m = Maps()
        m.data = usedata
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(crs=4326)

        # rectangles
        m.set_shape.geod_circles(radius=100000)
        m.plot_map(coastlines=False)
        m.indicate_masked_points()

        m.add_coastlines(coast=dict(color="r"), ocean=dict(fc="g"))

        plt.close("all")

        # rectangles
        m.set_shape.rectangles()
        m.plot_map(coastlines=False)
        m.add_coastlines(coast=False, ocean=dict(fc="g"))

        m.set_shape.rectangles(radius=1, radius_crs=4326)
        m.plot_map()

        m.set_shape.rectangles(radius=(1, 2), radius_crs="out")
        m.plot_map()

        # rectangles
        m.set_shape.rectangles(mesh=True)
        m.plot_map()

        m.set_shape.rectangles(radius=1, radius_crs=4326, mesh=True)
        m.plot_map()

        m.set_shape.rectangles(radius=(1, 2), radius_crs="out", mesh=True)
        m.plot_map()

        plt.close("all")

        # ellipses
        m.set_shape.ellipses()
        m.plot_map()

        m.set_shape.ellipses(radius=1, radius_crs=4326)
        m.plot_map()

        plt.close("all")

        # delaunay
        m.set_shape.delaunay_triangulation(flat=True)
        m.plot_map()
        m.indicate_masked_points(5)

        m.set_shape.delaunay_triangulation(flat=False)
        m.plot_map()
        m.indicate_masked_points(5)

        m.set_shape.delaunay_triangulation(masked=False)
        m.plot_map()
        m.indicate_masked_points(5)

        plt.close("all")

        # voroni
        m.set_shape.voroni_diagram(masked=False)
        m.plot_map()
        m.indicate_masked_points(5, ec="k")

        m.set_shape.voroni_diagram(masked=True, mask_radius=5)
        m.plot_map()
        m.indicate_masked_points(5, ec="k")

        plt.close("all")

    def test_cpos(self):
        m = Maps()
        m.data = self.data

        for cpos in ["ul", "ur", "ll", "lr", "c"]:
            m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
            m.set_plot_specs(
                plot_crs=4326,
                title="asdf",
                label="bsdf",
                cpos_radius=2,
                histbins=100,
                density=True,
                cpos=cpos,
            )
            m.plot_map()

            plt.close(m.figure.f)

    def test_alpha_and_splitbins(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=4326, alpha=0.4)
        m.set_shape.rectangles()
        m.set_classify_specs(scheme="Percentiles", pct=[0.1, 0.2])

        m.plot_map()

        plt.close(m.figure.f)

    def test_classification(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=4326)
        m.set_shape.rectangles(radius=1, radius_crs="out")

        m.set_classify_specs(scheme="Quantiles", k=5)

        m.plot_map()

        plt.close(m.figure.f)

    def test_add_callbacks(self):
        m = Maps()
        m.data = self.data.sample(10)
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=3857)
        m.set_shape.ellipses(radius=200000)

        m.plot_map()

        # attach all pick callbacks
        double_click, mouse_button = True, 1
        for n, cb in enumerate(m.cb.pick._cb_list):
            if n == 1:
                mouse_button = 1
                double_click = False
            if n == 2:
                mouse_button = 2
                double_click = False

            cbID = m.cb.pick.attach(cb, double_click=double_click, button=mouse_button)

            self.assertTrue(
                cbID
                == f"{cb}_0__{'double' if double_click else 'single'}__{mouse_button}"
            )
            self.assertTrue(len(m.cb.pick.get.attached_callbacks) == 1)
            m.cb.pick.remove(cbID)
            self.assertTrue(len(m.cb.pick.get.attached_callbacks) == 0)

        # attach all click callbacks
        double_click, mouse_button = True, 1
        for n, cb in enumerate(m.cb.click._cb_list):
            if n == 1:
                mouse_button = 1
                double_click = False
            if n == 2:
                mouse_button = 2
                double_click = False

            cbID = m.cb.click.attach(cb, double_click=double_click, button=mouse_button)

            self.assertTrue(
                cbID
                == f"{cb}_0__{'double' if double_click else 'single'}__{mouse_button}"
            )
            self.assertTrue(len(m.cb.click.get.attached_callbacks) == 1)
            m.cb.click.remove(cbID)
            self.assertTrue(len(m.cb.click.get.attached_callbacks) == 0)

        # attach all keypress callbacks
        double_click, mouse_button = True, 1
        for n, cb in enumerate(m.cb.keypress._cb_list):
            if n == 1:
                key = "x"
            if n == 2:
                key = "y"
            else:
                key = "z"

            cbID = m.cb.keypress.attach(cb, key=key)

            self.assertTrue(cbID == f"{cb}_0__{key}")
            self.assertTrue(len(m.cb.keypress.get.attached_callbacks) == 1)
            m.cb.keypress.remove(cbID)
            self.assertTrue(len(m.cb.keypress.get.attached_callbacks) == 0)

        plt.close(m.figure.f)

    def test_callbacks(self):

        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=3857)
        m.add_coastlines(layer=1)
        m.plot_map()

        # test all pick callbacks
        for n, cb in enumerate(m.cb.pick._cb_list):
            kwargs = dict(ID=1, pos=(1, 2), val=3.365734, ind=None)
            if cb == "load":
                kwargs["database"] = pd.DataFrame([1, 2, 3, 4])
                kwargs["load_method"] = "xs"

            callback = getattr(m.cb.pick._cb, cb)
            callback(**kwargs)

            dummymouseevent = SimpleNamespace(
                inaxes=m.figure.ax,
                dblclick=False,
                button=1,
                xdata=m.data.iloc[0]["x"],
                ydata=m.data.iloc[0]["x"],
                x=123,
                y=123,
            )
            dummyevent = SimpleNamespace(
                artist=m.figure.coll,
                mouseevent=dummymouseevent,
            )

            pick = m.cb.pick._picker(None, dummymouseevent)
            if pick[1] is not None:
                dummyevent.ind = pick[1]["ind"]
                if "dist" in pick[1]:
                    dummyevent.dist = pick[1]["dist"]
            else:
                dummyevent.ind = None
                dummyevent.dist = None

            m.cb.pick._onpick(dummyevent)

        # test all click callbacks
        for n, cb in enumerate(m.cb.click._cb_list):
            kwargs = dict(ID=1, pos=(1, 2), val=3.365734, ind=None)
            callback = getattr(m.cb.click._cb, cb)
            callback(**kwargs)

            dummyevent = SimpleNamespace(
                inaxes=m.figure.ax,
                dblclick=True,
                button=1,
                xdata=123456,
                ydata=123456,
            )
            m.cb.click._fwd_cb(dummyevent)

        # test all keypress callbacks
        for n, cb in enumerate(m.cb.keypress._cb_list):
            kwargs = dict(key="x")
            callback = getattr(m.cb.keypress._cb, cb)
            callback(**kwargs)

        plt.close("all")

    def test_add_overlay(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=3857)
        m.set_shape.rectangles(mesh=True)

        m.plot_map()

        m.add_overlay(
            dataspec=dict(resolution="10m", category="cultural", name="urban_areas"),
            styledict=dict(facecolor="r"),
        )
        m.add_overlay(
            dataspec=dict(resolution="10m", category="physical", name="lakes"),
            styledict=dict(facecolor="b"),
        )

        m.add_overlay_legend(
            loc="upper center",
            update_hl={
                "lakes": [None, "asdf"],
                "urban_areas": [plt.Line2D([], [], c="r"), "bsdf"],
            },
            sort_order=["lakes", "urban_areas"],
        )

        plt.close(m.figure.f)

    def test_add_annotate(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=4326)

        m.plot_map()

        m.add_annotation(ID=m.data["value"].idxmax(), fontsize=15, text="adsf")

        def customtext(m, ID, val, pos, ind):
            return f"{m.data_specs}\n {val}\n {pos}\n {ID} \n {ind}"

        m.add_annotation(ID=m.data["value"].idxmin(), text=customtext)

        m.add_annotation(
            xy=(m.data.x[0], m.data.y[0]), xy_crs=3857, fontsize=15, text="adsf"
        )

        plt.close(m.figure.f)

    def test_add_marker(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.plot_specs.crs = Maps.CRS.Orthographic(
            central_latitude=45, central_longitude=45
        )
        m.plot_map()

        m.add_marker(
            np.arange(1810, 1840, 1),
            facecolor=[1, 0, 0, 0.5],
            edgecolor="r",
            shape="ellipses",
        )

        m.add_marker(
            np.arange(1810, 1840, 1),
            facecolor="none",
            edgecolor="k",
            shape="geod_circles",
            radius=300000,
        )

        m.add_marker(
            np.arange(1710, 1740, 1),
            facecolor=[1, 0, 0, 0.5],
            edgecolor="r",
            shape="rectangles",
        )

        m.add_marker(
            np.arange(1410, 1440, 1),
            facecolor=[1, 0, 0, 0.5],
            edgecolor="r",
            radius=50000,
            radius_crs="in",
        )

        m.add_marker(
            1630,
            facecolor=[1, 0, 0, 0.5],
            edgecolor="r",
            radius=2500000,
            shape="rectangles",
        )
        m.add_marker(
            1630, facecolor="none", edgecolor="k", linewidth=3, buffer=3, linestyle="--"
        )

        for r in [5, 10, 15, 20]:
            m.add_marker(
                1635, fc="none", ec="y", ls="--", radius=r, radius_crs=4326, lw=2
            )

        for r in np.linspace(10000, 1000000, 10):
            m.add_marker(
                1635, fc="none", ec="b", ls="--", radius=r, lw=2, shape="geod_circles"
            )

        for x in np.linspace(5000000, 6000000, 10):
            m.add_marker(
                xy=(x, 4000000),
                xy_crs="out",
                facecolor="none",
                edgecolor="r",
                radius=1000000,
                radius_crs="out",
            )

        m.add_marker(
            xy=(5040816, 4265306), facecolor="none", edgecolor="c", radius=800000, lw=5
        )

        m.add_marker(
            xy=(m.data.x[10], m.data.y[10]),
            xy_crs=3857,
            facecolor="none",
            edgecolor="r",
            radius="pixel",
            buffer=5,
        )

        for shape in ["ellipses", "rectangles"]:
            m.add_marker(
                1232, facecolor="none", edgecolor="r", radius="pixel", shape=shape, lw=2
            )

        plt.close(m.figure.f)

    def test_copy(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=3857)

        m.set_classify_specs(scheme="Quantiles", k=5)

        m2 = m.copy()

        self.assertTrue(
            m.data_specs[["xcoord", "ycoord", "parameter", "crs"]]
            == m2.data_specs[["xcoord", "ycoord", "parameter", "crs"]]
        )
        self.assertTrue(
            all(
                [
                    [i == j]
                    for i, j in zip(m.plot_specs, m2.plot_specs)
                    if i[0] != "cmap"
                ]
            )
        )
        self.assertTrue([*m.classify_specs] == [*m2.classify_specs])
        self.assertTrue(m2.data == None)

        m3 = m.copy(copy_data=True)

        self.assertTrue(
            m.data_specs[["xcoord", "ycoord", "parameter", "crs"]]
            == m3.data_specs[["xcoord", "ycoord", "parameter", "crs"]]
        )
        self.assertTrue(
            all(
                [
                    [i == j]
                    for i, j in zip(m.plot_specs, m3.plot_specs)
                    if i[0] != "cmap"
                ]
            )
        )
        self.assertTrue([*m.classify_specs] == [*m3.classify_specs])
        self.assertFalse(m3.data is m.data)
        self.assertTrue(m3.data.equals(m.data))

        m3.plot_map()
        plt.close(m3.figure.f)

        m4 = m.copy(copy_data="share")
        self.assertTrue(m4.data is m.data)

    def test_connect(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_crs=3857)
        m.set_shape.rectangles()
        m.set_classify_specs(scheme="Quantiles", k=5)
        m.plot_map()

        # plot on the same axes
        m2 = m.copy(connect=True, copy_data="share", gs_ax=m.figure.ax)
        m2.set_shape.ellipses()
        m2.plot_map(facecolor="none", edgecolor="r")

        plt.close(m.figure.f)

    def test_prepare_data(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857, parameter="value")
        data = m._prepare_data()

    def test_draggable_axes(self):

        mgrid = MapsGrid(2, 2)

        for m in mgrid:
            m.plot_map(colorbar=False)
        mgrid.parent._draggable_axes._make_draggable()
        mgrid.parent._draggable_axes._undo_draggable()

        m = Maps(orientation="horizontal")
        m.plot_map()
        m._draggable_axes._make_draggable()
        m._draggable_axes._undo_draggable()

    def test_add_colorbar(self):
        gs = GridSpec(2, 2)

        m = Maps(gs_ax=gs[0, 0])
        m.set_data_specs(data=self.data, xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(histbins=5)
        m.plot_map(colorbar=True)
        cb1 = m.add_colorbar(gs[1, 0], orientation="horizontal")
        cb2 = m.add_colorbar(gs[0, 1], orientation="vertical")

        cb3 = m.add_colorbar(
            gs[1, 1], orientation="horizontal", density=True, label="naseawas"
        )
        m.figure.set_colorbar_position(cb=cb1, ratio=10)
        m.figure.set_colorbar_position(cb=cb2, ratio=20)
        m.figure.set_colorbar_position((0.625, 0.25, 0.2, 0.1), cb=cb3)

        m.figure.set_colorbar_position((0.625, 0.25, 0.2, 0.1))

    def test_MapsGrid(self):
        mg = MapsGrid(2, 2)
        mg.set_data(data=self.data, xcoord="x", ycoord="y", in_crs=3857)
        mg.set_plot_specs(crs=4326, title="asdf", label="bsdf")
        mg.set_classify_specs(scheme=Maps.CLASSIFIERS.EqualInterval, k=4)

        for m in mg:
            m.plot_map()

        mg.add_annotation(ID=520)
        mg.add_marker(ID=5, fc="r", radius=10, radius_crs=4326)

        self.assertTrue(mg.m_0_0 is mg[0, 0])
        self.assertTrue(mg.m_0_1 is mg[0, 1])
        self.assertTrue(mg.m_1_0 is mg[1, 0])
        self.assertTrue(mg.m_1_1 is mg[1, 1])

        plt.close(mg.f)

    def test_ScaleBar(self):

        m = Maps()
        m.add_coastlines()

        s = m.add_scalebar(scale=250000)
        s.set_position(10, 20, 30)
        s.set_label_props(every=2, scale=1.25, offset=0.5, weight="bold")
        s.set_scale_props(n=6, colors=("k", "r"))
        s.set_patch_props(offsets=(1, 1.5, 1, 0.75))

        s1 = m.add_scalebar(
            -31,
            -50,
            90,
            scale=500000,
            scale_props=dict(n=10, width=3, colors=("k", ".25", ".5", ".75", ".95")),
            patch_props=dict(fc=(1, 1, 1, 1)),
            label_props=dict(every=5, weight="bold", family="Calibri"),
        )

        s2 = m.add_scalebar(
            -45,
            45,
            45,
            scale=500000,
            scale_props=dict(n=6, width=3, colors=("k", "r")),
            patch_props=dict(fc="none", ec="r", lw=0.25, offsets=(1, 1, 1, 1)),
            label_props=dict(rotation=45, weight="bold", family="Impact"),
        )

        s3 = m.add_scalebar(
            78,
            -60,
            0,
            scale=250000,
            scale_props=dict(n=20, width=3, colors=("k", "w")),
            patch_props=dict(fc="none", ec="none"),
            label_props=dict(scale=1.5, weight="bold", family="Courier New"),
        )

        for si in [s, s1, s2, s3]:
            si.remove()

    def test_WMS_OSM(self):
        m = Maps()
        m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR
        m.add_wms.OpenStreetMap.add_layer.default()
        plt.close(m.figure.f)

    def test_WMS_S1GBM(self):
        m = Maps()
        m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR
        m.add_wms.S1GBM.add_layer.vv()
        plt.close(m.figure.f)

    def test_WMS_ESA_WorldCover(self):
        m = Maps()
        m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR

        m.plot_map(colormap=False)
        ESA_layer = m.add_wms.ESA_WorldCover.add_layer.WORLDCOVER_2020_MAP
        ESA_layer.info

        ESA_layer()

        plt.close(m.figure.f)

    def test_WMS_legend_capabilities_NASA_GIBS(self):
        m = Maps()
        m.plot_specs.crs = 4326
        m.plot_map(colormap=False)
        m.figure.ax.set_extent((-130, 160, -50, 50))

        # use a layer that provides a legend
        NASA_layer = (
            m.add_wms.NASA_GIBS.EPSG_3857.add_layer.AIRS_L2_Cloud_Top_Height_Night
        )
        NASA_layer.info

        NASA_layer(transparent=True)
        NASA_layer.add_legend()

        legax = ax = m.figure.f.axes[-1]
        leg_cpos = (
            (legax.bbox.x0 + legax.bbox.x1) / 2,
            (legax.bbox.y0 + legax.bbox.y1) / 2,
        )

        # pick up the the legend (e.g. click on it)
        m.figure.f.canvas.button_press_event(*leg_cpos, 1, False)

        # resize the legend
        m.figure.f.canvas.scroll_event(*leg_cpos, 20, False)

        # move the legend
        m.figure.f.canvas.motion_notify_event(
            (m.figure.ax.bbox.x0 + m.figure.ax.bbox.x1) / 2,
            (m.figure.ax.bbox.y0 + m.figure.ax.bbox.y1) / 2,
            None,
        )

        # release the legend
        m.figure.f.canvas.button_press_event(0, 0, 1, False)
        plt.close(m.figure.f)

    def test_a_complex_figure(self):
        # %%
        lon, lat = np.linspace(-180, 180, 500), np.linspace(-90, 90, 500)
        lon, lat = np.meshgrid(lon, lat)

        df = pd.DataFrame(
            dict(lon=lon.flat, lat=lat.flat, data=(lon ** 2 + lat ** 2).flat)
        )

        mgrid = MapsGrid(3, 4)
        mgrid.parent.set_data(
            data=df.sample(2000), xcoord="lon", ycoord="lat", crs=4326
        )
        for m in mgrid.children:
            m.set_data(**mgrid.parent.data_specs)

        crss = iter(
            (
                m.CRS.Stereographic(),
                m.CRS.Sinusoidal(),
                m.CRS.Mercator(),
                #
                m.CRS.EckertI(),
                m.CRS.EckertII(),
                m.CRS.EckertIII(),
                #
                m.CRS.EckertIV(),
                m.CRS.EckertV(),
                m.CRS.Mollweide(),
                #
                m.CRS.Orthographic(central_longitude=45, central_latitude=45),
                m.CRS.AlbersEqualArea(),
                m.CRS.LambertCylindrical(),
            )
        )

        for i, m, title in zip(
            (
                ["ellipses", dict(radius=1.0, radius_crs="in")],
                ["ellipses", dict(radius=100000, radius_crs="out")],
                ["geod_circles", dict(radius=100000)],
                #
                ["rectangles", dict(radius=1.5, radius_crs="in")],
                ["rectangles", dict(radius=100000, radius_crs="out")],
                ["rectangles", dict(radius=1.5, radius_crs="in", mesh=True)],
                #
                ["rectangles", dict(radius=100000, radius_crs="out", mesh=True)],
                ["voroni_diagram", dict(mask_radius=200000)],
                ["voroni_diagram", dict(masked=False)],
                #
                [
                    "delaunay_triangulation",
                    dict(mask_radius=(100000, 100000), mask_radius_crs="in"),
                ],
                [
                    "delaunay_triangulation",
                    dict(mask_radius=100000, mask_radius_crs="out"),
                ],
                ["delaunay_triangulation", dict(masked=False)],
            ),
            list(mgrid),
            (
                "in_ellipses",
                "out_ellipses",
                "geod_circles",
                "in_rectangles",
                "out_rectangles",
                "in_trimesh_rectangles",
                "out_trimesh_rectangles",
                "voroni",
                "voroni_unmasked",
                "delaunay_flat",
                "delaunay",
                "delaunay_unmasked",
            ),
        ):

            print(title)

            m.plot_specs.title = title
            getattr(m.set_shape, i[0])(**i[1])
            m.plot_specs.plot_crs = next(crss)

            m.plot_map(
                edgecolor="none", colorbar=True, coastlines=True, pick_distance=5
            )
            m.cb.click.attach.annotate()

        mgrid.parent.cb.click.share_events(*mgrid.children)

        m.figure.f.tight_layout()
        # %%
        plt.close(m.figure.f)
