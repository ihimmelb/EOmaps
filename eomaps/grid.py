from matplotlib.collections import LineCollection
import numpy as np


class GridLines:
    def __init__(
        self, m, d=None, auto_n=10, layer=None, bounds=(-180, 180, -90, 90), n=100
    ):
        self.m = m._proxy(m)

        self._d = d
        self._auto_n = auto_n
        self._bounds = bounds
        self._n = n

        self._kwargs = dict()
        self._coll = None

        self._layer = layer

    @property
    def d(self):
        return self._d

    @property
    def layer(self):
        return self._layer

    @property
    def auto_n(self):
        return self._auto_n

    @property
    def n(self):
        return self._n

    @property
    def bounds(self):
        return self._bounds

    def set_bounds(self, bounds):
        """
        Set the boundaries in which gridlines are drawn.

        Parameters
        ----------
        bounds : tuple
            (lon_min, lon_max, lat_min, lat_max)

        """
        self._bounds = bounds
        self._redraw()

    def set_d(self, d):
        """
        Set a fixed grid-distance.

        Parameters
        ----------
        d : int, float or None
            The separation of the gridlines in degrees.
            To use a different separation for longitude/latitude, provide a tuple
            of numbers, e.g.: `(d_lon, d_lat)`

            If None, "auto_n" is used to automatically determine an appropriate
            grid-spacing.

        """
        self._d = d
        self._redraw()

    def set_layer(self, layer):
        """
        The layer at which the gridlines will be drawn.

        Parameters
        ----------
        layer : str
            The name of the layer on which the gridlines should be visible.

        """
        self._layer = layer
        self._redraw()

    def set_auto_n(self, auto_n):
        """
        The number of gridlines to draw in the currently visible extent.

        Note: this is an approximate value!

        Parameters
        ----------
        auto_n : int or tuple of int
            The (rough) number of gridlines to use when evaluating the automatic
            grid-spacing. To use different numbers of gridlines in each direction,
            provide a tuple of ints, e.g.: `(n_lon, n_lat)`.

        """
        self._auto_n = auto_n
        self._redraw()

    def _update_line_props(self, **kwargs):
        color = None
        if "c" in kwargs:
            color = kwargs.pop("c", None)
        if "color" in kwargs:
            color = kwargs.pop("color", None)

        if color is not None:
            kwargs["edgecolor"] = color

        self._kwargs.update(kwargs)

    def update_line_props(self, **kwargs):
        """
        Update the properties of the drawn lines.

        Any kwargs accepted by `matplotlib.collections.LineCollection` are supported.

        Commonly used parameters are:

        - "edgecolor" (or "ec" or "color" or "c"): the color of the lines
        - "linewidth" (or "lw"): the linewidth
        - "linestyle" (or "ls"): the linestyle to use

        Parameters
        ----------
        kwargs :
            keyword-arguments used to update the properties of the lines.

        """
        self._update_line_props(**kwargs)
        self._redraw()

    @n.setter
    def n(self, n):
        """
        Set the number of intermediate points to calculate for each line.

        Parameters
        ----------
        n : int
            Number of intermedate points.

        """
        self._n = val
        self._redraw()

    def _get_lines(self):
        if self.d is not None:
            if isinstance(self.d, tuple) and len(self.d) == 2:
                dlon, dlat = self.d
            elif isinstance(self.d, (int, float, np.number)):
                dlon = dlat = self.d
            else:
                raise TypeError(f"EOmaps: d={self.d} is not a valid grid-spacing.")

            if all(isinstance(i, (int, float, np.number)) for i in (dlon, dlat)):
                lons = np.arange(self.bounds[0], self.bounds[1] + dlon, dlon)
                lats = np.arange(self.bounds[2], self.bounds[3] + dlat, dlat)

                lines = [
                    np.linspace([x, lats[0]], [x, lats[-1]], self.n, endpoint=True)
                    for x in lons
                ]
                linesy = [
                    np.linspace([lons[0], y], [lons[-1], y], self.n, endpoint=True)
                    for y in lats
                ]
                lines.extend(linesy)

                return np.array(lines)

            else:
                raise TypeError("EOmaps: dlon and dlat must be numbers!")
        else:
            return self._get_auto_grid_lines()

    def _get_auto_grid_lines(self):
        if isinstance(self.auto_n, tuple):
            nlon, nlat = self.auto_n
        else:
            nlon = nlat = self.auto_n

        bounds = np.array(self.m.ax.get_extent(self.m.CRS.PlateCarree()))

        b_lon = bounds[1] - bounds[0]
        b_lat = bounds[3] - bounds[2]

        # get the magnitudes
        glon = 10 ** np.floor(np.log10(b_lon))
        glat = 10 ** np.floor(np.log10(b_lat))

        bounds[0] = max(-180, bounds[0] - bounds[0] % glon)
        bounds[1] = min(180, bounds[1] - bounds[1] % glon + glon)
        bounds[2] = max(-90, bounds[2] - bounds[2] % glat)
        bounds[3] = min(90, bounds[3] - bounds[3] % glat + glat)

        dlon, dlat = (bounds[1] - bounds[0]) / nlon, (bounds[3] - bounds[2]) / nlat

        lons = np.arange(bounds[0], min(180 + dlon, bounds[1] + 10 * dlon), dlon)
        lats = np.arange(bounds[2], min(90 + dlat, bounds[3] + 10 * dlat), dlat)

        lines = [
            np.linspace([x, lats[0]], [x, lats[-1]], self.n, endpoint=True)
            for x in lons
        ]
        linesy = [
            np.linspace([lons[0], y], [lons[-1], y], self.n, endpoint=True)
            for y in lats
        ]

        lines.extend(linesy)

        return np.array(lines)

    def _get_coll(self, **kwargs):
        lines = self._get_lines()
        l0, l1 = self.m._transf_lonlat_to_plot.transform(lines[..., 0], lines[..., 1])

        coll = LineCollection(np.dstack((l0, l1)), **kwargs)
        return coll

    def _add_grid(self, **kwargs):
        self._update_line_props(**kwargs)

        self._coll = self._get_coll(**self._kwargs)
        self.m.ax.add_collection(self._coll)
        self.m.BM.add_bg_artist(self._coll, layer=self.layer)

    def _redraw(self):
        try:
            self._remove()
        except Exception as ex:
            # catch exceptions to avoid issues with dynamic re-drawing of
            # invisible grids
            pass

        self._add_grid()

    def _remove(self):
        if self._coll is None:
            print("EOmaps: there is no grid to remove... ")
            return

        self.m.BM.remove_bg_artist(self._coll, layer=self.layer)
        try:
            self._coll.remove()
        except ValueError:
            pass

    def remove(self):
        """Remove the grid from the map."""
        self._remove()

        if self in self.m._grid._gridlines:
            self.m._grid._gridlines.remove(self)


