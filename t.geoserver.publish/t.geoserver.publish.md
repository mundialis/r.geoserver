## DESCRIPTION

*t.geoserver.publish* is a GRASS GIS addon to publish and style each
raster map of a space-time raster dataset (STRDS) to a GeoServer. The
following environment variables are expected:

- GEOSERVER_HOST
- GEOSERVER_PORT
- GEOSERVER_USER
- GEOSERVER_PASSWORD
- GEOSERVER_WORKSPACE

In case a shared directory between GRASS GIS and GeoServer is possible,
two further environment variables can be used to tell GeoServer to
publish data from this local path instead of uploading the data:

- OUTPUTFOLDER (path from GRASS GIS to shared directory)
- GEOSERVER_DATAPATH (path from GeoServer to shared directory)

There are two ways to publish GeoServer layers with
*t.geoserver.publish*:

Using the **layername_prefix** parameter, `n` GeoServer layers
(referring to `n` maps in the input STRDS) are published. The output
layers will receive a consecutive digit suffix (starting with **\_1**).
Internally, [r.out.geoserver](r.out.geoserver.md) (with COG export) and
[r.geoserver.style](r.geoserver.style.md) are applied for each raster
map of the input STRDS. In this case, the GEOSERVER_DATAPATH must be
set - no upload is possible yet.

The second way is to use the **mosaic_layername** parameter. This
publishes only a single GeoServer layer, where data is stored in an
[ImageMosaic](https://docs.geoserver.org/stable/en/user/data/raster/imagemosaic/index.html)
coverage store. The individual time steps of the STRDS can be accessed
via a GetCapabilities request towards the WMS:

```sh
# excerpt from an example GetCapabilities response (note the time steps in the last line):
...
<Layer queryable="1" opaque="0">
<Name>imagemosaiclayer_ndvi_test</Name>
<Title>imagemosaiclayer_ndvi_test</Title>
<Abstract>Layer-Group type layer: imagemosaiclayer_ndvi_test</Abstract>
<KeywordList>
<Keyword>WMS</Keyword>
<Keyword>imagemosaiclayer_ndvi_test</Keyword>
</KeywordList>
<SRS>EPSG:32632</SRS>
<LatLonBoundingBox minx="6.863079303626465" miny="50.95291761097877" maxx="7.074111500405225" maxy="51.09954810295821"/>
<BoundingBox SRS="EPSG:32632" minx="350370.0" miny="5646750.0" maxx="364740.0" maxy="5662670.0"/>
<Dimension name="time" units="ISO8601"/>
<Extent name="time" default="current">2022-04-17T00:00:00.000Z,2022-06-16T00:00:00.000Z,2022-08-10T00:00:00.000Z</Extent>
...
```

The individual time steps can be visualised by adding

```sh
&TIME=yyyymmDD
```

to the WMS URL.

## NOTES

To comply with GeoServer layer styling and still have a meaningful color
range, raster values are rescaled to a range of 0-255 based on the 2%
and 98% percentiles.

Note that always the entire rasters of the STRDS are published,
regardless of the current computational region (the computational region
is temporarily set to the registered raster maps).

## EXAMPLE

```sh
# Publish all maps of the STRDS S2_STRDS as individual layers "s2_layer_1", "s2_layer_2", "s2_layer_3",...
t.geoserver.publish input=S2_STRDS color=viridis layername_prefix=s2_layer
```

```sh
# Publish all maps of the STRDS S2_STRDS together as a single image mosaic layer "s2_layer"
t.geoserver.publish input=S2_STRDS color=ryg mosaic_layername=s2_layer
```

## SEE ALSO

*[r.out.geoserver](r.out.geoserver.md),
[r.geoserver.style](r.geoserver.style.md)*

## AUTHOR

Guido Riembauer, [mundialis](https://www.mundialis.de/)
