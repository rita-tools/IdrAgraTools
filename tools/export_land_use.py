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
import shutil

from .write_pars_to_template import writeParsToTemplate

def exportLandUse(DBM,outPath, feedback = None,tr=None):
	# export crop params
	listOfCrops = []
	maxCropId = DBM.getMax('idr_crop_types','id')
	if maxCropId is None:
		feedback.reportError('No crop parameters to be processed. Exiting...',True)

	path2croppar = os.path.join(outPath, 'crop_parameters')
	if os.path.exists(path2croppar):
		feedback.pushInfo('Directory %s already exists and will be deleted' % path2croppar, False)
		shutil.rmtree(path2croppar)

	os.makedirs(path2croppar)

	for cropId in range(1, maxCropId + 1):
		# create crop params folder

		table = ['GDD	Kcb LAI	Hc	Sr']
		cropDict = {'NAME': 'empty crop parameters file',
					'SOWINGDATE_MIN': 0,
					'SOWINGDATE_MAX': 0,
					'HARVESTDATE_MAX': 0,
					'HARVNUM_MAX': 0,
					'CROPSOVERLAP': 0,
					'TSOWING': 0,
					'TDAYBASE': 0,
					'TCUTOFF': 0,
					'VERN': 0,
					'TV_MIN': 0,
					'TV_MAX': 0,
					'VFMIN': 0,
					'VSTART': 0,
					'VEND': 0,
					'VSLOPE': 0,
					'PH_R': 0,
					'DAYLENGTH_IF': 0,
					'DAYLENGTH_INS': 0,
					'WP': 0,
					'FSINK': 0,
					'TCRIT_HS': 0,
					'TLIM_HS': 0,
					'HI': 0,
					'KYT': 0,
					'KY1': 0,
					'KY2': 0,
					'KY3': 0,
					'KY4': 0,
					'PRAW': 0,
					'AINTERCEPTION': 0,
					'CL_CN': 0,
					'IRRIGATION': 0,
					'CROPTABLE': 'GDD Kcb LAI Hc Sr\n0 0 0 0 0\n0 0 0 0 0'
					}
		soiluse = DBM.getRecord(tableName='idr_crop_types', fieldsList='', filterFld='id', filterValue=cropId)
		if len(soiluse)>0:
			soiluse = soiluse[0] # get first element in the list
			soiluse = soiluse[1:]  # remove first field "fid"
			listOfCrops.append(soiluse[0])

			aZip = zip(soiluse[34].split(' '), soiluse[35].split(' '), soiluse[36].split(' '), soiluse[37].split(' '),
					   soiluse[38].split(' '))
			for z in aZip:
				table.append(' '.join(z))

			table = '\n'.join(table)

			cropDict['NAME'] = soiluse[1]
			cropDict['SOWINGDATE_MIN'] = soiluse[2]
			cropDict['SOWINGDATE_MAX'] = soiluse[3]
			cropDict['HARVESTDATE_MAX'] = soiluse[4]
			cropDict['HARVNUM_MAX'] = soiluse[5]
			cropDict['CROPSOVERLAP'] = soiluse[6]
			cropDict['TSOWING'] = soiluse[7]
			cropDict['TDAYBASE'] = soiluse[8]
			cropDict['TCUTOFF'] = soiluse[9]
			cropDict['VERN'] = soiluse[10]
			cropDict['TV_MIN'] = soiluse[11]
			cropDict['TV_MAX'] = soiluse[12]
			cropDict['VFMIN'] = soiluse[13]
			cropDict['VSTART'] = soiluse[14]
			cropDict['VEND'] = soiluse[15]
			cropDict['VSLOPE'] = soiluse[16]
			cropDict['PH_R'] = soiluse[17]
			cropDict['DAYLENGTH_IF'] = soiluse[18]
			cropDict['DAYLENGTH_INS'] = soiluse[19]
			cropDict['WP'] = soiluse[20]
			cropDict['FSINK'] = soiluse[21]
			cropDict['TCRIT_HS'] = soiluse[22]
			cropDict['TLIM_HS'] = soiluse[23]
			cropDict['HI'] = soiluse[24]
			cropDict['KYT'] = soiluse[25]
			cropDict['KY1'] = soiluse[26]
			cropDict['KY2'] = soiluse[27]
			cropDict['KY3'] = soiluse[28]
			cropDict['KY4'] = soiluse[29]
			cropDict['PRAW'] = soiluse[30]
			cropDict['AINTERCEPTION'] = soiluse[31]
			cropDict['CL_CN'] = soiluse[32]
			cropDict['IRRIGATION'] = soiluse[33]
			cropDict['CROPTABLE'] = table

		# loop in used crop and export
		# save to file
		writeParsToTemplate(outfile=os.path.join(path2croppar, '%s.tab' % cropId),
							parsDict=cropDict,
							templateName='crop_par.txt')


	soiluseList = DBM.getRecord(tableName = 'idr_soiluses',fieldsList='',filterFld='', filterValue=None)

	#recTemplate = '%-8s %-24s %-24s # %s'
	recTemplate = '%s\t%s\t%s\t# %s'
	soiluseRecs = []
	soiluseRecs.append(recTemplate%('Cr_ID','Crop1','Crop2','Comments'))
	soiluseIds = []

	# export soil uses
	for soiluse in soiluseList:
		soiluse = soiluse[1:]  # remove first field "fid"
		i = soiluse[0]
		landuseName = soiluse[1]
		cropIdList = soiluse[3].split(' ')
		if len(cropIdList) ==0:
			feedback.reportError('Land use "%s" (id=%s) has empty crop list and will not be processed' % (landuseName,i),
								 False)
			continue

		soiluseIds.append(str(i))
		firstCrop = '*'
		secondCrop = '*'

		
		if len(cropIdList)==1:
			if int(cropIdList[0]) not in listOfCrops:
				feedback.reportError(
					'Land use "%s" (id=%s) has an un-parametrized crop in the list.' % (
					landuseName, i),
					False)
			firstCrop = '%s.tab'%cropIdList[0]
		else:
			if len(cropIdList)>2:
				feedback.reportError(
					'Land use "%s" (id=%s) has more than two crops found. Only the first two will be considered'% (landuseName,i),
					False)

			if int(cropIdList[0]) not in listOfCrops:
				feedback.reportError(
					'Land use "%s" (id=%s) has an un-parametrized crop in the list.' % (
					landuseName, i),
					False)
			firstCrop = '%s.tab'%cropIdList[0]
			if int(cropIdList[1]) not in listOfCrops:
				feedback.reportError(
					'Land use "%s" (id=%s) has an un-parametrized crop in the list.' % (
					landuseName, i),
					False)
			secondCrop = '%s.tab'%cropIdList[1]

		soiluseRecs.append(recTemplate%(i,firstCrop,secondCrop,landuseName))
		
	# collapse soiluserecords
	tableString = '\n'.join(soiluseRecs)
	# save to file
	writeParsToTemplate(outfile=os.path.join(outPath,'soil_uses.txt'),
									parsDict =  {'SOILUSES':tableString},
									templateName='soil_uses.txt')
	

	return soiluseIds