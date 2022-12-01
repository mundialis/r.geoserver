#!/usr/bin/env bash

# fail on non-zero return code from a subprocess
set -e

#GRASSDB=/grassdb
GRASSDB=/tmp

# download NC test location if the test needs the data
if [ "$1" == "NC" ]
then
  # this is run in nc_spm_empty
  g.extension g.download.location
  # fetch default NC location
  g.download.location url=https://grass.osgeo.org/sampledata/north_carolina/nc_spm_08_grass7.tar.gz path=$GRASSDB
  g.mapset location=nc_spm_08_grass7 mapset=PERMANENT -c
  r.info -g elevation

  # download NC MODIS LST time series and unpack it in nc_spm_08_grass7
  cd $GRASSDB/nc_spm_08_grass7/ && \
	wget https://grass.osgeo.org/sampledata/north_carolina/nc_spm_mapset_modis2015_2016_lst.zip && \
	unzip nc_spm_mapset_modis2015_2016_lst.zip && \
	rm -f nc_spm_mapset_modis2015_2016_lst.zip
  g.mapset location=nc_spm_08_grass7 mapset=modis_lst -c
  r.info -g MOD11B3.A2015182.h11v05.single_LST_Day_6km
fi

# run tests in docker space
cd /src

# collect and run all tests in folder
FILENAME=$(basename "$(find . -name *.html -maxdepth 1)")
ADDON="${FILENAME%%.html}"

CURRENTDIR=$(pwd)
g.extension extension=${ADDON} url=. && \
for file in $(find . -type f -name test*.py) ; \
do  \
  echo ${file} ; \
  BASENAME=$(basename "${file}") ; \
  DIR=$(dirname "${file}") ; \
  cd ${CURRENTDIR}/${DIR} && python3 -m unittest ${BASENAME}
done
