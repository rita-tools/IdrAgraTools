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

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication,QVariant
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
						NULL)
						
import processing

import numpy as np

from datetime import datetime

import os

from ..tools.gis_grid import GisGrid
from ..tools.compact_dataset import getRasterInfos


class IdragraSaveAscii(QgsProcessingAlgorithm):
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
	
	INPUT= 'INPUT'
	DIGITS = 'DIGITS'
	OUTPUT = 'OUTPUT'

	FEEDBACK = None
	

	def tr(self, string):
		"""
		Returns a translatable string with the self.tr() function.
		"""
		return QCoreApplication.translate('Processing', string)

	def createInstance(self):
		return IdragraSaveAscii()

	def name(self):
		"""
		Returns the algorithm name, used for identifying the algorithm. This
		string should be fixed for the algorithm, and must not be localised.
		The name should be unique within each provider. Names should contain
		lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraSaveAscii'

	def displayName(self):
		"""
		Returns the translated algorithm name, which should be used for any
		user-visible display of the algorithm name.
		"""
		return self.tr('Save raster as ascii')

	def group(self):
		"""
		Returns the name of the group this algorithm belongs to. This string
		should be localised.
		"""
		return self.tr('Utility')

	def groupId(self):
		"""
		Returns the unique ID of the group this algorithm belongs to. This
		string should be fixed for the algorithm, and must not be localised.
		The group id should be unique within each provider. Group id should
		contain lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraUtility'

	def shortHelpString(self):
		"""
		Returns a localised short helper string for the algorithm. This string
		should provide a basic description about what the algorithm does and the
		parameters and outputs associated with it..
		"""
		
		helpStr = """
						The algorithm transform a raster file in ascii format (i.e. useful for Idragra model). 
						<b>Parameters:</b>
						Input raster: the raster layer to be transformed [INPUT]
						Digit: number of digit to maintain [DIGIT]
						Output raster: the name of the output raster [OUTPUT]
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
	
		self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, self.tr('Input raster')))
				
		self.addParameter(QgsProcessingParameterNumber(self.DIGITS, self.tr('Digit')))
		
		self.addParameter(QgsProcessingParameterFileDestination(self.OUTPUT, self.tr('Output raster'), self.tr('ASCII (*.asc)')))
		
		
	def processAlgorithm(self, parameters, context, feedback):
		"""
		Here is where the processing itself takes place.
		"""
		self.FEEDBACK = feedback
		# get params

		inputLay = self.parameterAsRasterLayer(parameters, self.INPUT, context)
		digits = self.parameterAsInt(parameters, self.DIGITS, context)
		outputFile = self.parameterAsFileOutput(parameters,	self.OUTPUT, context)

		# get array
		inputArray = self.convertRasterToNumpyArray(inputLay.source())

		feedback.pushInfo(self.tr('Saving output ...'))
		feedback.setProgress(90)
		geoDict = getRasterInfos(inputLay.source())
		# feedback.pushInfo(self.tr('Georeference parameters: %s') % str(geoDict))
		dx = geoDict['dx']
		dy = geoDict['dy']
		ncols = geoDict['ncols']
		nrows = geoDict['nrows']
		xllcorner = geoDict['xllcorner']
		yllcorner = geoDict['yllcorner']
		xurcorner = geoDict['xllcorner'] + ncols * geoDict['dx']
		yurcorner = geoDict['yllcorner'] - nrows * geoDict['dy']

		self.aGrid = GisGrid(ncols=ncols, nrows=nrows, xcell=xllcorner, ycell=yllcorner, dx=dx, dy=-dy, nodata=-9,
						EPSGid=inputLay.crs().postgisSrid(), progress=self.FEEDBACK,parent = self.FEEDBACK)
		self.aGrid.data = inputArray  # maxDepthArray#

		# save to file
		self.aGrid.saveAsASC(filename = outputFile, d=digits, useCellSize=True)
		feedback.pushInfo(self.tr('... to %s')%outputFile)

		self.aGrid = None

		outRaster = QgsRasterLayer(outputFile,self.tr('As ascii'))

		return {'OUTPUT':outRaster}

	def convertRasterToNumpyArray(self,lyrFile):  # Input: QgsRasterLayer
		lyr = QgsRasterLayer(lyrFile, 'temp')
		values = []
		provider = lyr.dataProvider()
		nodata = provider.sourceNoDataValue (1)
		block = provider.block(1, lyr.extent(), lyr.width(), lyr.height())

		for i in range(lyr.height()):
			for j in range(lyr.width()):
				values.append(block.value(i, j))

		a = np.array(values)
		#print('shape of %s: %s, %s'%(lyrFile,lyr.height(),lyr.width()))
		a = np.reshape(a,(lyr.height(),lyr.width()))
		a[a==nodata]= np.nan
		return a