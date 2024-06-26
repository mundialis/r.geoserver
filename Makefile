MODULE_TOPDIR = ../..

PGM = r.geoserver

# note: to deactivate a module, just place a file "DEPRECATED" into the subdir
ALL_SUBDIRS := ${sort ${dir ${wildcard */.}}}
DEPRECATED_SUBDIRS := ${sort ${dir ${wildcard */DEPRECATED}}}
RM_SUBDIRS := bin/ docs/ etc/ scripts/
SUBDIRS_1 := $(filter-out $(DEPRECATED_SUBDIRS), $(ALL_SUBDIRS))
SUBDIRS := $(filter-out $(RM_SUBDIRS), $(SUBDIRS_1))

include $(MODULE_TOPDIR)/include/Make/Dir.make

python-requirements:
	pip install -r requirements.txt

default: python-requirements parsubdirs htmldir

install: installsubdirs
	$(INSTALL_DATA) $(PGM).html $(INST_DIR)/docs/html/
