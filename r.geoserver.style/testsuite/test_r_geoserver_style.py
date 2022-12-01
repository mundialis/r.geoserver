#!/usr/bin/env python3
#
############################################################################
#
# MODULE:      r.geoserver.style test
# AUTHOR(S):   Anika Weinmann
#
# PURPOSE:     Tests r.geoserver.style.
#              Uses NC full sample data set and MODIS data mapset
#              https://grass.osgeo.org/sampledata/north_carolina/nc_spm_mapset_modis2015_2016_lst.zip.
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

import os
import random
import requests
import string
import unittest

import grass.script as grass
from grass.gunittest.case import TestCase
from grass.gunittest.main import test
from grass.gunittest.gmodules import SimpleModule


def check_geoserver_connection(geoserver_user, geoserver_password, baseurl):
    """Function that checks the geoserver connection and sets the
    TEST_GEOSERVER_CONNECTION environment variable to 'True' or 'False'"""
    url = f"{baseurl}/rest"
    try:
        resp = requests.get(url, auth=(geoserver_user, geoserver_password))
        if resp.status_code == 200:
            os.environ["TEST_GEOSERVER_CONNECTION"] = str(True)
        else:
            os.environ["TEST_GEOSERVER_CONNECTION"] = str(False)
    except Exception:
        os.environ["TEST_GEOSERVER_CONNECTION"] = str(False)


class TestGeoserverPublish(TestCase):
    """Base class for the r.geoserver.publish tests.
    Copy of the TestGeoserverPublish class from r.geoserver.publish
    """

    geoserver_host = "localhost"
    geoserver_port = 8080
    geoserver_user = "admin"
    geoserver_password = "geoserver"
    geoserver_grass_path = "/grassdb"
    baseurl = f"http://{geoserver_host}:{geoserver_port}/geoserver"
    headers = {"content-type": "application/json"}
    check_geoserver_connection(geoserver_user, geoserver_password, baseurl)

    @classmethod
    def delete_coveragestore(cls, workspace, coveragestore):
        """Delete the created coveragestore"""
        url = (
            f"{cls.baseurl}/rest/workspaces/{workspace}/"
            f"coveragestores/{coveragestore}?recurse=true"
        )
        resp = requests.delete(url, auth=(cls.geoserver_user, cls.geoserver_password))
        if resp.status_code != 200:
            cls.assertIn(
                "No such coverage store",
                resp.text,
                "Coverage store can not be deleted!",
            )

    @classmethod
    def delete_workspace(cls, workspace):
        """Delete the created workspace"""
        url = f"{cls.baseurl}/rest/workspaces/{workspace}?recurse=true"
        resp = requests.delete(url, auth=(cls.geoserver_user, cls.geoserver_password))
        if resp.status_code != 200:
            cls.assertIn(
                "Status 404 – Not Found", resp.text, "Workspace can not be deleted!"
            )


class TestRGeoserverStyleRaster(TestGeoserverPublish):
    """Test class to test the style of published raster"""

    location_name = "nc_spm_08_grass7"
    mapset = "PERMANENT"
    current_mapset = None

    random_str = "".join(random.choice(string.ascii_letters) for i in range(8))
    workspace = f"r_geoserver_publish_test_raster_WS_{random_str}"
    coveragestore = f"r_geoserver_publish_test_raster_CS_{random_str}"
    layername = f"r_geoserver_publish_test_raster_L_{random_str}"
    sld = """<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:Title>elevation : "South-West Wake county: Elevation NED 10m"</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#000000" opacity="0" quantity="0"/>
              <sld:ColorMapEntry color="#00bfbf" opacity="1" quantity="55.5788"/>
              <sld:ColorMapEntry color="#00ff00" opacity="1" quantity="75.729"/>
              <sld:ColorMapEntry color="#ffff00" opacity="1" quantity="95.8792"/>
              <sld:ColorMapEntry color="#ff7f00" opacity="1" quantity="116.029"/>
              <sld:ColorMapEntry color="#bf7f3f" opacity="1" quantity="136.18"/>
              <sld:ColorMapEntry color="#141414" opacity="1" quantity="156.33"/>
            </sld:ColorMap>
            <sld:ContrastEnhancement/>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>"""

    run_tests = False

    @classmethod
    def tearDownClass(cls):
        """Remove the created workspace and coveragestore"""
        if cls.run_tests is not False:
            # delete coveragestore
            cls.delete_coveragestore(cls.workspace, cls.coveragestore)
            # delete workspace
            cls.delete_workspace(cls.workspace)
        # remove env var from check_geoserver_connection
        if "TEST_GEOSERVER_CONNECTION" in os.environ:
            del os.environ["TEST_GEOSERVER_CONNECTION"]

    def getGeoServerPath(self):
        return os.path.join(self.geoserver_grass_path, self.location_name, self.mapset)

    @unittest.skipIf(
        os.environ["TEST_GEOSERVER_CONNECTION"] != "True",
        "Geoserver can not be reached.",
    )
    def test_style_of_raster(self):
        """Test style of a raster map"""
        self.__class__.run_tests = True
        self.runModule(
            "r.geoserver.publish",
            input="elevation",
            host=self.geoserver_host,
            port=self.geoserver_port,
            user=self.geoserver_user,
            password=self.geoserver_password,
            workspace=self.workspace,
            coveragestore=self.coveragestore,
            layername=self.layername,
            gs_file_path=self.getGeoServerPath(),
        )

        r_geoserver_style = SimpleModule(
            "r.geoserver.style",
            host=self.geoserver_host,
            port=self.geoserver_port,
            user=self.geoserver_user,
            password=self.geoserver_password,
            workspace=self.workspace,
            layername=self.layername,
        )
        self.assertModule(r_geoserver_style)
        stderr = r_geoserver_style.outputs.stderr
        self.assertIn("Style attached.", stderr)
        url = (
            f"{self.baseurl}/rest/workspaces/{self.workspace}/styles/"
            f"{self.layername}.sld"
        )
        resp = requests.get(url, auth=(self.geoserver_user, self.geoserver_password))
        self.assertEqual(
            resp.status_code,
            200,
            "Requesting the style of the layer does not return status code 200",
        )
        resp_content = resp.text
        self.assertIn(self.sld, resp_content, "SLD in response is not as expected")


