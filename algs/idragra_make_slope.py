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

import math
from math import tan, radians

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication,QVariant
from processing.algs.gdal import GdalUtils
from qgis._analysis import QgsZonalStatistics, QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.core import (QgsProcessing,
					   QgsFeatureSink,
					   QgsProcessingException,
					   QgsProcessingAlgorithm,
					   QgsProcessingParameterFeatureSource,
					   QgsProcessingParameterFeatureSink,
					   QgsProcessingParameterMultipleLayers,
					   QgsProcessingParameterFileDestination,
					   QgsProcessingParameterEnum,
					   QgsProcessingParameterRasterLayer,
					   QgsProcessingParameterVectorLayer,
					   QgsProcessingParameterFile,
					   QgsProcessingParameterString,
					   QgsProcessingParameterNumber,
					   QgsProcessingParameterBoolean,
					   QgsProcessingParameterField,
					   QgsProcessingParameterExtent,
					   QgsProcessingParameterRasterDestination,
					   QgsExpression,
					   QgsFeatureRequest,
					   QgsCoordinateReferenceSystem,
					   QgsCoordinateTransform,
					   QgsProcessingParameterFolderDestination,
					   QgsWkbTypes,
					   QgsFields,
					   QgsField,
					   QgsVectorFileWriter,
					   QgsRasterFileWriter,
					   QgsVectorLayer,
					   QgsRasterLayer,
					   QgsProject,
					   NULL, QgsFeature, edit, QgsRaster, QgsRectangle)
						
import processing

from numpy import array

from datetime import datetime

import os


