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
from PyQt5.QtCore import QObject
from qgis import processing


from tools.write_pars_to_template import writeParsToTemplate


class ExportGeodataVector(QObject):

    def __init__(self, parent=None, sim_dict = None, feedback=None, tr=lambda x: x):
        QObject.__init__(self, parent)
        self.sim_dict = sim_dict
        self.feedback = feedback
        self.tr = tr

        self.algResults = None  # store temporary outputs
        self.algResults1 = None  # store temporary outputs
        self.algResults2 = None  # store temporary outputs

    def exportGeodata(self):
        db_name = self.sim_dict['DBFILE']

        outPath = os.path.join(self.sim_dict['OUTPUTPATH'],'geodata_v')
        if not os.path.exists(outPath): os.makedirs(outPath)

        depthList = [self.sim_dict['ZEVALAY'],self.sim_dict['ZTRANSLAY']]

        self.feedback.pushInfo(self.tr('Get slope and water table depth'))
        self.feedback.setProgress(10.0)

        # make a new shapefile with elev,slope and water table depth
        wt_lay_list = []
        wt_map = None
        for wt_map in list(self.sim_dict['WATERTABLEMAP'].keys()):
            wt_lay_list.append('GPKG:'+db_name +':'+wt_map)

        self.algResults = processing.run("idragratools:IdragraCreateRasterToField",
                            {'FIELD_LAY': db_name + '|layername=idr_usemap',
                            'ELEV_LAY': 'GPKG:'+db_name +':elevation',
                            'WT_ELEV_LAY': wt_lay_list,
                            'SLP_MIN': 0,
                            'SLP_MAX': 1000, 'WTD_MIN': 0.5,
                             'OUT_LAY': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('1',self.algResults['OUT_LAY'].fields().names())

        self.feedback.pushInfo(self.tr('Get land use, irrigation methods, irrigation units and meteo weights'))
        self.feedback.setProgress(20.0)

        # make a new shapefile with main landuse, soil, irrigation methods, irrigation units and meteo weights
        self.algResults = processing.run("idragratools:IdragraCreateFieldTable",
                       {'FIELD_LAY': self.algResults['OUT_LAY'], 'FIELD_COL': 'id', 'LU_COL': 'extid',
                        'SOIL_LAY': db_name + '|layername=idr_soilmap', 'SOIL_COL': 'extid',
                        'IRRMETH_LAY': db_name + '|layername=idr_irrmap','IRRMETH_COL': 'extid',
                        'IRRUNIT_LAY': db_name + '|layername=idr_distrmap','IRRUNIT_COL': 'id',
                        'WSTAT_LAY': db_name + '|layername=idr_weather_stations','WSTAT_COL': 'id',
                        'OUT_LAY': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('1-2', self.algResults['OUT_LAY'].fields().names())

        # join attributes from irrigation unit
        self.feedback.pushInfo(self.tr('Join attributes from irrigation units'))
        self.feedback.setProgress(30.0)

        self.algResults =  processing.run("native:joinattributestable", {
            'INPUT': self.algResults['OUT_LAY'],
            'FIELD': 'irrunit_id', 'INPUT_2': db_name + '|layername=idr_distrmap',
            'FIELD_2': 'id', 'FIELDS_TO_COPY': ['distr_eff', 'expl_factor', 'wat_shift'], 'METHOD': 1,
            'DISCARD_NONMATCHING': False, 'PREFIX': '', 'OUTPUT': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('2', self.algResults['OUTPUT'].fields().names())

        # join attributes from irrigation methods
        self.feedback.pushInfo(self.tr('Join attributes from irrigation methods'))
        self.feedback.setProgress(40.0)

        self.algResults = processing.run("native:joinattributestable", {
            'INPUT': self.algResults['OUTPUT'],
            'FIELD': 'irrmeth_id', 'INPUT_2': db_name + '|layername=idr_irrmet_types',
            'FIELD_2': 'id', 'FIELDS_TO_COPY': ['irr_eff'], 'METHOD': 1,
            'DISCARD_NONMATCHING': False, 'PREFIX': '', 'OUTPUT': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('3', self.algResults['OUTPUT'].fields().names())

        self.feedback.pushInfo(self.tr('Exporting soils parameters'))
        self.feedback.setProgress(50.0)
        # SOIL PARAMETERS MAP
        # make aggregate parameters
        sourceTable = db_name + '|layername=idr_soil_profiles'
        depths = ' '.join([str(x) for x in depthList])
        # make aggregate soil params
        self.algResults2 = processing.run("idragratools:IdragraSoilParams",
                                         {'SOURCE_TABLE': sourceTable,
                                          'SOILID_FLD': 'soilid', 'MAXDEPTH_FLD': 'maxdepth',
                                          'KSAT_FLD': 'ksat',
                                          'TFC_FLD': 'theta_fc', 'TWP_FLD': 'theta_wp', 'TR_FLD': 'theta_r',
                                          'TS_FLD': 'theta_sat',
                                          'DEPTHS': depths, 'OUT_TABLE': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('check', self.algResults2['OUT_TABLE'].fields().names())
        #check ['soilid', 'ksat1', 'n1', 'rew1', 'theta_fc1', 'theta_wp1', 'theta_r1', 'theta_sat1', 'ksat2', 'n2', 'rew2', 'theta_fc2', 'theta_wp2', 'theta_r2', 'theta_sat2']
        # link to table
        colToJoin = ['ksat','n','rew','theta_fc','theta_wp','theta_r','theta_sat']
        colToJoin =[x+'1' for x in colToJoin]+[x+'2' for x in colToJoin]

        self.algResults = processing.run("native:joinattributestable", {
            'INPUT': self.algResults['OUTPUT'],
            'FIELD': 'soil_id', 'INPUT_2': self.algResults2['OUT_TABLE'],
            'FIELD_2': 'soilid', 'FIELDS_TO_COPY': colToJoin, 'METHOD': 1,
            'DISCARD_NONMATCHING': False, 'PREFIX': '', 'OUTPUT': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('4', self.algResults['OUTPUT'].fields().names())
        for feat in self.algResults['OUTPUT'].getFeatures():
            print(feat.attributes())
            break

        # make capillary rise params maps
        self.algResults2 = processing.run("idragratools:IdragraCreateCapriseTable",
                                         {'SOURCE_TABLE': sourceTable,
                                          'SOILID_FLD': 'soilid', 'MAXDEPTH_FLD': 'maxdepth',
                                          'TXTR_FLD': 'txtr_code', 'DEPTHS': depths,
                                          'OUT_TABLE': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        colToJoin = ['CapRisePar_a3','CapRisePar_a4','CapRisePar_b1','CapRisePar_b2','CapRisePar_b3','CapRisePar_b4']

        # link to table
        self.algResults = processing.run("native:joinattributestable", {
            'INPUT': self.algResults['OUTPUT'],
            'FIELD': 'soil_id', 'INPUT_2': self.algResults2['OUT_TABLE'],
            'FIELD_2': 'soilid',
            'FIELDS_TO_COPY': colToJoin,
            'METHOD': 1,
            'DISCARD_NONMATCHING': False, 'PREFIX': '', 'OUTPUT': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('5', self.algResults['OUTPUT'].fields().names())
        for feat in self.algResults['OUTPUT'].getFeatures():
            print(feat.attributes())
            break

        # HSG MAP
        self.feedback.pushInfo(self.tr('Exporting HSG map'))
        self.feedback.setProgress(70.0)

        self.algResults2 = processing.run("idragratools:IdragraCreatePreHSGTable",
                                          {'SOURCE_TABLE': sourceTable,
                                           'SOILID_FLD': 'soilid', 'MAXDEPTH_FLD': 'maxdepth', 'KSAT_FLD': 'ksat',
                                           'OUT_TABLE': 'TEMPORARY_OUTPUT'},
                                          context=None, feedback=self.feedback, is_child_algorithm=False)

        # link to table
        self.algResults = processing.run("native:joinattributestable", {
            'INPUT': self.algResults['OUTPUT'],
            'FIELD': 'soil_id', 'INPUT_2': self.algResults2['OUT_TABLE'],
            'FIELD_2': 'soilid',
            'FIELDS_TO_COPY': ['maxsoildepth', 'minksat50', 'minksat60', 'minksat100'],
            'METHOD': 1,
            'DISCARD_NONMATCHING': False, 'PREFIX': '', 'OUTPUT': 'TEMPORARY_OUTPUT'},
                                         context=None, feedback=self.feedback, is_child_algorithm=False)

        print('6', self.algResults['OUTPUT'].fields().names())
        for feat in self.algResults['OUTPUT'].getFeatures():
            print(feat.attributes())
            break

        # make a data dictionary
        data = {}
        col_list = self.algResults['OUTPUT'].fields().names()
        # add HSG
        col_list.append('hydr_group')

        for col in col_list:
            data[col] = []

        n_feat = 0
        mean_area = 0
        for feat in self.algResults['OUTPUT'].getFeatures():
            n_feat+=1

            # calculate mean feat area to use as reference cell dimension
            mean_area += feat['shape_area']

            for col in col_list:
                if col == 'hydr_group':
                    # get first wt map if exist
                    if wt_map: wt_depth = feat[wt_map+'_mean']
                    else: wt_depth = 1000
                    # calculate HSG
                    hsg = self.assignHydrGroup(max_depth = feat['maxsoildepth'],
                                             wt_depth = wt_depth,
                                             min_ksat50 = feat['minksat50'],
                                             min_ksat100 = feat['minksat100'])
                    data[col].append(hsg)
                else:
                    data[col].append(feat[col])

        mean_area = mean_area/n_feat
        mean_cell_size = round(mean_area**0.5,2)
        # add hydrological condition
        data['hydr_cond']=[1]*n_feat
        # add domain
        data['domain'] = [1] * n_feat
        # save single file asc file

        # TODO: export output columns to rasters
        # use the following attributes, aliases
        replaceDict = {'theta_fc1': 'ThetaI_FC',
                       'theta_fc2': 'ThetaII_FC',
                       'theta_r1': 'ThetaI_r',
                       'theta_r2': 'ThetaII_r',
                       'theta_sat1': 'ThetaI_sat',
                       'theta_sat2': 'ThetaII_sat',
                       'theta_wp1': 'ThetaI_WP',
                       'theta_wp2': 'ThetaII_WP',
                       'ksat1': 'Ksat_I',
                       'ksat2': 'Ksat_II',
                       'n1': 'N_I',
                       'n2': 'N_II',
                       'rew1': 'REW_I',
                       'rew2': 'REW_II',
                       'land_use': 'soiluse',
                       'irr_eff': 'appl_eff',
                       'irrmeth_id':'irr_meth',
                       'irrunit_id':'irr_units',
                       'slp':'slope',
                       'shape_area':'shapearea',
                       'distr_eff':'conv_eff',
                       'watertable':'waterdepth',
                       'domain':'domain',
                       'CapRisePar_a3':'CapRisePar_a3',
                       'CapRisePar_a4':'CapRisePar_a4',
                       'CapRisePar_b1':'CapRisePar_b1',
                       'CapRisePar_b2': 'CapRisePar_b2',
                       'CapRisePar_b3': 'CapRisePar_b3',
                       'CapRisePar_b4': 'CapRisePar_b4',
                       'hydr_cond':'hydr_cond',
                       'hydr_group':'hydr_group',
                       'main_txtr':'main_txtr'
                       }

        for k,v_list in data.items():
            asc_dict = {'n_cols':1,
                        'n_rows':n_feat,
                        'xll_corner':-1.0,
                        'yll_corner':-1.0,
                        'cell_size':mean_cell_size,
                        'nodata_value':-9999,
                        'data':'\n'.join([str(v) for v in v_list])
                        }

            out_file = k
            out_file = out_file.replace('_mean','')

            if out_file.startswith('watertable_'):
                #get the last numeric part
                out_file = 'watertable' # TODO: fix multiple year

            if out_file in list(replaceDict.keys()):
                out_file = replaceDict[out_file]

                writeParsToTemplate(outfile=os.path.join(outPath, out_file+'.asc'),
                                    parsDict=asc_dict,
                                    templateName='asc_grid.txt')

            if out_file.startswith('meteo_'):
                writeParsToTemplate(outfile=os.path.join(outPath, out_file + '.asc'),
                                    parsDict=asc_dict,
                                    templateName='asc_grid.txt')

        # export rice params
        writeParsToTemplate(outfile=os.path.join(outPath, 'rice_soilparam.txt'),
                            parsDict={},
                            templateName='rice_soilparam.txt')

        self.feedback.setPercentage(100.0)
        
    def assignHydrGroup(self,max_depth,wt_depth,min_ksat50,min_ksat100):
        # conversion factors
        cm2m = 0.01
        nms2cmh = 3600.0 / (10 * 1000)

        # assign HSG code:
        # A=1, B=2, C=3 and D=4
        hsg = - 9
        # ---------------------------
        if (max_depth < 50.0 * cm2m) and (max_depth >= 0): hsg = 4
        # ---------------------------
        if ((wt_depth < 60.0 * cm2m) and (max_depth >= 0)): hsg = 4
        # ---------------------------
        if ((max_depth >= 50.0 * cm2m) and (max_depth <= 100.0 * cm2m) and
                 (wt_depth >= 60.0 * cm2m) and (min_ksat50 > 40.0 * nms2cmh)): hsg = 1
        if ((max_depth >= 50.0 * cm2m) and (max_depth <= 100.0 * cm2m) and
                 (wt_depth >= 60.0 * cm2m) and (min_ksat50 <= 40.0 * nms2cmh) and
                 (min_ksat50 > 10.0 * nms2cmh)): hsg = 2

        if ((max_depth >= 50.0 * cm2m) and (max_depth <= 100.0 * cm2m) and
                 (wt_depth >= 60.0 * cm2m) and
                 (min_ksat50 <= 10.0 * nms2cmh) and (min_ksat50 > 1.0 * nms2cmh)): hsg = 3
        if ((max_depth >= 50.0 * cm2m) and (max_depth <= 100.0 * cm2m) and
                 (wt_depth >= 60.0 * cm2m) and
                 (min_ksat50 <= 1.0 * nms2cmh)): hsg = 4
        # ---------------------------
        if ((max_depth > 100.0 * cm2m) and (wt_depth > 60.0 * cm2m) and (wt_depth <= 100.0 * cm2m) and
                 (min_ksat50 > 40.0 * nms2cmh)): hsg = 1
        if ((max_depth > 100.0 * cm2m) and (wt_depth > 60.0 * cm2m) and (wt_depth <= 100.0 * cm2m) and
                 (min_ksat50 <= 40.0 * nms2cmh) and (min_ksat50 > 10.0 * nms2cmh)): hsg= 2
        if((max_depth > 100.0 * cm2m) and (wt_depth > 60.0 * cm2m) and (wt_depth <= 100.0 * cm2m) and
                 (min_ksat50 <= 10.0 * nms2cmh) and (min_ksat50 > 1.0 * nms2cmh)): hsg = 3
        if((max_depth > 100.0 * cm2m) and (wt_depth > 60.0 * cm2m) and (wt_depth <= 100.0 * cm2m) and
                 (min_ksat50 <= 1.0 * nms2cmh)): hsg = 4
        # ---------------------------
        if (wt_depth > 100.0 * cm2m) and (min_ksat100 > 40.0 * nms2cmh): hsg = 1
        if((wt_depth > 100.0 * cm2m) and (min_ksat100 <= 40.0 * nms2cmh) and (
                    min_ksat100 > 10.0 * nms2cmh)): hsg = 2
        if ((wt_depth > 100.0 * cm2m) and (min_ksat100 <= 10.0 * nms2cmh) and
                (min_ksat100 > 1.0 * nms2cmh)): hsg = 3
        if (wt_depth > 100.0 * cm2m) and (min_ksat100 <= 1.0 * nms2cmh): hsg = 4
        
        return hsg

if __name__ == '__main__':
    pass