class TestRGeoserverPublishSTRDS(TestGeoserverPublish):
    """Test class to test the style of a published STRDS"""

    location_name = "nc_spm_08_grass7"
    mapset = "modis_lst"
    current_mapset = None

    random_str = "".join(random.choice(string.ascii_letters) for i in range(8))
    workspace = f"r_geoserver_publish_test_strds_WS_{random_str}"
    coveragestore = f"r_geoserver_publish_test_strds_CS_{random_str}"
    layername = f"r_geoserver_publish_test_strds_L_{random_str}"
    sld = """<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:Title>MOD11B3.A2015001.h11v05.single_LST_Day_6km : ""</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#000000" opacity="0" quantity="0"/>
              <sld:ColorMapEntry color="#0000ff" opacity="1" quantity="13022"/>
              <sld:ColorMapEntry color="#00ffff" opacity="1" quantity="13480"/>
              <sld:ColorMapEntry color="#ffff00" opacity="1" quantity="13938"/>
              <sld:ColorMapEntry color="#ff0000" opacity="1" quantity="14396"/>
            </sld:ColorMap>
            <sld:ContrastEnhancement/>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>"""

    run_tests = False

    @classmethod
    def setUpClass(cls):
        """Change the mapset"""
        cls.current_mapset = [x for x in grass.parse_command("g.mapset", flags="p")][0]
        cls.runModule("g.mapset", mapset=cls.mapset)

    @classmethod
    def tearDownClass(cls):
        """Remove the created workspace and coveragestore"""
        if cls.run_tests is not False:
            # delete coveragestore
            cls.delete_coveragestore(cls.workspace, cls.coveragestore)
            # delete workspace
            cls.delete_workspace(cls.workspace)
        # remove env var from check_geoserver_connection
        if "TEST_GEOSERVER_CONNECTION" in os.environ:
            del os.environ["TEST_GEOSERVER_CONNECTION"]
        # change to previouse mapset
        if cls.current_mapset is not None:
            cls.runModule("g.mapset", mapset=cls.current_mapset)

    def getGeoServerPath(self):
        return os.path.join(self.geoserver_grass_path, self.location_name, self.mapset)

    @unittest.skipIf(
        os.environ["TEST_GEOSERVER_CONNECTION"] != "True",
        "Geoserver can not be reached.",
    )
    def test_style_of_strds(self):
        """Test style of a STRDS"""
        self.__class__.run_tests = True

        self.runModule(
            "r.geoserver.publish",
            input="LST_Day_monthly",
            host=self.geoserver_host,
            port=self.geoserver_port,
            user=self.geoserver_user,
            password=self.geoserver_password,
            workspace=self.workspace,
            coveragestore=self.coveragestore,
            layername=self.layername,
            gs_file_path=self.getGeoServerPath(),
        )

        r_geoserver_style = SimpleModule(
            "r.geoserver.style",
            host=self.geoserver_host,
            port=self.geoserver_port,
            user=self.geoserver_user,
            password=self.geoserver_password,
            workspace=self.workspace,
            layername=self.layername,
        )
        self.assertModule(r_geoserver_style)

        stderr = r_geoserver_style.outputs.stderr
        self.assertIn("Style attached.", stderr)
        url = (
            f"{self.baseurl}/rest/workspaces/{self.workspace}/styles/"
            f"{self.layername}.sld"
        )
        resp = requests.get(url, auth=(self.geoserver_user, self.geoserver_password))
        self.assertEqual(
            resp.status_code,
            200,
            "Requesting the style of the layer does not return status code 200",
        )
        resp_content = resp.text
        self.assertIn(self.sld, resp_content, "SLD in response is not as expected")


if __name__ == "__main__":
    test()
