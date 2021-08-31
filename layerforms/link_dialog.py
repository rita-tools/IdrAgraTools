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
from PyQt5.QtWidgets import *
from qgis.gui import *

from IdragraTools.layerforms.utils import *

def formOpen(dialog,layerid,featureid):
	global myDialog
	myDialog = dialog
	global layer
	layer = layerid
	global feature
	feature = featureid
	
	#~ 'idr_soil_types':self.tr('Soil Types'),'idr_crop_types':self.tr('Crop types'), 'idr_irrmet_types':self.tr('Irrigation methods'),
									#~ 'idr_weather_stations':self.tr('Weather stations'),'idr_gw_wells':self.tr('Ground water wells'),
									#~ 'idr_nodes':self.tr('Nodes'),'idr_links':self.tr('Links'),
									#~ 'idr_crop_fields':self.tr('Crop fields')
		
	tr = qgis.utils.plugins['IdragraTools'].tr
	getIdNameDict = qgis.utils.plugins['IdragraTools'].getIdNameDict
	getIdNameDictXY = qgis.utils.plugins['IdragraTools'].getIdNameDictXY
	
	# prepare a list of widget to enable/disable
	global objToBeEnabledList
	objToBeEnabledList = []
	
	# get vertex from geometry TODO
	#~ geom = feature.geometry()
	
	
	#~ if geom:
		#~ vertices = geom.asPolyline()
		#~ n = len(vertices)
		#~ x1 = vertices[0].x()
		#~ y1 = vertices[0].y()
		#~ x2 = vertices[n-1].x()
		#~ y2 = vertices[n-1].y()
		
		#~ # populate combos with values
		#~ setupCombo('inlet_node',getIdNameDictXY('idr_nodes',x1,y1))
		#~ setupCombo('outlet_node',getIdNameDictXY('idr_nodes',x2,y2))
	#~ else:
	setupCombo('inlet_node',getIdNameDict('idr_nodes'))
	setupCombo('outlet_node',getIdNameDict('idr_nodes'))
			
	# enable/disable edit mode
	setEditMode(layer.isEditable())
		
	# connect start edit button to setEditMode to get edit tool pressed	
	#qgis.utils.plugins['IdragraTools'].iface.actionToggleEditing().toggled[bool].connect(setEditMode)
	try:
		parentForm = myDialog.window() 
		act = parentForm.findChild(QAction,'mActionToggleEditing')
		if act: act.toggled[bool].connect(setEditMode)
	except Exception as e:
		print('error: %s'%str(e))


def setupCombo(attrName,allItems):
	CB = myDialog.findChild(QComboBox,attrName+'_CB')
	objToBeEnabledList.append(CB)
	updateComboItems(CB,allItems)
	LE = myDialog.findChild(QLineEdit,attrName)
	LE.setHidden(True)
	CB.currentIndexChanged[str].connect(lambda txt: updateLineEdit(txt,allItems,LE))
	updateSelected(CB, LE,allItems)
	
def setEditMode(mode):
	try:
		for obj in objToBeEnabledList:
			obj.setEnabled(mode)
	except Exception as e:
		print('error: %s'%str(e))
		
def validate():
	# Make sure that the name field isn't empty.
	myDialog.accept()

