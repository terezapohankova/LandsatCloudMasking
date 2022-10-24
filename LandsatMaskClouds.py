# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterVectorLayer
                       )
from qgis import processing
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
import os
import time
import shutil
from osgeo import gdal
class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):

    INPUT_FOLDER = 'INPUT_FOLDER'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        return 'landsatmaskcloud'

    def displayName(self):
        return self.tr('Cloud Mask - Landsat')

    def group(self):
        return self.tr('Example scripts')

    def groupId(self):
        return 'examplescripts'

    def shortHelpString(self):
        """
        Creates a simple cloudless bands of Landsat satellite data using r.mask and fillNA. 
        """
        return self.tr("Example algorithm short description")
        
    def initAlgorithm(self, config=None):

        self.addParameter(QgsProcessingParameterFile(self.INPUT_FOLDER, self.tr('Folder with Landsat images containing unzipped satellite bundles'), behavior=QgsProcessingParameterFile.Folder, defaultValue = ''))
        
    
    def processAlgorithm(self, parameters, context, feedback):
        self.parameters = parameters
        self.context = context
        self.feedback = feedback
        

        files_in_dirs = []
        
        #create a list with files in input folder
        for root, dirs, files in os.walk(self.parameters['INPUT_FOLDER']):
            if not dirs and files:
                files_in_dirs.append([os.path.join(root,file) for file in files])
       
                
        
        for bands in files_in_dirs:
            # get each band containing a cloud information (QA_PIXEL)
            QA_PIXEL = [cloudmask for cloudmask in bands if cloudmask.endswith('QA_PIXEL.TIF')] 
            
            #if WA_PIXEL exists then 
            if QA_PIXEL:
                for band in bands: 
                    # for bands that are NOT QA_PIXEL and are TIF bands
                    if band != QA_PIXEL[0] and 'B' in band and band.endswith('.TIF'): 
                        
                        # get name of band
                        maskedBandName = os.path.basename(band)
                        
                        #check if folder for output data exists, if it doe snot, create it
                        # create path to the output file
                        OUT_MASKED_FOLDER = os.path.join(os.path.join(parameters['INPUT_FOLDER'],'MASKED', os.path.basename(band.split('/')[-1][0:40]))) 
                        outputFile = os.path.join(OUT_MASKED_FOLDER , maskedBandName)
                        os.makedirs(OUT_MASKED_FOLDER,exist_ok = True)
                        
                        # run masking from grassGIS
                        outputs = {}
                            # r.mask.rast
                        alg_params = {
                            '-i': True,
                            'GRASS_RASTER_FORMAT_META': '',
                            'GRASS_RASTER_FORMAT_OPT': '',
                            'GRASS_REGION_CELLSIZE_PARAMETER': 0,
                            'GRASS_REGION_PARAMETER': None,
                            'input': band,
                            'maskcats': '22280 thru 55052',
                            'raster': QA_PIXEL[0],
                            'output': outputFile
                        }
                        outputs['Rmaskrast'] = processing.run('grass7:r.mask.rast', alg_params)
                        
                        if outputs['Rmaskrast']:
                            self.feedback.pushInfo(str(f'[SUCESS] The layer {band} has been masked'))
                        else:
                            self.feedback.pushInfo(str(f'[ERROR] The layer {band} has not been masked'))
                        
                        # Fill nodata
                        alg_params = {
                            'BAND': 1,
                            'DISTANCE': 200,
                            'EXTRA': '',
                            'INPUT': outputs['Rmaskrast']['output'],
                            'ITERATIONS': 4,
                            'MASK_LAYER': None,
                            'NO_MASK': False,
                            'OPTIONS': '',
                            'OUTPUT': outputFile
                        }
                        process_fill = processing.run('gdal:fillnodata', alg_params)
                                                
                        if process_fill:
                            self.feedback.pushInfo(str(f'[SUCESS] The layer {band} has been filled'))
                        else:
                            self.feedback.pushInfo(str(f'[ERROR] The layer {band} has not been filled'))
                    
                    #if bands in subdirectories are other than TIF, copy them
                    if not band.endswith('.TIF'):
                
                        
                        OUT_MASKED_FOLDER = os.path.join(os.path.join(parameters['INPUT_FOLDER'],'MASKED', os.path.basename(band.split('/')[-1][0:40]))) 
                        os.makedirs(OUT_MASKED_FOLDER,exist_ok = True)
                        shutil.copy2(os.path.abspath(band), OUT_MASKED_FOLDER)
                        self.feedback.pushInfo(f'[SUCESS] The metadata for {band} has been copied')

        return {}
