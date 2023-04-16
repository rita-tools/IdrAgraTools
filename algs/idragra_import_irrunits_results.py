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

import qgis
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QCoreApplication, QVariant, QDate

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
					   NULL, QgsFeature, edit, QgsRaster, QgsProcessingUtils)
						

import numpy as np
import pandas as pd

from datetime import datetime,timedelta

import os

from tools.sqlite_driver import SQLiteDriver


class IdragraImportIrrUnitsResults(QgsProcessingAlgorithm):
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
	
	IDRAGRAFILE= 'IDRAGRA_FILE'
	AGGRVAR = 'AGGR_VAR'
	DB_FILENAME = 'DB_FILENAME'
	FEEDBACK = None

	def __init__(self):
		super().__init__()


	def tr(self, string):
		"""
		Returns a translatable string with the self.tr() function.
		"""
		return QCoreApplication.translate('Processing', string)

	def createInstance(self):
		return IdragraImportIrrUnitsResults()

	def name(self):
		"""
		Returns the algorithm name, used for identifying the algorithm. This
		string should be fixed for the algorithm, and must not be localised.
		The name should be unique within each provider. Names should contain
		lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraImportIrrUnitsResults'

	def displayName(self):
		"""
		Returns the translated algorithm name, which should be used for any
		user-visible display of the algorithm name.
		"""
		return self.tr('Irrigation units results')

	def group(self):
		"""
		Returns the name of the group this algorithm belongs to. This string
		should be localised.
		"""
		return self.tr('Import')

	def groupId(self):
		"""
		Returns the unique ID of the group this algorithm belongs to. This
		string should be fixed for the algorithm, and must not be localised.
		The group id should be unique within each provider. Group id should
		contain lowercase alphanumeric characters only and no spaces or other
		formatting characters.
		"""
		return 'IdragraImport'

	def shortHelpString(self):
		"""
		Returns a localised short helper string for the algorithm. This string
		should provide a basic description about what the algorithm does and the
		parameters and outputs associated with it..
		"""

		helpStr = """
						The algorithm import simulation results by the aggregation on the irrigation units. 
						<b>Parameters:</b>
						IdrAgra file: the parameters file used for the IdrAgra simulation (*.txt) [IDRAGRA_FILE]
						Aggregation raster map: the raster layer that define aggregation areas [AGGR_LAY]
						Aggregation variable: the variable to be aggregated [AGGR_VAR]
						Aggregation function: the function to use for aggregation [AGGR_FUN]
						Output table: the resultant table [OUTPUT_TABLE]
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
		self.STEPNAME = qgis.utils.plugins['IdragraTools'].STEPNAME
		self.GROUPBY =  qgis.utils.plugins['IdragraTools'].GROUPBYRASTER

		self.AGGRFUNCTIONS = qgis.utils.plugins['IdragraTools'].AGGRFUNCTIONS

		self.TIMESTEP = qgis.utils.plugins['IdragraTools'].TIMESTEP

		#### PARAMETERS ####

		self.addParameter(QgsProcessingParameterFile(self.IDRAGRAFILE, self.tr('IdrAgra file'),
													  QgsProcessingParameterFile.Behavior.File,'*.*','',False,
													  'IdrAgra pars file (*.txt);;All files (*.*)'))

		self.addParameter(QgsProcessingParameterEnum(self.AGGRVAR, self.tr('Aggregation variable'),
													 list(self.STEPNAME.values())))

		self.addParameter(QgsProcessingParameterFile(self.DB_FILENAME, self.tr('DB filename'),
													 QgsProcessingParameterFile.Behavior.File, '*.*', '', False,
													 self.tr('Geopackage (*.gpkg);;All files (*.*)')))

	def processAlgorithm(self, parameters, context, feedback):
		"""
		Here is where the processing itself takes place.
		"""
		self.FEEDBACK = feedback

		nodata = -9999
		# get params
		idragraFile = self.parameterAsFile(parameters, self.IDRAGRAFILE, context)

		varIdx = self.parameterAsEnum(parameters, self.AGGRVAR, context)
		varToUse = list(self.STEPNAME.keys())[varIdx]

		dbFilename = self.parameterAsFile(parameters, self.DB_FILENAME, context)
		self.DBM = SQLiteDriver(dbFilename, False, None, self.FEEDBACK, self.tr, QgsProject.instance())

		layToUse = 'irr_units'

		# TODO: explode over days in period


		# init table
		resTable = {
			'wsid' : [],
			'recval' :[],
			'count' : [],
			'timestamp': []
		}

		# loop in the idragra project file

		# ... get path to geodata folder InputPath
		# ... get path to results folder OutputPath
		# ... get output settings MonthlyFlag, StartDate, EndDate, DeltaDate
		monthlyFlag = True
		startDate = 1
		endDate = 366
		deltaDate = 366

		try:
			f = open(idragraFile,'r')
			for l in f:
				l = l.replace(' ','')
				l = l.rstrip('\n')  # remove return carriage
				l = l.split('=')
				if len(l)==2:
					parName = l[0].lower()
					#print(parName)
					if parName== 'inputpath':
						inputPath = l[1]
					elif parName== 'outputpath':
						outputPath = l[1]
					elif parName == 'monthlyflag':
						if l[1]=='F':
							monthlyFlag = False
					elif parName == 'startdate':
						startDate = int(l[1])
					elif parName == 'enddate':
						endDate = int(l[1])
					elif parName == 'deltadate':
						deltaDate = int(l[1])
					else:
						pass
		except Exception as e:
			self.FEEDBACK.reportError(self.tr('Cannot parse %s because %s') %
									  (idragraFile, str(e)),True)

		# TODO: get raster base map
		rootSimPath = os.path.dirname(idragraFile)

		baseFileName = os.path.join(rootSimPath,inputPath,layToUse+'.asc')
		# create a grid file
		baseData = np.loadtxt(baseFileName,dtype=np.int,skiprows=6)
		baseList = list(np.unique(baseData))
		if nodata in baseList: baseList.remove(nodata)

		# get the list of the output for the selected variable

		fileFilter = '*'+varToUse[4:]+'.asc'

		pathToImport = os.path.join(rootSimPath,outputPath)[:-1] # because ends with //
		#print('pathToImport',pathToImport)
		fileList = glob.glob(os.path.join(pathToImport, fileFilter))
		#print('fileList',fileList)
		nOfFiles = len(fileList)
		i = 0.
		yearList = []
		for f in fileList:
			# parse file name
			fname = os.path.basename(f)
			# extract date time
			parsedDate = None
			y = nodata
			if monthlyFlag:
				# 2000_month1_caprise
				try:
					y = int(fname[0:4])
					tokStart = fname.index('_month')+len('_month')
					tokEnd = fname.index('_', tokStart)
					s = int(fname[tokStart:tokEnd])
					parsedDate = self.monthToDate(year=y, month = s)
				except:
					pass
			else:
				# 2000_step1_caprise.asc
				if '_step' in fname:
					#self.FEEDBACK.pushInfo(self.tr('last file %s') % fname)
					y = int(fname[0:4])
					tokStart = fname.index('_step')+len('_step')
					tokEnd = fname.index('_',tokStart)
					s = int(fname[tokStart:tokEnd])
					# step to date
					parsedDate = self.stepToDate(year=y,step = s,periodStart =startDate, periodDelta = deltaDate)

			if y not in yearList: yearList.append(y)

			self.FEEDBACK.pushInfo(self.tr('Processing %s --> %s'%(f,parsedDate)))
			if parsedDate:
				varData = np.loadtxt(f, dtype=np.float, skiprows=6)

				for i in baseList:
					print('varData shape',np.shape(varData))
					#mask = np.where(np.logical_and(baseData[:,:] == i,varData[:,:] != nodata))
					mask = np.where(np.logical_and(baseData == i, varData != nodata))
					calcVal = (np.mean(varData[mask]))
					countVal = (np.count_nonzero(mask))
					# store data
					resTable['wsid'].append(i.item())
					resTable['recval'].append(calcVal.item())
					resTable['count'].append(countVal)
					resTable['timestamp'].append(parsedDate)

			i+=1.
			self.FEEDBACK.setProgress(100.0*i/nOfFiles)

		# make table ad pandas dataframe
		resTable = pd.DataFrame(resTable)

		if nodata in yearList: yearList.remove(nodata)
		yearList = sorted(yearList)

		daysArray = np.array([])
		valuesArray = np.array([])
		idArray = np.array([])

		if monthlyFlag: startDate = None

		# TODO: fix function
		for i in baseList:
			a, b = self.dayValueArray(resTable, i, yearList, startDate, 0.0)
			if len(daysArray) > 0:
				daysArray = np.concatenate((daysArray, a))
			else:
				daysArray = a

			if len(valuesArray) > 0:
				valuesArray = np.concatenate((valuesArray, b))
			else:
				valuesArray = b

			c = np.repeat(i, len(a))
			if len(idArray) > 0:
				idArray = np.concatenate((idArray, c))
			else:
				idArray = c

		# save values to database table

		concatValues = []
		for timestamp,sensorId,value in zip(daysArray,idArray,valuesArray):
			concatValues.append("('" + timestamp.strftime('%Y-%m-%d') + "', '" + str(sensorId) + "', '" + str(value) + "')")

		concatValues = ', '.join(concatValues)

		sql = 'DELETE FROM %s;' % varToUse
		sql += 'VACUUM;'
		sql += 'BEGIN; '
		sql += 'INSERT INTO %s (timestamp,wsid,recval) VALUES %s; ' % (varToUse,concatValues)
		sql += 'COMMIT;'

		msg = self.DBM.executeSQL(sql)
		if msg != '':
			self.FEEDBACK.pushInfo(self.tr('SQL error: %s' % msg))
			self.FEEDBACK.pushInfo(self.tr('at: %s' % sql))

		return {'OUTPUT_TABLE':None}

	def arrayOfDays(self,startDate, endDate):
		return np.arange(startDate, endDate+timedelta(days=1), timedelta(days=1)).astype(datetime)

	def dayValueArray(self,table,sensorId, yearList, startDay, nodata = -999):
		# create an empty time series
		firstDate = datetime(yearList[0],1,1)
		endDay = datetime(yearList[-1],12,31)
		datesArray = self.arrayOfDays(firstDate, endDay)
		valueArray = np.zeros(len(datesArray)) + nodata

		#print('date len:',len(datesArray))

		nOfYears = len(yearList)
		for c,y in enumerate(yearList):
			firstDayOfYear = datetime(y, 1, 1)-timedelta(days=1)
			if startDay:
				#firstDayOfYear += timedelta(days=(startDay - 1-1)) # -1 to consider the previous date and -1 because the first day of the year is 1
				firstDayOfYear += timedelta(days=(startDay - 1))  # -1 to consider the previous date
				print('startDay',startDay,'firstDayOfYear:', firstDayOfYear)
				# FIXED: IdrAgra gets exactly the DoY number and does not consider the date
				# so the 155 day is the Jun-13 in leap year and Jun-14 in the others
				# if ((not isLeap(y)) and (startDay >= 59)):
				# 	#print('not leap year',y)
				# 	firstDayOfYear -= timedelta(days=(1))

			dayList = [firstDayOfYear]
			valueList = [None]
			# dayList = []
			# valueList = []
			# select a subset
			# q = "wsid == %s and timestamp like \'%s%s\'" % (sensorId, y, '%')
			# selection = table.query(q)
			#print('table:',table)

			 #selection=table[table['wsid'] == sensorId & table['timestamp'].str().startswith("%s"%y)]
			selection = table[(table['wsid'] == sensorId) & (table['timestamp'].dt.year == y)]
			selection = selection.sort_values(by="timestamp")
			print('selection:', selection)

			dayList = selection['timestamp'].to_list()
			valueList = selection['recval'].to_list()

			i = 1
			while i < len(dayList):
				nOfDay = (dayList[i] - dayList[i - 1]).days
				#print(i,valueList[i],dayList[i - 1], dayList[i], nOfDay)
				# test = np.logical_and(datesArray >= dayList[i - 1], datesArray < dayList[i])
				test = np.logical_and(datesArray > dayList[i - 1], datesArray <= dayList[i])
				if valueList[i]: # if it is a valid number
					valueArray[test] = valueList[i] / nOfDay

				i += 1

			self.FEEDBACK.setProgress(100.0 * c / nOfYears)

		return datesArray,valueArray

	# TODO: step is calculate from the first day of the year or the irrigation period? --> from the outputs dates
	# TODO: check if it works correctly with leap year
	def stepToDate(self, year, step, periodStart, periodDelta):
		# calculate the day of the year for the selected period
		# added -2 to clear starting point
		# if ((not isLeap(year)) and (periodStart >= 59)):
		# 	#print('not leap year',y)
		#  	offset = -2 - 1
		# else:
		# 	offset = -1 - 1

		# offset = -2 - 1
		#if (isLeap(year)): offset = -1-1
		offset = -1 - 1 #FIXED: IdrAgra does not aware for leap year

		selDate = datetime(year, 1, 1)+timedelta(periodStart+step*periodDelta+offset)
		lastDate = datetime(year, 12, 31)
		#print('lastDate:',lastDate)
		if selDate>lastDate: selDate =lastDate #limit to selected period
		return selDate#.strftime('%Y-%m-%d')

	def monthToDate(self, year, month):
		if month == 12:
			month = 1
			year +=1
		else: month+=1

		selDate = datetime(year, month, 1)-timedelta(1)
		return selDate#.strftime('%Y-%m-%d')