[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/MapIt)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
# EOmaps

a general-purpose library to plot maps of large non-rectangular datasets.

❗❗❗ this library is a **work-in-progress** and subject to structural changes ❗❗❗  
🚀  feel free to contribute!

### features
- reproject & plot datasets as ellipses or rectangles with actual geographical dimensions
- interact with the database underlying the plot via "callback-functions"
- add overlays to the plots (NaturalEarth features, geo-dataframes, etc.)
- get a nice colorbar with a colored histogram on top

## install

a simple `pip install eomaps` should do the trick

## basic usage

- check out the example-notebook: 🛸 [A_basic_map.ipynb](https://github.com/raphaelquast/maps/blob/dev/examples/A_basic_map.ipynb) 🛸

```python
from eomaps import Maps

m = Maps()

m.data = "... a pandas-dataframe with coordinates and data-values ..."

m.set_data_specs("... data specifications ...")
m.set_plot_specs("... variables that control the appearance of the plot ...")
m.set_classify_specs("... automatic classification of the data va mapclassify ...")

# plot the map
m.plot_map()

m.add_callback(...)        # attach a callback-function
m.add_discrete_layer(...)  # plot additional data-layers
m.add_gdf(...)             # plot geo-dataframes

m.add_overlay(...)         # add overlay-layers

m.add_annotation(...)      # add annotations
m.add_marker(...)          # add markers


m.savefig(...)             # save the figure

# access individual objects of the generated figure
# (f, ax, cb, gridspec etc.)
m.figure.<...>
```


### callbacks
execute functions when clicking on the map:
- `"annotate"`: add annotations to the map
- `"mark"`: add marker to the map
- `"plot"`: generate a plot of the picked values
- `"print_to_console"`: print pixel-info to the console
- `"get_values"`: save the picked values to a dict
- `"load"`: load objects from a collection
- ... or use a custom function

    ```python
    def some_callback(self, **kwargs):
        print("hello world")
        print("the position of the clicked pixel", kwargs["pos"])
        print("the data-index of the clicked pixel", kwargs["ID"])
        print("data-value of the clicked pixel", kwargs["val"])
        self.m  # access to the Maps object
    m.add_callback(some_callback)
    ```
