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


from PyQt5.QtCore import *
from PyQt5.QtGui import *

from PyQt5 import uic

from PyQt5.QtWidgets import QDialog, QToolBox, QWidget, QVBoxLayout, QFileDialog, QListWidgetItem, QSpinBox, \
	QCalendarWidget, QToolButton, QLabel, QCheckBox, QMainWindow

import os

from qgis._core import QgsCoordinateReferenceSystem, QgsRectangle, QgsProject, QgsPoint, QgsGeometry, QgsPointXY
from qgis._gui import QgsDateTimeEdit, QgsRubberBand, QgsVertexMarker

from ..tools.utils import returnExtent

class NoYearCalendar(QCalendarWidget):
	def __init__(self,parent):
		QCalendarWidget.__init__(self,parent)
		self.findChild(QToolButton,'qt_calendar_yearbutton').setHidden(True)

class NoYearDate(QgsDateTimeEdit):
	def __init__(self,parent):
		QgsDateTimeEdit.__init__(self,parent)
		newCal = NoYearCalendar(self)
		self.setCalendarWidget(newCal)
		self.setMinimumDate(QDate(2000, 1, 1))
		self.setMaximumDate(QDate(2000,12,31))
		self.setDisplayFormat('MMMM, dd')

	def value(self):
		# get date
		aTime = self.date()
		# transform to dayOfYear
		return aTime.dayOfYear()

	def setValue(self,dayOfYear):
		selDate = QDate(2000, 1, 1).addDays(dayOfYear-1)
		self.setDate(selDate)


