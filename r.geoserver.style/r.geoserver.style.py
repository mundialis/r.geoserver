#!/usr/bin/env python3
#
############################################################################
#
# MODULE:      r.geoserver.style
# AUTHOR(S):   Anika Weinmann
#              Carmen Tawalika
#
# PURPOSE:     Publish a style based on GRASS GIS map and attach it to
#              a layer in GeoServer
# COPYRIGHT:    (C) 2019-2022 by mundialis GmbH & Co. KG and the GRASS Development Team
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
# % description: Publishes a map style based on GRASS GIS map and attaches it to a layer in GeoServer.
# % keyword: geoserver-grass-datastore
# % keyword: raster
# % keyword: temporal
# % keyword: geoserver
# %End

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
# % key: layername
# % type: string
# % required: yes
# % multiple: no
# % label: Layername
# %end

# %option
# % key: grassmap
# % type: string
# % required: no
# % multiple: no
# % label: GRASS map to use style from (only required if grass gis raster datastore plugin is not used)
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

# %flag
# % key: n
# % description: Prevent to set 0 as nodata value in SLD
# %end

import json
import re
import requests
from grass.script import core as grass


def main():

    host = options["host"]
    port = options["port"]
    user = options["user"]
    pw = options["password"]
    workspace = options["workspace"]
    layername = options["layername"]
    type = options["type"]
    prevent_nodata = flags["n"]

    # Check if r.colors.out_sld is installed first
    if not grass.find_program("r.colors.out_sld", "--help"):
        grass.fatal(
            _(
                "The 'r.colors.out_sld' module was not found, install it"
                " first:\n g.extension r.colors.out_sld"
            )
        )

    url = "%s:%s/geoserver/rest/workspaces/%s/layers/%s" % (
        host,
        port,
        workspace,
        layername,
    )
    resp = requests.get(url, auth=(user, pw))
    layer_dict = json.loads(resp.text)
    coverages_url = layer_dict["layer"]["resource"]["href"]
    resp = json.loads(requests.get(coverages_url, auth=(user, pw)).text)
    if options["grassmap"]:
        grassmap = options["grassmap"]
    else:
        grass.message(_("Find out GRASS mapname..."))
        grassmap = resp["coverage"]["nativeCoverageName"].split("@")[0]

    # Check type and if map exists
    strds_exists = False
    if type == "auto" or type == "strds":
        strds_in_mapset = [
            strds.split("@")[0] for strds in grass.parse_command("t.list")
        ]
        if grassmap in strds_in_mapset:
            strds_exists = True
            type = "strds"
    raster_exists = False
    if type == "auto" or type == "raster":
        raster_in_mapset = [
            rast.split("@")[0] for rast in grass.parse_command("g.list", type="raster")
        ]
        if grassmap in raster_in_mapset:
            raster_exists = True
            type = "raster"
    if raster_exists and strds_exists:
        grass.fatal(_(f"There is both a strds and a raster with name <{grassmap}>"))
    elif raster_exists is False and strds_exists is False:
        grass.fatal(_(f"Input <{grassmap}> does not exist"))

    if type == "strds":
        grassmap = [
            *grass.parse_command(
                "t.rast.list", input=grassmap, columns="name", flags="u"
            )
        ][0]

    grass.message(_("Generate SLD..."))
    style = grass.read_command("r.colors.out_sld", map=grassmap)
    broken_entry = re.search(r"(<).*?NaN.*?(>)", style)
    if broken_entry is not None:
        style = style.replace(broken_entry.group() + "\n", "")
    if not prevent_nodata:
        nodata_l = '<ColorMapEntry color="#000000" opacity="0" quantity="0"/>'
        style = style.replace("<ColorMap>\n", "<ColorMap>\n" + nodata_l + "\n")

    grass.message(_("Create empty style..."))
    headers = {"content-type": "application/json"}
    style_dict = {"style": {"name": layername, "filename": layername + ".sld"}}
    postbody = json.dumps(style_dict)
    url = "%s:%s/geoserver/rest/workspaces/%s/styles" % (host, port, workspace)
    resp = requests.post(url, headers=headers, data=postbody, auth=(user, pw))
    if resp.status_code != 201:
        grass.fatal(_("Creation of style failed!"))
    else:
        grass.message(_("Empty style created."))

    grass.message(_("Add content to empty style..."))
    headers = {"content-type": "application/vnd.ogc.sld+xml"}
    url = "%s:%s/geoserver/rest/workspaces/%s/styles/%s" % (
        host,
        port,
        workspace,
        layername,
    )
    resp = requests.put(url, headers=headers, data=style, auth=(user, pw))
    if resp.status_code != 200:
        grass.fatal(_("Adding content to empty style failed!"))
    else:
        grass.message(_("Added content to empty style."))

    grass.message(_("Attaching style to layer..."))
    layer_dict["layer"]["defaultStyle"]["name"] = layername
    layer_dict["layer"]["defaultStyle"][
        "href"
    ] = "%s:%s/geoserver/rest/workspaces/%s/styles/%s.json" % (
        host,
        port,
        workspace,
        layername,
    )
    headers = {"content-type": "application/json"}
    postbody = json.dumps(layer_dict)
    url = "%s:%s/geoserver/rest/workspaces/%s/layers/%s" % (
        host,
        port,
        workspace,
        layername,
    )
    resp = requests.put(url, headers=headers, data=postbody, auth=(user, pw))
    print(resp.status_code)
    print(resp.text)
    if resp.status_code != 200:
        grass.fatal(_("Attaching of style failed!"))
    else:
        grass.message(_("Style attached."))


if __name__ == "__main__":
    options, flags = grass.parser()
    main()
