## DESCRIPTION

*r.geoserver.publish* is a GRASS GIS addon Python script to publish
raster maps as well as space time raster data sets with
[geoserver-grass-datastore](https://mundialis.github.io/geoserver-grass-raster-datastore/)
and creates a GeoServer layer for it. The module uses the GeoServer REST
API.

It is important that you are in the mapset in which the raster map or
space time raster data set is stored.

If you have a raster map and a space time raster map with the same name,
which you use as **input**, then you have to set the **type** to
"raster" or "strds".

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

### Publish space time raster data set to geoserver

Publish MODIS LST space time raster data to geoserver and set style (a
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

## SEE ALSO

*[r.out.gdal](r.out.gdal.md), [r.out.geoserver](r.out.geoserver.md),
[r.geoserver.style](r.geoserver.style.md)*

## AUTHORS

Anika Weinmann and Carmen Tawalika,
[mundialis](https://www.mundialis.de/)
