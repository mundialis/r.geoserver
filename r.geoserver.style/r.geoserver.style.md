## DESCRIPTION

*r.geoserver.style* is a GRASS GIS addon Python script to publish a
style based on GRASS GIS map and attach to layer with
[geoserver-grass-datastore](https://mundialis.github.io/geoserver-grass-raster-datastore/)
store. The module uses the GeoServer REST API.

For space time raster data sets the first map is taken to set the style
for all raster maps in the space time raster data set.

## EXAMPLES

### Publish raster map to GeoServer

Publish elevation map to GeoServer and set the style:

```sh
# publish layer
r.geoserver.publish input=elevation \
  host=http://geoserver port=8080 user=admin password=geoserver \
  workspace=spieltag coveragestore=elevation layername=elevation \
  gs_file_path=/grassdb/nc_spm_08/PERMANENT
# set style (applies current map color table)
r.geoserver.style host=http://geoserver port=8080 user=admin password=geoserver \
  workspace=spieltag layername=elevation
```

### Publish space time raster data set to GeoServer

Publish MODIS LST space time raster data to GeoServer and set style (a
mapset with the example mapset of the MODIS data is available here:
[nc_spm_mapset_modis2015_2016_lst.zip](https://grass.osgeo.org/sampledata/north_carolina/nc_spm_mapset_modis2015_2016_lst.zip)):

```sh
# publish layer
r.geoserver.publish input=LST_Day_monthly \
  host=http://geoserver port=8080 user=admin password=geoserver \
  workspace=spieltag coveragestore=modis_lst_strds layername=LST_Day_monthly \
  gs_file_path=/grassdb/nc_spm_08_grass7/modis_lst
# set style (applies color table of first map)
r.colors MOD11B3.A2015001.h11v05.single_LST_Day_6km color=bcyr
r.geoserver.style host=http://geoserver port=8080 user=admin password=geoserver \
  workspace=spieltag layername=LST_Day_monthly
```

### Publish raster map to GeoServer **without geoserver-grass-datastore**

It is also possible to publish and style a raster map to a GeoSever
without
[geoserver-grass-datastore](https://mundialis.github.io/geoserver-grass-raster-datastore/).
In this case, a GeoTIFF raster is exported by
[r.out.geoserver](r.out.geoserver.md) and used to create a new GeoServer
coveragestore. The **grassmap** parameter is then required in
*r.geoserver.style* to export the style from a given map in the current
GRASS GIS session.

```sh
# publish layer
r.out.geoserver input=elevation \
  host=http://geoserver port=8080 user=admin password=geoserver \
  workspace=spieltag layername=elevation title=some_title \
  outputfolder=/mnt/geoserverdata geoserver_path=/opt/geoserver_data
  gs_file_path=/grassdb/nc_spm_08/PERMANENT

# set style (applies current map color table)
r.geoserver.style host=http://geoserver port=8080 user=admin password=geoserver \
  workspace=spieltag layername=elevation grassmap=elevation
```

## SEE ALSO

*[r.out.gdal](https://grass.osgeo.org/grass-stable/manuals/r.out.gdal.html),
[r.out.geoserver](r.out.geoserver.md),
[r.geoserver.publish](r.geoserver.publish.md),
[r.out.geoserver](r.out.geoserver.md)*

## AUTHORS

Anika Weinmann and Carmen Tawalika,
[mundialis](https://www.mundialis.de/)