class SetSimulationDialog(QMainWindow):
	closed = pyqtSignal()
	accepted = pyqtSignal()
	
	FILELIST = {}
	VARLIST = {}
	FUNLIST = {}
	
	def __init__(self, parent=None, yearList=[],modeList = [], simSettings = {}):
		QMainWindow.__init__(self, parent.mainWindow())
		# Set up the user interface from Designer.
		uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'set_simulation_dialog.ui'))
		uic.loadUi(uiFilePath, self)

		# init overall list
		self.rbList = []
		self.canvas = parent.mapCanvas()
		#self.allCaseYearList = allCaseYearList
		#self.consumeYearList = consumeYearList
		self.yearList = yearList

		# init irrigation page
		self.IRRSTART_LB = QLabel(self.tr('Irrigation season starts at'), self)
		self.IRREND_LB = QLabel(self.tr('Irrigation season ends at'), self)
		self.IRRSTART_TE = NoYearDate(self)
		self.IRREND_TE = NoYearDate(self)
		layout = self.IRRIGATION_PG.layout()
		layout.addRow(self.IRRSTART_LB, self.IRRSTART_TE)
		layout.addRow(self.IRREND_LB, self.IRREND_TE)

		# init output page
		self.USEMONTHS_CB = QCheckBox(self.tr('Output each month'),self)
		self.STARTDATE_LB = QLabel(self.tr('From day'),self)
		self.ENDDATE_LB = QLabel(self.tr('To day'),self)
		self.STEPDATE_LB = QLabel(self.tr('Time step (number of day)'),self)
		self.STARTDATE_TE = NoYearDate(self)
		self.ENDDATE_TE = NoYearDate(self)
		self.STEPDATE_SB = QSpinBox()
		self.STEPDATE_SB.setMinimum(1)
		self.STEPDATE_SB.setMaximum(366)
		self.STEPDATE_SB.setValue(10)
		layout = self.OUTPUT_PG.layout()
		layout.addRow(self.USEMONTHS_CB)
		layout.addRow(self.STARTDATE_LB,self.STARTDATE_TE)
		layout.addRow(self.ENDDATE_LB, self.ENDDATE_TE)
		layout.addRow(self.STEPDATE_LB, self.STEPDATE_SB)

		self.setWindowTitle('Idragra Tools')

		# simulation mode
		self.MODE_CB.addItems(modeList)  # populate list of simulation mode
		self.MODE_CB.currentIndexChanged.connect(self.enableIrrPeriod)
		if simSettings['MODE'] in range(0, len(modeList)):
			self.MODE_CB.setCurrentText(modeList[simSettings['MODE']])
			self.MODE_CB.currentIndexChanged.emit(simSettings['MODE'])

		# yearly maps
		if simSettings['SOILUSEVARFLAG'] == 'T':
			self.SOILUSEVARFLAG_CB.setChecked(True)
		else:
			self.SOILUSEVARFLAG_CB.setChecked(False)

		### set output path
		self.OUTFOLDER_FW.setFilePath(simSettings['OUTPUTPATH'])

		### set simulation period
		#yearList = self.allCaseYearList
		#if simSettings['MODE']==1: yearList=self.consumeYearList

		# self.PERIOD_CB.addItems(yearList)
		# if str(simSettings['PERIOD']) in yearList:
		# 	self.FROM_CB.setCurrentText(str(simSettings['PERIOD']))

		self.FROM_CB.addItems(yearList)
		if str(simSettings['STARTYEAR']) in yearList:
			self.FROM_CB.setCurrentText(str(simSettings['STARTYEAR']))

		self.TO_CB.addItems(yearList)
		if str(simSettings['ENDYEAR']) in yearList:
			self.TO_CB.setCurrentText(str(simSettings['ENDYEAR']))

		# update based on selection
		self.updateLastYear()

		### set spatial resolution
		self.DOMAINEXT.setMapCanvas(self.canvas)
		try:
			crsCode = float(simSettings['CRS'])
		except:
			print('CRS', simSettings['CRS'])
			crsCode = 32632

		crs = QgsCoordinateReferenceSystem()
		crs.createFromSrsId(crsCode)

		# xmin,ymin : xmax,ymax
		extStr = simSettings['EXTENT']
		ext = returnExtent(extStr)
		if ext is None:
			ext = self.canvas.extent()

		self.DOMAINEXT.setOriginalExtent(ext, crs)
		self.DOMAINEXT.setCurrentExtent(ext, crs)
		self.DOMAINEXT.setOutputCrs(crs)

		self.DOMAINEXT.setOutputExtentFromUser(ext, crs)
		self.CELLSIZE_SB.setValue(simSettings['CELLSIZE'])

		### set hydrological model
		self.EVALAY_SB.setValue(simSettings['ZEVALAY'])
		self.TRANSLAY_SB.setValue(simSettings['ZTRANSLAY'])
		# capillary rise
		if simSettings['CAPILLARYFLAG']=='T':
			self.CAPRISE_CB.setChecked(True)
		else:
			self.CAPRISE_CB.setChecked(False)

		# slope limits
		self.MINSLOPE_SB.setValue(simSettings['MINSLOPE'])
		self.MAXSLOPE_SB.setValue(simSettings['MAXSLOPE'])

		### set irrigation variable
		self.IRRSTART_TE.setValue(simSettings['STARTIRRSEASON'])
		self.IRREND_TE.setValue(simSettings['ENDIRRSEASON'])

		if simSettings['MODE']==0:
		 	self.IRRSTART_TE.setEnabled(False)
		 	self.IRREND_TE.setEnabled(False)

		### set output settings
		self.USEMONTHS_CB.stateChanged.connect(self.enableOutTime)
		if simSettings['MONTHOUTPUT']=='T':
			self.USEMONTHS_CB.setChecked(True)
			self.USEMONTHS_CB.stateChanged.emit(2)
		else:
			self.USEMONTHS_CB.setChecked(False)
			self.USEMONTHS_CB.stateChanged.emit(0)

		self.STARTDATE_TE.setValue(simSettings['STARTOUTPUT'])
		self.ENDDATE_TE.setValue(simSettings['ENDOUTPUT'])
		self.STEPDATE_SB.setValue(simSettings['STEPOUTPUT'])

		self.FROM_CB.currentTextChanged.connect(self.updateLastYear)

		self.DRAW_GRID_BT.clicked.connect(self.drawGrid)

		self.buttonBox.accepted.connect(self.accept)
		self.buttonBox.rejected.connect(self.reject)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.accept)
		#QObject.connect(self.buttonBox, SIGNAL("rejected()"), self.reject)
		QMetaObject.connectSlotsByName(self)

	def accept(self):
		self.close()
		self.accepted.emit()
		return 1

	def reject(self):
		self.close()
		return 0

	def updateLastYear(self):
		fromYear = int(self.FROM_CB.currentText())
		selYear = int(self.TO_CB.currentText())

		self.updateYearList(self.TO_CB, self.yearList, fromYear, selYear)

	def updateYearList(self,yearCB,yearList,minYear,selYear):
		minYearIdx = yearList.index(str(minYear))
		yearList=yearList[minYearIdx:]
		yearCB.clear()
		yearCB.addItems(yearList)
		if str(selYear) in yearList:
			yearCB.setCurrentText(str(selYear))

	def enableIrrPeriod(self,index):
		flag = True
		if index == 0:
			flag = False

		self.IRRSTART_TE.setEnabled(flag)
		self.IRREND_TE.setEnabled(flag)

	def enableOutTime(self,state):
		flag = True
		if state == 2:
			flag = False

		self.STARTDATE_TE.setEnabled(flag)
		self.ENDDATE_TE.setEnabled(flag)
		self.STEPDATE_SB.setEnabled(flag)

	def closeEvent(self, event):
		self.deleteGrid()
		self.closed.emit()

	def drawGrid(self):
		self.deleteGrid()

		col = QColor(153,153,153) # gray color

		rasterExt = self.DOMAINEXT.outputExtent()
		cellDim = self.CELLSIZE_SB.value()

		xllcorner = rasterExt.xMinimum()
		# yllcorner = extension.yMinimum()
		yurcorner = rasterExt.yMaximum()
		h = rasterExt.height()
		w = rasterExt.width()

		nrows = round(h / cellDim)
		ncols = round(w / cellDim)

		xurcorner = xllcorner + ncols * cellDim
		# yurcorner = yllcorner+nrows*outputCellSize
		yllcorner = yurcorner - nrows * cellDim

		cellsize = self.CELLSIZE_SB.value()

		xList = [xllcorner+i*cellDim for i in range(0,ncols+1)]
		yList = [yllcorner+i*cellDim for i in range(0,nrows+1)]
		# draw vertical lines
		for x in xList:
			r = QgsRubberBand(self.canvas, False)  # False = not a polygon
			r.setColor(col)
			r.setWidth(3)
			points = [QgsPoint(x, yllcorner), QgsPoint(x, yurcorner), QgsPoint(x, yllcorner)]
			r.setToGeometry(QgsGeometry.fromPolyline(points), None)
			self.rbList.append(r)
		# draw horizontal lines
		for y in yList:
			r = QgsRubberBand(self.canvas, False)  # False = not a polygon
			r.setColor(col)
			r.setWidth(3)
			points = [QgsPoint(xllcorner, y), QgsPoint(xurcorner, y), QgsPoint(xllcorner, y)]
			r.setToGeometry(QgsGeometry.fromPolyline(points), None)
			self.rbList.append(r)

		for x in xList[:-1]:
			for y in yList[:-1]:
				m = QgsVertexMarker(self.canvas)
				m.setCenter(QgsPointXY(x+0.5*cellsize, y+0.5*cellsize))
				m.setColor(col)
				m.setIconSize(5)
				m.setIconType(QgsVertexMarker.ICON_CROSS)  # or ICON_CROSS, ICON_X, ICON_BOX
				m.setPenWidth(3)
				self.rbList.append(m)

	def deleteGrid(self):
		#print('deleteGrid')
		for r in self.rbList:
			self.canvas.scene().removeItem(r)

	
	def getData(self):
		### get output path
		outfolder = self.OUTFOLDER_FW.filePath()
		useYearlyMaps = ['F', 'T'][int(self.SOILUSEVARFLAG_CB.isChecked())]
		### get simulation period
		fromYear = int(self.FROM_CB.currentText())
		toYear = int(self.TO_CB.currentText())
		### get spatial resolution
		dtmExtent = self.DOMAINEXT.outputExtent()
		crs = self.DOMAINEXT.outputCrs()
		cellsize = self.CELLSIZE_SB.value()
		### get hydrological model
		zevalay = self.EVALAY_SB.value()
		ztranslay = self.TRANSLAY_SB.value()
		capRise = ['F','T'][int(self.CAPRISE_CB.isChecked())]
		minSlope = self.MINSLOPE_SB.value()
		maxSlope = self.MAXSLOPE_SB.value()
		### get irrigation variable
		simMode = self.MODE_CB.currentIndex()
		irrStart = self.IRRSTART_TE.value()
		irrEnd = self.IRREND_TE.value()
		### get output settings
		outMonth = ['F', 'T'][int(self.USEMONTHS_CB.isChecked())]
		outStartDate = self.STARTDATE_TE.value()
		outEndDate = self.ENDDATE_TE.value()
		outStep = self.STEPDATE_SB.value()

		return {'outfolder':outfolder,'simMode':simMode,'useyearlymaps':useYearlyMaps, 'from':fromYear, 'to':toYear,
				'extent':dtmExtent, 'crs':crs, 'cellsize':cellsize,
				'zevalay':zevalay,'ztranslay':ztranslay,'capRise':capRise,'minSlope':minSlope, 'maxSlope':maxSlope,
				'irrStart':irrStart, 'irrEnd':irrEnd,
				'outMonth':outMonth, 'outStartDate': outStartDate, 'outEndDate': outEndDate, 'outStep': outStep
				}
