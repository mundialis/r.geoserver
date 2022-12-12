#!/usr/bin/env python3
#
############################################################################
#
# MODULE:      t.geoserver.publish
# AUTHOR(S):   Guido Riembauer
#
# PURPOSE:     Exports GRASS GIS STRDS to GeoServer and styles it
# COPYRIGHT:   (C) 2022 by mundialis GmbH & Co. KG and the GRASS Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#############################################################################
# %Module
# % description: Exports GRASS GIS STRDS to GeoServer and styles it.
# % keyword: temporal
# % keyword: export
# % keyword: OGC
# %End

# %option G_OPT_STRDS_INPUT
# % key: input
# % label: Input STRDS
# %end

# %option
# % key: layername_prefix
# % type: string
# % required: no
# % multiple: no
# % label: Prefix for layernames. All published layers will have the prefix, an underscore and an continuous digit suffix
# %end

# %option
# % key: color
# % type: string
# % required: yes
# % multiple: no
# % options: bcyr,bgyr,blues,byg,byr,elevation,evi,forest_cover,grass,greens,grey,gyr,inferno,magma,ndvi,ndwi,reds,ryb,ryg,viridis
# % label: Name of color table for layer styling
# %end

# %option
# % key: mosaic_layername
# % type: string
# % required: no
# % multiple: no
# % label: Name of a single image mosaic layer to be created
# %end

# %rules
# % required: layername_prefix,mosaic_layername
# % exclusive: layername_prefix,mosaic_layername
# %end


import atexit
import grass.script as grass
import grass.temporal as tgis
import json
import os
import stat
import requests
import uuid
from shutil import make_archive, rmtree

rm_rasters = []
rm_dirs = []
rm_files = []
region = None


def cleanup():
    nuldev = open(os.devnull, "w")
    kwargs = {"flags": "f", "quiet": True, "stderr": nuldev}
    for rmrast in rm_rasters:
        if grass.find_file(name=rmrast, element="raster")["file"]:
            grass.run_command("g.remove", type="raster", name=rmrast, **kwargs)
    if region:
        if grass.find_file(name=region, element="region")["file"]:
            grass.run_command("g.region", region=region)
            grass.run_command(
                "g.remove",
                flags="f",
                type="region",
                name=region,
                quiet=True,
                stderr=nuldev,
            )
    for rm_dir in rm_dirs:
        rmtree(rm_dir)
    for rm_file in rm_files:
        os.remove(rm_file)


def get_env(envname, required=True):
    env = os.getenv(envname)
    if env is None and required is True:
        grass.fatal(_(f"Environment variable {envname} not defined."))
    else:
        return env


def get_color_rules():
    # get color ranges
    rules_list = list(grass.parse_command("r.colors", flags="d").keys())
    rules_dict = dict()
    for item in rules_list:
        name = item.split(":")[0]
        range = item.split("range: ")[1].replace("]", "")
        if range == "map values":
            range_dict = range
        else:
            min = float(range.split(" to ")[0])
            max = float(range.split(" to ")[1])
            range_dict = [min, max]
        rules_dict[name] = range_dict
    return rules_dict


def create_imagemosaic_auxfiles(targetdir):
    # creates indexer.properties and timeregex.properties files
    indexer_file = os.path.join(targetdir, "indexer.properties")
    timeregex_file = os.path.join(targetdir, "timeregex.properties")
    if not os.path.isfile(indexer_file):
        indexer_string = (
            "TimeAttribute=date\n"
            "PropertyCollectors=TimestampFileNameExtractorSPI"
            "[timeregex](date)\nSchema=*the_geom:Polygon,"
            "location:String,date:java.util.Date"
        )
        with open(indexer_file, "w") as file:
            file.write(indexer_string)
    if not os.path.isfile(timeregex_file):
        # assumption: filename is <something_time_YYYYMMDD>.tif
        timeregex_string = "regex=(?<=_time_)[0-9]{8}"
        with open(timeregex_file, "w") as file:
            file.write(timeregex_string)
    return


def create_imagemosaic_coveragestore(geoserver_path, name, host, port, workspace, auth):
    # creates a new image mosaic coverage store
    grass.message(_("Creating ImageMosaic coveragestore..."))
    headers = {"content-type": "application/json"}
    postbody_dict = {
        "coverageStore": {
            "name": name,
            "type": "ImageMosaic",
            "enabled": True,
            "workspace": {"name": workspace},
            "url": f"file:{geoserver_path}",
        }
    }
    postbody = json.dumps(postbody_dict)
    url = f"{host}:{port}/geoserver/rest/" f"workspaces/{workspace}/coveragestores"
    resp = requests.post(url, headers=headers, data=postbody, auth=auth)
    if resp.status_code != 201:
        grass.fatal(
            _(
                f"Creation of ImageMosaic coveragestore failed! "
                f"\n <{resp.status_code}> \n <{resp.text}>"
            )
        )


