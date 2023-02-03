"""a collection of useful helper-functions."""
from itertools import tee
import re
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from itertools import chain
from matplotlib.transforms import Bbox, TransformedBbox
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from contextlib import contextmanager, ExitStack
from pathlib import Path
import json
import warnings

# class copied from matplotlib.axes
class _TransformedBoundsLocator:
    """
    Axes locator for `.Axes.inset_axes` and similarly positioned Axes.
    The locator is a callable object used in `.Axes.set_aspect` to compute the
    Axes location depending on the renderer.
    """

    def __init__(self, bounds, transform):
        """
        *bounds* (a ``[l, b, w, h]`` rectangle) and *transform* together
        specify the position of the inset Axes.
        """
        self._bounds = bounds
        self._transform = transform

    def __call__(self, ax, renderer):
        # Subtracting transSubfigure will typically rely on inverted(),
        # freezing the transform; thus, this needs to be delayed until draw
        # time as transSubfigure may otherwise change after this is evaluated.
        return TransformedBbox(
            Bbox.from_bounds(*self._bounds),
            self._transform - ax.figure.transSubfigure,
        )


def pairwise(iterable, pairs=2):
    """
    a generator to return n consecutive values from an iterable.

        pairs = 2
        s -> (s0,s1), (s1,s2), (s2, s3), ...

        pairs = 3
        s -> (s0, s1, s2), (s1, s2, s3), (s2, s3, s4), ...

    adapted from https://docs.python.org/3.7/library/itertools.html
    """
    x = tee(iterable, pairs)
    for n, n_iter in enumerate(x[1:]):
        [next(n_iter, None) for i in range(n + 1)]
    return zip(*x)


def _sanitize(s, prefix="layer_"):
    # taken from https://stackoverflow.com/a/3303361/9703451
    s = str(s)
    # Remove leading characters until we find a letter or underscore
    s2 = re.sub("^[^a-zA-Z_]+", "", s)
    if len(s2) == 0:
        s2 = _sanitize(prefix + str(s))
    # replace invalid characters with an underscore
    s = re.sub("[^0-9a-zA-Z_]", "_", s2)
    return s


def cmap_alpha(cmap, alpha, interpolate=False, name="new_cmap"):
    """
    add transparency to an existing colormap

    Parameters
    ----------
    cmap : matplotlib.colormap
        the colormap to use
    alpha : float
        the transparency
    interpolate : bool
        indicator if a listed colormap (False) or a interpolated colormap (True)
        should be generated. The default is False
    name : str
        the name of the new colormap
        The default is "new_cmap"
    Returns
    -------
    new_cmap : matplotlib.colormap
        a new colormap with the desired transparency
    """
    cmap = plt.get_cmap(cmap)
    new_cmap = cmap(np.arange(cmap.N))
    new_cmap[:, -1] = alpha

    if interpolate:
        new_cmap = LinearSegmentedColormap(name, new_cmap)
    else:
        new_cmap = ListedColormap(new_cmap, name=name)

    return new_cmap


# a simple progressbar
# taken from https://stackoverflow.com/a/34482761/9703451
def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)

    def show(j):
        x = int(size * j / count)
        file.write("\r%s[%s%s] %i/%i\r" % (prefix, "#" * x, "." * (size - x), j, count))
        file.flush()

    show(0)
    for i, item in enumerate(it):
        yield item
        show(i + 1)
    file.write("\n")
    file.flush()


