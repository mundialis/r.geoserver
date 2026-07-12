[![image-alt](grass_logo.png)](https://grass.osgeo.org/grass-stable/manuals/index.html)

------------------------------------------------------------------------

## NAME

***r.geoserver*** - collection of GRASS GIS addons to publish and style
raster maps as well as space time raster data sets with different
coverage stores (Tiff, image mosaic, `geoserver-grass-datastore`) and to
create GeoServer layers for it. All modules use the GeoServer REST API.

## KEYWORDS

[geoserver](https://grass.osgeo.org/grass-stable/manuals/geoserver.html),
[WMS](https://grass.osgeo.org/grass-stable/manuals/WMS.html)

## DESCRIPTION

The *r.geoserver* collection consists of currently three modules.

[r.geoserver.publish](r.geoserver.publish.md)  
Publishes raster maps as well as STRDS with `geoserver-grass-datastore`
coverage store and creates a GeoServer layer for it.

[r.geoserver.style](r.geoserver.style)  
Publishes a style based on GRASS GIS map and attaches to layer. For
STRDS the first map is taken to set the style for all raster maps in the
STRDS.

[t.geoserver.publish](t.geoserver.publish)  
Publishes and styles each raster map of a STRDS to a geoserver. Either
each map inside STRDS is published individually as COG, or all are
combined to an image mosaic store. Data can either be shared via mount
point or uploaded.

## REQUIREMENTS

- A running [GeoServer](https://geoserver.org/) instance

## AUTHORS

Anika Weinmann, Carmen Tawalika and Guido Riembauer,
[mundialis](https://www.mundialis.de/), Germany
