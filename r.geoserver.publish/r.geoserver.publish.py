#!/usr/bin/env python3
#
############################################################################
#
# MODULE:      r.geoserver.publish
# AUTHOR(S):   Anika Weinmann
#              Carmen Tawalika
#
# PURPOSE:     Publishes a raster map and space time raster data sets with
#              geoserver-grass-datastore
# COPYRIGHT:   (C) 2019-2022 by mundialis GmbH & Co. KG and the GRASS Development Team
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
# % description: Publishes a raster map or STRDS set through the geoserver-grass-raster-datastore.
# % keyword: geoserver-grass-datastore
# % keyword: raster
# % keyword: temporal
# % keyword: geoserver
# %End

# %option
# % key: input
# % type: string
# % required: yes
# % multiple: no
# % label: Name of raster map or space time raster dataset
# %end

# %option
# % key: host
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer host including URI scheme
# %end

# %option
# % key: port
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer port
# %end

# %option
# % key: user
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer user
# %end

# %option
# % key: password
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer password
# %end

# %option
# % key: workspace
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer workspace
# %end

# %option
# % key: coveragestore
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer coveragestore
# %end

# %option
# % key: layername
# % type: string
# % required: yes
# % multiple: no
# % label: Layername
# %end

# %option
# % key: title
# % type: string
# % required: no
# % multiple: no
# % label: Layer title
# %end

# %option
# % key: gs_file_path
# % type: string
# % required: yes
# % multiple: no
# % label: GeoServer filepath to GRASS mapset
# %end

# %option
# % key: type
# % type: string
# % required: no
# % multiple: no
# % options: raster,strds,auto
# % label: Data set type of input
# % answer: auto
# %end

# TODO test if layer already exists

import json
import os
import requests
from grass.script import core as grass


def main():

    input = options["input"].split("@")[0]
    type = options["type"]
    host = options["host"]
    port = options["port"]
    user = options["user"]
    pw = options["password"]
    workspace = options["workspace"]
    coveragestore = options["coveragestore"]
    layername = options["layername"]
    if options["title"]:
        title = options["title"]
    else:
        title = layername
    gs_file_path = options["gs_file_path"]

    # check location
    location = gs_file_path.split(os.sep)[-2]
    mapset = gs_file_path.split(os.sep)[-1]
    with open(os.environ["GISRC"], "r") as f:
        gisrc = f.read()
    current_location = [
        line.split(":")[1].strip()
        for line in gisrc.splitlines()
        if line.startswith("LOCATION_NAME")
    ][0]
    if location != current_location:
        grass.fatal(
            _(
                "The <gs_file_path> contains a location which is not "
                "the current location"
            )
        )

    # get projection of current location
    proj = grass.parse_command("g.proj", flags="g")
    if "epsg" in proj:
        epsg = proj["epsg"]
    else:
        epsg = proj["srid"].split("EPSG:")[1]

    # check type and build path
    strds_exists = False
    if type == "auto" or type == "strds":
        strds_in_mapset = [
            strds.split("@")[0] for strds in grass.parse_command("t.list")
        ]
        if input in strds_in_mapset:
            strds_exists = True
            gs_file_path = os.path.join(gs_file_path, "tgis", "sqlite.db")
            type = "strds"
    raster_exists = False
    if type == "auto" or type == "raster":
        raster_in_mapset = [
            rast.split("@")[0] for rast in grass.parse_command("g.list", type="raster")
        ]
        if input in raster_in_mapset:
            raster_exists = True
            gs_file_path = os.path.join(gs_file_path, "cellhd", input)
            type = "raster"
    if raster_exists and strds_exists:
        grass.fatal(_(f"There is both a strds and a raster with name <{input}>"))
    elif raster_exists is False and strds_exists is False:
        grass.fatal(_(f"Input <{input}> does not exist"))

    headers = {"content-type": "application/json"}

    grass.message(_("Create workspace if not exists..."))
    workspace_dict = {"workspace": {"name": workspace}}

    postbody = json.dumps(workspace_dict)
    url = "%s:%s/geoserver/rest/workspaces" % (host, port)
    resp = requests.post(url, headers=headers, data=postbody, auth=(user, pw))
    if resp.status_code != 201:
        if resp.status_code == 401:
            grass.message(_("Workspace already exists"))
        else:
            grass.fatal(_("Creation of workspace failed!"))
    else:
        grass.message(_("Workspace did not exist and was created."))

    grass.message(_("Create coveragestore..."))
    coveragestore_dict = {
        "coverageStore": {
            "name": coveragestore,
            "type": "GRASS",
            "enabled": True,
            "workspace": {"name": workspace},
            "url": "file:%s" % gs_file_path,
        }
    }
    postbody = json.dumps(coveragestore_dict)
    url = "%s:%s/geoserver/rest/workspaces/%s/coveragestores" % (host, port, workspace)
    resp = requests.post(url, headers=headers, data=postbody, auth=(user, pw))
    if resp.status_code != 201:
        grass.fatal(_("Creation of coveragestore failed!"))

    grass.message(_("Create layer..."))
    if type == "raster":
        metadata = {}
    else:
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
                {"@key": "dirName", "$": f"{coveragestore}_{layername}"},
            ]
        }

    coverage_dict = {
        "coverage": {
            "description": "Generated from GRASS GIS",
            "enabled": True,
            "nativeCoverageName": f"{input}@{mapset}",
            "keywords": {"string": ["WCS", title]},
            "name": layername,
            "namespace": {"name": workspace},
            "metadata": metadata,
            "srs": "EPSG:%s" % str(epsg),
            "store": {
                "@class": "coverageStore",
                "name": "%s:%s" % (workspace, coveragestore),
            },
            "title": title,
        }
    }

    postbody = json.dumps(coverage_dict)
    url = "%s:%s/geoserver/rest/workspaces/%s/coveragestores/%s/coverages" % (
        host,
        port,
        workspace,
        coveragestore,
    )
    resp = requests.post(url, headers=headers, data=postbody, auth=(user, pw))
    if resp.status_code != 201:
        grass.fatal(
            _("Creation of coverage failed! \n <%s> \n <%s>")
            % (str(resp.status_code), resp.text)
        )
    else:
        grass.message(_("Creation of coverage succeeded!"))


if __name__ == "__main__":
    options, flags = grass.parser()
    main()
