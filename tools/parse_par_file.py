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

def parseParFile(filename,parSep = '=', colSep=' ', feedback = None,tr=None):
	#~ if not feedback: feedback=MyProgress()
	#~ if not tr: tr=translate
	#if feedback: feedback.pushInfo('in parseParFile, processing: %s'%filename)
	#print('in parseParFile, processing: %s'%filename)
	lines=[]
	with open(filename)as f:
		lines = f.readlines()

	parDict = {}
	tableList = []
	for l in lines:
		# replace TAB
		l = l.replace('\t',' ')
		# remove EOL
		l = l.rstrip('\r\n')
		# remove all comments
		comIdx = l.find('#')
		subStr = l
		if comIdx>=0:
			# get substring to comIdx
			subStr = l[0:comIdx]
			
		if len(subStr)>0:
			toks = subStr.split(parSep)
			if len(toks)==2:
				# k,v pair
				parDict[toks[0].strip()]=toks[1].strip()
			else:
				# is not a inline par, probably is a table
				tableList.append(subStr)
				
	#process tableList
	isFirst = True
	tableDict = {}
	nCol = 0
	
	for r in  tableList:
		if isFirst:
			isFirst = False
			colNames = r.split(colSep)
			nCol = len(colNames)
			for c in range(0,nCol):
				tableDict[colNames[c]]=[]
		else:
			vals = r.split(colSep)
			if len(vals)==nCol:
				for c in range(0,nCol):
					tableDict[colNames[c]].append(vals[c])
	
	if not isFirst:
		parDict['table']=tableDict
			
	return parDict
		
	
if __name__ == '__console__':
	pars = parseParFile(filename='C:/Users/enrico/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/idragra4qgis/sample/geodata/links.csv',colSep=';')
	print(pars)