import glob
import math
import os
from copy import deepcopy

import numpy as np
import pandas as pd
import re

import matplotlib
from matplotlib.sankey import Sankey

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import cm
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec

from datetime import datetime,timedelta

# import as module
from report.overview_report_builder import OverviewReportBuilder

class AnnualTotalsReportBuilder(OverviewReportBuilder):

    def __init__(self,feedback = None, tr = None):
        super().__init__(feedback, tr)

        self.annual_template = os.path.join(self.rb_dir, 'default', 'annual_report.html')

        self.statFun= {'min':np.nanmin,'max':np.nanmax,'mean':np.nanmean,
                       'std':np.nanstd, 'var':np.nanvar,
                       'sum':np.nansum,'median':np.nanmedian}

    def makeAnnualStats(self,outFolder,parFNList,parName, statList=['min', 'mean', 'max'], maskIdFN = 'pathTo/domain.asc',maskId = 1):
        if isinstance(maskIdFN,str):
            maskRl = self.loadASC(maskIdFN)
        else:
            maskRl = maskIdFN

        mask_data = np.where(maskRl['data'] == maskRl['nodata_value'], np.nan, maskRl['data'])
        mask_data = np.where(mask_data[:] != maskId, np.nan, mask_data[:] * 0 + 1)

        # setup res table
        res = {'year':[],'month':[],'step':[]}

        for i in parName:
            for s in statList: res['%s_%s'%(i,s)]= []

        for i,parFN in enumerate(parFNList):
            # match only if start with four characters
            outFileList = glob.glob(os.path.join(outFolder, parFN + '.asc'))
            outFileList.sort()
            # reset year list
            res['year']=[]
            res['month']=[]
            res['step']=[]

            for outFile in outFileList:
                month = 0  # months range from 1 to 12
                step = 0  # always greater than 0

                # get year
                try:
                    nums = re.findall(r'\d+', os.path.basename(outFile))
                    y = int(nums[0])
                    if '_month' in os.path.basename(outFile):
                        month = int(nums[1])
                    if '_step' in os.path.basename(outFile):
                        step = int(nums[1])

                except:
                    self.FEEDBACK.reportError(self.tr('Bad-formatted landuse file name:'), outFile)

                #print(outFile,y,month,step)

                res['year'].append(y)
                res['month'].append(month)
                res['step'].append(step)

                # compute stats
                parRl = self.loadASC(outFile, np.float)
                parData = np.where(parRl['data'] == parRl['nodata_value'], np.nan, parRl['data'])
                filteredParData = np.where(mask_data[:] != 1., np.nan, parData)
                nan_flag = np.isnan(filteredParData).all()
                for stat in statList:
                    aVal = np.nan
                    if not nan_flag: aVal = self.statFun[stat](filteredParData)

                    res['%s_%s' % (parName[i], stat)].append(aVal)

        #print(res)
        # remove empty month and step
        if len(res['month']) == 0:
            del res['month']
        elif max(res['month'])==0:
            del res['month']
        else:
            pass
        if len(res['step']) == 0:
            del res['step']
        elif max(res['step']) == 0:
            del res['step']

        #print('res',res)

        return pd.DataFrame(res)

    def addFluxChart(self, ax, flows=[25, 0, 60, -10, -20, -5, -15, -10, -40],
                     labels=['', '', '', 'First', 'Second', 'Third', 'Fourth',
                             'Fifth', 'Hurray!'],
                     orientations=[-1, 1, 0, 1, 1, 1, -1, -1, 0],
                     pathlengths=[0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25,
                                  0.25],
                     patchlabel="Widget\nA"):

        ax.axis('off')

        sankey = Sankey(ax=ax, scale=0.01, offset=2, head_angle=160, format='%.0f', unit='', gap=0.1)
        sankey.add(flows=flows, labels=labels, orientations=orientations, pathlengths=pathlengths,
                   patchlabel=patchlabel,edgecolor = 'skyblue', facecolor = 'skyblue')  # Arguments to matplotlib.patches.PathPatch

        # sankey = Sankey(ax=self.ax, flows=flows, labels=labels, orientations=orientations)
        diagrams = sankey.finish()

        diagrams[0].texts[-1].set_color('r')
        diagrams[0].text.set_fontweight('bold')


        # xmin,xmax = ax.get_xlim()
        # ymin, ymax = ax.get_ylim()
        #
        # w = xmax-xmin
        # h = ymax-ymin
        #
        # ax.set_xlim(xmin-0.1*w,xmax+0.1*w)
        # ax.set_ylim(ymin - 0.1 * h, ymax + 0.1 * h)

    def makeFluxPlot(self,outFile, dataToPlot, labels, alias,signs, orientations,pathlengths):
        nPlot = len(dataToPlot.index)
        nRows = math.ceil(nPlot/2)
        nCols = 2
        if nPlot==1: nCols=1
        # print('nPlot',nPlot,'nRows',nRows,'nCols',nCols)
        fig, axs = plt.subplots(nRows, nCols, figsize=(10,3.5*nRows))#, constrained_layout=True)

        if nPlot > 1:
            axsList = axs.flat
        else:
            axsList = [axs]

        for n in range(nPlot):
            flows = []
            row = dataToPlot.iloc[[n]]
            for label,sign in zip(labels,signs):
                #print('row val',float(row[label+'_mean']))
                flows.append(float(row[label+'_mean'])*sign)

            self.addFluxChart(axsList[n],flows,alias,orientations,pathlengths,'year\n%s'%int(row['year']))

        # save to file
        fig.savefig(outFile, format='png')
        plt.close(fig)

    def makeFluxBars(self,ax, dataToPlot, labels, aliases,signs,bar_w=0.35,timeFld = 'year'):
        nRows = len(dataToPlot.index)
        barList =[]

        pos_flows = np.array([0.]*nRows)
        neg_flows = np.array([0.] * nRows)

        for label, sign, alias in zip(labels, signs,aliases):
            flows = []
            time_step = []
            for n in range(nRows):
                row = dataToPlot.iloc[[n]]
                #print('row val',float(row[label+'_mean']))
                flows.append(float(row[label + '_mean']) * sign)
                time_step.append(str(int(row[timeFld])))

            if sign>0:
                bar = ax.bar(range(nRows), flows, bar_w, bottom=pos_flows, label=alias)
                barList.append(bar)
                pos_flows+=np.array(flows)
            else:
                bar = ax.bar(range(nRows), flows, bar_w, bottom=neg_flows, label=alias)
                barList.append(bar)
                neg_flows += np.array(flows)

            # add junction lines
            if bar_w<1.:
                i=0
                while i<(len(time_step)-1):
                    xmin = i+0.5*bar_w
                    xmax = (i+1) - 0.5*bar_w
                    if sign>0:
                        ymin = pos_flows[i]
                        ymax = pos_flows[i + 1]
                    else:
                        ymin = neg_flows[i]
                        ymax = neg_flows[i+1]

                    l = mlines.Line2D([xmin, xmax], [ymin, ymax],color=bar.patches[0].get_facecolor())
                    ax.add_line(l)
                    i+=1

        # customize plot
        ax.hlines(0,0.-bar_w,(nRows-1)+bar_w)
        ax.set_xlim([-bar_w,(nRows-1)+bar_w])

        # draw maximum 20+1 labels
        numTs = len(time_step)
        skip = int(numTs/20)
        skip = max(skip,1)

        new_time_step = deepcopy(time_step)
        for i,ts in enumerate(time_step):
            f1,f2 = divmod(i, skip)
            if f2>0:
                new_time_step[i] =''

        ax.set_xticks(range(nRows))
        ax.set_xticklabels(new_time_step)

        ylim = ax.get_ylim()
        max_ylim = max([abs(y) for y in ylim])
        ax.set_ylim([-max_ylim,max_ylim])
        ax.set_ylabel(self.tr('Volume per unit area (mm)'))

        return barList, aliases


    def makeReport(self,simFolder,outfile):
        #set default folder
        outImageFolder = self.makeImgFolder(outfile)

        # read idragra file
        idragraFile = os.path.join(simFolder, 'idragra_parameters.txt')
        simPar = self.readIdragraParameters(idragraFile, self.FEEDBACK, self.tr)

        # set domain file
        geodataPath = os.path.join(simFolder, simPar['inputpath'])
        domainFile = os.path.join(geodataPath, 'domain.asc')

        # set sim output path
        outputPath = os.path.join(simFolder,simPar['outputpath'])

        # annual report
        report_contents = ""

        statLabel = ['min', 'mean', 'std','max']

        self.FEEDBACK.setProgress(0.)

        ### ADD WATER FLUXES STATISTICS ###
        self.FEEDBACK.pushInfo(self.tr('Water fluxes processing ...'))

        waterFlux = {
            'prec_tot': self.tr('Cumulative precipitation (mm)'),
            'eva_act_agr': self.tr('Cumulative actual evaporation (mm)'),
            'trasp_act_tot': self.tr('Cumulative actual transpiration (mm)'),
            'irr_tot': self.tr('Cumulative irrigation (mm)'),
            'irr_loss': self.tr('Irrigation application losses (mm)'),
            'run_tot':self.tr('Cumulative runoff (mm)'),
            'flux_tot': self.tr('Net flux to groundwater (mm)'),
        }

        waterFlux_table = self.makeAnnualStats(outputPath, ['????_'+x for x in list(waterFlux.keys())],
                                               list(waterFlux.values()), statLabel,domainFile,1)

        temp_png = os.path.join(outImageFolder, 'wat_fluxes.png')
        self.makeFluxPlot(temp_png, waterFlux_table, list(waterFlux.values()),['P','E','T','I','L','R','N'],
                          [1,-1,-1,1,-1,-1,-1], [1, 1, 1, 1, 1, 0, -1],
                          [0.25, 0.25, 0.25, 2., 0.5, 2., 2.])

        temp_png_rel = os.path.relpath(temp_png, os.path.dirname(outfile))

        waterFlux_table = self.dataframeToHtml(waterFlux_table.values.tolist(),
                                                    ['year'] + list(waterFlux.values()),
                                                    statLabel,
                                                    ['{:.0f}'] + ['{:.2f}'] * (
                                                                len(list(waterFlux_table.columns)) - 1))

        self.FEEDBACK.setProgress(30.)

        ### ADD WATER MANAGEMENT STATISTICS ###
        self.FEEDBACK.pushInfo(self.tr('Meteo management processing ...'))

        waterMan = {
            'eva_act_agr': self.tr('Cumulative actual evaporation (mm)'),
            'eva_pot_agr': self.tr('Cumulative potential evaporation (mm)'),
            'trasp_act_tot': self.tr('Cumulative actual transpiration (mm)'),
            'trasp_pot_tot': self.tr('Cumulative potential transpiration (mm)'),
            'irr_loss':self.tr('Irrigation application losses (mm)'),
            'irr_mean':self.tr('Mean irrigation application (mm)'),
            'irr_nr':self.tr('Number of irrigation application (-)'),
            'irr_tot':self.tr('Cumulative irrigation (mm)')
        }
        waterMan_table = self.makeAnnualStats(outputPath,['????_'+x for x in  list(waterMan.keys())], list(waterMan.values()), statLabel,
                                               domainFile, 1)
        waterMan_table = self.dataframeToHtml(waterMan_table.values.tolist(),
                                               ['year'] + list(waterMan.values()),
                                               statLabel,
                                               ['{:.0f}'] + ['{:.2f}'] * (
                                                       len(list(waterMan_table.columns)) - 1))



        self.FEEDBACK.setProgress(60.)

        ### ADD PRODUCTION STATISTICS ###
        self.FEEDBACK.pushInfo(self.tr('First crop production processing ...'))

        production1Vars = {
            'biomass_pot_1': self.tr('Potential biomass for the main crop (t/ha)'),
            'yield_act_1': self.tr('Actual yield for the main crop (t/ha)'),
            'yield_pot_1': self.tr('Potential yield for the main crop (t/ha)')
        }

        first_prod_table = self.makeAnnualStats(outputPath,['????_'+x for x in  list(production1Vars.keys())], list(production1Vars.values()), statLabel,
                                              domainFile, 1)
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

        sec_prod_table = self.makeAnnualStats(outputPath,['????_'+x for x in  list(production2Vars.keys())], list(production2Vars.values()),
                                          statLabel,
                                          domainFile, 1)
        sec_prod_table = self.dataframeToHtml(sec_prod_table.values.tolist(),
                                          ['year'] + list(production2Vars.values()),
                                          statLabel,
                                          ['{:.0f}'] + ['{:.2f}'] * (
                                                  len(list(sec_prod_table.columns)) - 1))


        self.FEEDBACK.setProgress(90.)

        report_contents = self.writeParsToTemplate(None, {'annual_fluxes': temp_png_rel,
                                                          'wbf_table': waterFlux_table,
                                                          'wm_table':waterMan_table,
                                                          'fcp_table':first_prod_table,
                                                          'scp_table':sec_prod_table},
                                                    self.annual_template)

        # BUILD MAIN TOC
        mainToc = self.makeToc(report_contents)

        ### WRITE TO FILE ###
        self.writeParsToTemplate(outfile, {'sub_title': self.tr(' - Annual results'),
                                      'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                      'sim_path':simFolder,
                                      'report_toc': mainToc,
                                      'report_body': report_contents},
                               self.index_template)

        self.FEEDBACK.setProgress(100.)

        return outfile


if __name__ == '__main__':
    simFolder=r'C:\examples\ex_report_SIM'
    outputFile = 'C:/examples/test_img/test_annual.html'
    RB = AnnualTotalsReportBuilder()
    outfile = RB.makeReport(simFolder,outputFile)
    print(outfile)
