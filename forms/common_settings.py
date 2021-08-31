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

from PyQt5.QtWidgets import QDialog,QToolBox,QWidget,QVBoxLayout,QFileDialog,QListWidgetItem
	
#qgis import
from qgis.core import *
from qgis.gui import *
#other
import os
import sys
import glob

from .custom_input import *

#~ uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'project_dialog.ui'))
#~ print('uiFilePath: %s'%uiFilePath)
#~ FormClass = uic.loadUiType(uiFilePath)[0]

class CommonSettings(QDialog):
	closed = pyqtSignal()
	
	FILELIST = {}
	VARLIST = {}
	FUNLIST = {}
	
	def __init__(self, parent=None, varIds = [],varNames=[]):
		QDialog.__init__(self, parent)
		# Set up the user interface from Designer.
		uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'common_settings.ui'))
		uic.loadUi(uiFilePath, self)
		self.setWindowTitle('mobidiQ')
		
		self.VARIDS = varIds
		self.VARNAMES = varNames
		
		# set data:
		s = QSettings('UNIFI-DICEA', 'mobidiQ')
		self.BUFDIST_LE.setText(s.value('bufDist'))
		self.NUMSEG_LE.setText(s.value('bufSeg'))
		
		# set CRS
		aCRS = QgsCoordinateReferenceSystem(int(s.value('crsId')))
		self.CRS_SEL.setCrs(aCRS)

		# populate list of variable
		plotVarList = s.value('plotVar').split(';')
		for key, value in zip(self.VARIDS,self.VARNAMES):
			item = QListWidgetItem(value)
			item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
			if key in plotVarList:
				item.setCheckState(Qt.Checked)
			else:
				item.setCheckState(Qt.Unchecked)
				
			self.PLOTVAR_LB.addItem(item)
			
		self.buttonBox.accepted.connect(self.accept)
		self.buttonBox.rejected.connect(self.reject)
		#QObject.connect(self.buttonBox, SIGNAL("accepted()"), self.accept)
		#QObject.connect(self.buttonBox, SIGNAL("rejected()"), self.reject)
		QMetaObject.connectSlotsByName(self)
		
	def closeEvent(self, event):
		self.closed.emit()
		
	def setOutputFile(self):
		s = QSettings('UNIFI-DICEA', 'mobidiQ')
		res = QFileDialog.getSaveFileName(self, caption = self.tr('Save output as:'), directory = s.value('lastPath'), filter = 'Geotiff (*.tif)')
		filePath = res[0]
		if filePath != '':
			self.OUTPUT_LE.setText(res[0])
	
	def getData(self):
		# get selected vars
		selVarList = []
		for i in range(self.PLOTVAR_LB.count()):
			item = self.PLOTVAR_LB.item(i)
			if item.checkState()==2:
				# is checked
				selVar = self.VARIDS[self.VARNAMES.index(item.text())]
				selVarList.append(selVar)
			
		plotVar = ';'.join(selVarList)
		
		# get buffer distace
		bufDist = float(self.BUFDIST_LE.text())
		bufSeg = int(self.NUMSEG_LE.text())
		
		# get CRS
		aCRS = self.CRS_SEL.crs()
		crsId = aCRS.postgisSrid()
		
		return {'plotVar':plotVar, 'bufDist':bufDist,  'bufSeg':bufSeg, 'crsId':crsId}
