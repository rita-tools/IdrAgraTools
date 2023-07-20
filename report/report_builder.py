import glob
import os

import numpy as np
import pandas as pd
import re

import matplotlib

from report.toc_item import TocItem

matplotlib.use('Agg')

from datetime import datetime,timedelta

# import as module
from report.my_progress import MyProgress

class ReportBuilder():
    """
       This class represents object to use for report building
    """

    def __init__(self,feedback = None, tr = None):
        """
        Initialize the report builder object
        Parameters:
            feedback = an object that manage messagge and progression (see my_progress for example)
            tr = a function that makes string translation. if None, the same string is returned
        """
        if not feedback:self.FEEDBACK = MyProgress()
        else: self.FEEDBACK = feedback

        if not tr: self.tr = lambda x: x
        else: self.tr = tr

        self.rb_dir = os.path.dirname(__file__)

        self.index_template = os.path.join(self.rb_dir, 'default', 'index_report.html')
        self.sim_template = os.path.join(self.rb_dir, 'default', 'simulation_report.html')

        # these properties are for future developments
        self.name = ''
        self.description = ''

    def set_title(self, name):
        """
        Set report name
        """
        self.name = str(name)

    def set_description(self, description):
        """
        Set report description
        """
        self.description = str(description)

    def replace_values_by_list(self, a, oldVals, newVals):
        """
        Replace values contained in val_old with those contained in val_new
        """
        #a_new = np.array(a,copy=True)
        for old,new in zip(oldVals,newVals):
            np.place(a, a == old, new)

        return a

    def maskExtent(self,maskData):
        """
        Get the extent as cells coordinates of a 2d array mask (1-value area)
        """
        nrows,ncols = maskData.shape
        rindex = []
        cindex = []
        for r in range(nrows):
            cindex.append(list(range(ncols)))

        for c in range(ncols):
            rindex.append(list(range(nrows-1,-1,-1)))

        rindex = np.array(rindex)
        cindex = np.array(cindex)

        rindex = np.transpose(rindex)

        rindex_masked = rindex*maskData
        cindex_masked = cindex * maskData

        cmin = np.nanmin(cindex_masked)
        cmax = np.nanmax(cindex_masked)

        rmin = np.nanmin(rindex_masked)
        rmax = np.nanmax(rindex_masked)

        return (cmin,cmax,rmin,rmax)

    def calcExtent(self,cmin,cmax,rmin,rmax,xll_ref,yll_ref,cellsize):
       """
       Calculate extents in geographic projected coordinates from cells coordinates
       """
       xll = xll_ref+cmin*cellsize
       xlr = xll_ref + (cmax +1)* cellsize
       yll = yll_ref+rmin*cellsize
       yur = yll_ref + (rmax+1) * cellsize

       return (xll, xlr, yll, yur)



    def dataframeToHtml(self, df, header, subHeader=None, formatList=None, tableClass='statistics', oddClass='odd'):
        """
        Convert a pandas dataframe to html table
        More advanced respected to simple pandas.DataFrame.to_html method
        """
        nMains = len(header)
        if subHeader:
            nsubs = len(subHeader)
            subHeader =  subHeader * (nMains - 1)
            nMains = len(subHeader)

        if not formatList:
            formatList = ['{:}'] * nMains

        text = '<table class="' + tableClass + '">\n'
        # add header
        text += '<thead>\n'
        if subHeader:
            text += '<tr>'
            text += '<th rowspan="2">' + header[0] + '</th>' + ('<th colspan="%s">' % nsubs) + (
                        '</th><th colspan="%s">' % nsubs).join(header[1:]) + '</th>'
            text += '</tr><tr>'
            text += '<th>' + '</th><th>'.join(subHeader) + '</th>'
            text += '</tr>\n'
        else:
            text += '<tr>'
            text += '<th>' + '</th><th>'.join([str(x) for x in header]) + '</th>'
            text += '</tr>\n'

        text += '</thead>\n'
        text += '<tbody>\n'
        odd = True
        # print('type df',type(df))
        for v in df:
            # add values
            # print('v',v)

            if odd:
                text += '<tr class="' + oddClass + '">'
                odd = False
            else:
                text += '<tr>'
                odd = True
            text += '\t<td>' + '</td><td>'.join([formatList[i].format(x) for i, x in enumerate(v)]) + '</td>\n'

            text += '</tr>'

        text += '</tbody>\n'
        text += '</table>\n'

        return text

    def loadASC(self, filename, val_type=int):
        """
        Open and ascii raster file as dictionary
        The header structure should be:
            ncols 4
            nrows 3
            xllcorner 520197.5534
            yllcorner 5018050.0
            cellsize 250.0
            nodata_value -9

        Note that data are stored in numpy 2d array of type val_type
        """

        res = {'ncols': 0, 'nrows': 0, 'xllcorner': 0, 'yllcorner': 0, 'cellsize': 0, 'nodata_value': 0,
               'data': np.array([])}

        if not os.path.exists(filename):
            self.FEEDBACK.reportError(self.tr('Unknown file: %s'%filename))
            return None

        with open(filename) as f:
            for i in range(0, 6):
                line = f.readline()
                toks = line.split()
                k = toks[0].strip().lower()
                v = toks[1].strip()
                #print(filename,k,v)
                res[k] = float(v)

        # floats (left, right, bottom, top), optional
        xll = res['xllcorner']
        xlr = res['xllcorner'] + res['ncols'] * res['cellsize']
        yll = res['yllcorner']
        yur = res['yllcorner'] + res['nrows'] * res['cellsize']

        res['xll'] = xll
        res['xlr'] = xlr
        res['yll'] = yll
        res['yur'] = yur

        res['width'] = xlr - xll
        res['height'] = yur - yll

        res['extent'] = (xll, xlr, yll, yur)

        res['data'] = np.loadtxt(filename, dtype=val_type, skiprows=6)
        res['nodata_value'] = val_type(res['nodata_value'])
        return res

    def readIdragraParameters(self,idragraFile, feedback, tr):
        """
        Read (most of) idragra parameters files
        """
        pars = {}
        rows = []

        try:
            f = open(idragraFile, 'r')
            for l in f:
                l = l.replace('\t', ' ')
                # l = l.replace(' ', '')
                l = l.rstrip('\n')  # remove return carriage
                com = l.find('#')
                if com < 0: com = len(l)

                comment = l[com + 1:]
                l = l[:com]  # remove comment part if exists

                if 'Irrigation method:' in comment:
                    pars['irrmeth_name'] = comment.replace('Irrigation method:', '').strip()

                l = l.split('=')
                if len(l) == 2:
                    parName = l[0].lower().strip()
                    l[1] = l[1].strip()
                    # print(parName)
                    if parName == 'inputpath':
                        pars['inputpath'] = l[1]
                    elif parName == 'outputpath':
                        pars['outputpath'] = l[1]
                    elif parName == 'monthlyflag':
                        if l[1] == 'F':
                            pars['monthlyflag'] = False
                        else:
                            pars['monthlyflag'] = True
                    elif parName == 'capillaryflag':
                        if l[1] == 'F':
                            pars['capillaryflag'] = False
                        else:
                            pars['capillaryflag'] = True
                    elif parName == 'startdate':
                        pars['startdate'] = int(l[1])
                    elif parName == 'enddate':
                        pars['enddate'] = int(l[1])
                    elif parName == 'deltadate':
                        pars['deltadate'] = int(l[1])
                    else:
                        # all the other cases
                        pars[parName] = l[1]

                if len(l) == 1:
                    # add as table
                    if l[0]: rows.append(l[0].strip())

            # parse table row
            table = {}
            header = []
            for i, r in enumerate(rows):
                toks = r.split(' ')
                if i == 0:
                    header = toks
                    for t in toks:
                        table[t] = []
                else:
                    for c, t in enumerate(toks):
                        if t.lower() == 'endtable': break

                        if t == '*':
                            table[header[c]].append(np.nan)
                        else:
                            table[header[c]].append(float(t))

            table = pd.DataFrame(table)
            pars['table'] = table

        except Exception as e:
            feedback.reportError(tr('Cannot parse %s because %s') %
                                 (idragraFile, str(e)), True)
        finally:
            if f: f.close()

        return pars

    def writeParsToTemplate(self,outfile, parsDict, templateName):
        """
        Replace in a template file the contents assigned to a specific key in the provided dictionary
        """
        content = ''
        try:
            templateFileName = templateName
            if not os.path.exists(templateName):
                templateFileName = os.path.join(os.path.dirname(__file__), '..', 'templates', templateName)

            # open template file
            f = open(templateFileName)
            template = f.read()
            f.close()
            # replace value from the dictionary
            for k, v in parsDict.items():
                template = template.replace('[%' + k + '%]', str(v))
            content = template
            # save file
            if outfile:
                f = open(outfile, "w", encoding='UTF8')
                f.write(content)
                f.close()
        except Exception as e:
            self.FEEDBACK.reportError(str(e))

        return content

    def makeImgFolder(self,outfile):
        """
        Set the image folder for html output
        """
        # set default folder
        outImageFolder = outfile[:-5] + '_img'
        if not os.path.exists(outImageFolder):
            os.mkdir(outImageFolder)
        else:
            # delete all files inside
            files = glob.glob(os.path.join(outImageFolder,'*.*'))
            for f in files:
                try: os.remove(f)
                except: self.FEEDBACK.reportError(self.tr('Unable to remove file %s')%f)

        return outImageFolder

    def makeToc(self,text):
        """
        Make a table of cointents, ToC, from an html string
        """
        searchExp = '<a id="(.*)"><h[0-9]+.*>(.*)</h([0-9]+)></a>'
        result = re.findall(searchExp, text)
        root = TocItem('','')
        for r in result:
            subItem = TocItem(r[0], r[1])
            root.addSubItem(subItem,int(r[2]))

        return root.to_html()

    def makeReport(self,simFolder,outfile):
        """
        Make an html report file with tables and images
        It should be overloaded by inheriting class
        """
        outImageFolder = self.makeImgFolder(outfile)
        # read idragra file
        ### WRITE TO FILE ###
        self.writeParsToTemplate(outfile, {'sub_title': self.tr(' - example'),
                                           'current_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                           'sim_path': simFolder,
                                           'report_toc': 'Insert your table of content here',
                                           'report_body': 'Insert your body content here'},
                            self.index_template)

        self.FEEDBACK.setProgress(100.)

        return outfile


if __name__ == '__main__':
    # simFolder='C:/examples/demo/demo_import3_SIM'
    # outputFile = 'C:/examples/test_img/test_empty.html'
    # RB = ReportBuilder()
    # outfile = RB.makeReport(simFolder,outputFile)
    # # print(outfile)
    # maskData = np.array([[np.nan,np.nan,np.nan,np.nan,],
    #             [np.nan,1,1,np.nan],
    #             [np.nan,1,np.nan,np.nan],
    #             [np.nan,1,np.nan,np.nan],
    #             [1,1,1,np.nan]])
    #
    # RB = ReportBuilder()
    # res = RB.maskExtent(maskData)
    #
    # print(maskData)
    #
    # print(res)
    fileName = r'C:\examples\test_img\test_irrigation_units.html'
    RB = ReportBuilder()
    with open(fileName) as f:
        lines = f.readlines()

    text = ''.join(lines)
    res = RB.makeToc(text)
    print('res',res)