def generate_postbody_for_layer(layername, workspace, coveragestore, epsg):
    metadata = {
        "entry": [
            {"@key": "elevation", "dimensionInfo": {"enabled": False}},
            {
                "@key": "time",
                "dimensionInfo": {
                    "enabled": True,
                    "presentation": "LIST",
                    "units": "ISO8601",
                    "defaultValue": {
                        "strategy": "NEAREST",
                        "referenceValue": "CURRENT",
                    },
                    "nearestMatchEnabled": False,
                },
            },
        ]
    }
    postbody_dict = {
        "coverage": {
            "abstract": "",
            "defaultInterpolationMethod": "nearest neighbor",
            "description": "Generated from actinia",
            "enabled": True,
            "keywords": {"string": ["WMS", layername]},
            "name": layername,
            "namespace": {"name": workspace},
            "nativeFormat": "GeoTIFF",
            "nativeName": layername,
            "requestSRS": {"string": [f"EPSG:{epsg}"]},
            "responseSRS": {"string": [f"EPSG:{epsg}"]},
            "srs": f"EPSG:{epsg}",
            "store": {
                "@class": "coverageStore",
                "name": f"{workspace}:{coveragestore}",
            },
            "title": layername,
            "metadata": metadata,
        }
    }
    postbody = json.dumps(postbody_dict)
    return postbody


def create_geoserver_layer(layername, workspace, coveragestore, epsg, host, port, auth):
    # publishes a new layer with time dimension enabled
    grass.message(_(f"Creating ImageMosaic layer {workspace}:{layername}..."))
    headers = {"content-type": "application/json"}
    postbody = generate_postbody_for_layer(layername, workspace, coveragestore, epsg)
    url = (
        f"{host}:{port}/geoserver/rest/workspaces/{workspace}/"
        f"coveragestores/{coveragestore}/coverages"
    )
    resp = requests.post(url, headers=headers, data=postbody, auth=auth)
    if resp.status_code != 201:
        grass.fatal(
            _(
                f"Creation of ImageMosaic layer failed! "
                f"\n <{resp.status_code}> \n <{resp.text}>"
            )
        )
    else:
        grass.message(_("Creation of ImageMosaic layer succeeded!"))


def update_geoserver_layer(layername, workspace, coveragestore, epsg, host, port, auth):
    # updates an existing layer (name and time dimension enabled)
    grass.message(_(f"Updating ImageMosaic layer {workspace}:{coveragestore}..."))
    headers = {"content-type": "application/json"}
    postbody = generate_postbody_for_layer(layername, workspace, coveragestore, epsg)
    url = (
        f"{host}:{port}/geoserver/rest/workspaces/{workspace}/"
        f"coveragestores/{coveragestore}/coverages/{coveragestore}"
    )
    resp = requests.put(url, headers=headers, data=postbody, auth=auth)
    if resp.status_code != 200:
        grass.fatal(
            _(
                f"Updating of ImageMosaic layer failed! "
                f"\n <{resp.status_code}> \n <{resp.text}>"
            )
        )
    else:
        grass.message(_("Updating of ImageMosaic layer succeeded!"))


def zip_mosaic_definition_and_granules(targetdir_grass, zip_basename):
    grass.message(_("Creating ImageMosaic Archive for upload..."))
    make_archive(zip_basename, "zip", targetdir_grass)
    grass.message(_("Archive of ImageMosaic created! "))


def upload_new_imagemosaic(workspace, coveragestore, host, port, auth, zipname):
    grass.message(_("Uploading ImageMosaic..."))
    headers = {"Content-type": "application/zip"}
    url = (
        f"{host}:{port}/geoserver/rest/workspaces/{workspace}/"
        f"coveragestores/{coveragestore}/file.imagemosaic"
    )
    resp = requests.put(url, headers=headers, data=open(zipname, "rb"), auth=auth)
    if resp.status_code != 201:
        grass.fatal(_("Upload of ImageMosaic failed!"))
    else:
        grass.message(_("Upload of ImageMosaic succeeded!"))


