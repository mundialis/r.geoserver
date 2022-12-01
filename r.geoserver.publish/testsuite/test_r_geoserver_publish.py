#!/usr/bin/env python3
#
############################################################################
#
# MODULE:      r.geoserver.publish test
# AUTHOR(S):   Anika Weinmann
#
# PURPOSE:     Tests r.geoserver.publish.
#              Uses NC full sample data set and MODIS data mapset
#              https://grass.osgeo.org/sampledata/north_carolina/nc_spm_mapset_modis2015_2016_lst.zip.
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
############################################################################

import json
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
    """Base class for the r.geoserver.publish tests"""

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


class TestRGeoserverPublishRaster(TestGeoserverPublish):
    """Test class to test the publishing of raster maps"""

    location_name = "nc_spm_08_grass7"
    mapset = "PERMANENT"
    current_mapset = None

    random_str = "".join(random.choice(string.ascii_letters) for i in range(8))
    workspace = f"r_geoserver_publish_test_raster_WS_{random_str}"
    coveragestore = f"r_geoserver_publish_test_raster_CS_{random_str}"
    layername = f"r_geoserver_publish_test_raster_L_{random_str}"

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
    def test_publish_raster(self):
        """Test publishing of a raster"""
        self.__class__.run_tests = True

        r_geoserver_publish = SimpleModule(
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
        self.assertModule(r_geoserver_publish)
        stderr = r_geoserver_publish.outputs.stderr
        self.assertIn("Creation of coverage succeeded!", stderr)
        url = (
            f"{self.baseurl}/{self.workspace}/wms?SERVICE=WMS&VERSION=1.1.1"
            "&REQUEST=GetFeatureInfo&FORMAT=application%2Fjson&TRANSPARENT"
            f"=true&QUERY_LAYERS={self.workspace}%3A{self.layername}&"
            f"LAYERS={self.workspace}%3A{self.layername}&exceptions="
            "application%2Fvnd.ogc.se_inimage&INFO_FORMAT=application%2Fjson"
            "&FEATURE_COUNT=50&X=50&Y=50&SRS=EPSG%3A32119&STYLES=&WIDTH=101"
            "&HEIGHT=101&BBOX=634509.2720376598%2C221209.27014859256%2C"
            "636437.1464258735%2C223137.14453680618"
        )
        resp = requests.get(url, auth=(self.geoserver_user, self.geoserver_password))
        self.assertEqual(
            resp.status_code,
            200,
            "Requesting the published layer does not return status code 200",
        )
        resp_content = json.loads(resp.text)
        self.assertIn("features", resp_content, "'features' not in response")
        self.assertEqual(1, len(resp_content["features"]), "Length of 'features' not 1")
        feat = resp_content["features"][0]
        self.assertIn("properties", feat, "'properties' not feature")
        self.assertIn(
            "elevation", feat["properties"], "'elevation' not features properties"
        )
        self.assertEqual(
            121.71666717529297,
            feat["properties"]["elevation"],
            "Value of feature is not 14193",
        )


class TestRGeoserverPublishSTRDS(TestGeoserverPublish):
    """Test class to test the publishing of STRDS"""

    location_name = "nc_spm_08_grass7"
    mapset = "modis_lst"
    current_mapset = None

    random_str = "".join(random.choice(string.ascii_letters) for i in range(8))
    workspace = f"r_geoserver_publish_test_strds_WS_{random_str}"
    coveragestore = f"r_geoserver_publish_test_strds_CS_{random_str}"
    layername = f"r_geoserver_publish_test_strds_L_{random_str}"

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
    def test_publish_strds(self):
        """Test publishing of a STRDS"""
        self.__class__.run_tests = True

        r_geoserver_publish = SimpleModule(
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
        self.assertModule(r_geoserver_publish)
        stderr = r_geoserver_publish.outputs.stderr
        self.assertIn("Creation of coverage succeeded!", stderr)
        url = (
            f"{self.baseurl}/{self.workspace}/wms?SERVICE=WMS&VERSION=1.1.1"
            "&REQUEST=GetFeatureInfo&FORMAT=application%2Fjson&TRANSPARENT"
            f"=true&QUERY_LAYERS={self.workspace}%3A{self.layername}&"
            f"LAYERS={self.workspace}%3A{self.layername}&exceptions="
            "application%2Fvnd.ogc.se_inimage&INFO_FORMAT=application%2Fjson"
            "&FEATURE_COUNT=50&X=50&Y=50&SRS=EPSG%3A32119&STYLES=&WIDTH=101"
            "&HEIGHT=101&BBOX=276086.8826843766%2C-107502.85697444755"
            "%2C769622.726067068%2C386032.9864082438"
        )

        resp = requests.get(url, auth=(self.geoserver_user, self.geoserver_password))
        self.assertEqual(
            resp.status_code,
            200,
            "Requesting the published layer does not return status code 200",
        )
        resp_content = json.loads(resp.text)
        self.assertIn("features", resp_content, "'features' not in response")
        self.assertEqual(1, len(resp_content["features"]), "Length of 'features' not 1")
        feat = resp_content["features"][0]
        self.assertIn("properties", feat, "'properties' not feature")
        self.assertIn(
            "sqlite.db", feat["properties"], "'sqlite.db' not features properties"
        )
        self.assertEqual(
            14193, feat["properties"]["sqlite.db"], "Value of feature is not 14193"
        )


if __name__ == "__main__":
    test()