class IdragraMakeSlope(QgsProcessingAlgorithm):
	"""
	This is an example algorithm that takes a vector layer and
	creates a new identical one.

	It is meant to be used as an example of how to create your own
	algorithms and explain methods and variables used to do it. An
	algorithm like this will be available in all elements, and there
	is not need for additional work.

	All Processing algorithms should extend the QgsProcessingAlgorithm
	class.
	"""

	# Constants used to refer to parameters and outputs. They will be
	# used when calling the algorithm from another algorithm, or when
	# calling from the QGIS console.
	
	EXTENT = 'EXTENT'
	CELLSIZE = 'CELLSIZE'
	DTMLAY = 'DTM_LAY'
	OUTSLOPELAY = 'OUTSLOPE_LAY'

	FEEDBACK = None

	def tr(self, string):
		"""
		Returns a translatable string with the self.tr() function.
		"""
		return QCoreApplication.translate('Processing', string)

	def createInstance(self):
		return IdragraMakeSlope()

	def name(self):
		"""
		Returns the algorithm name, used for identifying the algorithm. This
		string should be fixed for the algorithm, and must not be localised.
		The name should be unique within each provider. Names should contain
		lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraMakeSlope'

	def displayName(self):
		"""
		Returns the translated algorithm name, which should be used for any
		user-visible display of the algorithm name.
		"""
		return self.tr('Slope map')

	def group(self):
		"""
		Returns the name of the group this algorithm belongs to. This string
		should be localised.
		"""
		return self.tr('Create')

	def groupId(self):
		"""
		Returns the unique ID of the group this algorithm belongs to. This
		string should be fixed for the algorithm, and must not be localised.
		The group id should be unique within each provider. Group id should
		contain lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraCreate'

	def shortHelpString(self):
		"""
		Returns a localised short helper string for the algorithm. This string
		should provide a basic description about what the algorithm does and the
		parameters and outputs associated with it..
		"""
		
		helpStr = """
						The algorithm clip elevation map and create slope. 
						<b>Parameters:</b>
						DTM raster map: the source of the altimetric information [DTM_LAY]
						Output Slope map: the slope map expressed as ratio (m/m) [OUTDTM_LAY]
						"""
		
		return self.tr(helpStr)

	def icon(self):
		self.alg_dir = os.path.dirname(__file__)
		icon = QIcon(os.path.join(self.alg_dir, 'idragra_tool.png'))
		return icon

	def initAlgorithm(self, config=None):
		"""
		Here we define the inputs and output of the algorithm, along
		with some other properties.
		"""
	
		self.addParameter(QgsProcessingParameterRasterLayer(self.DTMLAY, self.tr('DTM raster map')))

		self.addParameter(QgsProcessingParameterExtent(self.EXTENT, self.tr('Output extent')))

		self.addParameter(QgsProcessingParameterNumber(self.CELLSIZE, self.tr('Output cell size')))

		self.addParameter(QgsProcessingParameterRasterDestination(self.OUTSLOPELAY, self.tr('Output slope map')))

	def processAlgorithm(self, parameters, context, feedback):
		"""
		Here is where the processing itself takes place.
		"""
		self.FEEDBACK = feedback
		# get params
		dtmLayer = self.parameterAsRasterLayer(parameters,self.DTMLAY,context)
		outputExt = self.parameterAsExtent(parameters, self.EXTENT, context)
		outputCellSize = self.parameterAsDouble(parameters, self.CELLSIZE, context)
		outSlpMap = self.parameterAsFileOutput(parameters, self.OUTSLOPELAY, context)

		#source = QgsRasterLayer(dtmLayer, 'test', 'gdal')
		crs = dtmLayer.crs()

		sExtent = dtmLayer.extent()
		ulx = sExtent.xMinimum()
		uly = sExtent.yMaximum()
		lrx = sExtent.xMaximum()
		lry = sExtent.yMinimum()
		feedback.pushInfo(self.tr('Source extension: %s %s %s %s') % (ulx, uly, lrx, lry))

		print('selected extension', outputExt)
		ulx = outputExt.xMinimum()
		uly = outputExt.yMaximum()
		lrx = outputExt.xMaximum()
		lry = outputExt.yMinimum()
		feedback.pushInfo(self.tr('Selected extension: %s %s %s %s') % (ulx, uly, lrx, lry))

		extension = sExtent.intersect(outputExt)
		ulx = extension.xMinimum()
		uly = extension.yMaximum()
		lrx = extension.xMaximum()
		lry = extension.yMinimum()
		feedback.pushInfo(self.tr('intersected extension: %s %s %s %s') % (ulx, uly, lrx, lry))

		if extension.area() == 0:
			feedback.reportError(self.tr('Error: selected extension not intersects layer extension'), False)
			extension = sExtent

		ulx = extension.xMinimum()
		uly = extension.yMaximum()
		lrx = extension.xMaximum()
		lry = extension.yMinimum()

		extraString = '-projwin %s %s %s %s -tr %s %s' % (ulx, uly, lrx, lry,outputCellSize,outputCellSize)
		feedback.pushInfo(self.tr('Final extension: %s %s %s %s') % (ulx, uly, lrx, lry))
		# clip/resample raster
		algresult = processing.run("gdal:translate",
								   {'INPUT': dtmLayer, 'TARGET_CRS': crs, 'NODATA': None,
									'COPY_SUBDATASETS': False, 'OPTIONS': '', 'EXTRA': extraString, 'DATA_TYPE': 6,
									'OUTPUT': 'TEMPORARY_OUTPUT'},
								   context=None,
								   feedback=feedback,
								   is_child_algorithm=True)

		# create slope
		algresult = processing.run("native:slope",
									{'INPUT': algresult['OUTPUT'],
									'Z_FACTOR': 1,
									'OUTPUT': 'TEMPORARY_OUTPUT'},
									context=context,
									feedback=feedback,
									is_child_algorithm=True)

		slopeLay = QgsRasterLayer(algresult['OUTPUT'],'slope')

		# fit extension
		xllcorner = outputExt.xMinimum()
		# yllcorner = extension.yMinimum()
		yurcorner = outputExt.yMaximum()
		h = outputExt.height()
		w = outputExt.width()

		nrows = round(h / outputCellSize)
		ncols = round(w / outputCellSize)

		xurcorner = xllcorner + ncols * outputCellSize
		# yurcorner = yllcorner+nrows*outputCellSize
		yllcorner = yurcorner - nrows * outputCellSize

		newExt = QgsRectangle(xllcorner, yllcorner, xurcorner, yurcorner)
		# make slope as ratio

		entries = []
		# Define band1
		raster1 = QgsRasterCalculatorEntry()
		raster1.ref = 'slope@1'
		raster1.raster = slopeLay
		raster1.bandNumber = 1
		entries.append(raster1)

		driverName = GdalUtils.GdalUtils.getFormatShortNameFromFilename(outSlpMap)
		# Process calculation with input extent and resolution
		calc = QgsRasterCalculator('tan("slope@1"*%s/180)'%math.pi, outSlpMap, driverName,
								   newExt, ncols, nrows, entries)
		calc.processCalculation(self.FEEDBACK)

		return {'OUTSLOPE_LAY': outSlpMap}