class searchtree:
    def __init__(self, m):
        """
        Nearest-neighbour search.

        Parameters
        ----------
        m : eomaps.Maps
            The maps-object that provides the data.
        """
        self._m = m
        # set starting pick-distance to 50 times the radius
        self.set_search_radius("50")

        self._misses = 0

    @property
    def d(self):
        """Side-length of the search-rectangle (in units of the plot-crs)"""
        return self._d

    def set_search_radius(self, r):
        """
        Set the rectangle side-length that is used to limit the query.

        (e.g. only points that are within a rectangle of the specified size
         centered at the clicked point are considered!)

        Parameters
        ----------
        r : int, float or str, optional
            Set the radius of the (circular) area that is used to limit the
            number of pixels when searching for nearest-neighbours.

            - if `int` or `float`:
              The radius of the circle in units of the plot_crs
            - if `str`:
              A multiplication-factor for the estimated pixel-radius.
              (e.g. a circle with (`r=search_radius * m.shape.radius`) is
              used if possible and else np.inf is used.

            The default is "50" (e.g. 50 times the pixel-radius).
        """

        self._search_radius = r

        if isinstance(r, str):
            # evaluate an appropriate pick-distance
            if getattr(self._m.shape, "radius_crs", None) != "out":
                try:
                    radius = self._m.set_shape._estimate_radius(self._m, "out", np.max)
                except AssertionError:
                    print(
                        "EOmaps: Unable to estimate search-radius based on data."
                        "Defaulting to `np.inf`. "
                        "See `m.tree.set_search_radius` for more details!"
                    )
                    radius = [np.inf]
            else:
                radius = self._m.shape.radius

            self._d = np.max(radius) * float(self._search_radius)
        elif isinstance(r, (int, float, np.number)):
            self._d = float(r)
        else:
            raise TypeError(
                f"EOmaps: {r} is not a valid search-radius. "
                "The search-radius must be provided as "
                "int, float or as string that can be identified "
                "as float!"
            )

    def _identify_search_subset(self, x, d):
        # select a rectangle around the pick-coordinates
        # (provides tremendous speedups for very large datasets)

        if self._m._data_manager.x0_1D is not None:
            # TODO check this!
            # get a rectangular boolean mask
            mx = np.logical_and(
                self._m._data_manager.x0_1D > (x[0] - d),
                self._m._data_manager.x0_1D < (x[0] + d),
            )
            my = np.logical_and(
                self._m._data_manager.y0_1D > (x[1] - d),
                self._m._data_manager.y0_1D < (x[1] + d),
            )

            mx_id, my_id = np.where(mx)[0], np.where(my)[0]
            m_rect_x, m_rect_y = np.meshgrid(mx_id, my_id)

            x_rect = self._m._data_manager.x0[m_rect_x].ravel()
            y_rect = self._m._data_manager.y0[m_rect_y].ravel()

            # get the unravelled indexes of the boolean mask
            idx = np.ravel_multi_index((m_rect_x, m_rect_y), self._m._zshape).ravel()
        else:
            # get a rectangular boolean mask
            mx = np.logical_and(
                self._m._data_manager.x0 > (x[0] - d),
                self._m._data_manager.x0 < (x[0] + d),
            )
            my = np.logical_and(
                self._m._data_manager.y0 > (x[1] - d),
                self._m._data_manager.y0 < (x[1] + d),
            )

            m = np.logical_and(mx, my)
            # get the indexes of the search-rectangle
            idx = np.where(m.ravel())[0]

            if len(idx) > 0:
                x_rect = self._m._data_manager.x0[m].ravel()
                y_rect = self._m._data_manager.y0[m].ravel()
            else:
                x_rect, y_rect = [], []

        if len(x_rect) > 0 and len(y_rect) > 0:
            mcircle = (x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2 < d**2
            return x_rect[mcircle], y_rect[mcircle], idx[mcircle]
        else:
            return [], [], []

    def query(self, x, k=1, d=None, pick_relative_to_closest=True):
        """
        Find the (k) closest points.

        Parameters
        ----------
        x : list, tuple or np.array of length 2
            The x- and y- coordinates to search.
        k : int, optional
            The number of points to identify.
            The default is 1.
        d : float, optional
            The max. distance (in plot-crs) to consider when identifying points.
            If None, the currently assigned distance (e.g. `m.tree.d`) is used.
            (see `m.tree.set_search_radius` on how to set the default distance!)
            The default is None.
        pick_relative_to_closest : bool, optional
            ONLY relevant if `k > 1`.

            - If True: pick (k) nearest neighbours based on the center of the
              closest point
            - If False: pick (k) nearest neighbours based on the click-position

            The default is True.

        Returns
        -------
        i : list
            The indexes of the selected datapoints with respect to the
            flattened array.
        """
        if d is None:
            d = self.d
        i = None
        # take care of 1D coordinates and 2D data
        if self._m._data_manager.x0_1D is not None:
            if k > 1 and pick_relative_to_closest is True:
                ix = np.argmin(np.abs(self._m._data_manager.x0_1D - x[0]))
                iy = np.argmin(np.abs(self._m._data_manager.y0_1D - x[1]))
                # query again (starting from the closest point)
                return self.query(
                    (self._m._data_manager.x0_1D[ix], self._m._data_manager.y0_1D[iy]),
                    k=k,
                    d=d,
                    pick_relative_to_closest=False,
                )
            else:

                # perform a brute-force search for 1D coords
                ix = np.argpartition(
                    np.abs(self._m._data_manager.x0_1D - x[0]), range(k)
                )[:k]
                iy = np.argpartition(
                    np.abs(self._m._data_manager.y0_1D - x[1]), range(k)
                )[:k]

                if k > 1:
                    # select a circle within the kxk rectangle
                    ix, iy = np.meshgrid(ix, iy)

                    idx = np.ravel_multi_index(
                        (iy, ix),
                        (
                            self._m._data_manager.y0_1D.size,
                            self._m._data_manager.x0_1D.size,
                        ),
                    ).ravel()

                    x_rect, y_rect = (
                        i.ravel()
                        for i in (
                            self._m._data_manager.x0_1D[ix],
                            self._m._data_manager.y0_1D[iy],
                        )
                    )

                    i = idx[
                        ((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argpartition(
                            range(int(min(k, x_rect.size)))
                        )[:k]
                    ]

                else:
                    ix = np.argmin(np.abs(self._m._data_manager.x0_1D - x[0]))
                    iy = np.argmin(np.abs(self._m._data_manager.y0_1D - x[1]))

                    # TODO check treatment of transposed data in here!
                    i = np.ravel_multi_index(
                        (iy, ix),
                        (
                            self._m._data_manager.y0_1D.size,
                            self._m._data_manager.x0_1D.size,
                        ),
                    )

                return i

        x_rect, y_rect, idx = self._identify_search_subset(x, d)
        if len(idx) > 0:

            if k == 1:
                i = idx[((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argmin()]
            else:
                if pick_relative_to_closest is True:
                    i0 = ((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argmin()

                    return self.query(
                        (x_rect[i0], y_rect[i0]),
                        k=k,
                        d=d,
                        pick_relative_to_closest=False,
                    )
                i = idx[
                    ((x_rect - x[0]) ** 2 + (y_rect - x[1]) ** 2).argpartition(
                        range(min(k, x_rect.size))
                    )[:k]
                ]
        else:
            # show a warning if no points are found in the search area
            if self._misses < 3:
                self._misses += 1
            else:
                text = "Found no data here...\n Increase search_radius?"
                # TODO fix cleanup of temporary artists!!
                self._m.add_annotation(
                    xy=x,
                    permanent=False,
                    text=text,
                    xytext=(0.98, 0.98),
                    textcoords=self._m.ax.transAxes,
                    horizontalalignment="right",
                    verticalalignment="top",
                    arrowprops=None,
                    fontsize=7,
                    bbox=dict(ec="r", fc=(1, 0.9, 0.9, 0.5), lw=0.25, boxstyle="round"),
                )

            i = None

        return i


class LayoutEditor:
    def __init__(self, m, modifier="alt+d", cb_modifier="control"):
        self.modifier = modifier
        self.cb_modifier = cb_modifier

        self.m = m
        self.f = self.m.parent.f

        self._ax_picked = []
        self._m_picked = []
        self._cb_picked = []

        self._modifier_pressed = False

        self.cids = []

        # indicator if the pick-callback should be re-attached or not
        self._reattach_pick_cb = False

        self.f.canvas.mpl_connect("key_press_event", self.cb_key_press)

        self._artists_visible = dict()
        self._ax_visible = dict()
        self._ax_animated = dict()

        # the snap-to-grid interval (0 means no snapping)
        self._snap_id = 5

        # an optional filepath that will be used to store the layout once the
        # editor exits
        self._filepath = None

        # indicator if scaling should be in horizontal or vertical direction
        self._scale_direction = "both"

        # indicator if multiple-axis select key is pressed or not (e.g. "shift")
        self._shift_pressed = False

    @property
    def modifier_pressed(self):
        return self._modifier_pressed

    @modifier_pressed.setter
    def modifier_pressed(self, val):
        self._modifier_pressed = val
        self.m.cb.execute_callbacks(not val)

    @property
    def ms(self):
        return [self.m.parent, *self.m.parent._children]

    @property
    def maxes(self):
        return [m.ax for m in self.ms]

    @property
    def cbaxes(self):
        axes = list()
        for m in self.ms:
            axes.extend((i._ax for i in m._colorbars))
        return axes

    @property
    def axes(self):
        return self.f.axes

    def get_spines_visible(self):
        return [
            {key: val.get_visible() for key, val in ax.spines.items()}
            for ax in self.axes
        ]

    @property
    def cbs(self):
        # get all colorbars
        cbs = list()
        for m in self.ms:
            cbs.extend(m._colorbars)
        return cbs

    @staticmethod
    def roundto(x, base=10):
        if base == 0:
            return x
        if x % base <= base / 2:
            return x - x % base
        else:
            return x + (base - x % base)

    def _get_move_with_key_bbox(self, ax, key):
        snapx, snapy = self._snap
        intervalx, intervaly = (
            max(0.25, snapx),
            max(0.25, snapy),
        )

        if key == "left":
            bbox = Bbox.from_bounds(
                self.roundto(ax.bbox.x0 - intervalx, snapx),
                ax.bbox.y0,
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "right":
            bbox = Bbox.from_bounds(
                self.roundto(ax.bbox.x0 + intervalx, snapx),
                ax.bbox.y0,
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "up":
            bbox = Bbox.from_bounds(
                ax.bbox.x0,
                self.roundto(ax.bbox.y0 + intervaly, snapy),
                ax.bbox.width,
                ax.bbox.height,
            )
        elif key == "down":
            bbox = Bbox.from_bounds(
                ax.bbox.x0,
                self.roundto(ax.bbox.y0 - intervaly, snapy),
                ax.bbox.width,
                ax.bbox.height,
            )

        bbox = bbox.transformed(self.f.transFigure.inverted())
        return bbox

    def _get_move_bbox(self, ax, x, y):
        w, h = ax.bbox.width, ax.bbox.height
        x0, y0 = (
            self._start_ax_position[ax][0] + (x - self._start_position[0]),
            self._start_ax_position[ax][1] + (y - self._start_position[1]),
        )

        if self._snap_id > 0:
            sx, sy = self._snap
            x0 = self.roundto(x0, sx)
            y0 = self.roundto(y0, sy)

        bbox = Bbox.from_bounds(x0, y0, w, h).transformed(self.f.transFigure.inverted())

        return bbox

    def _get_resize_bbox(self, ax, step):
        origw, origh = ax.bbox.width, ax.bbox.height
        x0, y0 = ax.bbox.x0, ax.bbox.y0

        sx, sy = self._snap

        h, w = origh, origw

        if self._scale_direction == "horizontal":
            w += max(0.25, sx) * step
            w = self.roundto(w, sx)
        elif self._scale_direction == "vertical":
            h += max(0.25, sy) * step
            h = self.roundto(h, sy)
        else:
            w += max(0.25, sx) * step
            w = self.roundto(w, sx)

            h += max(0.25, sy) * step
            h = self.roundto(h, sy)

        if h <= 0 or w <= 0:
            return

        # x0 = self.roundto(x0, sx)
        # y0 = self.roundto(y0, sy)

        # keep the center-position of the scaled axis
        x0 = x0 + (origw - w) / 2
        y0 = y0 + (origh - h) / 2

        bbox = Bbox.from_bounds(x0, y0, w, h).transformed(self.f.transFigure.inverted())

        if bbox.width <= 0 or bbox.height <= 0:
            return

        return bbox

    def _color_unpicked(self, ax):
        for spine in ax.spines.values():
            spine.set_edgecolor("b")

            if ax in self._ax_visible and self._ax_visible[ax]:
                spine.set_linestyle("-")
                spine.set_linewidth(1)
            else:
                spine.set_linestyle(":")
                spine.set_linewidth(1)

    def _color_picked(self, ax):
        for spine in ax.spines.values():
            spine.set_edgecolor("r")

            if ax in self._ax_visible and self._ax_visible[ax]:
                spine.set_linestyle("-")
                spine.set_linewidth(2)
            else:
                spine.set_linestyle(":")
                spine.set_linewidth(1)

    def _color_axes(self):
        for ax in self.axes:
            self._color_unpicked(ax)

        for cb in self.cbs:
            for ax in (cb.ax_cb, cb.ax_cb_plot):
                self._color_unpicked(ax)

        for ax in self._ax_picked:
            if ax is not None:
                self._color_picked(ax)

        for cb in self._cb_picked:
            for ax in (cb.ax_cb, cb.ax_cb_plot):
                self._color_picked(ax)

    def _set_startpos(self, event):
        self._start_position = (event.x, event.y)
        self._start_ax_position = {
            i: (i.bbox.x0, i.bbox.y0)
            for i in (*self._ax_picked, *(cb._ax for cb in self._cb_picked))
        }

    def cb_release(self, event):
        self._set_startpos(event)
        self._remove_snap_grid()

    def cb_pick(self, event):
        if not self.modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        eventax = event.inaxes

        if eventax not in self.axes:
            # if no axes is clicked "unpick" previously picked axes
            if len(self._ax_picked) + len(self._cb_picked) == 0:
                # if there was nothing picked there's nothing to do...
                return

            self._ax_picked = []
            self._cb_picked = []
            self._m_picked = []
            self._color_axes()
            self.m.redraw()
            return

        if self._shift_pressed:
            if eventax in self.maxes:
                m = self.ms[self.maxes.index(eventax)]
                if eventax in self._ax_picked:
                    self._ax_picked.remove(eventax)
                else:
                    self._ax_picked.append(eventax)

                if m in self._m_picked:
                    self._m_picked.remove(m)
                else:
                    self._m_picked.append(m)
            elif eventax in self.cbaxes:
                cb = self.cbs[self.cbaxes.index(eventax)]
                if cb in self._cb_picked:
                    self._cb_picked.remove(cb)
                else:
                    self._cb_picked.append(cb)
            else:
                if eventax in self._ax_picked:
                    self._ax_picked.remove(eventax)
                else:
                    self._ax_picked.append(eventax)
        else:
            selected = eventax in self._ax_picked
            if eventax in self.cbaxes:
                selected = (
                    selected or self.cbs[self.cbaxes.index(eventax)] in self._cb_picked
                )

            if not selected:
                self._m_picked = []
                self._cb_picked = []
                self._ax_picked = []

                if eventax in self.axes:
                    if eventax in self.maxes:
                        self._ax_picked.append(eventax)
                        self._m_picked.append(self.ms[self.maxes.index(eventax)])
                    elif eventax in self.cbaxes:
                        self._cb_picked.append(self.cbs[self.cbaxes.index(eventax)])
                    else:
                        self._m_picked = []
                        self._cb_picked = []
                        self._ax_picked.append(eventax)

                    self._show_snap_grid()

            else:
                self._show_snap_grid()

        self._color_axes()
        self._set_startpos(event)
        self.m.redraw()

    def cb_move_with_key(self, event):
        if not self.modifier_pressed:
            return
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        if event.key not in ["left", "right", "up", "down"]:
            return

        for ax in self._ax_picked:
            bbox = self._get_move_with_key_bbox(ax, event.key)
            ax.set_position(bbox)

        for cb in self._cb_picked:
            bbox = self._get_move_with_key_bbox(cb._ax, event.key)
            cb.set_position(bbox)

        self._color_axes()
        self.m.redraw()

    def cb_move(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self.modifier_pressed:
                return False

        if event.button != 1:
            return

        for ax in self._ax_picked:
            if ax is None:
                return

            bbox = self._get_move_bbox(ax, event.x, event.y)
            ax.set_position(bbox)

        for cb in self._cb_picked:
            if cb is None:
                return

            bbox = self._get_move_bbox(cb._ax, event.x, event.y)
            cb.set_position(bbox)

        self.m.redraw()

    def cb_scroll(self, event):
        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False
        if self.modifier is not None:
            if not self.modifier_pressed:
                return False

        # ordinary axes picked
        if self._scale_direction not in ["set_hist_size"]:
            for ax in self._ax_picked:
                if ax is None:
                    continue
                resize_bbox = self._get_resize_bbox(ax, event.step)
                if resize_bbox is not None:
                    ax.set_position(resize_bbox)

        for cb in self._cb_picked:
            if cb is None:
                continue

            if self._scale_direction == "set_hist_size":
                start_size = cb._hist_size

                new_size = np.clip(start_size + event.step * 0.02, 0.0, 1.0)
                cb.set_hist_size(new_size)
                self._ax_visible[cb.ax_cb_plot] = cb.ax_cb_plot.get_visible()
            else:
                resize_bbox = self._get_resize_bbox(cb._ax, event.step)
                if resize_bbox is not None:
                    cb.set_position(resize_bbox)

        self._color_axes()
        self.m.redraw()

    def cb_key_press(self, event):
        # release shift key on every keypress
        self._shift_pressed = False

        if (self.f.canvas.toolbar is not None) and self.f.canvas.toolbar.mode != "":
            return False

        if (event.key == self.modifier) and (not self.modifier_pressed):
            self._make_draggable()
            return
        elif (event.key == self.modifier or event.key == "escape") and (
            self.modifier_pressed
        ):
            self._undo_draggable()
            return
        else:
            if not self.modifier_pressed:
                # only continue if  modifier is pressed!
                return

        if event.key == "h":
            self._scale_direction = "horizontal"
        elif event.key == "v":
            self._scale_direction = "vertical"
        elif event.key == "control":
            self._scale_direction = "set_hist_size"

        elif event.key == "shift":
            self._shift_pressed = True

        # assign snaps with keys 0-9
        if event.key in map(str, range(10)):
            self._snap_id = int(event.key)
            self._show_snap_grid()

        # assign snaps with keys 0-9
        if event.key in ["+", "-"]:

            class dummyevent:
                pass

            d = dummyevent()
            d.key = event.key
            d.step = 1 * {"+": 1, "-": -1}[event.key]

            self.cb_scroll(d)

    def cb_key_release(self, event):
        # reset scale direction on every key release event
        if event.key in ["h", "v", "control"]:
            self._scale_direction = "both"
        if event.key in ["shift"]:
            self._shift_pressed = False

    @property
    def _snap(self):
        # grid-separation distance
        if self._snap_id == 0:
            snap = (0, 0)
        else:
            n = (self.f.bbox.width / 400) * (self._snap_id)

            snap = (n, n)

        return snap

    def _undo_draggable(self):

        toolbar = getattr(self.m.f, "toolbar", None)
        if toolbar is not None:
            # Reset the axes stack to make sure the "home" "back" and "forward" buttons
            # of the toolbar do not reset axis positions
            # see "matplotlib.backend_bases.NavigationToolbar2.update"
            if hasattr(toolbar, "update"):
                try:
                    toolbar.update()
                except Exception:
                    print("EOmaps: Error while trying to reset the axes stack!")

        # clear all picks on exit
        self._ax_picked = []
        self._cb_picked = []
        self._m_picked = []

        print("EOmaps: Exiting layout-editor mode...")
        if self._filepath:
            try:
                self.m.get_layout(filepath=self._filepath, override=True)
            except Exception:
                print(
                    "EOmaps WARNING: The layout could not be saved to the provided "
                    + f"filepath: '{self._filepath}'."
                )

        # reset the "animated" state of the axes
        for ax, val in self._ax_animated.items():
            ax.set_animated(val)

        for ax, frameQ, spine_vis, patch_props, spine_props in zip(
            self.axes,
            self._frameon,
            self._spines_visible,
            self._patchprops,
            self._spineprops,
        ):
            pvis, pfc, pec, plw, palpha = patch_props
            ax.patch.set_visible(pvis)
            ax.patch.set_fc(pfc)
            ax.patch.set_ec(pec)
            ax.patch.set_lw(plw)
            ax.patch.set_alpha(palpha)

            ax.set_frame_on(frameQ)

            for key, (svis, sfc, sec, slw, salpha) in spine_props.items():
                ax.spines[key].set_visible(svis)
                ax.spines[key].set_fc(sfc)
                ax.spines[key].set_ec(sec)
                ax.spines[key].set_lw(slw)
                ax.spines[key].set_alpha(salpha)

            while len(self.cids) > 0:
                cid = self.cids.pop(-1)
                self.f.canvas.mpl_disconnect(cid)

        for a, visQ in self._artists_visible.items():
            a.set_visible(visQ)
        self._artists_visible.clear()

        # apply changes to the visibility state of the axes
        # do this at the end since axes might also be artists!
        for ax, val in self._ax_visible.items():
            ax.set_visible(val)

            # remember any axes that are intentionally hidden
            if not val:
                if ax in self.m.BM._bg_artists[self.m.BM.bg_layer]:
                    self.m.BM._hidden_artists.add(ax)
            else:
                if ax in self.m.BM._hidden_artists:
                    self.m.BM._hidden_artists.remove(ax)

        for cb in self.cbs:
            if cb is not None:
                for p in cb.ax_cb_plot.patches:
                    p.set_visible(True)

        self._ax_visible.clear()
        self._ax_animated.clear()

        # do this at the end!
        self.modifier_pressed = False

        # make sure the snap-grid is removed
        self._remove_snap_grid()
        self.m.redraw()

    def _make_draggable(self, filepath=None):
        self._filepath = filepath

        # all ordinary callbacks will not execute if" self.modifier_pressed" is True!
        print("EOmaps: Activating layout-editor mode (press 'esc' to exit)")
        if filepath:
            print("EOmaps: On exit, the layout will be saved to:\n       ", filepath)

        # remember the visibility state of the axes
        # do this as the first thing since axes might be artists as well!
        for ax in self.axes:
            self._ax_visible[ax] = ax.get_visible()
            self._ax_animated[ax] = ax.get_animated()
            # treat all axes as "non-animated"
            # TODO implement a better treatment for this
            # (e.g. just blit them on draw)!
            ax.set_animated(False)

        # make all artists invisible (and remember their visibility state for later)
        for a in {
            *self.m.f.artists,
            *chain(*self.m.BM._bg_artists.values()),
            *chain(*self.m.BM._artists.values()),
        }:
            # keep axes visible!
            if not isinstance(a, plt.Axes):
                self._artists_visible[a] = a.get_visible()
                a.set_visible(False)

        for cb in self.cbs:
            if cb is not None:
                for p in cb.ax_cb_plot.patches:
                    p.set_visible(False)

        # remember which spines were visible before
        self._spines_visible = self.get_spines_visible()
        self._frameon = [i.get_frame_on() for i in self.axes]
        self._patchprops = [
            (
                i.patch.get_visible(),
                i.patch.get_fc(),
                i.patch.get_ec(),
                i.patch.get_lw(),
                i.patch.get_alpha(),
            )
            for i in self.axes
        ]

        self._spineprops = [
            {
                name: (
                    s.get_visible(),
                    s.get_fc(),
                    s.get_ec(),
                    s.get_lw(),
                    s.get_alpha(),
                )
                for name, s in i.spines.items()
            }
            for i in self.axes
        ]

        self.modifier_pressed = True

        for ax in self.axes:
            ax.patch.set_visible(True)
            ax.patch.set_facecolor("w")
            ax.patch.set_alpha(0.75)

            if ax not in chain(
                self.m.BM._bg_artists.get(self.m.BM.bg_layer, []),
                self.m.BM._artists.get(self.m.BM.bg_layer, []),
            ):
                continue
            ax.set_visible(True)

            ax.set_frame_on(True)
            for spine in ax.spines.values():
                spine.set_visible(True)

        self._color_axes()

        if len(self.cids) == 0:
            self.cids.append(self.f.canvas.mpl_connect("scroll_event", self.cb_scroll))
            self.cids.append(
                self.f.canvas.mpl_connect("button_press_event", self.cb_pick)
            )

            self.cids.append(
                self.f.canvas.mpl_connect("button_release_event", self.cb_release)
            )

            self.cids.append(
                self.f.canvas.mpl_connect("motion_notify_event", self.cb_move)
            )

            self.cids.append(
                self.f.canvas.mpl_connect("key_press_event", self.cb_move_with_key)
            )

            self.cids.append(
                self.f.canvas.mpl_connect("key_release_event", self.cb_key_release)
            )

        self.m.redraw()

    def _show_snap_grid(self, snap=None):
        # snap = (snapx, snapy)

        if snap is None:
            if self._snap_id == 0:
                return
            else:
                snapx, snapy = self._snap
        else:
            snapx, snapy = snap

        self._remove_snap_grid()

        bbox = self.m.f.bbox
        t = self.m.f.transFigure.inverted()

        gx, gy = np.mgrid[
            0 : int(bbox.width) + int(snapx) : snapx,
            0 : int(bbox.height) + int(snapy) : snapy,
        ]
        g = t.transform(np.column_stack((gx.flat, gy.flat)))

        l = Line2D(
            *g.T,
            lw=0,
            marker=".",
            markerfacecolor="k",
            markeredgecolor="none",
            ms=(snapx + snapy) / 6,
        )
        self._snap_grid_artist = self.m.f.add_artist(l)

        self.f.draw_artist(self._snap_grid_artist)
        self.f.canvas.blit()

    def _remove_snap_grid(self):
        if hasattr(self, "_snap_grid_artist"):
            self._snap_grid_artist.remove()
            del self._snap_grid_artist

        self.m.redraw()

    def get_layout(self, filepath=None, override=False, precision=5):
        """
        Get the positions of all axes within the current plot.

        To re-apply a layout, use:

            >>> l = m.get_layout()
            >>> m.set_layout(l)

        Note
        ----
        The returned list is only a snapshot of the current layout.
        It can only be re-applied to a given figure if the order at which the axes are
        created remains the same!

        Parameters
        ----------
        filepath : str or pathlib.Path, optional
            If provided, a json-file will be created at the specified destination that
            can be used in conjunction with `m.set_layout(...)` to apply the layout:

            >>> m.get_layout(filepath=<FILEPATH>, override=True)
            >>> m.apply_layout_layout(<FILEPATH>)

            You can also manually read-in the layout-dict via:
            >>> import json
            >>> layout = json.load(<FILEPATH>)
        override: bool
            Indicator if the file specified as 'filepath' should be overwritten if it
            already exists.
            The default is False.
        precision : int or None
            The precision of the returned floating-point numbers.
            If None, all available digits are returned
            The default is 5
        Returns
        -------
        layout : dict or None
            A dict of the positons of all axes, e.g.: {1:(x0, y0, width height), ...}
        """
        figsize = [*self.f.get_size_inches()]

        axes = [
            a for a in self.axes if a.get_label() not in ["EOmaps_cb", "EOmaps_cb_hist"]
        ]

        # identify relevant colorbars
        colorbars = [getattr(m, "colorbar", None) for m in self.ms]
        cbaxes = [getattr(cb, "_ax", None) for cb in colorbars]
        cbs = [(colorbars[cbaxes.index(a)] if a in cbaxes else None) for a in axes]
        # -----------

        layout = dict()
        layout["figsize"] = figsize

        for i, ax in enumerate(axes):
            if cbs[i] is not None:
                if cbs[i]._ax.get_axes_locator() is not None:
                    continue

            label = ax.get_label()
            name = f"{i}_{label}"
            if precision is not None:
                layout[name] = np.round(ax.get_position().bounds, precision).tolist()
            else:
                layout[name] = ax.get_position().bounds

            if cbs[i] is not None:
                layout[f"{name}_histogram_size"] = cbs[i]._hist_size

        if filepath is not None:
            filepath = Path(filepath)
            assert (
                not filepath.exists() or override
            ), f"The file {filepath} already exists! Use override=True to relace it."
            with open(filepath, "w") as file:
                json.dump(layout, file)
            print("EOmaps: Layout saved to:\n       ", filepath)

        return layout

    def apply_layout(self, layout):
        """
        Set the positions of all axes within the current plot based on a previously
        defined layout.

        To apply a layout, use:

            >>> l = m.get_layout()
            >>> m.set_layout(l)

        To save a layout to disc and apply it at a later stage, use
            >>> m.get_layout(filepath=<FILEPATH>)
            >>> m.set_layout(<FILEPATH>)

        Note
        ----
        The returned list is only a snapshot of the current layout.
        It can only be re-applied to a given figure if the order at which the axes are
        created remains the same!

        Parameters
        ----------
        layout : dict, str or pathlib.Path
            If a dict is provided, it is directly used to define the layout.

            If a string or a pathlib.Path object is provided, it will be used to
            read a previously dumped layout (e.g. with `m.get_layout(filepath)`)

        """
        if isinstance(layout, (str, Path)):
            with open(layout, "r") as file:
                layout = json.load(file)

        # check if all relevant axes are specified in the layout
        valid_keys = set(self.get_layout())
        if valid_keys != set(layout):
            warnings.warn(
                "EOmaps: The the layout does not match the expected structure! "
                "Layout might not be properly restored. "
                "Invalid or missing keys:\n"
                f"{sorted(valid_keys.symmetric_difference(set(layout)))}\n"
            )

        # set the figsize
        figsize = layout.pop("figsize", None)
        if figsize is not None:
            self.f.set_size_inches(*figsize)

        axes = [
            a for a in self.axes if a.get_label() not in ["EOmaps_cb", "EOmaps_cb_hist"]
        ]

        # identify relevant colorbars
        colorbars = [getattr(m, "colorbar", None) for m in self.ms]
        cbaxes = [getattr(cb, "_ax", None) for cb in colorbars]
        cbs = [(colorbars[cbaxes.index(a)] if a in cbaxes else None) for a in axes]

        for key in valid_keys.intersection(set(layout)):
            val = layout[key]

            i = int(key[: key.find("_")])
            if key.endswith("_histogram_size"):
                cbs[i].set_hist_size(val)
            else:
                axes[i].set_position(val)

        self.m.redraw()


# taken from https://matplotlib.org/stable/tutorials/advanced/blitting.html#class-based-example
class BlitManager:
    def __init__(self, m):
        """
        Parameters
        ----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for sub-classes of the Agg
            canvas which have the `~FigureCanvasAgg.copy_from_bbox` and
            `~FigureCanvasAgg.restore_region` methods.

        animated_artists : Iterable[Artist]
            List of the artists to manage
        """

        self._m = m

        self._bg = None
        self._artists = dict()

        self._bg_artists = dict()
        self._bg_layers = dict()

        # grab the background on every draw
        self.cid = self.canvas.mpl_connect("draw_event", self.on_draw)

        self._after_update_actions = []
        self._after_restore_actions = []
        self._bg_layer = 0

        self._artists_to_clear = dict()

        self._hidden_artists = set()

        self._refetch_bg = True
        self._layers_to_refetch = set()

        # TODO these activate some crude fixes for jupyter notebook and webagg
        # backends... proper fixes would be nice
        self._mpl_backend_blit_fix = any(
            i in plt.get_backend().lower() for i in ["webagg", "nbagg"]
        )

        # self._mpl_backend_force_full = any(
        #     i in plt.get_backend().lower() for i in ["nbagg"]
        # )
        # recent fixes seem to take care of this nbagg issue...
        self._mpl_backend_force_full = False
        self._mpl_backend_blit_fix = False

        self._on_layer_change = dict()
        self._on_layer_activation = dict()

        self._on_add_bg_artist = list()
        self._on_remove_bg_artist = list()

        self._before_fetch_bg_actions = list()
        self._before_update_actions = list()

    @property
    def figure(self):
        return self._m.f

    @property
    def canvas(self):
        return self.figure.canvas

    def _do_on_layer_change(self, layer):
        # general callbacks executed on any layer change
        if len(self._on_layer_change) > 0:
            actions = list(self._on_layer_change)
            for action in actions:
                action(self._on_layer_change[action], layer)

        # individual callables executed if a specific layer is activated
        for l in layer.split("|"):
            activate_action = self._on_layer_activation.get(l, None)
            if activate_action is not None:
                actions = list(activate_action)
                for action in actions:
                    action(activate_action[action], l)

    @contextmanager
    def _without_artists(self, artists=None, layer=None):
        try:
            removed_artists = {layer: set(), "all": set()}
            if artists is None:
                yield
            else:
                for a in artists:
                    if a in self._artists.get(layer, []):
                        self.remove_artist(a, layer=layer)
                        removed_artists[layer].add(a)
                    elif a in self._artists.get("all", []):
                        self.remove_artist(a, layer="all")
                        removed_artists["all"].add(a)

                yield
        finally:
            for layer, artists in removed_artists.items():
                for a in artists:
                    self.add_artist(a, layer=layer)

    def _get_active_bg(self, exclude_artists=None):
        with self._without_artists(artists=exclude_artists, layer=self.bg_layer):
            # fetch the current background (incl. dynamic artists)
            self.update()
            from contextlib import ExitStack

            with ExitStack() as stack:
                # get rid of the axes background patch
                for ax_i in self._m.f.axes:
                    stack.enter_context(
                        ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                    )
                # get rid of the figure background patch
                stack.enter_context(
                    self._m.f.patch._cm_set(facecolor="none", edgecolor="none")
                )

                bg = self.canvas.copy_from_bbox(self.figure.bbox)

        return bg

    @property
    def bg_layer(self):
        return self._bg_layer

    @bg_layer.setter
    def bg_layer(self, val):
        # make sure we use a "full" update for webagg and ipympl backends
        # (e.g. force full redraw of canvas instead of a diff)
        self.canvas._force_full = True
        self._bg_layer = val

        # a general callable to be called on every layer change
        self._do_on_layer_change(layer=val)

        layer_names = val.split("|")

        # hide all colorbars that are not on the visible layer
        for m in [self._m.parent, *self._m.parent._children]:
            layer_visible = m.layer in layer_names

            for cb in m._colorbars:
                if layer_visible:
                    m.colorbar.set_visible(True)
                else:
                    m.colorbar.set_visible(False)

        # hide all wms_legends that are not on the visible layer
        if hasattr(self._m.parent, "_wms_legend"):
            for layer, legends in self._m.parent._wms_legend.items():
                if layer in layer_names:
                    for i in legends:
                        i.set_visible(True)
                else:
                    for i in legends:
                        i.set_visible(False)

        self._clear_temp_artists("on_layer_change")

        if val not in self._bg_layers:
            self.fetch_bg(val)

    def on_layer(self, func, layer=None, persistent=False, m=None):
        """
        Add callables that are executed whenever the visible layer changes.

        NOTE: if m is None this function always falls back to the parent Maps-object!!

        Parameters
        ----------
        func : callable
            The callable to use.
            The call-signature is:

            >>> def func(m, l):
            >>>    # m... the Maps-object
            >>>    # l... the name of the layer


        layer : str or None, optional
            - If str: The function will only be called if the specified layer is
              activated.
            - If None: The function will be called on any layer-change.

            The default is None.
        persistent : bool, optional
            Indicator if the function should be called only once (False) or if it
            should be called whenever a layer is activated.
            The default is False.

        """
        if m is None:
            m = self._m

        if layer is None:
            if not persistent:

                def remove_decorator(func):
                    def inner(*args, **kwargs):
                        try:
                            func(*args, **kwargs)
                            if inner in self._on_layer_change:
                                self._on_layer_change.pop(inner)
                        except IndexError:
                            pass

                    return inner

                func = remove_decorator(func)

            self._on_layer_change[func] = m

        else:
            if not persistent:

                def remove_decorator(func):
                    def inner(*args, **kwargs):
                        try:
                            func(*args, **kwargs)
                            if inner in self._on_layer_activation.get(layer, dict()):
                                self._on_layer_activation[layer].pop(inner)
                        except IndexError:
                            pass

                    return inner

                func = remove_decorator(func)

            self._on_layer_activation.setdefault(layer, dict())[func] = m

    def _refetch_layer(self, layer):
        if layer == "all":
            # if the all layer changed, all backgrounds need a refetch
            self._refetch_bg = True
        else:
            # set any background that contains the layer for refetch
            self._layers_to_refetch.add(layer)
            for l in self._bg_layers:
                if layer in l.split("|"):
                    self._layers_to_refetch.add(l)

    def get_bg_artists(self, layer):
        artists = set()
        for l in np.atleast_1d(layer):
            # get all relevant artists for combined background layers
            l = str(l)  # w make sure we convert non-string layer names to string!

            # get artists defined on the layer itself
            # Note: it's possible to create explicit multi-layers and attach
            # artists that are only visible if both layers are visible! (e.g. "l1|l2")
            artists = artists.union(set(self._bg_artists.get(l, [])))

        artists = [*artists]  # convert to list for sorting
        artists.sort(key=lambda x: getattr(x, "zorder", -1))

        return artists

    def _combine_bgs(self, layer):
        # TODO decide on layer-ordering! (currently transposed)
        layers, alphas = [], []
        for l in layer.split("|")[::-1]:
            if l.endswith("}") and "{" in l:
                try:
                    name, a = l.split("{")
                    a = float(a.replace("}", ""))

                    layers.append(name)
                    alphas.append(a)
                except Exception:
                    raise TypeError(
                        "EOmaps: unable to parse multilayer-transparency " f"for '{l}'"
                    )
            else:
                layers.append(l)
                alphas.append(1)

        # make sure all layers are already fetched
        for l in layers:
            if l not in self._bg_layers:
                # execute actions on layer-changes
                # (to make sure all lazy WMS services are properly added)
                self._do_on_layer_change(layer=l)
                self._do_fetch_bg(l)

        gc = self.canvas.renderer.new_gc()
        gc.set_clip_rectangle(self.canvas.figure.bbox)

        # switch to a blank background layer before merging backgrounds
        # TODO is there a beter way to avoid drawing on initial backgrounds?
        initial_layer = self._bg_layer
        self._m.bg_layer = "__BLANK__"

        x0, y0, w, h = self.figure.bbox.bounds
        for l, a in zip(layers, alphas):
            rgba = self._get_array(l, a=a)
            self.canvas.renderer.draw_image(
                gc,
                int(x0),
                int(y0),
                rgba[int(y0) : int(y0 + h), int(x0) : int(x0 + w), :],
            )
        # cache the combined background
        self._bg_layers[layer] = self._m.f.canvas.copy_from_bbox(self._m.f.bbox)
        gc.restore()

        # restore initial layer
        self._m.show_layer(initial_layer)

    def _get_array(self, l, a=1):
        rgba = np.array(self._bg_layers[l])[::-1, :, :]
        if a != 1:
            rgba = rgba.copy()
            rgba[..., -1] = (rgba[..., -1] * a).astype(rgba.dtype)
        return rgba

    def _do_fetch_bg(self, layer=None, bbox=None):
        cv = self.canvas

        if layer is None:
            layer = self.bg_layer

        # use contextmanagers to make sure the background patches are not stored
        # in the buffer regions!
        with ExitStack() as stack:
            # get rid of the figure background patch
            stack.enter_context(
                self._m.f.patch._cm_set(facecolor="none", edgecolor="none")
            )
            # get rid of the axes background patch
            for ax_i in self._m.f.axes:
                stack.enter_context(
                    ax_i.patch._cm_set(facecolor="none", edgecolor="none")
                )

            # execute actions before fetching new artists
            # (e.g. update data based on extent etc.)
            for action in self._before_fetch_bg_actions:
                action(layer=layer, bbox=bbox)

            # execute actions on layer-changes
            # (to make sure all lazy WMS services are properly added)
            self._do_on_layer_change(layer=layer)

            if "|" in layer:
                if layer not in self._bg_layers:
                    self._combine_bgs(layer)
                return

            # get all relevant artists to plot and remember zorders
            # self.get_bg_artists() already returns artists sorted by zorder!
            allartists = self.get_bg_artists(["all", layer])

            # check if all artists are stale, and if so skip re-fetching the background
            # (only if also the axis extent is the same!)
            no_stale_artists = not any(art.stale for art in allartists)

            # don't re-fetch the background if it is not necessary
            if no_stale_artists and (self._bg_layers.get(layer, None) is not None):
                return

            if bbox is None:
                bbox = self.figure.bbox

            if not self._m.parent._layout_editor._modifier_pressed:
                # make all artists of the corresponding layer visible
                for l in self._bg_artists:
                    if l not in [layer, "all"]:
                        # artists on "all" are always visible!
                        # make all artists of other layers invisible
                        for art in self._bg_artists.get(l, []):
                            art.set_visible(False)

                for art in allartists:
                    if art not in self._hidden_artists:
                        art.set_visible(True)
                        # art.draw(cv.get_renderer())

                cv._force_full = True
                cv.draw()

                self._bg_layers[layer] = cv.copy_from_bbox(bbox)

    def fetch_bg(self, layer=None, bbox=None):
        cv = self.canvas

        if layer is None:
            layer = self.bg_layer

        if layer in self._bg_layers:
            # don't re-fetch existing layers
            # (layers get cleared automatically if limits)
            return

        # temporarily disconnect draw-event callback to avoid recursion
        # while we re-draw the artists
        if self.cid is not None:
            cv.mpl_disconnect(self.cid)
            self.cid = None

        # use contextmanagers to make sure the background patches are not stored
        # in the buffer regions!
        try:
            self._do_fetch_bg(layer, bbox)
        finally:
            # reconnect draw event
            if self.cid is None:
                self.cid = cv.mpl_connect("draw_event", self.on_draw)

    def on_draw(self, event):
        """Callback to register with 'draw_event'."""
        cv = self.canvas
        if event is not None:
            if event.canvas != cv:
                raise RuntimeError
        try:
            # reset all background-layers and re-fetch the default one
            if self._refetch_bg:
                self._bg_layers = dict()
                self._refetch_bg = False
            else:
                # remove all cached backgrounds that were tagged for refetch
                while len(self._layers_to_refetch) > 0:
                    self._bg_layers.pop(self._layers_to_refetch.pop(), None)

            if self.bg_layer not in self._bg_layers:
                # TODO there might be other reasons to re-fetch a background!
                self.fetch_bg()

            # workaround for nbagg backend to avoid glitches
            # it's slow but at least it works...
            # check progress of the following issuse
            # https://github.com/matplotlib/matplotlib/issues/19116
            if self._mpl_backend_blit_fix:
                self.update()
            else:
                self.update(blit=False)

            # re-draw indicator-shapes of active drawer
            # (to show indicators during zoom-events)
            active_drawer = getattr(self._m.parent, "_active_drawer", None)
            if active_drawer is not None:
                active_drawer.redraw(blit=False)

        except Exception:
            # we need to catch exceptions since QT does not like them...
            pass

    def add_artist(self, art, layer=None):
        """
        Add a dynamic-artist to be managed.
        (Dynamic artists are re-drawn on every update!)

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : str or None, optional
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is None in which case the layer of the base-Maps object is used.
        """

        if art.figure != self.figure:
            raise RuntimeError

        if layer is None:
            layer = self._m.layer

        # make sure all layers are converted to string
        layer = str(layer)

        self._artists.setdefault(layer, set())

        if art in self._artists[layer]:
            return
        else:
            art.set_animated(True)
            self._artists[layer].add(art)

    def add_bg_artist(self, art, layer=None):
        """
        Add a background-artist to be managed.
        (Background artists are only updated on zoom-events... they are NOT animated!)

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.
        layer : str or None, optional
            The layer name at which the artist should be drawn.

            - If "all": the corresponding feature will be added to ALL layers

            The default is None in which case the layer of the base-Maps object is used.
        """

        if layer is None:
            layer = self._m.layer

        # make sure all layer names are converted to string
        layer = str(layer)

        if art.figure != self.figure:
            raise RuntimeError

        if layer in self._bg_artists and art in self._bg_artists[layer]:
            print(f"EOmaps: Background-artist '{art}' already added")
            return

        self._bg_artists.setdefault(layer, []).append(art)

        # tag all relevant layers for refetch
        self._refetch_layer(layer)

        for f in self._on_add_bg_artist:
            f()

    def remove_bg_artist(self, art, layer=None):
        removed = False
        if layer is None:
            layers = []
            for key, val in self._bg_artists.items():
                if art in val:
                    art.set_animated(False)
                    val.remove(art)
                    removed = True
                    layers.append(key)
                layer = "|".join(layers)
        else:
            if layer not in self._bg_artists:
                return
            if art in self._bg_artists[layer]:
                art.set_animated(False)
                self._bg_artists[layer].remove(art)
                removed = True

        if removed:
            for f in self._on_remove_bg_artist:
                f()

            # tag all relevant layers for refetch
            self._refetch_layer(layer)

    def remove_artist(self, art, layer=None):
        # this only removes the artist from the blit-manager,
        # it does not clear it from the plot!

        if layer is None:
            for key, layerartists in self._artists.items():
                if art in layerartists:
                    art.set_animated(False)
                    layerartists.remove(art)
        else:
            if art in self._artists[layer]:
                art.set_animated(False)
                self._artists[layer].remove(art)

    def _get_artist_zorder(self, a):
        try:
            return a.get_zorder()
        except Exception:
            print(r"EOmaps: unalble to identify zorder of {a}... using 99")
            return 99

    def _draw_animated(self, layers=None, artists=None):
        """
        Draw animated artists

        - if layers is None and artists is None: active layer artists will be re-drawn
        - if layers is not None: all artists from the selected layers will be re-drawn
        - if artists is not None: all provided artists will be redrawn

        """
        fig = self.canvas.figure
        if layers is None:
            layers = set(self.bg_layer.split("|"))
            layers.add(self.bg_layer)
        else:
            layers = set(chain(*(i.split("|") for i in layers)))
            for l in layers:
                layers.add(l)

        if artists is None:
            artists = []

        # always redraw artists from the "all" layer
        layers.add("all")

        # redraw artists from the selected layers and explicitly provided artists
        # (sorted by zorder)
        allartists = chain(*(self._artists.get(layer, []) for layer in layers), artists)

        for a in sorted(allartists, key=self._get_artist_zorder):
            fig.draw_artist(a)

    def _clear_temp_artists(self, method, forward=True):
        # clear artists from connected methods
        if method == "_click_move" and forward:
            self._clear_temp_artists("click", False)
        elif method == "click" and forward:
            self._clear_temp_artists("_click_move", False)
        elif method == "pick" and forward:
            self._clear_temp_artists("click", True)
        elif method == "on_layer_change" and forward:
            self._clear_temp_artists("pick", False)
            self._clear_temp_artists("click", True)
            self._clear_temp_artists("move", False)

        if method == "on_layer_change":
            # clear all artists from "on_layer_change" list irrespective of the method
            artists = self._artists_to_clear.pop("on_layer_change", [])
            for art in artists:
                for met, met_artists in self._artists_to_clear.items():
                    if art in met_artists:
                        art.set_visible(False)
                        self.remove_artist(art)
                        try:
                            art.remove()
                        except ValueError:
                            # ignore errors if the artist no longer exists
                            pass
                        met_artists.remove(art)
        else:
            artists = self._artists_to_clear.pop(method, [])
            while len(artists) > 0:
                art = artists.pop(-1)
                art.set_visible(False)
                self.remove_artist(art)
                try:
                    art.remove()
                except ValueError:
                    # ignore errors if the artist no longer exists
                    pass

                try:
                    self._artists_to_clear.get("on_layer_change", []).remove(art)
                except ValueError:
                    # ignore errors if the artist is not present in the list
                    pass

    def update(
        self,
        layers=None,
        bbox_bounds=None,
        bg_layer=None,
        artists=None,
        clear=False,
        blit=True,
    ):
        """
        Update the screen with animated artists.

        Parameters
        ----------
        layers : list, optional
            The layers to redraw (if None and artists is None, all layers will be redrawn).
            The default is None.
        bbox_bounds : tuple, optional
            the blit-region bounds to update. The default is None.
        bg_layer : int, optional
            the background-layer number. The default is None.
        artists : list, optional
            A list of artists to update.
            If provided NO layer will be automatically updated!
            The default is None.
        """
        if self._m.parent._layout_editor._modifier_pressed:
            # don't update during layout-editing
            return

        cv = self.canvas

        if bg_layer is None:
            bg_layer = self.bg_layer

        while len(self._before_update_actions) > 0:
            action = self._before_update_actions.pop(0)
            action()

        # paranoia in case we missed the draw event,
        if bg_layer not in self._bg_layers or self._bg_layers[bg_layer] is None:
            self.on_draw(None)
            self.fetch_bg(bg_layer)
        else:
            if clear:
                self._clear_temp_artists(clear)

            # restore the background
            cv.restore_region(self._bg_layers[bg_layer])
            # draw all of the animated artists
            while len(self._after_restore_actions) > 0:
                action = self._after_restore_actions.pop(0)
                action()

            self._draw_animated(layers=layers, artists=artists)

            if blit:
                # workaround for nbagg backend to avoid glitches
                # it's slow but at least it works...
                # check progress of the following issuse
                # https://github.com/matplotlib/matplotlib/issues/19116
                if self._mpl_backend_force_full:
                    cv._force_full = True

                if bbox_bounds is not None:

                    class bbox:
                        bounds = bbox_bounds

                    cv.blit(bbox)
                else:
                    # update the GUI state
                    cv.blit(self.figure.bbox)

            # execute all actions registered to be called after blitting
            while len(self._after_update_actions) > 0:
                action = self._after_update_actions.pop(0)
                action()

        # let the GUI event loop process anything it has to do
        # don't do this! it is causing infinite loops
        # cv.flush_events()

    def blit_artists(self, artists, bg="active", blit=True):
        """
        Blit artists (optionally on top of a given background)

        Parameters
        ----------
        artists : iterable
            the artists to draw
        bg : matpltolib.BufferRegion, None or "active", optional
            A fetched background that is restored before drawing the artists.
            The default is "active".
        blit : bool
            Indicator if canvas.blit() should be called or not.
            The default is True
        """
        cv = self.canvas

        # paranoia in case we missed the first draw event
        if getattr(self.figure, "_cachedRenderer", "nope") is None:
            self.on_draw(None)
            self._after_update_actions.append(lambda: self.blit_artists(artists, bg))
            return

        # restore the background
        if bg is not None:
            if bg == "active":
                bg = self._get_active_bg()
            cv.restore_region(bg)

        for a in artists:
            self.figure.draw_artist(a)

        if blit:
            cv.blit()

    def _get_restore_bg_action(
        self,
        layer,
        bbox_bounds=None,
        alpha=1,
        clip_path=None,
        set_clip_path=False,
    ):
        """
        Update a part of the screen with a different background
        (intended as after-restore action)

        bbox_bounds = (x, y, width, height)
        """

        if bbox_bounds is None:
            bbox = self.figure.bbox
        else:
            bbox = Bbox.from_bounds(*bbox_bounds)

        def action():
            if self.bg_layer == layer:
                return
            # make sure the background is fetched
            if layer not in self._bg_layers:
                self.fetch_bg(layer)

            x0, y0, w, h = bbox.bounds

            # convert the buffer to rgba so that we can add transparency
            buffer = self._bg_layers[layer]

            x = buffer.get_extents()
            ncols, nrows = x[2] - x[0], x[3] - x[1]

            argb = (
                np.frombuffer(buffer, dtype=np.uint8).reshape((nrows, ncols, 4)).copy()
            )
            argb = argb[::-1, :, :]

            argb[:, :, -1] = (argb[:, :, -1] * alpha).astype(np.int8)

            gc = self.canvas.renderer.new_gc()

            gc.set_clip_rectangle(bbox)
            if set_clip_path is True:
                gc.set_clip_path(clip_path)

            self.canvas.renderer.draw_image(
                gc,
                int(x0),
                int(y0),
                argb[int(y0) : int(y0 + h), int(x0) : int(x0 + w), :],
            )
            gc.restore()

        return action

    def cleanup_layer(self, layer):
        self._cleanup_bg_artists(layer)
        self._cleanup_artists(layer)
        self._cleanup_bg_layers(layer)
        self._cleanup_on_layer_activation(layer)

    def _cleanup_bg_artists(self, layer):
        if layer not in self._bg_artists:
            return

        artists = self._bg_artists[layer]
        while len(artists) > 0:
            a = artists.pop()
            try:
                self.remove_bg_artist(a, layer)
                a.remove()
            except Exception:
                print(f"EOmaps-cleanup: Problem while clearing bg artist:\n {a}")

        del self._bg_artists[layer]

    def _cleanup_artists(self, layer):
        if layer not in self._artists:
            return

        artists = self._artists[layer]
        while len(artists) > 0:
            a = artists.pop()
            try:
                self.remove_artist(a)
                a.remove()
            except Exception:
                print(f"EOmaps-cleanup: Problem while clearing dynamic artist:\n {a}")

        del self._artists[layer]

    def _cleanup_bg_layers(self, layer):
        try:
            # remove cached background-layers
            if layer in self._bg_layers:
                del self._bg_layers[layer]
        except Exception:
            print("EOmaps-cleanup: Problem while clearing cached background layers")

    def _cleanup_on_layer_activation(self, layer):

        try:
            # remove not yet executed lazy-activation methods
            # (e.g. not yet fetched WMS services)
            if layer in self._on_layer_activation:
                del self._on_layer_activation[layer]
        except Exception:
            print("EOmaps-cleanup: Problem while clearing layer activation methods")
