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

import numpy as np

def makeWeightMatrix_WW(xmin, xmax, ymin, ymax, cellsize, xList, yList, idList, nMax, feedback = None,tr=None):
	res = []
	# populate the list with empty matrix
	for n in range(nMax):
		res.append(makeIndexArray(xmin, xmax, ymin, ymax, cellsize, np.nan))

	numOfId = len(idList)

	# FIX special case: single weather station
	# don't make distance weight but make uniform weight near to one
	if numOfId==1:
		# replace only the first two maps with the half weight
		uniqueW = float(idList[0]) + 0.5
		res[0] = np.flipud(makeIndexArray(xmin, xmax, ymin, ymax, cellsize,uniqueW))
		res[1] = np.flipud(makeIndexArray(xmin, xmax, ymin, ymax, cellsize,uniqueW))

		# exit and return res
		return res


	iMatrixList = []
	dMatrixList = []
	distDict = {}
	maxDist = -1
	# init distance matrix from each point
	for x,y,id in zip(xList, yList, idList):
		distDict[id] = makeDistanceArray(xmin, xmax, ymin, ymax, cellsize,x,y)
		maxDist = max(maxDist,distDict[id].max()) # overall maximum

	# recalculate nMax
	nMax = min(numOfId,nMax)
	# up to num max, find the closest excluding previously selected index
	for n in range(nMax):
		iMatrix = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,np.nan)
		dMatrix = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,maxDist)
		
		for id in idList:
			tempD = distDict[id]
			tempId = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,id)
			# check if id is already used before (n-1 matrix)
			for compMatrix in iMatrixList:
				tempId = np.where(tempId==compMatrix,np.nan,tempId)
			
			#replace value with the closer but not the used index
			iMatrix = np.where(np.logical_and((tempD<dMatrix),(~np.isnan(tempId))),tempId,iMatrix)
			dMatrix = np.where(np.logical_and((tempD<dMatrix),(~np.isnan(tempId))),tempD,dMatrix)
		
		dMatrixList.append(dMatrix)
		iMatrixList.append(iMatrix)
		
		feedback.setProgress(100*n/nMax)
			
	# sum all distance-based weight
	sMatrix = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,0.0)
	for dMatrix in dMatrixList:
		sMatrix+=1.0/dMatrix
		
	# normalize weight matrix on the total distance and merge id.weight results
	for n in range(nMax):
		res[n] = np.flipud(iMatrixList[n]+(1.0/dMatrixList[n])/sMatrix)
		feedback.setProgress(100*n/nMax)
	
	return res
	
def makeWeightMatrix_IDW(xmin, xmax, ymin, ymax, cellsize, xList, yList, idList, nMax, feedback = None,tr=None):
	
	# merge id.weight results
	res = []
	iMatrixList = []
	for n in range(nMax):
		#~ print('==== TEST %s ==='%n)
		isFirst = True
		iMatrix = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,np.nan)
		wMatrix = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,-1.0)
		
		for x,y,id in zip(xList, yList, idList):
			# if is the first case
			#~ print('*** ws %s ***'%id)
			tempW = makeWeightArray(xmin, xmax, ymin, ymax, cellsize,x,y)
			tempId = makeIndexArray(xmin, xmax, ymin, ymax, cellsize,id)
			c=1
			# set nan the cells where the index is already used before
			for compMatrix in iMatrixList:
				#~ print('comp n. %s'%c)
				#~ print(tempId)
				#~ print(compMatrix)
				tempId = np.where(tempId==compMatrix,np.nan,tempId)
				#~ print(tempId)
				
				c+=1
				
			#replace value with the closer with higher weight but not the used index
			iMatrix = np.where(np.logical_and((tempW>wMatrix),(~np.isnan(tempId))),tempId,iMatrix)
			wMatrix = np.where(np.logical_and((tempW>wMatrix),(~np.isnan(tempId))),tempW,wMatrix)
				

		res.append(np.flipud(iMatrix+wMatrix))
		iMatrixList.append(iMatrix)
		
		feedback.setProgress(100*n/nMax)
	
	#~ print(assignedId)
	return res

def makeDistanceArray(xmin, xmax, ymin, ymax, cellsize,x,y):
	# use normalized coordinates
	xRange = np.arange(xmin+0.5*cellsize,xmax, cellsize)-xmin
	yRange = np.arange(ymin+0.5*cellsize,ymax, cellsize)-ymin
	nCols = len(xRange)
	nRows = len(yRange)
	xArray = np.array([xRange,]*nRows)
	yArray = np.array([yRange,]*nCols).transpose()
	
	# calculate distance
	x = x-xmin
	y = y-ymin
	
	distance = ((xArray-x)**2+(yArray-y)**2)**0.5
	return distance

def makeWeightArray(xmin, xmax, ymin, ymax, cellsize,x,y):
	# use normalized coordinates
	xRange = np.arange(xmin+0.5*cellsize,xmax, cellsize)-xmin
	yRange = np.arange(ymin+0.5*cellsize,ymax, cellsize)-ymin
	#print(xRange)
	nCols = len(xRange)
	nRows = len(yRange)
	#yRange = yRange.reshape((nRows,1))
	#print(yRange)
	
	#~ print('nrows: %s'%nRows)
	#~ print('ncols: %s'%nCols)
	#xArray = np.repeat(xRange,nRows,0)
	xArray = np.array([xRange,]*nRows)
	#yArray = np.repeat(yRange,nCols,1)
	yArray = np.array([yRange,]*nCols).transpose()
	#xArray = xArray.reshape((nRows,nCols))
	#~ print(xArray)
	#~ print(yArray)
	
	# calculate distance
	x = x-xmin
	y = y-ymin
	
	weight = 1.0/(((xArray-x)**2+(yArray-y)**2)**0.5)**0.1
	#~ print(weight)
	return weight
	
def makeIndexArray(xmin, xmax, ymin, ymax, cellsize,id):
	# use normalized distance
	xRange = np.arange(xmin+0.5*cellsize,xmax, cellsize)-xmax
	yRange = np.arange(ymin+0.5*cellsize,ymax, cellsize)-ymin
	nCols = len(xRange)
	nRows = len(yRange)
	
	res = np.ones((nRows,nCols),type(id))*id
	return res

def makeUniformWeightMatrix(xmin, xmax, ymin, ymax, cellsize,id,weight=0.999):
	# use normalized coordinates
	xRange = np.arange(xmin + 0.5 * cellsize, xmax, cellsize) - xmax
	yRange = np.arange(ymin + 0.5 * cellsize, ymax, cellsize) - ymin
	nCols = len(xRange)
	nRows = len(yRange)

	res = np.ones((nRows, nCols),float) * id +weight
	return res
