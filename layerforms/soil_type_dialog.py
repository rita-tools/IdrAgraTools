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

from QWaDiS.layerforms.utils import *

def formOpen(dialog,layerid,featureid):
	global myDialog
	myDialog = dialog
	global layer
	layer = layerid
	global feature
	feature = featureid
		
	tr = qgis.utils.plugins['QWaDiS'].tr
	#global allItems
	cnItems = {tr('[0] Low runoff potential'):0,tr('[1] Moderately low runoff potential'):1,tr('[2] Moderately high runoff potential'):2,tr('[3] High runoff potential'):3}
	
	# populate combos with value
	global objToBeEnabledList
	objToBeEnabledList = []
	
	hydrGroupCB = dialog.findChild(QComboBox,'hydr_group_cb')
	
	objToBeEnabledList.append(hydrGroupCB)
	
	updateComboItems(hydrGroupCB,cnItems)
	hydrGroupLE = dialog.findChild(QLineEdit,'hydr_group')
	hydrGroupLE.setHidden(True)
	hydrGroupCB.currentIndexChanged[str].connect(lambda txt: updateLineEdit(txt,cnItems,hydrGroupLE))
	updateSelected(hydrGroupCB, hydrGroupLE,cnItems)
	
	setEditMode(layer.isEditable())
		
	# connect start edit button to setEditMode to get edit tool pressed	
	#qgis.utils.plugins['QWaDiS'].iface.actionToggleEditing().toggled[bool].connect(setEditMode)
	try:
		parentForm = myDialog.window() 
		act = parentForm.findChild(QAction,'mActionToggleEditing')
		if act: act.toggled[bool].connect(setEditMode)
	except Exception as e:
		print('error: %s'%str(e))
		 
def setEditMode(mode):
	try:
		for obj in objToBeEnabledList:
			obj.setEnabled(mode)
	except Exception as e:
		print('error: %s'%str(e))
		
def validate():
	# Make sure that the name field isn't empty.
	myDialog.accept()