def main():

    global rm_rasters, region

    tgis.init()
    input = options["input"]
    layername_prefix = options["layername_prefix"]
    mosaic_layername = options["mosaic_layername"]
    color = options["color"]
    color_rules = get_color_rules()

    # get env variables
    geoserver_host = get_env("GEOSERVER_HOST")
    geoserver_port = get_env("GEOSERVER_PORT")
    geoserver_user = get_env("GEOSERVER_USER")
    geoserver_pw = get_env("GEOSERVER_PASSWORD")
    geoserver_workspace = get_env("GEOSERVER_WORKSPACE")
    # geoserver_datapath can be empty if no shared folder
    # between GRASS GIS and GeoServer is allowed, so
    # data will be uploaded instead of shared.
    geoserver_datapath = get_env("GEOSERVER_DATAPATH", required=False)
    # if no shared folder exists, the OUTPUTFOLDER (where to store the temporary zip)
    # does not matter, hence it can be a temp dir
    if geoserver_datapath:
        outputfolder = get_env("OUTPUTFOLDER")
    else:
        outputfolder = grass.tempdir()

    layer_suffix = 1
    layernames = list()
    rescaled_maps = list()

    # save the old region
    pid = os.getpid()
    region = f"cur_region_{pid}"
    grass.run_command("g.region", save=region)

    # get all registered maps
    gisenv = grass.gisenv()
    mapset = gisenv["MAPSET"]
    strds_id = f"{input}@{mapset}"
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    strds = tgis.SpaceTimeRasterDataset(strds_id)
    strds.select(dbif=dbif)
    maps = strds.get_registered_maps_as_objects(dbif=dbif)
    map_names = [map.get_name() for map in maps]
    map_times = [map.get_temporal_extent_as_tuple() for map in maps]
    dbif.close()
    grass.message(_(f"STRDS {input} consists of {len(map_names)} maps."))

    # first get the rescale values in an own loop
    new_mins = list()
    new_maxs = list()
    for map in map_names:
        if color:
            if color not in color_rules.keys():
                grass.fatal(_(f"Color range {color} not known. Aborting..."))
            grass.run_command("g.region", raster=map)
            # rescale to 0-255 to comply with geoserver styling limits

            # use 2% and 98% percentiles as min/max to use histogram stretching
            # here, which avoids using the -e flag of r.colors (this would
            # make the output SLD too long)

            perc_list = list(
                grass.parse_command("r.quantile", input=map, percentiles="2,98").keys()
            )
            percentiles = [float(item.split(":")[2]) for item in perc_list]
            new_min = percentiles[0]
            new_max = percentiles[1]
            rescaled_map = f"{map}_255"
            rescaled_maps.append(rescaled_map)
            rm_rasters.append(rescaled_map)
            new_mins.append(new_min)
            new_maxs.append(new_max)
        else:
            rescaled_maps.append(map)

    if color:
        new_min_min = min(new_mins)
        new_max_max = max(new_maxs)

    # then rescale (and create layer for case layername_prefix)
    for map, rescaled_map in zip(map_names, rescaled_maps):
        grass.run_command("g.region", raster=map)
        if color:
            # values smaller than 2% get 1, larger than 98% get 255
            # small values don't get 0 because geoserver can't handle 0
            rescale_exp = (
                f"({map} - {new_min_min}) * 255.0 /" f" ({new_max_max} - {new_min_min})"
            )
            expression = (
                f"{rescaled_map} = float(if({map}<={new_min_min},1,"
                f"if({map}>{new_max_max},255,{rescale_exp})))"
            )
            grass.run_command("r.mapcalc", expression=expression)
        if layername_prefix:
            layername = f"{layername_prefix}_{layer_suffix}"
            layernames.append(layername)
            layer_suffix += 1
            grass.message(_(f"Publishing map {map} as layer {layername}..."))
            grass.run_command(
                "r.out.geoserver",
                input=rescaled_map,
                host=geoserver_host,
                port=geoserver_port,
                workspace=geoserver_workspace,
                user=geoserver_user,
                password=geoserver_pw,
                layername=layername,
                title=layername,
                outputfolder=outputfolder,
                geoserver_path=geoserver_datapath,
                outputformat="COG",
            )
    if mosaic_layername:
        # create a new dir in the geoserver geodata folder
        targetdir_grass = os.path.join(outputfolder, "geodata", mosaic_layername)
        if not geoserver_datapath:
            # Case when GRASS GIS and GeoServer don't share a common directory
            output_uuid = str(uuid.uuid4())
            targetdir_grass = os.path.join(targetdir_grass, output_uuid)
        if not os.path.isdir(targetdir_grass):
            os.makedirs(targetdir_grass)
        # if the dir exists and has files, cancel
        else:
            if len(os.listdir(targetdir_grass)) > 0:
                grass.fatal(
                    _(
                        f"Directory {targetdir_grass} is not empty!"
                        f" As data is shared between GeoServer and"
                        f" actinia, layer might already exist."
                    )
                )

        # if this addon is called via an actinia container, this dir is
        # created as root and geoserver may not have rights to create
        # a coverage store based on it. Therefore, change permissions to
        # USR RWX, OTHER RWX (the permissions are not updated, but overwritten):
        os.chmod(
            targetdir_grass,
            stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IXUSR
            | stat.S_IROTH
            | stat.S_IWOTH
            | stat.S_IXOTH,
        )

        # export maps with timestamp in their filename
        for rescaled_map, time in zip(rescaled_maps, map_times):
            time_str = time[0].strftime("%Y%m%d")
            uuid_str = str(uuid.uuid4())
            output_map = f"{rescaled_map}_{uuid_str}_time_{time_str}.tif"
            tif_path = os.path.join(targetdir_grass, output_map)
            grass.run_command("g.region", raster=rescaled_map)
            grass.run_command(
                "r.out.gdal",
                createopt="COMPRESS=LZW,TILED=YES",
                flags="mc",
                input=rescaled_map,
                output=tif_path,
                format="COG",
                overviews=5,
            )
        # add additional files in the geoserver dir for proper
        # temporal data handling
        create_imagemosaic_auxfiles(targetdir_grass)
        # create image mosaic coveragestore
        geoserver_auth = (geoserver_user, geoserver_pw)
        coverage_name = f"{mosaic_layername}_coverage_{pid}"

        # get projection of current location
        proj = grass.parse_command("g.proj", flags="g")
        if "epsg" in proj:
            epsg = proj["epsg"]
        else:
            epsg = proj["srid"].split("EPSG:")[1]

        if geoserver_datapath:
            # Case when GRASS GIS and GeoServer share a common directory
            # Data is stored there and GS is told to create a new layer
            targetdir_geoserver = os.path.join(
                geoserver_datapath, "geodata", mosaic_layername
            )
            create_imagemosaic_coveragestore(
                targetdir_geoserver,
                coverage_name,
                geoserver_host,
                geoserver_port,
                geoserver_workspace,
                geoserver_auth,
            )
            # create layer from coveragestore
            create_geoserver_layer(
                mosaic_layername,
                geoserver_workspace,
                coverage_name,
                epsg,
                geoserver_host,
                geoserver_port,
                geoserver_auth,
            )
            layernames.append(mosaic_layername)

        else:
            # Case when GRASS GIS and GeoServer cannot share a common directory
            # Data is archived and uploaded to GS to create a new layer

            zip_basename = f"{targetdir_grass.split(output_uuid)[0]}{output_uuid}"
            zip_name = f"{zip_basename}.zip"
            zip_mosaic_definition_and_granules(targetdir_grass, zip_basename)

            upload_new_imagemosaic(
                geoserver_workspace,
                coverage_name,
                geoserver_host,
                geoserver_port,
                geoserver_auth,
                zip_name,
            )
            # update name and time configuration in layer
            update_geoserver_layer(
                mosaic_layername,
                geoserver_workspace,
                coverage_name,
                epsg,
                geoserver_host,
                geoserver_port,
                geoserver_auth,
            )
            rm_dirs.append(outputfolder)
            layernames.append(mosaic_layername)

    # style the layer(s)
    if color:
        for layername in layernames:
            grass.message(
                _(f"Styling layer {layername} with" " GRASS color table {color}...")
            )
            ref_map = rescaled_maps[0]
            color_kwargs = {"map": ref_map, "color": color}
            if color_rules[color] != "map values":
                color_min = color_rules[color][0]
                color_max = color_rules[color][1]
                offset = 0 - color_min
                old_range = color_max - color_min
                scale = 255 / old_range
                color_kwargs["offset"] = offset
                color_kwargs["scale"] = scale
            grass.run_command("r.colors", **color_kwargs)
            grass.run_command(
                "r.geoserver.style",
                host=geoserver_host,
                port=geoserver_port,
                user=geoserver_user,
                password=geoserver_pw,
                workspace=geoserver_workspace,
                layername=layername,
                grassmap=ref_map,
                flags="n",
            )

    grass.message(_(f"Published layer/s {layernames} from STRDS {input}."))


if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    main()
