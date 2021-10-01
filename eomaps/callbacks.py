import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.patches import Circle, Ellipse


class callbacks(object):
    """
    a collection of callback-functions

    to attach a callback, use:
        >>> m.add_callback(m.cb.annotate)
        >>> # or
        >>> m.add_callback("annotate")

    to remove an already attached callback, use:
        >>> m.remove_callback(m.cb.annotate)
        >>> # or
        >>> m.remove_callback("annotate")

    you can also define custom callback functions as follows:

        >>> def some_callback(self, **kwargs):
        >>>     print("hello world")
        >>>     print("the position of the clicked pixel", kwargs["pos"])
        >>>     print("the data-index of the clicked pixel", kwargs["ID"])
        >>>     print("data-value of the clicked pixel", kwargs["val"])
        >>>
        >>> m.add_callback(some_callback)
    and remove them again via
        >>> m.remove_callback(some_callback)
    """

    def __init__(self, m):
        pass
        # self = m

    def __repr__(self):
        return "available callbacks:\n    - " + "\n    - ".join(
            [i for i in self.__dir__() if not i.startswith("_")]
        )

    def load(
        self,
        ID=None,
        pos=None,
        val=None,
        database=None,
        load_method="load_fit",
        load_multiple=False,
    ):
        """
        A callback-function that can be used to load objects from a given
        database.

        The returned object is accessible via `m.picked_object`.

        Note: `m.picked_object` will be replaced on each pick-event!

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        database : any
            The database object to use for loading the object
        load_method : str or callable
            If str: The name of the method to use for loading objects from the provided
                    database (the call-signature used is `database.load_method(ID)`)
            If callable: A callable that will be executed on the database with the
                         following call-signature: `load_method(database, ID)`
        load_multiple : bool
            True: A single-object is returned, replacing `m.picked_object` on each pick.
            False: A list of objects is returned that is extended with each pick.
        """

        assert database is not None, "you must provide a database object!"

        try:
            if isinstance(load_method, str):
                assert hasattr(
                    database, load_method
                ), "The provided database has no method '{load_method}'"
                pick = getattr(database, load_method)(ID)
            elif callable(load_method):
                pick = load_method(database, ID)
            else:
                raise TypeError("load_method must be a string or a callable!")
        except Exception:
            print(f"could not load object with ID:  '{ID}' from {database}")

        if load_multiple is True:
            self.picked_object = getattr(self, "picked_object", list()) + [pick]
        else:
            self.picked_object = pick

    def _load_cleanup(self, m):
        if hasattr(m, "picked_object"):
            del m.picked_object

    def print_to_console(self, ID=None, pos=None, val=None):
        """
        a callback-function that prints details on the clicked pixel to the
        console

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        """
        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # xlabel, ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        xlabel, ylabel = [i.name for i in self.figure.ax.projection.axis_info[:2]]

        printstr = ""
        x, y = [np.format_float_positional(i, trim="-", precision=4) for i in pos]
        printstr += f"{xlabel} = {x}\n{ylabel} = {y}\n"
        printstr += f"ID = {ID}\n"

        if isinstance(val, (int, float)):
            val = np.format_float_positional(val, trim="-", precision=4)
        printstr += f"{self.data_specs['parameter']} = {val}"

        print(printstr)

    def annotate(self, ID=None, pos=None, val=None, pos_precision=4, val_precision=4):
        """
        a callback-function to annotate basic properties from the fit on double-click
        use as:    spatial_plot(... , callback=cb_annotate)

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        pos_precision : int
            The floating-point precision of the coordinates.
            The default is 4.
        val_precision : int
            The floating-point precision of the parameter-values.
            The default is 4.
        """

        if not hasattr(self, "background"):
            # cache the background before the first annotation is drawn
            self.background = self.figure.f.canvas.copy_from_bbox(self.figure.f.bbox)

            # attach draw_event that handles blitting
            self.draw_cid = self.figure.f.canvas.mpl_connect(
                "draw_event", self._grab_background
            )

        # to hide the annotation, Maps._cb_hide_annotate() is called when an empty
        # area is clicked!
        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # xlabel, ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        xlabel, ylabel = [i.abbrev for i in self.figure.ax.projection.axis_info[:2]]

        ax = self.figure.ax

        if not hasattr(self, "annotation"):
            self.annotation = ax.annotate(
                "",
                xy=pos,
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round", fc="w"),
                arrowprops=dict(arrowstyle="->"),
            )

        self.annotation.set_visible(True)
        self.annotation.xy = pos

        printstr = ""
        x, y = [
            np.format_float_positional(i, trim="-", precision=pos_precision)
            for i in pos
        ]
        printstr += f"{xlabel} = {x}\n{ylabel} = {y}\n"
        printstr += f"ID = {ID}\n"

        if isinstance(val, (int, float)):
            val = np.format_float_positional(val, trim="-", precision=val_precision)
        printstr += f"{self.data_specs['parameter']} = {val}"

        self.annotation.set_text(printstr)
        self.annotation.get_bbox_patch().set_alpha(0.75)

        # use blitting instead of f.canvas.draw() to speed up annotation generation
        # in case a large collection is plotted
        self._blit(self.annotation)

    def _annotate_cleanup(self):
        if hasattr(self, "background"):
            # delete cached background
            del self.background
        # remove draw_event callback
        if hasattr(self, "draw_cid"):
            self.figure.f.canvas.mpl_disconnect(self.draw_cid)
            del self.draw_cid

    def plot(self, ID=None, pos=None, val=None, x_index="pos", precision=4, **kwargs):
        """
        a callback-function to generate a dynamically updated plot of the
        values

            - x-axis represents pixel-coordinates (or IDs)
            - y-axis represents pixel-values

        a new figure is started if the callback is removed and added again, e.g.

            >>> m.remove_callback("scatter")
            >>> m.add_callback("scatter")


        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        x_index : str
            Indicator how the x-axis is labelled

                - pos : The position of the pixel in plot-coordinates
                - ID  : The index of the pixel in the data
        precision : int
            The floating-point precision of the coordinates printed to the
            x-axis if `x_index="pos"` is used.
            The default is 4.
        **kwargs :
            kwargs forwarded to the call to `plt.plot([...], [...], **kwargs)`.

        """

        style = dict(marker=".")
        style.update(**kwargs)

        if not hasattr(self, "_pick_f"):
            self._pick_f, self._pick_ax = plt.subplots()
            self._pick_ax.tick_params(axis="x", rotation=90)
            self._pick_ax.set_ylabel(self.data_specs["parameter"])

            # call the cleanup function if the figure is closed
            def on_close(event):
                self.cb._scatter_cleanup(self)

            self._pick_f.canvas.mpl_connect("close_event", on_close)

        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # _pick_xlabel, _pick_ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        _pick_xlabel, _pick_ylabel = [
            i.abbrev for i in self.figure.ax.projection.axis_info[:2]
        ]

        if x_index == "pos":
            x, y = [
                np.format_float_positional(i, trim="-", precision=precision)
                for i in pos
            ]
            xindex = f"{_pick_xlabel}={x}\n{_pick_ylabel}={y}"
        elif x_index == "ID":
            xindex = str(ID)

        if not hasattr(self, "_pick_l"):
            (self._pick_l,) = self._pick_ax.plot([xindex], [val], **style)
        else:
            self._pick_l.set_xdata(list(self._pick_l.get_xdata()) + [xindex])
            self._pick_l.set_ydata(list(self._pick_l.get_ydata()) + [val])

        # self._pick_ax.autoscale()
        self._pick_ax.relim()
        self._pick_ax.autoscale_view(True, True, True)

        self._pick_f.canvas.draw()
        self._pick_f.tight_layout()

    def _scatter_cleanup(self, m):
        # cleanup method for scatter callback
        if hasattr(m, "_pick_f"):
            del m._pick_f
        if hasattr(m, "_pick_ax"):
            del m._pick_ax
        if hasattr(m, "_pick_l"):
            del m._pick_l

    def get_values(self, ID=None, pos=None, val=None):
        """
        a callback-function that successively collects return-values in a dict
        that can be accessed via "m.picked_vals", with the following structure:

            >>> m.picked_vals = dict(pos=[... center-position tuples in plot_crs ...],
                                     ID=[... the IDs in the dataframe...],
                                     val=[... the values ...])

        removing the callback will also remove the associated value-dictionary!

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        """

        if not hasattr(self, "picked_vals"):
            self.picked_vals = defaultdict(list)

        for key, val in zip(["pos", "ID", "val"], [pos, ID, val]):
            self.picked_vals[key].append(val)

    def _get_values_cleanup(self, m):
        # cleanup method for get_values callback
        if hasattr(m, "picked_vals"):
            del m.picked_vals

    def mark(
        self,
        ID=None,
        pos=None,
        val=None,
        radius=None,
        shape="circle",
        buffer=1,
        **kwargs,
    ):
        """
        A callback to draw indicators over double-clicked pixels.

        Removing the callback will remove ALL markers that have been
        added to the map.

        The added patches are accessible via `m._picked_markers`

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        radius : float or None, optional
            The radius of the marker. If None, it will be evaluated based
            on the pixel-spacing of the provided dataset
            The default is None.
        shape : str, optional
            Indicator which shape to draw. Currently supported shapes are:
                - circle
                - ellipse

            The default is "circle".
        buffer : float, optional
            A factor to scale the size of the shape. The default is 1.
        **kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)
        """
        if not hasattr(self, "_pick_markers"):
            self._pick_markers = []

        if not hasattr(self, "background"):
            # attach draw_event that handles blitting
            self.draw_cid = self.figure.f.canvas.mpl_connect(
                "draw_event", self._grab_background
            )

        # always fetch the background so that makers remain visible
        self.background = self.figure.f.canvas.copy_from_bbox(self.figure.f.bbox)

        if shape == "circle":
            if radius is None:
                radiusx = np.abs(np.diff(np.unique(self._props["x0"])).mean()) / 2.0
                radiusy = np.abs(np.diff(np.unique(self._props["y0"])).mean()) / 2.0
            p = Circle(pos, np.sqrt(radiusx ** 2 + radiusy ** 2) * buffer, **kwargs)
        if shape == "ellipse":
            radiusx = np.abs(np.diff(np.unique(self._props["x0"])).mean()) / 2.0
            radiusy = np.abs(np.diff(np.unique(self._props["y0"])).mean()) / 2.0

            p = Ellipse(
                pos,
                np.mean(radiusx) * 2 * buffer,
                np.mean(radiusy) * 2 * buffer,
                **kwargs,
            )

        artist = self.figure.ax.add_patch(p)

        self._pick_markers.append(artist)
        self._blit(artist)

    def _mark_cleanup(self, m):
        if hasattr(m, "_pick_markers"):
            while len(m._pick_markers) > 0:
                m._pick_markers.pop(0).remove()
            del m._pick_markers

        # remove draw_event callback
        if hasattr(self, "draw_cid"):
            self.figure.f.canvas.mpl_disconnect(self.draw_cid)
            del self.draw_cid
