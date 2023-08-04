import copy
import glob
import math
import os

import numpy as np
import pandas as pd
import re

import matplotlib

from report.toc_item import TocItem

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import cm
from matplotlib.colors import Normalize


from datetime import datetime,timedelta

# import as module
from report.annual_totals_report_builder import AnnualTotalsReportBuilder

class IrrunitTotalsReportBuilder(AnnualTotalsReportBuilder):

    def __init__(self,feedback = None, tr = None):
        super().__init__(feedback, tr)

        self.irrunit_template = os.path.join(self.rb_dir, 'default', 'irrigation_unit_report.html')

    def addMapToPlot(self, ax, map_data, extent, values, offset=0.1):
        im = ax.imshow(map_data, extent=extent, interpolation='nearest', cmap='tab20',
                       norm=Normalize(min(values), max(values)))

        # credits: https://stackoverflow.com/questions/25482876/how-to-add-legend-to-imshow-in-matplotlib
        # colormap used by imshow
        colors = [im.cmap(im.norm(value)) for value in values]
        # create a patch (proxy artist) for every color
        patches = [mpatches.Patch(color=colors[i]) for i in range(len(values))]

        handles = patches
        labels = values

        # set axes extent
        xmin = round(extent[0] - offset * (extent[1]-extent[0]))
        xmax = round(extent[1] + offset * (extent[1]-extent[0]))
        ymin = round(extent[2] - offset * (extent[3]-extent[2]))
        ymax = round(extent[3] + offset * (extent[3]-extent[2]))

        #ax.set_xticks(np.arange(xmin, xmax, step=1000))
        #ax.set_yticks(np.arange(ymin, ymax, step=1000))
        ax.set_aspect(1.0)

        #ax.axis('equal')
        #print(xmin,xmax,ymin,ymax)
        ax.set_xlim([xmin, xmax])
        ax.set_ylim([ymin, ymax])

        ax.ticklabel_format(axis='both', style='sci', scilimits=(0, 0))
        return handles, labels

    def irrUnitsSummary(self, baseFN, mask_rl, values, outFile= None):
        if isinstance(mask_rl, str):
            mask_rl = self.loadASC(mask_rl,int)
            mask_data = np.where(mask_rl['data']==mask_rl['nodata_value'],np.nan,mask_rl['data'])
            mask_data = mask_data * 0 + 1
        else:
            mask_data = mask_rl['data']*0+1

        extent = self.maskExtent(mask_data)
        extent = self.calcExtent(extent[0], extent[1], extent[2], extent[3], mask_rl['xllcorner'], mask_rl['yllcorner'],
                                 mask_rl['cellsize'])
        #print('extent', extent)

        # search all files that match baseFN
        baseFileList = glob.glob(baseFN)
        #print('baseFileList',baseFileList)
        baseFileList.sort()
        numOfFile = len(baseFileList)
        nPlot = math.ceil((numOfFile) / 2)# always add one-axes for legend
        #print('numOfFile',numOfFile,'nPlot',nPlot)
        fig, axs = plt.subplots(nPlot, 2, figsize=(10, 3 * nPlot), constrained_layout=True)
        #print('axs',axs)

        tableList = []

        i = 0
        for i,ax in enumerate(axs.flat):
            if i<len(baseFileList):
                baseFile=baseFileList[i]
                # extract date time
                fname = os.path.basename(baseFile)
                y = 'general'
                #print('fname: ',fname)
                try:
                    nums = re.findall(r'\d+', fname)
                    y = int(nums[0])
                except:
                    self.FEEDBACK.reportError(self.tr('Bad-formatted landuse file name: %s') % fname, False)
                    #self.FEEDBACK.reportError(self.tr('Bad-formatted landuse file name:'), fname)

                base_rl = self.loadASC(baseFile, float)
                base_data = np.where(base_rl['data']==base_rl['nodata_value'],np.nan,base_rl['data'])
                filtered_data = base_data*mask_data

                # extent = self.maskExtent(filtered_data)
                # extent = self.calcExtent(extent[0], extent[1], extent[2], extent[3], base_rl['xllcorner'],
                #                          base_rl['yllcorner'],
                #                          base_rl['cellsize'])

                # count
                unique, counts = np.unique(filtered_data[~np.isnan(filtered_data)], return_counts=True)
                res = pd.DataFrame({y: (counts*mask_rl['cellsize']*mask_rl['cellsize'])}, index=unique)
                tableList.append(res)

                # add map to the figure
                handles, labels = self.addMapToPlot(ax, filtered_data, extent,values)
                ax.set_title(str(y))
                #print('labels', labels)
            else:
                ax.axis('off')

        fig.legend(handles, labels,loc=7)

        # join dataframe to only one
        newDf = pd.concat(tableList, axis=1)

        # save to file
        if outFile: fig.savefig(outFile, format='png')

        plt.close(fig)

        return newDf

    def makeReport(self,simFolder,outfile):
        #set default folder
        outImageFolder = self.makeImgFolder(outfile)

        # read idragra file
        idragraFile = os.path.join(simFolder, 'idragra_parameters.txt')
        simPar = self.readIdragraParameters(idragraFile, self.FEEDBACK, self.tr)

        cropcoefFile = os.path.join(simFolder, 'cropcoef.txt')
        cropcoefPar = self.readIdragraParameters(cropcoefFile, self.FEEDBACK, self.tr)

        # set domain file
        geodataPath = os.path.join(simFolder, simPar['inputpath'])
        domainFile = os.path.join(geodataPath, 'domain.asc')

        # set sim output path
        outputPath = os.path.join(simFolder,simPar['outputpath'])

        self.FEEDBACK.setProgress(0.)
        self.FEEDBACK.pushInfo(self.tr('List irrigation units'))

        irrunitsFile = os.path.join(geodataPath, 'irr_units.asc')
        iuRl = self.loadASC(irrunitsFile,int)
        iu_data = iuRl['data']
        iuList = np.unique(iu_data.ravel()).tolist()
        if iuRl['nodata_value'] in iuList: iuList.remove(iuRl['nodata_value'])
        iuList.sort()

        self.FEEDBACK.pushInfo(str(iuList))

        # read landuse table file
        landusePath = os.path.join(simFolder, cropcoefPar['cropinputsfolder'])

        landuseFile = os.path.join(landusePath, 'soil_uses.txt')
        landusePar = self.parseLanduseFile(landuseFile)
        landusePar['new_id']= landusePar['id']
        landusePar.set_index('new_id',inplace=True)

        # read irrigation methods files
        irrmethPath = os.path.join(simFolder, simPar['irrmethpath'])
        irrmethFileList = glob.glob(os.path.join(irrmethPath, '*.txt'))

        irrmethPars = {}
        for irrmethFile in irrmethFileList:
            if os.path.basename(irrmethFile) != 'irrmethods.txt':
                irrmethPars[os.path.basename(irrmethFile)] = self.readIdragraParameters(irrmethFile, self.FEEDBACK,
                                                                                        self.tr)

        irrmethPar = {'id': [], 'name': []}
        for k, v in irrmethPars.items():
            irrmethPar['id'].append(int(v['id']))
            irrmethPar['name'].append(v['irrmeth_name'])

        irrmethPar = pd.DataFrame(irrmethPar)
        irrmethPar['new_id'] = irrmethPar['id']
        irrmethPar.set_index('new_id', inplace=True)

        ### PLOT IRRIGATION UNITS MAP

        irrunits_image = os.path.join(outImageFolder, 'all_irr_units.png')
        self.plotCatMap(irrunits_image, irrunitsFile, domainFile)
        irrunits_image = os.path.relpath(irrunits_image, os.path.dirname(outfile))

        report_contents = """
                            <h3>Irrigation units map</h3>
                                <div>
                                    <div class="image_container">
                                        <img src="%s">
                                    </div>
                                </div>
                            """%irrunits_image

        # loop in each irrigation units
        for i,iu in enumerate(iuList):
            selIuRL = copy.deepcopy(iuRl)
            selIuRL['data'] = np.where(selIuRL['data']==iu,1,np.nan)

            ### MAKE LANDUSE STATITICS
            lu_image = os.path.join(outImageFolder, 'lu_by_year_map_%s.png'%(iu))
            soiluse_table = self.irrUnitsSummary(baseFN=os.path.join(geodataPath,'soiluse*.asc'),
                                                 mask_rl=selIuRL, values=list(landusePar['id']),
                                                 outFile=lu_image)
            lu_image = os.path.relpath(lu_image, os.path.dirname(outfile))

            soiluse_table=pd.concat([landusePar,soiluse_table], axis=1)

            soiluse_table.drop(columns=['cr1', 'cr2'], inplace=True) # delete unused column
            soiluse_table.rename(columns={"cr_name": "Land use"},inplace=True) # rename specific column
            soiluse_table.fillna(0,inplace=True) # replace nan with zeros

            soiluse_table = self.dataframeToHtml(soiluse_table.values.tolist(),
                                                   list(soiluse_table.columns),
                                                   None,
                                                   ['{:.0f}','{:}']+['{:.2f}'] * (len(list(soiluse_table.columns)) -2))

            ### MAKE SOIL STATISTICS

            soilPar1FNList = ['ThetaI_r.asc', 'ThetaI_WP.asc', 'ThetaI_FC.asc', 'ThetaI_sat.asc', 'Ksat_I.asc']
            soilPar2FNList = ['ThetaII_r.asc', 'ThetaII_WP.asc', 'ThetaII_FC.asc', 'ThetaII_sat.asc', 'Ksat_II.asc']

            soilParName = ['Res. (-)', 'WP (-)', 'FC (-)', 'Sat. (-)', 'K sat. (cm/hour)']
            statLabel = ['min', 'mean', 'max']

            first_soil_par_table = self.makeGroupedStats(geodataPath, soilPar1FNList, soilParName, statLabel,irrunitsFile,[iu])
            first_soil_par_table = self.dataframeToHtml(first_soil_par_table.values.tolist(),
                                                        ['id'] + soilParName,
                                                        statLabel,
                                                        ['{:.0f}'] + ['{:.2f}'] * (
                                                                    len(list(first_soil_par_table.columns)) - 1))

            sec_soil_par_table = self.makeGroupedStats(geodataPath, soilPar2FNList, soilParName, statLabel,irrunitsFile,[iu])
            sec_soil_par_table = self.dataframeToHtml(sec_soil_par_table.values.tolist(),
                                                      ['id'] + soilParName,
                                                      statLabel,
                                                      ['{:.0f}'] + ['{:.2f}'] * (
                                                                  len(list(sec_soil_par_table.columns)) - 1))

            soilPar3FNList = ['CapRisePar_b1.asc', 'CapRisePar_b2.asc', 'CapRisePar_b3.asc', 'CapRisePar_b4.asc',
                              'CapRisePar_a3.asc', 'CapRisePar_b1.asc']

            soilParName = ['b1', 'b2', 'b3', 'b4', 'a4', 'a5']
            statLabel = ['min', 'mean', 'max']

            deep_soil_par_table = self.makeGroupedStats(geodataPath, soilPar3FNList, soilParName, statLabel,irrunitsFile,[iu])
            deep_soil_par_table = self.dataframeToHtml(deep_soil_par_table.values.tolist(),
                                                      ['id'] + soilParName,
                                                      statLabel,
                                                      ['{:.0f}'] + ['{:.2f}'] * (
                                                                  len(list(deep_soil_par_table.columns)) - 1))

            soilPar4FNList = ['hydr_group.asc', 'main_txtr.asc']

            soilParName = ['HSG', 'Texture']
            statLabel = ['min', 'mean', 'max']

            other_soil_par_table = self.makeGroupedStats(geodataPath, soilPar4FNList, soilParName, statLabel,irrunitsFile,[iu])
            other_soil_par_table = self.dataframeToHtml(other_soil_par_table.values.tolist(),
                                                        ['id'] + soilParName,
                                                        statLabel,
                                                        ['{:.0f}'] + ['{:.2f}'] * (
                                                                    len(list(other_soil_par_table.columns)) - 1))

            ### MAKE IRRIGATION METHOD STATISTICS
            im_image = os.path.join(outImageFolder, 'im_by_year_map_%s.png'%(iu))
            irrmeth_table = self.irrUnitsSummary(baseFN=os.path.join(geodataPath,'irr_meth*.asc'),
                                                 mask_rl=selIuRL, values=list(irrmethPar['id']),
                                                 outFile=im_image)
            im_image = os.path.relpath(im_image, os.path.dirname(outfile))

            irrmeth_table=pd.concat([irrmethPar,irrmeth_table], axis=1)

            irrmeth_table.fillna(0,inplace=True) # replace nan with zeros

            irrmeth_table = self.dataframeToHtml(irrmeth_table.values.tolist(),
                                                   list(irrmeth_table.columns),
                                                   None,
                                                   ['{:.0f}','{:}']+['{:.2f}'] * (len(list(irrmeth_table.columns)) -2))

            ### ADD WATER FLUXES STATISTICS ###
            self.FEEDBACK.pushInfo(self.tr('Water fluxes processing ...'))

            waterFlux = {
                'prec_tot': self.tr('Cumulative precipitation (mm)'),
                'irr_tot': self.tr('Cumulative irrigation (mm)'),
                'irr_loss': self.tr('Irrigation application losses (mm)'),
                'eva_act_agr': self.tr('Cumulative actual evaporation (mm)'),
                'trasp_act_tot': self.tr('Cumulative actual transpiration (mm)'),
                'run_tot': self.tr('Cumulative runoff (mm)'),
                'flux_tot': self.tr('Net flux to groundwater (mm)'),
            }

            waterFlux_table = self.makeAnnualStats(outputPath, ['????_' + x for x in list(waterFlux.keys())],
                                                   list(waterFlux.values()), statLabel, selIuRL, 1)

            years = waterFlux_table['year'].to_list()

            # make flux bar plot for each year
            temp_png = os.path.join(outImageFolder, 'wat_fluxes_%s.png'%(iu))
            fig, ax = plt.subplots(figsize=(10, 3), constrained_layout=True)
            patches, labels = self.makeFluxBars(ax, waterFlux_table, list(waterFlux.values()),
                                  ['P', 'I', 'L', 'E', 'T', 'R', 'N'],
                                  [1, 1, -1, -1, -1, -1, -1])

            fig.legend(patches, labels, loc=7)
            # save to file
            fig.savefig(temp_png, format='png')
            plt.close(fig)

            wat_fluxes_by_year = os.path.relpath(temp_png, os.path.dirname(outfile))

            waterFlux_table = self.dataframeToHtml(waterFlux_table.values.tolist(),
                                                   ['year'] + list(waterFlux.values()),
                                                   statLabel,
                                                   ['{:.0f}'] + ['{:.2f}'] * (
                                                           len(list(waterFlux_table.columns)) - 1))

            # make flux plot for each period and year
            stepname = 'step'
            if simPar['monthlyflag']:
                stepname = 'month'

            stepWaterFlux = {
                'prec': self.tr('Precipitation (mm)'),
                'irr': self.tr('Irrigation (mm)'),
                'irr_loss': self.tr('Irrigation application losses (mm)'),
                'et_act': self.tr('Actual evapotranspiration (mm)'),
                'runoff': self.tr('Runoff (mm)'),
                'flux2': self.tr('Flux to groundwater (mm)'),
                'caprise': self.tr('Capillary rise (mm)')
            }
            stepWaterLabel = ['P', 'I', 'L', 'ET', 'R', 'F', 'C']
            stepWaterSign = [1, 1, -1, -1, -1, -1, -1]

            if simPar['mode']in [0,'0']:
                stepWaterFlux = {
                    'prec': self.tr('Precipitation (mm)'),
                    'irr_distr': self.tr('Irrigation from collective source (mm)'),
                    'irr_privw': self.tr('Irrigation from private wells (mm)'),
                    'irr_loss': self.tr('Irrigation application losses (mm)'),
                    'et_act': self.tr('Actual evapotranspiration (mm)'),
                    'runoff': self.tr('Runoff (mm)'),
                    'flux2': self.tr('Flux to groundwater (mm)'),
                    'caprise': self.tr('Capillary rise (mm)')
                }
                stepWaterLabel = ['P', 'Ic', 'Ip', 'L', 'ET', 'R', 'F', 'C']
                stepWaterSign = [1, 1, 1, -1, -1, -1, -1, -1]

            noteString = []
            for label,descr in zip(stepWaterLabel,list(stepWaterFlux.values())):
                noteString.append('%s: %s'%(label,descr))

            noteString = ', '.join(noteString)

            temp_png = os.path.join(outImageFolder, 'wat_fluxes_by_step_%s.png'%(iu))
            fig, axs = plt.subplots(len(years), 1,figsize=(10, 3*len(years)), constrained_layout=True)


            if len(years)>1: axsList = axs.flat
            else: axsList = [axs]

            for y,ax in zip(years,axsList):
                stepWaterFlux_table = self.makeAnnualStats(outputPath, ['%s_%s*_'%(y,stepname) + x for x in list(stepWaterFlux.keys())],
                                                       list(stepWaterFlux.values()), statLabel, selIuRL, 1)
                # sort by step num
                stepWaterFlux_table.sort_values(stepname, inplace = True)

                # make flux bar plot for each year
                patches, labels = self.makeFluxBars(ax, stepWaterFlux_table, list(stepWaterFlux.values()),
                                                    stepWaterLabel,
                                                    stepWaterSign,
                                                    bar_w=1.,timeFld=stepname)
                ax.set_title(str(y))

            plt.legend(patches, labels, loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=len(labels))
            # save to file
            fig.savefig(temp_png, format='png')
            plt.close(fig)

            wat_fluxes_by_step = os.path.relpath(temp_png, os.path.dirname(outfile))

            ### ADD WATER MANAGEMENT STATISTICS ###
            self.FEEDBACK.pushInfo(self.tr('Water management processing ...'))

            waterMan = {
                'eva_act_agr': self.tr('Cumulative actual evaporation (mm)'),
                'eva_pot_agr': self.tr('Cumulative potential evaporation (mm)'),
                'trasp_act_tot': self.tr('Cumulative actual transpiration (mm)'),
                'trasp_pot_tot': self.tr('Cumulative potential transpiration (mm)'),
                'irr_loss': self.tr('Irrigation application losses (mm)'),
                'irr_mean': self.tr('Mean irrigation application (mm)'),
                'irr_nr': self.tr('Number of irrigation application (-)'),
                'irr_tot': self.tr('Cumulative irrigation (mm)')
            }
            waterMan_table = self.makeAnnualStats(outputPath, ['????_' + x for x in list(waterMan.keys())],
                                                  list(waterMan.values()), statLabel,
                                                  selIuRL, 1)
            waterMan_table = self.dataframeToHtml(waterMan_table.values.tolist(),
                                                  ['year'] + list(waterMan.values()),
                                                  statLabel,
                                                  ['{:.0f}'] + ['{:.2f}'] * (
                                                          len(list(waterMan_table.columns)) - 1))

            ### ADD PRODUCTION STATISTICS ###
            self.FEEDBACK.pushInfo(self.tr('First crop production processing ...'))

            production1Vars = {
                'biomass_pot_1': self.tr('Potential biomass for the main crop (t/ha)'),
                'yield_act_1': self.tr('Actual yield for the main crop (t/ha)'),
                'yield_pot_1': self.tr('Potential yield for the main crop (t/ha)')
            }

            first_prod_table = self.makeAnnualStats(outputPath, ['????_' + x for x in list(production1Vars.keys())],
                                                    list(production1Vars.values()), statLabel,
                                                    selIuRL, 1)
            first_prod_table = self.dataframeToHtml(first_prod_table.values.tolist(),
                                                    ['year'] + list(production1Vars.values()),
                                                    statLabel,
                                                    ['{:.0f}'] + ['{:.2f}'] * (
                                                            len(list(first_prod_table.columns)) - 1))

            ### ADD PRODUCTION STATISTICS ###
            self.FEEDBACK.pushInfo(self.tr('Second crop production processing ...'))

            production2Vars = {
                'biomass_pot_2': self.tr('Potential biomass for the second crop (t/ha)'),
                'yield_act_2': self.tr('Actual yield for the second crop (t/ha)'),
                'yield_pot_2': self.tr('Potential yield for the second crop (t/ha)')
            }

            sec_prod_table = self.makeAnnualStats(outputPath, ['????_' + x for x in list(production2Vars.keys())],
                                                  list(production2Vars.values()),
                                                  statLabel,
                                                  selIuRL, 1)
            sec_prod_table = self.dataframeToHtml(sec_prod_table.values.tolist(),
                                                  ['year'] + list(production2Vars.values()),
                                                  statLabel,
                                                  ['{:.0f}'] + ['{:.2f}'] * (
                                                          len(list(sec_prod_table.columns)) - 1))


            report_contents += self.writeParsToTemplate(None, {'irr_unit_id': iu,
                                                               'lu_image':lu_image,
                                                              'landuse_table': soiluse_table,
                                                              'soil_first_table': first_soil_par_table,
                                                               'soil_second_table': sec_soil_par_table,
                                                               'soil_deep_table': deep_soil_par_table,
                                                               'soil_hydro_table': other_soil_par_table,
                                                               'im_image': im_image,
                                                              'irrmeth_table': irrmeth_table,
                                                               'annual_fluxes': wat_fluxes_by_year,
                                                               'stepname':stepname,
                                                               'step_fluxes':wat_fluxes_by_step,
                                                               'step_notes':noteString,
                                                               'wbf_table': waterFlux_table,
                                                               'wm_table': waterMan_table,
                                                               'fcp_table': first_prod_table,
                                                               'scp_table': sec_prod_table},
                                                       self.irrunit_template)

            self.FEEDBACK.setProgress(100.*(i+1)/len(iuList))

        ### BUILD MAIN TOC
        #mainToc = mainItem.to_html()
        mainToc = self.makeToc(report_contents)

        ### WRITE TO FILE ###
        self.writeParsToTemplate(outfile, {'sub_title': self.tr(' - Irrigation units results'),
                                      'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'sim_path':simFolder,
                                      'report_toc': mainToc,
                                      'report_body': report_contents},
                               self.index_template)

        self.FEEDBACK.setProgress(100.)

        return outfile


if __name__ == '__main__':
    simFolder=r'C:\examples\ex_report_SIM'
    outputFile = 'C:/examples/test_img/test_irrigation_units.html'
    RB = IrrunitTotalsReportBuilder()
    outfile = RB.makeReport(simFolder,outputFile)
    print(outfile)
