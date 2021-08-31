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

import os
from .write_pars_to_template import writeParsToTemplate

def exportCellList(DBM,outPath, feedback = None,tr=None):
	# get cropfilelds with f_alloutput
	res = DBM.getRecord(tableName = 'idr_crop_fields',fieldsList= ['fid'], filterFld = 'f_alloutput', filterValue='1')
	cellIdList = []
	# make a list of cells id
	for c in res:
		cellIdList.append('%-5s%-5s'%(c[0],1))
		
	nOfCell = len(cellIdList)
	table = '\n'.join(cellIdList)
	
	# save to file
	writeParsToTemplate(outfile=os.path.join(outPath,'cells.txt'),
									parsDict =  {'NUMCELL':nOfCell, 'CELLTABLE':table},
									templateName='cells.txt')
