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

from .speakingName import speakingName
from .write_pars_to_template import writeParsToTemplate

def exportLandUse(DBM,outPath, feedback = None,tr=None):
	# export crop params
	allCropsDict = {}

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
		soiluse = DBM.getRecordAsDict(tableName='idr_crop_types', fieldsList='', filterFld='id', filterValue=cropId)

		if len(soiluse)>0:
			soiluse = soiluse[0]

			feedback.pushInfo(tr('Exporting settings for crop %s') % (soiluse['name']))

			aZip = zip(soiluse['gdd'].split(' '), soiluse['kcb'].split(' '), soiluse['lai'].split(' '), soiluse['hc'].split(' '),
					   soiluse['sr'].split(' '))

			adv_opts = ''
			if len(list(soiluse.keys()))>40: # for legacy db structure
				adv_opts = soiluse['adv_opts'].split(';')
				adv_opts = [opt.strip() for opt in adv_opts]
				adv_opts = '\n'.join(adv_opts)

			for z in aZip:
				table.append(' '.join(z))

			table = '\n'.join(table)

			cropDict['NAME'] = soiluse['name']
			cropDict['SOWINGDATE_MIN'] = soiluse['sowingdate_min']
			cropDict['SOWINGDATE_MAX'] = soiluse['sowingdelay_max']
			cropDict['HARVESTDATE_MAX'] = soiluse['harvestdate_max']
			cropDict['HARVNUM_MAX'] = soiluse['harvnum_max']
			cropDict['CROPSOVERLAP'] = soiluse['cropsoverlap']
			cropDict['TSOWING'] = soiluse['tsowing']
			cropDict['TDAYBASE'] = soiluse['tdaybase']
			cropDict['TCUTOFF'] = soiluse['tcutoff']
			cropDict['VERN'] = soiluse['vern']
			cropDict['TV_MIN'] = soiluse['tv_min']
			cropDict['TV_MAX'] = soiluse['tv_max']
			cropDict['VFMIN'] = soiluse['vfmin']
			cropDict['VSTART'] = soiluse['vstart']
			cropDict['VEND'] = soiluse['vend']
			cropDict['VSLOPE'] = soiluse['vslope']
			cropDict['PH_R'] = soiluse['ph_r']
			cropDict['DAYLENGTH_IF'] = soiluse['daylength_if']
			cropDict['DAYLENGTH_INS'] = soiluse['daylength_ins']
			cropDict['WP'] = soiluse['wp']
			cropDict['FSINK'] = soiluse['fsink']
			cropDict['TCRIT_HS'] = soiluse['tcrit_hs']
			cropDict['TLIM_HS'] = soiluse['tlim_hs']
			cropDict['HI'] = soiluse['hi']
			cropDict['KYT'] = soiluse['kyT']
			cropDict['KY1'] = soiluse['ky1']
			cropDict['KY2'] = soiluse['ky2']
			cropDict['KY3'] = soiluse['ky3']
			cropDict['KY4'] = soiluse['ky4']
			cropDict['PRAW'] = soiluse['praw']
			cropDict['AINTERCEPTION'] = soiluse['ainterception']
			cropDict['CL_CN'] = soiluse['cl_cn']
			cropDict['IRRIGATION'] = soiluse['irrigation']
			cropDict['CROPTABLE'] = table
			cropDict['ADV_OPTS'] = adv_opts

		# prepare new file name
		cropFileName = '%s_%s.tab' % (cropId, speakingName(soiluse['name']))

		# loop in used crop and export
		# save to file
		writeParsToTemplate(outfile=os.path.join(path2croppar,cropFileName),
							parsDict=cropDict,
							templateName='crop_par.txt')

		allCropsDict[str(cropId)]=cropFileName


	soiluseList = DBM.getRecord(tableName = 'idr_soiluses',fieldsList='',filterFld='', filterValue=None, orderBy='id')

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
			if cropIdList[0] not in list(allCropsDict.keys()):
				feedback.reportError(
					'Land use "%s" (id=%s) has an un-parametrized crop in the list.' % (
					landuseName, i),
					False)
			firstCrop = allCropsDict[cropIdList[0]]
		else:
			if len(cropIdList)>2:
				feedback.reportError(
					'Land use "%s" (id=%s) has more than two crops found. Only the first two will be considered'% (landuseName,i),
					False)

			if cropIdList[0] not in list(allCropsDict.keys()):
				feedback.reportError(
					'Land use "%s" (id=%s) has an un-parametrized crop in the list.' % (
					landuseName, i),
					False)
			firstCrop = allCropsDict[cropIdList[0]]
			if cropIdList[1] not in list(allCropsDict.keys()):
				feedback.reportError(
					'Land use "%s" (id=%s) has an un-parametrized crop in the list.' % (
					landuseName, i),
					False)
			secondCrop = allCropsDict[cropIdList[1]]

		soiluseRecs.append(recTemplate%(i,firstCrop,secondCrop,landuseName))
		
	# collapse soiluserecords
	tableString = '\n'.join(soiluseRecs)
	# save to file
	writeParsToTemplate(outfile=os.path.join(outPath,'soil_uses.txt'),
									parsDict =  {'SOILUSES':tableString},
									templateName='soil_uses.txt')
	

	return soiluseIds