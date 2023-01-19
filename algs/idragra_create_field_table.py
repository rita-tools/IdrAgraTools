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
from qgis._core import QgsProcessingParameterRasterDestination
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
					   NULL, QgsFeature, QgsProcessingOutputRasterLayer)

import numpy as np

from datetime import datetime

import os

from ..tools.make_weight_matrix import makeWeightMatrix_WW
from ..tools.import_from_csv import *
from ..tools.compact_dataset import getRasterInfos


class IdragraCreateFieldTable(QgsProcessingAlgorithm):
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

	FIELD_LAY = 'FIELD_LAY'
	FIELD_COL = 'FIELD_COL'
	LU_COL = 'LU_COL'

	SOIL_LAY = 'SOIL_LAY'
	SOIL_COL = 'SOIL_COL'

	IRRMETH_LAY = 'IRRMETH_LAY'
	IRRMETH_COL = 'IRRMETH_COL'

	IRRUNIT_LAY = 'IRRUNIT_LAY'
	IRRUNIT_COL = 'IRRUNIT_COL'

	WSTAT_LAY = 'WSTAT_LAY'
	WSTAT_COL = 'WSTAT_COL'
	WSTAT_NUM = 'WSTAT_NUM'

	DTM_LAY = 'DTM_LAY'
	WT_ELEV = 'WT_ELEV'

	LOWER_LIM = 'LOWER_LIM'
	UPPER_LIM = 'UPPER_LIM'

	OUT_LAY = 'OUT_LAY'

	FEEDBACK = None
	

	def tr(self, string):
		"""
		Returns a translatable string with the self.tr() function.
		"""
		return QCoreApplication.translate('Processing', string)

	def createInstance(self):
		return IdragraCreateFieldTable()

	def name(self):
		"""
		Returns the algorithm name, used for identifying the algorithm. This
		string should be fixed for the algorithm, and must not be localised.
		The name should be unique within each provider. Names should contain
		lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraCreateFieldTable'

	def displayName(self):
		"""
		Returns the translated algorithm name, which should be used for any
		user-visible display of the algorithm name.
		"""
		return self.tr('Pre field table')

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
						The algorithm create a new table with data referred to each field.
						<b>Parameters:</b>
						Fields: the field map [FIELD_LAY]
						Field id: the column with the id of the field [FIELD_COL]
						Land use id: the column with the id of the landuse [LU_COL]
						Soils: the soil map [SOIL_LAY]
						Soil id: the column with the id of the soil [SOIL_COL]
						Irrigation methods: the irrigation methods map [IRRMETH_LAY]
						Irr. method id: the column with the id of the irrigation method [IRRMETH_COL]
						Irrigation units: the irrigation unit map [IRRUNIT_LAY]
						Irr. unit id: the column of irrigation unit id [IRRUNIT_COL]
						Weather stations: the map of weather stations as point layer [WSTAT_LAY]
						W. station id: the field with weather station ids [WSTAT_COL]
						Output table: the file path to the output table [OUT_LAY]
						
						<b>Notes</b>
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

		self.addParameter(QgsProcessingParameterFeatureSource(self.FIELD_LAY, self.tr('Fields'),
															  [QgsProcessing.TypeVectorPolygon], None, False))
		self.addParameter(QgsProcessingParameterField(self.FIELD_COL, self.tr('Field id'), 'id', self.FIELD_LAY,
													  QgsProcessingParameterField.Numeric))
		self.addParameter(QgsProcessingParameterField(self.LU_COL, self.tr('Land use id'), 'extid', self.FIELD_LAY,
													  QgsProcessingParameterField.Numeric))

		self.addParameter(QgsProcessingParameterFeatureSource(self.SOIL_LAY, self.tr('Soils'),
															  [QgsProcessing.TypeVectorPolygon], None, False))
		self.addParameter(QgsProcessingParameterField(self.SOIL_COL, self.tr('Soil id'), 'extid', self.SOIL_LAY,
													  QgsProcessingParameterField.Numeric))

		self.addParameter(QgsProcessingParameterFeatureSource(self.IRRMETH_LAY, self.tr('Irrigation methods'),
															  [QgsProcessing.TypeVectorPolygon], None, False))
		self.addParameter(QgsProcessingParameterField(self.IRRMETH_COL, self.tr('Irr. method id'), 'extid', self.IRRMETH_LAY,
													  QgsProcessingParameterField.Numeric))

		self.addParameter(QgsProcessingParameterFeatureSource(self.IRRUNIT_LAY, self.tr('Irrigation units'),
															  [QgsProcessing.TypeVectorPolygon], None, False))
		self.addParameter(QgsProcessingParameterField(self.IRRUNIT_COL, self.tr('Irr. unit id'), 'extid', self.IRRUNIT_LAY,
													  QgsProcessingParameterField.Numeric))


		self.addParameter(QgsProcessingParameterFeatureSource(self.WSTAT_LAY, self.tr('Weather stations layer'),
															  [QgsProcessing.TypeVectorPoint], None, False))
		self.addParameter(QgsProcessingParameterField(self.WSTAT_COL, self.tr('W. station id'), 'id', self.WSTAT_LAY,
													  QgsProcessingParameterField.Numeric))
		self.addParameter(QgsProcessingParameterNumber(self.WSTAT_NUM, self.tr('Number of station to use'),
													   QgsProcessingParameterNumber.Integer, 5))

		self.addParameter(
			QgsProcessingParameterFeatureSink(self.OUT_LAY, self.tr('Output layer'), QgsProcessing.TypeVectorPolygon))

	def processAlgorithm(self, parameters, context, feedback):
		"""
		Here is where the processing itself takes place.
		"""
		self.FEEDBACK = feedback
		# get params
		field_lay = self.parameterAsVectorLayer(parameters, self.FIELD_LAY, context)
		field_col = self.parameterAsFields(parameters, self.FIELD_COL, context)[0]
		lu_col = self.parameterAsFields(parameters, self.LU_COL, context)[0]

		soil_lay = self.parameterAsVectorLayer(parameters, self.SOIL_LAY, context)
		soil_col = self.parameterAsFields(parameters, self.SOIL_COL, context)[0]

		irrmeth_lay = self.parameterAsVectorLayer(parameters, self.IRRMETH_LAY, context)
		irrmeth_col = self.parameterAsFields(parameters, self.IRRMETH_COL, context)[0]

		irrunit_lay = self.parameterAsVectorLayer(parameters, self.IRRUNIT_LAY, context)
		irrunit_col = self.parameterAsFields(parameters, self.IRRUNIT_COL, context)[0]

		wstat_lay = self.parameterAsVectorLayer(parameters, self.WSTAT_LAY, context)
		wstat_col = self.parameterAsFields(parameters, self.WSTAT_COL, context)[0]
		wstat_num = self.parameterAsInt(parameters, self.WSTAT_NUM, context)

		wt_lay_list = self.parameterAsLayerList(parameters, self.WT_ELEV, context)

		# TODO: needs optimization
		# get the list of weather stations
		ws_xs = []
		ws_ys = []
		ws_ids = []
		for feat_ws in wstat_lay.getFeatures():
			pt = feat_ws.geometry().asMultiPoint()[0]
			ws_xs.append(pt.x())
			ws_ys.append(pt.y())
			ws_ids.append(feat_ws[wstat_col])

		#wstat_num = min(len(ws_ids), wstat_num)

		# prepare the destination field
		fldList = field_lay.fields()

		fldList.append(QgsField('x_c', QVariant.Double))
		fldList.append(QgsField('y_c', QVariant.Double))
		fldList.append(QgsField('shape_area', QVariant.Double))

		fldList.append(QgsField('land_use', QVariant.Int))

		fldList.append(QgsField('soil_id', QVariant.Int))
		fldList.append(QgsField('soil_gidx', QVariant.Double))

		fldList.append(QgsField('irrmeth_id', QVariant.Int))
		fldList.append(QgsField('irrmeth_gidx', QVariant.Double))

		fldList.append(QgsField('irrunit_id', QVariant.Int))
		fldList.append(QgsField('irrunit_gidx', QVariant.Double))

		# add meteo fields
		for n in range(wstat_num):
			fldList.append(QgsField('meteo_%s'%(n+1), QVariant.Double))

		(sink, dest_id) = self.parameterAsSink(
			parameters,
			self.OUT_LAY,
			context,
			fldList,
			field_lay.wkbType(),
			field_lay.sourceCrs()
		)

		# get value from source table
		c = 0
		nFeat = field_lay.featureCount()
		for feat in field_lay.getFeatures():
			c+=1
			self.FEEDBACK.setProgress(100.0 * c / nFeat)

			# get geometry and geometry data
			id = feat['id']
			geom = feat.geometry()
			shape_area = float(geom.area())
			x_c = geom.centroid().asPoint().x()
			y_c = geom.centroid().asPoint().y()

			# get landuse id
			lu_id = feat[lu_col]

			# get id from other maps (maximum covered area)
			soil_id, soil_gidx = self.selectByLocation(inputLayer=soil_lay, refGeom=geom, inputFld=soil_col)
			irrmeth_id, irrmeth_gidx = self.selectByLocation(inputLayer=irrmeth_lay, refGeom=geom, inputFld=irrmeth_col)
			irrunit_id, irrunit_gidx = self.selectByLocation(inputLayer=irrunit_lay, refGeom=geom, inputFld=irrunit_col)

			# calculate weather weights matrix
			ws_ww = makeWeightMatrix_WW(xmin=None, xmax=None, ymin=None, ymax=None, cellsize=None,
								xList =ws_xs, yList=ws_ys, idList=ws_ids, nMax=wstat_num,
								xc_list=[x_c], yc_list=[y_c],
								feedback=self.FEEDBACK, tr=None)

			attr_list =feat.attributes()+[x_c,y_c,shape_area,lu_id,soil_id,soil_gidx,irrmeth_id,irrmeth_gidx,irrunit_id,irrunit_gidx]
			for x in ws_ww:
				if np.isnan(x[0]): x_val = -9.0
				else: x_val = float(x[0])

				attr_list.append(x_val)

			#print('attr_list',attr_list)

			new_feat = QgsFeature(fldList)
			new_feat.setGeometry(geom)
			new_feat.setAttributes(attr_list)

			sink.addFeature(new_feat, QgsFeatureSink.FastInsert)



		return {self.OUT_LAY: dest_id}

	def calcGeomIndex(self, aGeom, refGeom, refArea, refLen):
		xGeom = refGeom.intersection(aGeom)
		geomIndex = 0.0
		try:
			xArea = xGeom.area()
			xLen = xGeom.length()
			if refArea > 0:
				geomIndex = round(100 * xArea / refArea, 2)  # it's a polygon
			elif refLen > 0:
				geomIndex = round(100 * xLen / refLen, 2)  # it's a line
			else:
				geomIndex = 100.0  # it's a point
		except Exception as e:
			print('Error in calcGeomIndex, %s' % str(e))

		return geomIndex


	def selectByLocation(self, inputLayer, refGeom, inputFld):
		# set a filter
		refArea = refGeom.area()
		refLen = 0  # unused
		max_gidx = 0
		target_id = None
		for feature in inputLayer.getFeatures(QgsFeatureRequest().setFilterRect(refGeom.boundingBox())):
			aGeom = feature.geometry()
			geomIndex = self.calcGeomIndex(aGeom, refGeom, refArea, refLen)
			if geomIndex > max_gidx:
				max_gidx = geomIndex
				#print('inputFld', inputFld)
				target_id = feature[inputFld]

		return target_id, max_gidx
