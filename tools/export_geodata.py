# -*- coding: utf-8 -*-

"""
/***************************************************************************
 IdrAgraTools
 A QGIS plugin to manage water demand simulation with IdrAgra model
 The plugin shares user interfaces and tools to manage water in irrigation districts
-------------------
		begin				: 2020-12-01
		copyright			: (C) 2020 by Enrico A. Chiaradia
		email				    : enrico.chiaradia@unimi.it
 ***************************************************************************/

/***************************************************************************
 *																		   *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or	   *
 *   (at your option) any later version.								   *
 *																		   *
 ***************************************************************************/
"""
__author__ = 'Enrico A. Chiaradia'
__date__ = '2020-12-01'
__copyright__ = '(C) 2020 by Enrico A. Chiaradia'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import glob
import os
import numpy as np
from qgis import processing

from .compact_dataset import save2idragra
from .gis_grid import GisGrid
from .utils import returnExtent
from .write_pars_to_template import writeParsToTemplate


def exportGeodata(DBM,outPath, extent, cellSize, dtm, watertableDict, depthList,yearList,feedback = None,tr=None):
	yearList = [str(x) for x in yearList] # make a list of strings
	# TODO: fix output digits
	# export water district map
	# DISTRICT SOURCE
	feedback.pushInfo(tr('Exporting districts data'))
	feedback.setProgress(10.0)
	fileName = os.path.join(outPath, 'irr_units' + '.asc')
	laySource = DBM.DBName+ '|layername=idr_distrmap'
	fieldName = 'node'

	algResults = processing.run("idragratools:IdragraRasterizeMap",
							   {'VECTOR_LAY': laySource, 'VECTOR_FLD': fieldName,
								'RASTER_EXT': extent,
								'CELL_DIM': cellSize,
								'DEST_FILE': fileName},
							context = None, feedback = feedback, is_child_algorithm = False)

	# DISTRICT EFFICIENCY
	fileName = os.path.join(outPath, 'conv_eff' + '.asc')
	laySource = DBM.DBName+ '|layername=idr_distrmap'
	fieldName = 'distr_eff'

	feedback.setProgress(35.0)
	algResults = processing.run("idragratools:IdragraRasterizeMap",
								{'VECTOR_LAY': laySource, 'VECTOR_FLD': fieldName,
								 'RASTER_EXT': extent,
								 'CELL_DIM': cellSize,
								 'DEST_FILE': fileName},
								context=None, feedback=feedback, is_child_algorithm=False)

	feedback.pushInfo(tr('Exporting soils parameters'))
	feedback.setProgress(50.0)
	# SOIL PARAMETERS MAP
	# make aggregate parameters
	sourceTable = DBM.DBName + '|layername=idr_soil_profiles'
	soilMap = DBM.DBName + '|layername=idr_soilmap'
	depths = ' '.join([str(x) for x in depthList])
	# make aggregate soil params
	algResults = processing.run("idragratools:IdragraSoilParams",
								{'SOURCE_TABLE':sourceTable,
								 'SOILID_FLD':'soilid','MAXDEPTH_FLD':'maxdepth',
								 'KSAT_FLD':'ksat',
								 'TFC_FLD':'theta_fc','TWP_FLD':'theta_wp','TR_FLD':'theta_r','TS_FLD':'theta_sat',
								 'DEPTHS':depths,'OUT_TABLE':'TEMPORARY_OUTPUT'},
								context=None, feedback=feedback, is_child_algorithm=False)

	# export to maps
	algResults =  processing.run("idragratools:IdragraRasterizeMaptable",
								 {'TABLE_LAY': algResults['OUT_TABLE'],# export aggregate params maps by aritmetic mean ...
								  'TABLE_FLD': 'soilid', 'VECTOR_LAY': soilMap,
								  'VECTOR_FLD': 'extid', 'RASTER_LAY': None,
								  'RASTER_EXT':extent,
								  'CELL_DIM': cellSize, 'DEST_FOLDER': outPath},
							     context=None, feedback=feedback, is_child_algorithm=False)

	# make capillary rise params maps
	algResults = processing.run("idragratools:IdragraCreateCapriseTable",
				   {'SOURCE_TABLE': sourceTable,
					'SOILID_FLD': 'soilid', 'MAXDEPTH_FLD': 'maxdepth',
					'TXTR_FLD': 'txtr_code', 'DEPTHS': depths,
					'OUT_TABLE': 'TEMPORARY_OUTPUT'},
				   context=None, feedback=feedback, is_child_algorithm=False)

	# export capillary rise params maps...
	algResults = processing.run("idragratools:IdragraRasterizeMaptable", {
		'TABLE_LAY': algResults['OUT_TABLE'],
		'TABLE_FLD': 'soilid', 'VECTOR_LAY': soilMap,
		'VECTOR_FLD': 'extid', 'RASTER_LAY': None,
		'RASTER_EXT': extent,
		'CELL_DIM': cellSize, 'DEST_FOLDER': outPath},
								context=None, feedback=feedback, is_child_algorithm=False)

	# HSG MAP
	feedback.pushInfo(tr('Exporting HSG map'))
	feedback.setProgress(70.0)

	algResults1 = processing.run("idragratools:IdragraCreatePreHSGTable",
							   {'SOURCE_TABLE': sourceTable,
								'SOILID_FLD': 'soilid', 'MAXDEPTH_FLD': 'maxdepth', 'KSAT_FLD': 'ksat',
								'OUT_TABLE': 'TEMPORARY_OUTPUT'},
								context=None, feedback=feedback, is_child_algorithm=False)

	algResults2 = processing.run("gdal:rasterize",
								{'INPUT': soilMap, 'FIELD': 'extid', 'BURN': 0,
								 'UNITS': 1, 'WIDTH': cellSize, 'HEIGHT': cellSize,
								 'EXTENT': extent,
								 'NODATA': -9, 'OPTIONS': '', 'DATA_TYPE': 4, 'INIT': -9, 'INVERT': False,
								 'EXTRA': '',
								 'OUTPUT': 'TEMPORARY_OUTPUT'},
								context=None, feedback=feedback, is_child_algorithm=False
								)

	fileName = os.path.join(outPath, 'hydr_group' + '.asc')
	waterTableFirst = ''
	for var, waterTable in watertableDict.items():
		waterTableFirst = waterTable
		break

	algResults = processing.run("idragratools:IdragraCreateHSGMap", {
								'SOURCE_TABLE': algResults1['OUT_TABLE'],
								'SOILID_FLD': 'soilid', 'MAXDEPTH_FLD': 'maxsoildepth', 'MIN_KS50': 'minksat50', 'MIN_KS60': 'minksat60',
								'MIN_KS100': 'minksat100', 'SOIL_MAP': algResults2['OUTPUT'],
								'ELEVATION': dtm,
								'WATERTABLE': waterTableFirst, 'OUTPUT': fileName},
								context=None, feedback=feedback, is_child_algorithm=False)

	feedback.pushInfo(tr('Exporting land uses'))
	feedback.setProgress(80.0)

	# LANDUSE maps (time)
	# TODO: check if time is always necessary
	landuseMap = DBM.DBName + '|layername=idr_usemap'
	processing.run("idragratools:IdragraRasterizeTimeMap",
				   {'VECTOR_LAY': landuseMap, 'DATA_FLD': 'extid',
					'TIME_FLD': 'date', 'NAME_FORMAT': 'soiluse',
					'RASTER_EXT': extent,
					'CELL_DIM': cellSize, 'YEAR_LIST': ' '.join(yearList),'DEST_FOLDER': outPath},
								context=None, feedback=feedback, is_child_algorithm=False)

	# IRRIGATION MAP (time)
	feedback.pushInfo(tr('Exporting irrigation methods'))
	feedback.setProgress(90.0)
	irrMethodsMap = DBM.DBName + '|layername=idr_irrmap'
	processing.run("idragratools:IdragraRasterizeTimeMap",
				   {'VECTOR_LAY': irrMethodsMap, 'DATA_FLD': 'extid',
					'TIME_FLD': 'date', 'NAME_FORMAT': 'irr_meth',
					'RASTER_EXT': extent,
					'CELL_DIM': cellSize,  'YEAR_LIST': ' '.join(yearList), 'DEST_FOLDER': outPath},
								context=None, feedback=feedback, is_child_algorithm=False)

	# EXPORT IRRIGATION EFFICIENCY MAP (time)
	# join irrigation methods map with irrigation params
	irrMethodsPars = DBM.DBName + '|layername=idr_irrmet_types'
	algresult = processing.run("qgis:joinattributestable",
							   {'DISCARD_NONMATCHING': True,
								'FIELD': 'extid',
								'FIELDS_TO_COPY': ['irr_eff'],
								'FIELD_2': 'id',
								'INPUT': irrMethodsMap,
								'INPUT_2': irrMethodsPars,
								'METHOD': 1,
								'OUTPUT': 'TEMPORARY_OUTPUT',
								'PREFIX': ''},
							   context=None, feedback=feedback, is_child_algorithm=False)

	joinedLay = algresult['OUTPUT']

	# rasterize time maps of irrigation efficiency
	processing.run("idragratools:IdragraRasterizeTimeMap",
				   {'VECTOR_LAY': joinedLay, 'DATA_FLD': 'irr_eff',
					'TIME_FLD': 'date', 'NAME_FORMAT': 'irr_eff',
					'RASTER_EXT': extent,
					'CELL_DIM': cellSize,  'YEAR_LIST': ' '.join(yearList),'DEST_FOLDER': outPath},
				   context=None, feedback=feedback, is_child_algorithm=False)
	# SLOPE MAPS
	feedback.pushInfo(tr('Exporting slope maps'))
	feedback.setProgress(90.0)
	outputSlopeFile = os.path.join(outPath,'slope.asc')
	if dtm:
		algResults = processing.run("idragratools:IdragraMakeSlope",
					   {'DTM_LAY': dtm,
						'EXTENT': extent,
						'CELLSIZE': cellSize, 'OUTSLOPE_LAY': 'TEMPORARY_OUTPUT'},
						context=None, feedback=feedback, is_child_algorithm=False)

		processing.run("idragratools:IdragraSaveAscii",
					   {'INPUT':algResults['OUTSLOPE_LAY'], 'DIGITS': 6,
						'OUTPUT': outputSlopeFile},
					   context=None, feedback=feedback, is_child_algorithm=False)
	else:
		# make a zero raster
		feedback.reportError(tr('Slope will be set to zero for all the area'), False)
		aGrid = GisGrid(progress=feedback)
		aGrid.openASC(fileName)
		aGrid = aGrid *0.0
		aGrid.saveAsASC(outputSlopeFile, 6, True)

	# WATER TABLE DEPTHS
	nOfWTdepths = 0
	for var,waterTable in watertableDict.items():
		if nOfWTdepths==0:
			# make a general water table for the first year
			feedback.pushInfo(tr('A base waterdepth map was set for the simulation period'))
			wtdepthName = os.path.join(outPath, 'waterdepth.asc')  # remove month and day
			processing.run("idragratools:IdragraCalcWaterDepth", {'DTM': dtm,
																  'WATERTABLE': waterTable,
																  'EXTENT': extent,
																  'CELLSIZE': cellSize,
																  'OUTPUT': wtdepthName},
						   context=None, feedback=feedback, is_child_algorithm=False
						   )
		nOfWTdepths+=1
		wtdepthName = os.path.join(outPath,'waterdepth'+var[10:-4]+'.asc') # remove month and day
		processing.run("idragratools:IdragraCalcWaterDepth", {'DTM': dtm,
															  'WATERTABLE': waterTable,
															  'EXTENT': extent,
															  'CELLSIZE': cellSize,
															  'OUTPUT': wtdepthName},
					   context=None, feedback=feedback, is_child_algorithm=False
					   )

	if nOfWTdepths==0:
		feedback.reportError(tr('No water depths were processed'),False)

	# export rice params
	writeParsToTemplate(outfile=os.path.join(outPath, 'rice_soilparam.txt'),
						parsDict={},
						templateName='rice_soilparam.txt')

	# export domain map
	domainFile = os.path.join(outPath, 'domain.asc')
	# make a list of file *.asc in the output path
	fileList = glob.glob(os.path.join(outPath, '*.asc'))
	#feedback.pushInfo(tr('Map List: %s'%fileList))

	processing.run("idragratools:IdragraRasterizeDomain", {
		'INPUT_LIST': fileList,
		'RASTER_EXT': extent,
		'CELL_DIM': cellSize, 'DEST_FILE': domainFile},
					   context=None, feedback=feedback, is_child_algorithm=False)

	# export hydrological condition set to 1
	hydrcondFile = os.path.join(outPath, 'hydr_cond.asc')

	processing.run("idragratools:IdragraRasterizeDomain", {
		'INPUT_LIST': [domainFile],
		'RASTER_EXT': extent,
		'CELL_DIM': cellSize, 'DEST_FILE': hydrcondFile},
					   context=None, feedback=feedback, is_child_algorithm=False)

	# export cell area map
	cellareaFile = os.path.join(outPath, 'cellarea.asc')
	aGrid = GisGrid(progress= feedback)
	aGrid.openASC(domainFile)
	aGrid = aGrid*cellSize*cellSize
	aGrid.saveAsASC(cellareaFile,6,True)


	# weather weight maps, mandatory after the domain map!
	feedback.setText(tr('Export weight maps'))
	wsLaySource = DBM.DBName + '|layername=idr_weather_stations'
	processing.run("idragratools:IdragraExportWeights",
				   {'VECTOR_LAYER': wsLaySource,
					'ID_FLD':'id',
					'MAX_NUM': 5, 'RASTER_LAY': None,
					'EXTENT': extent,
					'CELLSIZE': cellSize, 'DEST_FOLDER': outPath},
				   context=None, feedback=feedback, is_child_algorithm=False
				   )

	# remove unused file xml
	fileList = glob.glob(os.path.join(outPath, '*.xml'))
	for f in fileList:
		os.remove(f)

	# rename file
	# TODO: to be removed
	replaceDict = {'theta_fc1': 'ThetaI_FC',
				   'theta_fc2': 'ThetaII_FC',
				   'theta_r1': 'ThetaI_r',
				   'theta_r2': 'ThetaII_r',
				   'theta_sat1': 'ThetaI_sat',
				   'theta_sat2': 'ThetaII_sat',
				   'theta_wp1': 'ThetaI_WP',
				   'theta_wp2': 'ThetaII_WP',
				   'ksat1': 'Ksat_I',
				   'ksat2': 'Ksat_II',
				   'n1': 'N_I',
				   'n2': 'N_II',
				   'rew1': 'REW_I',
				   'rew2': 'REW_II',
				   'landuse':'soiluse',
				   'irr_eff':'appl_eff'
				   }
	fileList = glob.glob(os.path.join(outPath, '*.asc'))
	for f in fileList:
		for k, v in replaceDict.items():
			newName = f.replace(k, v)
			if newName != f:
				break

		os.rename(f, newName)



	feedback.setPercentage(100.0)