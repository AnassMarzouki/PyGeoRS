from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import *
from qgis import *
from PyQt5.QtWidgets import *


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .PyGeoRS_dialog import PyGeoRSDialog
import os.path

# Import pushbuttons
from PyQt5.QtWidgets import QPushButton, QScrollArea, QListWidgetItem
from PyQt5.QtCore import pyqtSlot, QThread, Qt, QModelIndex

import itertools
from osgeo import gdal
#import pykml

import rasterio
import numpy as np
import os
import tarfile

from qgis.PyQt import QtWidgets, uic
from qgis.core import (QgsRasterLayer)
from qgis.core import (QgsVectorLayer)

import sys

from PyQt5.QtGui import QIcon, QTextCursor
from PyQt5 import QtWidgets, QtGui, uic, QtCore

class RSFunctions:
    def __init__(self, dlg):
        self.dlg = dlg
        self.selected_index = None
        self.extract_path = None #make this file callable from anywhere in the code
        self.MTL_path = None
        self.destfile = None
        self.outputs_folder = None
        self.output_path = None
        self.input_is_tif = None
        self.red_fcc = None
        self.green_fcc = None 
        self.blue_fcc = None
        self.input_path = None
        self.br_output_path = None
        
        self.r = 1
        self.g = 1
        self.b = 1
        
        self.r1 = 1
        self.r2 = 1
        self.b1 = 1
        self.b2 = 1
        self.g1 = 1
        self.g2 = 1

        self.L1TP = None 
        self.L2SP = None 

        self.working_path = None
        self.folder_set = False

        self.checkboxes = [self.dlg.pB_select_output_folder, self.dlg.cB_extract_archive, self.dlg.cB_layer_stacking, self.dlg.cB_calculate_all_br,
        self.dlg.radioButton, self.dlg.cB_dn_to_toa, self.dlg.cB_calculate_oif, 
        self.dlg.cB_calculate_pca, self.dlg.cB_calculate_mnf, self.dlg.cB_calculate_ica,
        self.dlg.cB_calculate_index, self.dlg.cB_calculate_br, self.dlg.cB_generate_fcc, self.dlg.cB_abrams, self.dlg.cB_sabins, self.dlg.cB_kaufmann]

        self.comboboxes = [self.dlg.comboBox, self.dlg.comboBox_2, self.dlg.comboBox_3,
        self.dlg.comboBox_4, self.dlg.comboBox_4, self.dlg.comboBox_6, 
        self.dlg.comboBox_7, self.dlg.comboBox_7, self.dlg.comboBox_8, self.dlg.comboBox_9,
        self.dlg.comboBox_10, self.dlg.comboBox_11]

        self.pushbuttons = [self.dlg.pB_load_mtl, self.dlg.pB_proceed]

    def welcome_msg(self):
        self.print_to_scroll_area('<b> Welcome to PyGeoRS </b>')
        self.print_to_scroll_area('Start by loading your Landsat 8 / 9 image and set an output folder')

    def select_output_folder(self):
        #self.working_path = working_path
        self.dlg.lineEdit.clear()
        self.working_path = str(QFileDialog.getExistingDirectory(self.dlg, "Select Directory"))
        if self.working_path:
            self.dlg.lineEdit.setText(f"{self.working_path}")
            self.print_to_scroll_area(f"<span style='color:blue;'>{self.working_path}</span> is set as a default output folder !")

            self.enable_all_tasks()
            self.dlg.pB_load_mtl.hide()

            if self.landsat_file[0].endswith(".tar.gz") or self.landsat_file[0].endswith(".tar"):
                self.dlg.cB_extract_archive.setChecked(True) #Force Extract
                self.dlg.cB_extract_archive.setEnabled(False) # Disable Extract
                self.dlg.cB_layer_stacking.setEnabled(False)
                self.dlg.cB_layer_stacking.setChecked(True) #Force LayerStacking
                #self.dlg.pB_load_mtl.hide()

            if self.landsat_file[0].endswith(".tif"):
                self.dlg.cB_extract_archive.setChecked(False)
                self.dlg.cB_extract_archive.setEnabled(False) #Disable archive
                self.dlg.cB_layer_stacking.setChecked(False) #Unchek LS
                self.dlg.cB_layer_stacking.setEnabled(False) #Disable layerstack


    def load_landsat_data(self): #WORKING OK - FF#
        import tarfile
        search_string_LC8 = 'SPACECRAFT_ID = "LANDSAT_8"'
        search_string_LC9 = 'SPACECRAFT_ID = "LANDSAT_9"'

        L1TP_tag = 'DATA_TYPE = "L1TP"'
        L2SP_tag = 'PROCESSING_LEVEL = "L2SP"'

        # Load a file
        self.landsat_file = QFileDialog.getOpenFileName(self.dlg, 'Open file', 'c:\\', "Landsat data (*.tar.gz  *.tar *.tif);;All Files (*)")
        self.tarfile_isvalid = False
        self.tiffile_isvalid = False

        self.print_to_scroll_area('Reading file. Please wait ..')
        QApplication.processEvents()
        #Check if input file ends with tar.gz or tif



        if not (self.landsat_file[0].endswith(".tar.gz") or self.landsat_file[0].endswith(".tif") or self.landsat_file[0].endswith(".tar")):
            self.print_to_scroll_area('File not supported ! Only .tar.gz / tar & .tif Landsat 8 and 9 files are supported')

        self.loaded_file_is_archive = False
        if self.landsat_file[0].endswith(".tar.gz") or self.landsat_file[0].endswith(".tar"):
                #Check if the input file is a Landsat 8 image
                
                tar_file_name = self.landsat_file[0]

                compression_format = "r:gz" if self.landsat_file[0].endswith(".tar.gz") else "r:"

                try:
                    # Open the tar.gz file
                    with tarfile.open(tar_file_name, compression_format) as tar:
                        total_files = len(tar.getmembers())
                        self.dlg.progressBar.setValue(0)
                        # Iterate through the members (files) in the tar.gz archive
                        for i, member in enumerate(tar.getmembers()):
                            # Check if the member is a .txt file ending with _MTL.txt
                            if member.isfile() and member.name.endswith('_MTL.txt'):
                                mtl_file = tar.extractfile(member)
                                mtl_content = mtl_file.read().decode('utf-8')

                                # Extract the file content
                                if search_string_LC8 in mtl_content:
                                    landsat_label = 'Landsat 8'

                                    self.dlg.pB_select_output_folder.setEnabled(True)
                                elif search_string_LC9 in mtl_content:
                                    landsat_label = 'Landsat 9'
                                    self.dlg.pB_select_output_folder.setEnabled(True)
                            
                                else:
                                    landsat_label = None

                                processing_level = None

                                if landsat_label:
                                    if L1TP_tag in mtl_content:
                                        self.L1TP = True
                                        processing_level = 'L1TP'
                                    elif L2SP_tag in mtl_content:
                                        self.L2SP = True
                                        processing_level = 'L2SP'

                                if landsat_label and processing_level:
                                    self.print_to_scroll_area(f'{landsat_label} file loaded successfully, processing level = <b>{processing_level}</b>')
                                    self.tarfile_isvalid = True
                                    self.dlg.lineEdit_2.clear()
                                    self.dlg.lineEdit_2.setText(self.landsat_file[0])
                                    self.dlg.progressBar.setValue(100)

                                    self.loaded_file_is_archive = True
                                    break


                        else:
                            self.print_to_scroll_area('Search string not found in any MTL.txt file.')
                except FileNotFoundError:
                    self.print_to_scroll_area(f"The file '{tar_file_name}' was not found.")
                except tarfile.ReadError:
                    self.print_to_scroll_area(f"Failed to read the tar.gz file '{tar_file_name}'.")


        elif self.landsat_file[0].endswith(".tif"):
            global input_is_tif
            self.destfile = self.landsat_file[0]
            self.input_is_tif = gdal.Open(self.destfile)
            if self.input_is_tif.RasterCount == 7:

                #return input_is_tif
                self.dlg.lineEdit_2.clear()
                self.dlg.lineEdit_2.setText(f"{self.landsat_file[0]}")
                self.print_to_scroll_area(f"<span style='color:green;'>{self.destfile}</span> is a valid Landsat 8 / 9 image")
                self.tiffile_isvalid = True
                self.dlg.pB_select_output_folder.setEnabled(True)
                
            else:
                self.print_to_scroll_area("<span style='color:red;'>WARNING : Invalid Landsat 8/9 image !</span>")

                

    def dn_to_toa_cb_changed(self, state):
        if state == QtCore.Qt.Checked:
            if self.landsat_file[0].endswith(".tif"):
                self.dlg.pB_load_mtl.show()

            else:
                self.dlg.pB_load_mtl.hide()
        else:
            self.dlg.pB_load_mtl.hide()

    def load_mtl(self): # WORKING #
        

        self.MTL_path, _ = QFileDialog.getOpenFileName(self.dlg, "Open Text File", "", "Text Files (*.txt)")
        
        if self.MTL_path:

            with open(self.MTL_path) as MTLfile:
                lines = MTLfile.readlines()
                lt_tag = '    LANDSAT_SCENE_ID'
                lt_tag2 = '    LANDSAT_PRODUCT_ID'
                lt_tag3 = '    FILE_DATE'

                valid_MTL = False

                for row in lines:
                    if lt_tag in row:
                        valid_MTL = True
                        break

                if valid_MTL:
                    self.print_to_scroll_area('valid MTL')
                        
                else:
                    self.print_to_scroll_area('invalid MTL')
        else:
            self.print_to_scroll_area('please select an MTL file')


    #Show / Hide Load shapefile button [WORKING]
    def enablePushButton(self, radioButton, radioButton_2):
        if radioButton.isChecked():
            #self.pushButton.setEnabled(True)
            self.dlg.pB_load_shapefile.show()
        elif radioButton_2.isChecked():
            #self.pushButton.setEnabled(False)
            self.dlg.pB_load_shapefile.hide()   

    def load_shapefile(self): #WORKING OK#
        self.shapefile_path = QFileDialog.getOpenFileName(self.dlg, 'Open file', 'c:\\', "Shapfiles (*.shp);;All Files (*)")
        if not self.shapefile_path[0].endswith(".shp"):
            self.print_to_scroll_area(f"<span style='color:orange;'>{self.shapefile_path[0]} is not a valid shp file</span>")
            self.warning_popup("Warning", f"{self.shapefile_path[0]} is not a valid tar.gz file")
            return 

        else:
            self.print_to_scroll_area(f"<span style='color:blue;'>{self.shapefile_path[0]}</span> loaded for subset !")
            self.dlg.cB_calculate_mnf.setEnabled(True)

    def print_to_scroll_area(self, text): #WORKING OK#
        self.dlg.textEdit.append(text)

    def close_main_window(self): #WORKING OK#
        self.dlg.close() #Close main Window
        qgis.utils.reloadPlugin('pygeors') #Completely Reload plugin

    def show_help(self):
        import webbrowser
        webbrowser.open('https://github.com/AnassMarzouki/PyGeoRS')

    #################################################### COMBOBOX FOR False Color Composite (FCC) ###############################################
    def red_fcc_activated(self, red_fcc_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]

        for band_text, band_index in zip(bands_text, bands_index):
            if red_fcc_text == band_text:
                self.r = band_index
                break  # Exit the loop when a match is found

        if self.r is not None:
            self.selected_band_r = self.r
            #self.print_to_scroll_area(f"<span style='color:red;'>Red Band= </span>{red_fcc_text}")
        else:
            self.print_to_scroll_area("Invalid band selection")

        return self.r

    def green_fcc_activated(self, green_fcc_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]

        for band_text, band_index in zip(bands_text, bands_index):
            if green_fcc_text == band_text:
                self.g = band_index
                #self.print_to_scroll_area(f"<span style='color:green;'>Green Band= </span>{green_fcc_text}")
                return self.g

        # If no match is found, set self.g to None
        self.g = None
        self.print_to_scroll_area("Invalid band selection")

        return self.g

    def blue_fcc_activated(self, blue_fcc_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]

        for band_text, band_index in zip(bands_text, bands_index):
            if blue_fcc_text == band_text:
                self.b = band_index
                #self.print_to_scroll_area(f"<span style='color:blue;'>Blue Band= </span>{blue_fcc_text}")
                return self.b

        # If no match is found, set self.b to None
        self.b = None
        self.print_to_scroll_area("Invalid band selection")

        return self.b
    
    #################################################### COMBOBOX FOR Band Ratio (BR) ###############################################
    def a_br_activated(self, a_br_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]

        for i, band_index in zip(bands_text, bands_index):
            if a_br_text == i:
                self.r1 = band_index
                
                return self.r1

    def b_br_activated(self, b_br_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]

        for i, band_index in zip(bands_text, bands_index):
            if b_br_text == i:
                self.r2 = band_index
                return self.r2
                

    def c_br_activated(self, c_br_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]
        
        for i, band_index in zip(bands_text, bands_index):
            if c_br_text == i:
                self.g1 = band_index
                return self.g1
                

    def d_br_activated(self, d_br_text):

        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]        

        for i, band_index in zip(bands_text, bands_index):
            if d_br_text == i:
                self.g2 = band_index
                return self.g2
                
    
    def e_br_activated(self, e_br_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]
        
        for i, band_index in zip(bands_text, bands_index):
            if e_br_text == i:
                self.b1 = band_index
                return self.b1


    def f_br_activated(self, f_br_text):
        bands_text = ["1. Coastal", "2. Blue", "3. Green", "4. Red", "5. NIR", "6. SWIR 1", "7. SWIR 2"]
        bands_index = [1, 2, 3, 4, 5, 6, 7]
        
        for i, band_index in zip(bands_text, bands_index):
            if f_br_text == i:
                self.b2 = band_index
                return self.b2
                

    def index_activated(self, indice_text):
        choice_text = ["Modified Normalized Difference Water Index (MNDWI)", "Normalized Difference Enhanced Sand Index (NDESI)", "Normalized Difference Vegetation Index (NDVI)", "Normalized Difference Water Index (NDWI)", "Clay Minerals Ratio", "Ferrous Minerals Ratio", "Iron Oxyde Ratio"]
        self.selected_index = ""

        for code in choice_text:
            if indice_text == code:
                self.selected_index = code
    
    def predefined_band_ratios(self, ratio):
        ratio_text = ["Abrams", "Sabins", "Kaufmann", "Sultan"]
        self.selected_ratio = ""
        for code in ratio_text:
            if ratio == code:
                self.selected_ratio = code 
                self.print_to_scroll_area(f"{code} will be calculated")

    def set_predefined_br(self):
        pass   

    def calculate_all_band_ratios(self):
        if not self.destfile:
            self.print_to_scroll_area('input file not found. skipping ..')
            pass
        else:
            import os
            import numpy as np
            import rasterio

            # Create the output folder if it does not exist
            if not os.path.exists(self.working_path):
                os.mkdir(self.working_path)

            # Open the multiband TIFF image
            with rasterio.open(self.destfile) as src:
                self.print_to_scroll_area(f"Input file '{self.destfile}' opened successfully")

                # Read the data as a numpy array
                data = src.read()

                # Get the number of bands and their names
                num_bands = src.count
                band_names = src.indexes

                self.print_to_scroll_area(f"Found {num_bands} bands in input file")

                # Get the spatial reference system
                crs = src.crs

                # Loop through all possible band ratios
                for i in range(num_bands):
                    for j in range(i+1, num_bands):
                        # Calculate the band ratio
                        band1 = data[i].astype(np.float32)
                        band2 = data[j].astype(np.float32)
                        ratio = np.divide(band1, band2, out=np.zeros_like(band1), where=band2!=0)

                        # Create a new filename based on the band ratio
                        ratio_name = f"{band_names[i]}_{band_names[j]}"

                        # Create a new TIFF file and write the band ratio to it
                        output_path = os.path.join(self.working_path, f"{ratio_name}.tif")
                        with rasterio.open(output_path, 'w', driver='GTiff', width=src.width, height=src.height, count=1, dtype=rasterio.float32, crs=crs, transform=src.transform) as dst:
                            dst.write(ratio, 1)
                        self.print_to_scroll_area(f"Saved band ratio {ratio_name} to {output_path}")
    
    def create_subfolder(self, name):
        main_folder = self.working_path
        subfolder_path = os.path.join(main_folder, name)
        try:
            os.mkdir(subfolder_path)
            print(f"Successfully created the subfolder: {subfolder_path}")
            return subfolder_path
        except FileExistsError:
            print(f"Subfolder {subfolder_path} already exists.")
            return subfolder_path        

    #Extract Landsat Archive [WORKING]
    def extract_landsat_archive(self):
        if self.landsat_file[0].endswith(".tar.gz") or self.landsat_file[0].endswith(".tar"):
            extracted_files = self.create_subfolder("Extracted_files")
            self.extract_path = os.path.join(self.working_path, extracted_files)
            self.print_to_scroll_area('Extracting archive ..')
            
            compression_format = "r:gz" if self.landsat_file[0].endswith(".tar.gz") else "r:"

            with tarfile.open(self.landsat_file[0], compression_format) as tar:
                # Create the extract path if it doesn't exist
                if not os.path.exists(self.extract_path):
                    os.makedirs(self.extract_path)
                
                #Progress bar initiation
                total_files = len(tar.getmembers())
                # Update the progress bar maximum value
                self.dlg.progressBar.setMaximum(total_files)
                
                # Display progression using print()
                for i, member in enumerate(tar.getmembers()):
                    tar.extract(member, self.extract_path)
                    # Update the progress bar value
                    self.dlg.progressBar.setValue(i+1)
                    # QApplication.processEvents() #Real-time update of the event console

            self.print_to_scroll_area(f"Files successfully extracted to <span style='color:blue;'>{self.extract_path}</span>")
        else:
            self.print_to_scroll_area('No files to be extracted. Skipping ..')

    def define_working_path(self, working_path): # WORKING #
        self.working_path = working_path
        self.dlg.lineEdit.clear()
        self.working_path = str(QFileDialog.getExistingDirectory(self.dlg, "Select Directory"))
        if self.working_path:
            self.dlg.lineEdit.setText(f"{self.working_path}")
            self.print_to_scroll_area(f"<span style='color:blue;'>{self.working_path}</span> is set as default working folder !")

            # Clear the listWidget
            self.dlg.listWidget.clear()

            # Repopulate the listWidget with the files in the new path
            for file_name in os.listdir(self.working_path):
                item = QListWidgetItem(file_name)
                self.dlg.listWidget.addItem(item)
                
            # Connect the itemClicked signal to the on_item_clicked slot
            self.dlg.listWidget.itemClicked.connect(self.on_item_clicked)


    def layer_stacking(self): # WORKING #
        #Locate files that ends with SR_BX.TIF
        import os
        import re

        #Check if extract_path exist
        # specify the directory containing the files
        
        if self.landsat_file[0].endswith(".tif"):
            self.print_to_scroll_area('input file is in tif format, Layerstacking not supported')
            pass

        else:
            bands_directory = self.extract_path

            # create an empty list to store the file names
            band_fnames = []

            # iterate through the directory
            for filename in os.listdir(bands_directory):
                # check if the file ends with SR_BX.tif or T1_BX.tif, where X is a number from 1 to 7
                if re.search(r'(T1|SR)_B[1-7]\.TIF$', filename):
                    # if the file matches the pattern, add it to the list as a tuple containing the band number and the file name
                    band_number = re.search(r'(T1|SR)_B([1-7])\.TIF$', filename).group(2)
                    band_fnames.append((band_number, filename))

            self.print_to_scroll_area("Attemping <span style='color:orange;'>LayerStacking</span>")

            import earthpy.spatial as es

            # Define the custom path for the input files
            input_path = self.extract_path
            

            # Create the full path for each input file
            band_paths = [os.path.join(input_path, fname[1]) for fname in band_fnames]

            # Define the path to save the stacked image
            outputs_folder = self.create_subfolder("Outputs")
            
            global destfile
            self.destfile = os.path.join(outputs_folder, "LayerStack.tif")

            # Stack the images and save the output
            arr, arr_meta = es.stack(band_paths, self.destfile)
            # QApplication.processEvents()

            # Print a message to indicate the process is complete
            self.print_to_scroll_area(f"<span style='color:green;'>Layerstacking done successfully:</span> {self.destfile}")
            # QtWidgets.QApplication.processEvents()

    def global_oif(self): # WORKING #
        self.print_to_scroll_area("Loading <span style='color:blue;'>Landsat 8</span> file ...")
        # QApplication.processEvents()

        global destfile
        oif_tif_input = self.destfile
        with rasterio.open(oif_tif_input) as src:
            bands = [src.read(i) for i in range(1, src.count+1)]
            shape = src.shape
            self.print_to_scroll_area(f"<span style='color:green;'>{oif_tif_input}</span> loaded successfully")
            

            # Calculate the correlations matrix
        correlations = np.zeros((src.count, src.count))

        self.print_to_scroll_area("<span style='color:orange;'>OIF Calculation</span> started, please wait ...")

            # Initialize the progress bar
        comb = list(itertools.combinations(range(src.count), 3))
        self.dlg.progressBar.setRange(0, len(comb))
        self.dlg.progressBar.setValue(0)
        # QApplication.processEvents()


        for i in range(src.count):
            for j in range(i, src.count):
                correlations[i][j] = np.corrcoef(bands[i].flatten(), bands[j].flatten())[0][1]
                correlations[j][i] = correlations[i][j]

        oif_results = self.oif(bands, correlations, self.dlg.progressBar)
        # QApplication.processEvents()

        print(correlations)

            # Sort the OIF results in descending order based on the OIF values
        oif_results.sort(key=lambda x: x[2], reverse=True)

        oif_txt = os.path.join(self.working_path, "OIF_Ranks.txt")

        with open(oif_txt, 'w') as f:
            for i, (index, comb, oif) in enumerate(oif_results):
                    self.print_to_scroll_area("OIF{}= {:>2}:  band{}  band{}  band{}  ({:.2f})".format(index, i+1, comb[0]+1, comb[1]+1, comb[2]+1, oif))
                    global oif_string
                    oif_string = "OIF{}= {:>2}:  band{}  band{}  band{}  ({:.2f})\n".format(index, i+1, comb[0]+1, comb[1]+1, comb[2]+1, oif)
                    f.write(oif_string)

        self.print_to_scroll_area("\n")
        self.print_to_scroll_area('OIF Calulation done successfully')
        # QApplication.processEvents()

        self.print_to_scroll_area(f"OIF Ranks saved in <span style='color:green;'> {self.working_path} </span>")
        # QApplication.processEvents()
        
    def oif(self, bands, correlations, progressBar): # WORKING #
        n_bands = len(bands)
        comb = list(itertools.combinations(range(n_bands), 3))
        oif_values = []
        for i, j, k in comb:
            Stdi = np.std(bands[i])
            Stdj = np.std(bands[j])
            Stdk = np.std(bands[k])
            Corrij = correlations[i][j]
            Corrik = correlations[i][k]
            Corrjk = correlations[j][k]
            oif = (Stdi + Stdj + Stdk) / (abs(Corrij) + abs(Corrik) + abs(Corrjk))
            oif_values.append(oif)
            self.dlg.progressBar.setValue(self.dlg.progressBar.value() + 1)
            # QApplication.processEvents()

        return list(zip(range(len(oif_values)), comb, oif_values))

    def calculate_pca(self): # WORKING #
        self.print_to_scroll_area("PCA Calculation started ...")
        # QApplication.processEvents()
        import numpy as np
        from sklearn.decomposition import PCA
        from osgeo import gdal

        def tif_to_array(file_path):
            """Convert TIF image to numpy array."""
            ds = gdal.Open(file_path)
            band = ds.GetRasterBand(1)
            data = band.ReadAsArray()
            for i in range(1, ds.RasterCount):
                band = ds.GetRasterBand(i+1)
                data = np.dstack((data, band.ReadAsArray()))
            return data

        def array_to_tif(data, file_path, ds_origin):
            """Save numpy array as TIF image."""
            driver = gdal.GetDriverByName('GTiff')
            rows, cols, n_bands = data.shape
            ds = driver.Create(file_path, cols, rows, n_bands, gdal.GDT_Float32)
            ds.SetGeoTransform(ds_origin.GetGeoTransform())
            ds.SetProjection(ds_origin.GetProjection())
            for i in range(n_bands):
                band = ds.GetRasterBand(i+1)
                band.WriteArray(data[:, :, i])
            ds = None

        # Load TIF image as numpy array
        ds = gdal.Open(self.destfile)
        data = tif_to_array(self.destfile)
        self.print_to_scroll_area(f"{self.destfile} loaded successfully")
        # QApplication.processEvents()
        self.print_to_scroll_area("Processing ...")


        # Perform PCA
        pca = PCA(n_components=data.shape[2])
        pca_data = pca.fit_transform(data.reshape(-1, data.shape[2]))

        # Save PCA result as TIF image
        pca_output = os.path.join(self.working_path, "PCA.tif")

        array_to_tif(pca_data.reshape(data.shape[0], data.shape[1], -1), pca_output, ds)
        self.print_to_scroll_area(f"PCA done successfully, PCA file: {pca_output}")
        # QApplication.processEvents()

    def calculate_mnf(self): # WORKING #
    #################### TESTED AND WORKING ########################
        from unmixing.utils import as_array
        lt8_image, gt, wkt = as_array(self.destfile)
        lt8_image.shape

        from unmixing.transform import mnf_rotation
        hsi_post_mnf = mnf_rotation(lt8_image)

        import numpy as np
        import pysptools.util as sp_utils
        from unmixing.lsma import ravel_and_filter

        # Filter out NoData values from the MNF-transformed image
        hsi_post_mnf_filtered = ravel_and_filter(np.where(lt8_image == -9999, -9999, hsi_post_mnf.T))

        # Obtain the covariance matrix
        cov_m = sp_utils.cov(hsi_post_mnf_filtered)

        # Compute the eigenvalues, sort them, reverse the sorting
        eigenvals = np.sort(np.linalg.eig(cov_m)[0])[::-1]
        eigenvals_p = np.power(eigenvals, 2) / sum(np.power(eigenvals, 2))

        import rasterio

        # Get shape of the arrays
        n_bands, height, width = hsi_post_mnf.T.shape

        # Define the profile for the output raster
        profile = {
            'driver': 'GTiff',
            'dtype': 'float32',
            'count': n_bands,
            'height': height,
            'width': width,
            'crs': rasterio.crs.CRS.from_wkt(wkt), # Add CRS (Coordinate Reference System) from input
            'transform': rasterio.transform.from_origin(gt[0], gt[3], gt[1], -gt[5]) # Add geotransformation from input
        }

        mnf_output = os.path.join(self.working_path, "MNF.tif")

        # Write each MNF component as a single band in the output raster
        with rasterio.open(mnf_output, 'w', **profile) as dst:
            for i in range(n_bands):
                dst.write(hsi_post_mnf.T[i,:,:], i+1)
        self.print_to_scroll_area(f"MNF done successfully, MNF file : {mnf_output}")


    def dn_to_toa_archive(self):
    # Check if all the required files are available
        if self.tiffile_isvalid and self.MTL_path:
            pass

        if self.tarfile_isvalid:

            search_directory = self.extract_path

            # Define the file extension to search for
            file_extension = "_MTL.txt"
            import os
            # Iterate through the files in the directory
            for root, dirs, files in os.walk(search_directory):
                for file in files:
                    if file.endswith(file_extension):
                        # Print the full path of the file
                        file_path = os.path.join(root, file)
                        self.print_to_scroll_area(f'MTL file found: {file_path}')
                        self.MTL_path = file_path


        def extract_lines(file, startswith, start, end):
            all_lines = []
            lines = []
            with open(self.MTL_path, 'r') as f:
                all_lines = f.readlines()
                if startswith:
                    for i, line in enumerate(all_lines):
                        if line.startswith(startswith):
                            lines.append(line.strip())
                elif start and end:
                    for i, line in enumerate(all_lines):
                        if start in line:
                            for j in range(i, len(all_lines)):
                                line = all_lines[j]
                                if end in line:
                                    break
                                lines.append(line.strip())
            return lines

        import os

        self.print_to_scroll_area(f"<span style='color:blue;'>{self.MTL_path}</span> successfully loaded !")
        
        if self.L1TP:
            lines = extract_lines(self.MTL_path, None, '  GROUP = RADIOMETRIC_RESCALING', 'END_GROUP = RADIOMETRIC_RESCALING') #L1TP
        elif self.L2SP:
            lines = extract_lines(self.MTL_path, None, '  GROUP = LEVEL1_RADIOMETRIC_RESCALING', 'END_GROUP = LEVEL1_RADIOMETRIC_RESCALING') #L1TP


        reflectance_mult = []
        reflectance_add = []
        sun_elev = None

        for line in lines:
            if line.startswith('REFLECTANCE_MULT_BAND_'):
                reflectance_mult.append(float(line.split('=')[1].strip()))
            elif line.startswith('REFLECTANCE_ADD_BAND_'):
                reflectance_add.append(float(line.split('=')[1].strip()))

        with open(self.MTL_path, 'r') as f:
            for line in f:
                if line.startswith('    SUN_ELEVATION'):
                    sun_elev = float(line.split('=')[1].strip())

        self.print_to_scroll_area("Conversion parameters loaded :")
        # QApplication.processEvents()

        import numpy as np
        from osgeo import gdal
        import os
        import math

        # Open the input TIF file
        ds = gdal.Open(self.destfile)

        # Get the number of rows and columns in the input TIF file
        cols = ds.RasterXSize
        rows = ds.RasterYSize

        # Get the data for each band
        bands = []
        for i in range(1, 8):
            band = ds.GetRasterBand(i)
            bands.append(band.ReadAsArray())

        # Get the sun elevation value
        #sun_elev = 39.11
        # QApplication.processEvents()
        self.print_to_scroll_area("DN to ToA in progress ...")
        # Calculate the top-of-atmosphere (TOA) reflectance
        toa_reflectance = []
        for i in range(7):
            band_toa = np.zeros_like(bands[0], dtype=np.float32)
            band_toa = (reflectance_mult[i] * bands[i] + reflectance_add[i]) / math.sin(math.radians(sun_elev))
            toa_reflectance.append(band_toa)

        # Normalize the TOA reflectance to the range [0, 1]
        toa_reflectance_normalized = []
        for i in range(7):
            min_val = np.min(toa_reflectance[i])
            max_val = np.max(toa_reflectance[i])
            band_normalized = (toa_reflectance[i] - min_val) / (max_val - min_val)
            toa_reflectance_normalized.append(band_normalized)

        # Save the output TIF file
        driver = gdal.GetDriverByName("GTiff")
        self.destfile = os.path.join(self.working_path, "ToA.tif")

        outds = driver.Create(self.destfile, cols, rows, 7, gdal.GDT_Float32)
        for i in range(7):
            outds.GetRasterBand(i + 1).WriteArray(toa_reflectance_normalized[i])
        self.print_to_scroll_area(f"DN to ToA conversion successfully done, your ToA file is <span style='color:green;'>{self.destfile}</span>")

        # Close the input and output datasets
        ds = None
        outds = None

    def calculate_ica(self): # WORKING #
        #for tif file
        if self.input_is_tif.RasterXSize > 3000 or self.input_is_tif.RasterYSize > 3000:
            self.print_to_scroll_area('ICA not supported for large files, consider cropping your image')
            pass

        else:

            from sklearn.decomposition import FastICA

            def ICA_raster(input_file, ica_output, n_components):
                # Open input raster
                src_ds = gdal.Open(input_file)
                src_band = src_ds.GetRasterBand(1)
                rows, cols = src_band.YSize, src_band.XSize
                self.print_to_scroll_area(f"{self.destfile} loaded successfully !")


                # Read data into a numpy array
                data = np.zeros((rows * cols, src_ds.RasterCount))
                for i in range(1, src_ds.RasterCount + 1):
                    src_band = src_ds.GetRasterBand(i)
                    data[:, i - 1] = src_band.ReadAsArray().reshape(-1)

                # Fit ICA model
                ica = FastICA(n_components=n_components)
                transformed = ica.fit_transform(data)

                # Write transformed data to output file
                driver = gdal.GetDriverByName("GTiff")
                out_ds = driver.Create(ica_output, cols, rows, n_components, gdal.GDT_Float32)

                out_ds.SetGeoTransform(src_ds.GetGeoTransform())
                out_ds.SetProjection(src_ds.GetProjection())

                for i in range(n_components):
                    out_band = out_ds.GetRasterBand(i + 1)
                    out_band.WriteArray(transformed[:, i].reshape(rows, cols))
                out_ds = None

            input_file = self.destfile

            ica_output = os.path.join(self.working_path, "ICA.tif")

            n_components = 7
            self.print_to_scroll_area("ICA started, please wait ...")

            ICA_raster(input_file, ica_output, n_components)
            self.print_to_scroll_area(f"ICA done successfully, ICA file: {ica_output}")

    def subset_by_shapefile(self): # WORKING #
        if not self.shapefile_path[0] and self.destfile:
            self.print_to_scroll_area("<span style='color:red;'>LayerStack image and/or shapefile is missing !</span>")
        import geopandas as gpd
        from rasterio.mask import mask

        # Open the multiband tif file
        with rasterio.open(self.destfile) as src:
            # Load the shapefile or kml file
            shapefile = gpd.read_file(self.shapefile_path[0])
            # Apply the subset to the image using the shapefile
            subset_image, subset_transform = mask(src, shapes=shapefile.geometry, crop=True)
            # Update metadata to reflect the subset
            subset_meta = src.meta.copy()
            subset_meta.update({
                "height": subset_image.shape[1],
                "width": subset_image.shape[2],
                "transform": subset_transform
            })
            # Save the new subset image as a tif file
        
            global destfile
            self.destfile = os.path.join(self.working_path, "Subset.tif")
            with rasterio.open(self.destfile, 'w', **subset_meta) as dst:
        # write data to output file

                dst.write(subset_image)
        self.print_to_scroll_area('Subset done successfully')
        self.print_to_scroll_area(f" self.destfile ====> {self.destfile}")
        self.print_to_scroll_area(f" self.working_path ==> {self.working_path}")

    def abrams(self):
        self.print_to_scroll_area('Abrams calculation started')
        if self.destfile:
            img = gdal.Open(self.destfile)
            self.b3 = img.GetRasterBand(3).ReadAsArray().astype(np.float32)
            self.b4 = img.GetRasterBand(4).ReadAsArray().astype(np.float32)
            self.b5 = img.GetRasterBand(5).ReadAsArray().astype(np.float32)
            self.b6 = img.GetRasterBand(6).ReadAsArray().astype(np.float32)
            self.b7 = img.GetRasterBand(7).ReadAsArray().astype(np.float32)

            red_band = np.divide(self.b6, self.b7, out=np.zeros_like(self.b6), where=self.b7!=0)
            green_band = np.divide(self.b4, self.b3, out=np.zeros_like(self.b4), where=self.b3!=0)
            blue_band = np.divide(self.b5, self.b6, out=np.zeros_like(self.b5), where=self.b6!=0)

            abrams_image = np.dstack((red_band, green_band, blue_band))

            x_size = img.RasterXSize
            y_size = img.RasterYSize

            driver = gdal.GetDriverByName("GTiff")
            fcc_output_path = os.path.join(self.working_path, "BR_Abrams.tif")

            fcc_output_image = driver.Create(fcc_output_path, x_size, y_size, 3, gdal.GDT_Float32)

            # Set the projection and geotransform of the output image
            fcc_output_image.SetProjection(img.GetProjection())
            fcc_output_image.SetGeoTransform(img.GetGeoTransform())

            # Write the new 3-band TIFF image
            for x in range(3):
                fcc_output_image.GetRasterBand(x + 1).WriteArray(abrams_image[..., x])

            self.print_to_scroll_area(fcc_output_path)

    def kaufmann(self):
        self.print_to_scroll_area('Kaufmann calculation started')
        if self.destfile:
            img = gdal.Open(self.destfile)
            self.b4 = img.GetRasterBand(4).ReadAsArray().astype(np.float32)
            self.b5 = img.GetRasterBand(5).ReadAsArray().astype(np.float32)
            self.b6 = img.GetRasterBand(6).ReadAsArray().astype(np.float32)
            self.b7 = img.GetRasterBand(7).ReadAsArray().astype(np.float32)

            red_band = np.divide(self.b7, self.b5, out=np.zeros_like(self.b7), where=self.b5!=0)
            green_band = np.divide(self.b5, self.b4, out=np.zeros_like(self.b5), where=self.b4!=0)
            blue_band = np.divide(self.b6, self.b7, out=np.zeros_like(self.b6), where=self.b7!=0)

            kaufmann_image = np.dstack((red_band, green_band, blue_band))

            x_size = img.RasterXSize
            y_size = img.RasterYSize

            driver = gdal.GetDriverByName("GTiff")
            fcc_output_path = os.path.join(self.working_path, "BR_Kaufmann.tif")

            fcc_output_image = driver.Create(fcc_output_path, x_size, y_size, 3, gdal.GDT_Float32)

            # Set the projection and geotransform of the output image
            fcc_output_image.SetProjection(img.GetProjection())
            fcc_output_image.SetGeoTransform(img.GetGeoTransform())

            # Write the new 3-band TIFF image
            for x in range(3):
                fcc_output_image.GetRasterBand(x + 1).WriteArray(kaufmann_image[..., x])

            self.print_to_scroll_area(fcc_output_path)

    def sabins(self):
        self.print_to_scroll_area('Sabins calculation started')
        if self.destfile:
            img = gdal.Open(self.destfile)
            self.b4 = img.GetRasterBand(4).ReadAsArray().astype(np.float32)
            self.b2 = img.GetRasterBand(2).ReadAsArray().astype(np.float32)
            self.b6 = img.GetRasterBand(6).ReadAsArray().astype(np.float32)
            self.b7 = img.GetRasterBand(7).ReadAsArray().astype(np.float32)

            red_band = np.divide(self.b4, self.b6, out=np.zeros_like(self.b4), where=self.b6!=0)
            green_band = np.divide(self.b4, self.b2, out=np.zeros_like(self.b4), where=self.b2!=0)
            blue_band = np.divide(self.b6, self.b7, out=np.zeros_like(self.b6), where=self.b7!=0)

            sabins_image = np.dstack((red_band, green_band, blue_band))

            x_size = img.RasterXSize
            y_size = img.RasterYSize

            driver = gdal.GetDriverByName("GTiff")
            fcc_output_path = os.path.join(self.working_path, "BR_Sabins.tif")

            fcc_output_image = driver.Create(fcc_output_path, x_size, y_size, 3, gdal.GDT_Float32)

            # Set the projection and geotransform of the output image
            fcc_output_image.SetProjection(img.GetProjection())
            fcc_output_image.SetGeoTransform(img.GetGeoTransform())

            # Write the new 3-band TIFF image
            for x in range(3):
                fcc_output_image.GetRasterBand(x + 1).WriteArray(sabins_image[..., x])

            self.print_to_scroll_area(fcc_output_path)    


    def set_fcc(self):

        global red_fcc, green_fcc, blue_fcc, gdf
        if self.destfile:


            gdf = gdal.Open(self.destfile) #gdf = global destfile
            self.red_fcc = gdf.GetRasterBand(self.r).ReadAsArray().astype(np.float32)
            self.green_fcc = gdf.GetRasterBand(self.g).ReadAsArray().astype(np.float32)
            self.blue_fcc = gdf.GetRasterBand(self.b).ReadAsArray().astype(np.float32)

            fcc_image = np.dstack((self.red_fcc, self.green_fcc, self.blue_fcc))

            x_size = gdf.RasterXSize
            y_size = gdf.RasterYSize

            driver = gdal.GetDriverByName("GTiff")
            fcc_output_path = os.path.join(self.working_path, f"FCC_R{self.r}_G{self.g}_B{self.b}.tif")

            fcc_output_image = driver.Create(fcc_output_path, x_size, y_size, 3, gdal.GDT_Float32)

            # Set the projection and geotransform of the output image
            fcc_output_image.SetProjection(gdf.GetProjection())
            fcc_output_image.SetGeoTransform(gdf.GetGeoTransform())

            # Write the new 3-band TIFF image
            for x in range(3):
                fcc_output_image.GetRasterBand(x + 1).WriteArray(fcc_image[..., x])
            self.print_to_scroll_area(f"FCC done successfully, Composite <span style='color:red;'>R:</span>{self.r} ; <span style='color:green;'>G:</span>{self.g} ; <span style='color:blue;'>B:</span>{self.b}")
        else:
            self.print_to_scroll_area("wrong input file")


    def calculate_band_ratio(self):
        global a_br_var, b_br_var, c_br_var, d_br_var, e_br_var, f_br_var
        # Check if self.working_path is set
        if self.working_path is None:
            self.print_to_scroll_area('Select a working path first!')
            return

        # Check if self.input_is_tif is set
        if self.input_is_tif is None:
            self.print_to_scroll_area('Select input data first!')
            return
            #self.working_path = str(QFileDialog.getExistingDirectory(self, "Select Directory"))

        if self.input_is_tif:

            input_is_tif = gdal.Open(self.destfile)

            a_br_var = input_is_tif.GetRasterBand(self.r1).ReadAsArray().astype(np.float32)
            b_br_var = input_is_tif.GetRasterBand(self.r2).ReadAsArray().astype(np.float32)
            c_br_var = input_is_tif.GetRasterBand(self.g1).ReadAsArray().astype(np.float32)
            d_br_var = input_is_tif.GetRasterBand(self.g2).ReadAsArray().astype(np.float32)
            e_br_var = input_is_tif.GetRasterBand(self.b1).ReadAsArray().astype(np.float32)
            f_br_var = input_is_tif.GetRasterBand(self.b2).ReadAsArray().astype(np.float32)

            a_b_ratio = np.divide(a_br_var, b_br_var, out=np.zeros_like(a_br_var), where=b_br_var!=0)
            c_d_ratio = np.divide(c_br_var, d_br_var, out=np.zeros_like(c_br_var), where=d_br_var!=0)
            e_f_ratio = np.divide(e_br_var, f_br_var, out=np.zeros_like(e_br_var), where=f_br_var!=0)

            br_image = np.dstack((a_b_ratio, c_d_ratio, e_f_ratio))
            # Get the metadata from the source image
            x_size = input_is_tif.RasterXSize
            y_size = input_is_tif.RasterYSize

            # Create the output image
            driver = gdal.GetDriverByName("GTiff")

            br_output_path = os.path.join(self.working_path, f"BandRatio_R{self.r1}{self.r2}_G{self.g1}{self.g2}_B{self.b1}{self.b2}.tif")

            br_output_image = driver.Create(br_output_path, x_size, y_size, 3, gdal.GDT_Float32)

            # Set the projection and geotransform of the output image
            br_output_image.SetProjection(input_is_tif.GetProjection())
            br_output_image.SetGeoTransform(input_is_tif.GetGeoTransform())

            # Write the new 3-band TIFF image
            for i in range(3):
                br_output_image.GetRasterBand(i + 1).WriteArray(br_image[..., i])

            self.print_to_scroll_area("<span style='color:green;'>Band Ratio done successfully</span>")

            # Close the datasets
            br_output_image = None
        else:
            self.print_to_scroll_area('select input data first !')

 #################################################### CALCULATE INDICES ############################################################

    def calculate_ndvi(self, input_path):
        with rasterio.open(input_path) as src:
            red = src.read(4).astype('float32')
            nir = src.read(5).astype('float32')

            ndvi = (nir - red) / (nir + red)

            return ndvi

    def calculate_mndwi(self, input_path):
        with rasterio.open(input_path) as src:

            green = src.read(3).astype('float32')
            swir = src.read(6).astype('float32')

            mndwi = (green - swir) / (green + swir)

            return mndwi

    def calculate_clay_mineral_ratio(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')

            clay_mineral_ratio = swir1 / swir2

            return clay_mineral_ratio

    def calculate_ndbi(self, input_path):
        with rasterio.open(input_path) as src:
            swir = src.read(6).astype('float32')
            nir = src.read(5).astype('float32')

            ndbi = (swir - nir) / (swir + nir)

            return ndbi

    def calculate_ferrous_mineral_ratio(self, input_path):
        with rasterio.open(input_path) as src:
            swir = src.read(6).astype('float32')
            nir = src.read(5).astype('float32')

            ferrous_mineral_ratio = swir / nir

            return ferrous_mineral_ratio

    def calculate_iron_oxide_ratio(self, input_path):
        with rasterio.open(input_path) as src:
            red = src.read(4).astype('float32')
            blue = src.read(2).astype('float32')

            iron_oxide_ratio = red / blue

            return iron_oxide_ratio

    def calculate_ndwi(self, input_path):
        with rasterio.open(input_path) as src:
            swir = src.read(6).astype('float32')
            nir = src.read(5).astype('float32')

            ndwi = (nir - swir) / (nir + swir)

            return ndwi

    def calculate_ndesi(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')
            red = src.read(4).astype('float32')
            blue = src.read(2).astype('float32')

            ndesi = ((red - blue) / (red + blue)) + ((swir1 - swir2 / swir1 + swir2))

            return ndesi
   

    def index_activated(self, indice_text):
        choice_text = ["Modified Normalized Difference Water Index (MNDWI)", "Normalized Difference Enhanced Sand Index (NDESI)", "Normalized Difference Vegetation Index (NDVI)", "Normalized Difference Water Index (NDWI)", "Clay Minerals Ratio", "Ferrous Minerals Ratio", "Iron Oxyde Ratio"]
        self.selected_index = ""

        for code in choice_text:
            if indice_text == code:
                self.selected_index = code

    def calculate_abrams(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')
            red = src.read(4).astype('float32')
            blue = src.read(2).astype('float32')

            abrams_ratio = ((red - blue) / (red + blue)) + ((swir1 - swir2 / swir1 + swir2))

            return ndesi

    def calculate_sabins(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')
            red = src.read(4).astype('float32')
            blue = src.read(2).astype('float32')

            ndesi = ((red - blue) / (red + blue)) + ((swir1 - swir2 / swir1 + swir2))

            return ndesi

    def calculate_kaufmann(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')
            red = src.read(4).astype('float32')
            blue = src.read(2).astype('float32')

            ndesi = ((red - blue) / (red + blue)) + ((swir1 - swir2 / swir1 + swir2))

            return ndesi

    def calculate_sultant(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')
            red = src.read(4).astype('float32')
            blue = src.read(2).astype('float32')

            ndesi = ((red - blue) / (red + blue)) + ((swir1 - swir2 / swir1 + swir2))

            return ndesi
    

    def save_index_image(self): 
        self.print_to_scroll_area('Index calculation started !')
        if self.destfile:

            input_path = self.destfile

            self.print_to_scroll_area(f"your input_path variable is:   {input_path}")

            acronyms = {
        "Modified Normalized Difference Water Index (MNDWI)": "MNDWI",
        "Normalized Difference Enhanced Sand Index (NDESI)": "NDESI",
        "Normalized Difference Vegetation Index (NDVI)": "NDVI",
        "Normalized Difference Water Index (NDWI)": "NDWI",
        "Clay Minerals Ratio": "ClayIndex",
        "Ferrous Minerals Ratio": "Ferrous",
        "Iron Oxyde Ratio": "Iron"}

            with rasterio.open(input_path) as src:
                profile = src.profile
                profile.update(dtype=rasterio.float32, count=1, nodata=0)

                self.print_to_scroll_area(f"image file: {src}")
                global index_output

                if self.selected_index == "Normalized Difference Vegetation Index (NDVI)":
                    index_output = self.calculate_ndvi(input_path)
                elif self.selected_index == "Modified Normalized Difference Water Index (MNDWI)":
                    index_output = self.calculate_mndwi(input_path)
                elif self.selected_index == "Normalized Difference Water Index (NDWI)":
                    index_output = self.calculate_ndwi(input_path)
                elif self.selected_index == "Normalized Difference Enhanced Sand Index (NDESI)":
                    index_output = self.calculate_ndesi(input_path)
                elif self.selected_index == "Clay Minerals Ratio":
                    index_output = self.calculate_clay_mineral_ratio(input_path)
                elif self.selected_index == "Ferrous Minerals Ratio":
                    index_output = self.calculate_ferrous_mineral_ratio(input_path)
                elif self.selected_index == "Iron Oxyde Ratio":
                    index_output = self.calculate_iron_oxide_ratio(input_path)
                else:
                    self.print_to_scroll_area("No index selected.")
                    return

                # Generate the output file path with the directory path included
                output_filename = f"{os.path.splitext(os.path.basename(input_path))[0]}_{acronyms[self.selected_index]}.tif"
                output_path = os.path.join(self.working_path, output_filename)


                self.index_output_path = output_path

                with rasterio.open(output_path, 'w', **profile) as dst:
                    dst.write(index_output.astype(rasterio.float32), 1)

                self.print_to_scroll_area("Index done successfully")
        else:
            self.print_to_scroll_area('Input file required !')

    def disable_all_tasks(self): #WORKING - FF#
        #Disable all tasks
        for item in self.checkboxes:
            item.setEnabled(False)

        for pb in self.pushbuttons:
            pb.setEnabled(False)

        for combo in self.comboboxes:
            combo.setEnabled(False)

    def enable_all_tasks(self):
        for item in self.checkboxes:
            item.setEnabled(True)

        for pb in self.pushbuttons:
            pb.setEnabled(True)

        for combo in self.comboboxes:
            combo.setEnabled(True)

    def set_folder_and_proceed(self): # WORKING #
        import time
        start_time = time.time()

        if self.working_path:
            if self.dlg.cB_extract_archive.isChecked():
                self.extract_landsat_archive()

            if self.dlg.cB_layer_stacking.isChecked():
                self.layer_stacking()

            if self.dlg.cB_dn_to_toa.isChecked() and self.loaded_file_is_archive:

                self.dn_to_toa_archive() 
                
            if self.dlg.cB_generate_fcc.isChecked():
                self.set_fcc()
            
            if self.dlg.radioButton.isChecked() and self.shapefile_path[0] and self.destfile:
                self.subset_by_shapefile()

            if self.dlg.cB_calculate_oif.isChecked(): #Calculate OIF
                self.global_oif()

            if self.dlg.cB_calculate_pca.isChecked(): #Calculate PCA
                self.calculate_pca()

            if self.dlg.cB_calculate_mnf.isChecked(): #Calculate MNF
                self.calculate_mnf()

            if self.dlg.cB_calculate_ica.isChecked(): #Calculate ICA
                self.calculate_ica()

            if self.dlg.cB_calculate_index.isChecked(): #Calculate Index
                global input_is_tif
                self.save_index_image()

            if self.dlg.cB_calculate_br.isChecked(): #Calculate Band Ratio
                self.calculate_band_ratio()

            if self.dlg.cB_calculate_all_br.isChecked(): #Calculate all possible Band Ratios
                self.calculate_all_band_ratios()

            if self.dlg.cB_abrams.isChecked(): #Abrams Index
                self.abrams()

            if self.dlg.cB_sabins.isChecked(): #Sabins Index
                self.sabins()

            if self.dlg.cB_kaufmann.isChecked(): #Kaufmann
                self.kaufmann()
            
            self.print_to_scroll_area("<b><span style='color:Red;'>All tasks ended successfully</span></b>")

            end_time = time.time()

            processing_time = end_time - start_time
            self.print_to_scroll_area(f"Processing time: {processing_time:.2f} seconds")
        else:
            self.print_to_scroll_area('Input file or output folder not defined')