class GridFactory:
    def __init__(self, m):
        self.m = m
        self._gridlines = []
        self.m.BM._before_fetch_bg_actions.append(self._update_autogrid)

    def add_grid(
        self,
        m,
        d=None,
        auto_n=10,
        n=100,
        bounds=(-180, 180, -90, 90),
        layer=None,
        **kwargs,
    ):
        """
        Add gridlines to the map.

        By default, an appropriate grid-spacing is determined via the "auto_n" kwarg.

        An explicit grid-spacing can be used by providing the grid-separation
        via the "d" kwarg.

        Parameters
        ----------
        d : tuple, int or float or None
            The separation of the gridlines in degrees.
            To use a different separation for longitude/latitude, provide a tuple
            of numbers, e.g.: `(d_lon, d_lat)`

            If None, "auto_n" is used to automatically determine an appropriate
            grid-spacing.
            The default is None.
        auto_n : int or (int, int)
            The (rough) number of gridlines to use when evaluating the automatic
            grid-spacing. To use different numbers of gridlines in each direction,
            provide a tuple of ints, e.g.: `(n_lon, n_lat)`.
            The default is 10.
        layer : str
            The name of the layer on which the gridlines should be visible.
        bounds : tuple
            A tuple of boundaries to limit the gridlines to a certain area.
            (lon_min, lon_max, lat_min, lat_max)
            The default is: (-180, 180, -90, 90)
        n : int
            The number of intermediate points to draw for each line.
            (e.g. to nicely draw curved grid lines)
            The default is 100
        kwargs :
            Additional kwargs passed to matplotlib.collections.LineCollection.

            The default is: (ec="0.2", lw=0.5, zorder=100)

        Returns
        -------
        m_grid : EOmaps.Maps
            The Maps-object used to draw the gridlines.

        Examples
        --------
        >>> m = Maps(Maps.CRS.InterruptedGoodeHomolosine())
        >>> m.add_feature.preset.ocean()
        >>> g0 = m.add_gridlines(d=10, ec=".5", lw=0.25, zorder=1, layer="g")
        >>> g1 = m.add_gridlines(d=(10, 20), ec="k", lw=0.5, zorder=2, layer="g")
        >>> g2 = m.add_gridlines(d=5, ec="darkred", lw=0.25, zorder=0,
        >>>                      bounds=(-20, 40, -20, 60), layer="g")
        >>> m.show_layer(m.layer, "g")

        """
        fc = kwargs.pop("facecolor", "none")
        ec = kwargs.pop("edgecolor", ".2")
        lw = kwargs.pop("linewidth", 0.5)

        kwargs.setdefault("fc", fc)
        kwargs.setdefault("ec", ec)
        kwargs.setdefault("lw", lw)
        kwargs.setdefault("zorder", 100)

        g = GridLines(m=m, d=d, auto_n=auto_n, n=n, bounds=bounds, layer=layer)
        g._add_grid(**kwargs)
        self._gridlines.append(g)

        return g

    def _update_autogrid(self, *args, **kwargs):
        for g in self._gridlines:
            if g.d is None:
                try:
                    g._redraw()
                except Exception as ex:
                    # catch exceptions to avoid issues with dynamic re-drawing of
                    # invisible grids
                    continue