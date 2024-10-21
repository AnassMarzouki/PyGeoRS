from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import *
from qgis import *
from PyQt5.QtWidgets import *
import concurrent.futures




from qgis.core import QgsVectorLayer, QgsProject, QgsCoordinateTransform, QgsCoordinateReferenceSystem


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

        #Checkboxes
        self.checkboxes = [self.dlg.pB_select_output_folder, self.dlg.cB_extract_archive, self.dlg.cB_layer_stacking, self.dlg.cB_calculate_all_br,
        self.dlg.radioButton, self.dlg.cB_dn_to_toa, self.dlg.cB_calculate_oif, 
        self.dlg.cB_calculate_pca, self.dlg.cB_calculate_mnf, self.dlg.cB_calculate_ica,
        self.dlg.cB_calculate_index, self.dlg.cB_calculate_br, self.dlg.cB_generate_fcc, self.dlg.cB_abrams, self.dlg.cB_sabins, self.dlg.cB_kaufmann]

        #Comboboxes
        self.comboboxes = [self.dlg.comboBox, self.dlg.comboBox_2, self.dlg.comboBox_3,
        self.dlg.comboBox_6, 
        self.dlg.comboBox_7, self.dlg.comboBox_7, self.dlg.comboBox_8, self.dlg.comboBox_9,
        self.dlg.comboBox_10, self.dlg.comboBox_11]

        self.pushbuttons = [self.dlg.pB_load_mtl, self.dlg.pB_proceed]

        #BR items
        self.br_items = [self.dlg.cB_abrams, self.dlg.cB_sabins, self.dlg.cB_kaufmann, 
        self.dlg.comboBox_6, self.dlg.comboBox_7, self.dlg.comboBox_8, self.dlg.comboBox_9,
        self.dlg.comboBox_10, self.dlg.comboBox_11, self.dlg.cB_calculate_all_br]

        #fcc items
        self.fcc_combo = [self.dlg.comboBox, self.dlg.comboBox_2, self.dlg.comboBox_3]

        self.dlg.comboBox_4.setEnabled(False)

        

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

            #Enables checkboxes
            self.enable_all_tasks()
            self.dlg.pB_load_mtl.hide()

            #Disable Indices & BR
            self.dlg.comboBox_4.setEnabled(False)

            #disable BR items
            for item in self.br_items:
                item.setEnabled(False)

            #disable FCC items
            for item in self.fcc_combo:
                item.setEnabled(False)




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

    def enable_indice_list(self):
        if self.dlg.cB_calculate_index.isChecked():
            self.dlg.comboBox_4.setEnabled(True)
        else:
            self.dlg.comboBox_4.setEnabled(False)

    def enable_band_ratio(self):
        for item in self.br_items:
            if self.dlg.cB_calculate_br.isChecked():
                item.setEnabled(True)
            else:
                item.setEnabled(False)

    def enable_generate_fcc(self):
        
        for item in self.fcc_combo:

            if self.dlg.cB_generate_fcc.isChecked():
                item.setEnabled(True)
            else:
                item.setEnabled(False)

    def load_landsat_data(self): #WORKING OK - FF#
        import tarfile
        search_string_LC8 = 'SPACECRAFT_ID = "LANDSAT_8"'
        search_string_LC9 = 'SPACECRAFT_ID = "LANDSAT_9"'

        L1TP_tag = 'DATA_TYPE = "L1TP"'
        L2SP_tag = 'PROCESSING_LEVEL = "L2SP"'

        # Load a file
        self.landsat_file = QFileDialog.getOpenFileName(self.dlg, 'Open file', '', "Landsat data (*.tar.gz  *.tar *.tif);;All Files (*)")
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
                        # self.dlg.progressBar.setValue(0)
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
                                    # self.dlg.progressBar.setValue(100)

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


    #Load shp kml kmz vector files
    def load_vector_file(self):  # Updated function name to reflect broader support
        # parent_directory = os.path.dirname(self.destfile)
        file_filter = "Vector Files (*.shp *.kml *.kmz)"
        self.vector_file_path = QFileDialog.getOpenFileName(self.dlg, 'Open vector file', '', file_filter)
        
        if not self.vector_file_path[0]:
            return  # User cancelled file selection
        
        file_extension = os.path.splitext(self.vector_file_path[0])[1].lower()
        
        if file_extension not in ['.shp', '.kml', '.kmz']:
            self.print_to_scroll_area(f"<span style='color:orange;'>{self.vector_file_path[0]} is not a valid vector file</span>")
            self.warning_popup("Warning", f"{self.vector_file_path[0]} is not a valid vector file. Please select a .shp, .kml, or .kmz file.")
            return 
        else:
            file_type = "Shapefile" if file_extension == '.shp' else "KML file" if file_extension == '.kml' else "KMZ file"
            self.print_to_scroll_area(f"<span style='color:blue;'>{self.vector_file_path[0]}</span> ({file_type}) loaded for subset!")
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
                # self.dlg.progressBar.setMaximum(total_files)
                
                # Display progression using print()
                for i, member in enumerate(tar.getmembers()):
                    tar.extract(member, self.extract_path)
                    # Update the progress bar value
                    # self.dlg.progressBar.setValue(i+1)
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


    def layer_stacking(self):
        import os
        import re
        import earthpy.spatial as es
        import rasterio
        
        if self.landsat_file[0].endswith(".tif"):
            self.print_to_scroll_area('input file is in tif format, Layerstacking not supported')
            return
            
        bands_directory = self.extract_path
        band_fnames = []
        
        # Dictionary mapping band numbers to their descriptive names
        band_names = {
            '1': 'Coastal_Aerosol',
            '2': 'Blue',
            '3': 'Green',
            '4': 'Red',
            '5': 'NIR',
            '6': 'SWIR1',
            '7': 'SWIR2'
        }
        
        # iterate through the directory
        for filename in os.listdir(bands_directory):
            if re.search(r'(T1|SR)_B[1-7]\.TIF$', filename):
                band_number = re.search(r'(T1|SR)_B([1-7])\.TIF$', filename).group(2)
                band_fnames.append((band_number, filename))
                
        self.print_to_scroll_area("Attempting <span style='color:orange;'>LayerStacking</span>")
        
        # Sort band_fnames by band number to ensure correct order
        band_fnames.sort(key=lambda x: int(x[0]))
        
        # Create the full path for each input file
        input_path = self.extract_path
        band_paths = [os.path.join(input_path, fname[1]) for fname in band_fnames]
        
        # Define the path to save the stacked image
        outputs_folder = self.working_path
        self.destfile = os.path.join(outputs_folder, "LayerStack.tif")
        
        # Stack the images and save the output
        arr, arr_meta = es.stack(band_paths, self.destfile)
        
        # Update the band descriptions in the output file
        with rasterio.open(self.destfile, 'r+') as src:
            for idx, (band_number, _) in enumerate(band_fnames, start=1):
                src.set_band_description(idx, band_names[band_number])
        
        self.print_to_scroll_area(f"<span style='color:green;'>Layerstacking done successfully:</span> {self.destfile}")
        self.print_to_scroll_area("Band names have been updated with descriptive labels")


    def global_oif(self):  # WORKING #
        self.print_to_scroll_area("Loading <span style='color:blue;'>Landsat 8</span> file ...")
        
        global destfile
        oif_tif_input = self.destfile
        self.print_to_scroll_area(f"{self.destfile} is the input for OIF")

        # Open the raster file
        with rasterio.open(oif_tif_input) as src:
            # Read the data into memory
            bands = [src.read(i) for i in range(1, src.count + 1)]

            shape = src.shape
            self.print_to_scroll_area(f"<span style='color:green;'>{oif_tif_input}</span> loaded successfully")
            
            # Initialize the correlations matrix
            correlations = np.zeros((src.count, src.count))

            self.print_to_scroll_area("<span style='color:orange;'>OIF Calculation</span> started, please wait ...")

            # Calculate the correlations for the band pairs
            for i in range(src.count):
                for j in range(i, src.count):
                    correlations[i][j] = np.corrcoef(bands[i].flatten(), bands[j].flatten())[0][1]
                    correlations[j][i] = correlations[i][j]

            # Use parallel processing to calculate OIF for each combination of bands
            oif_results = self.oif_parallel(bands, correlations)

            # Sort OIF results based on the OIF values in descending order
            oif_results.sort(key=lambda x: x[2], reverse=True)

            # Save the OIF results to a text file
            oif_txt = os.path.join(self.working_path, "OIF_Ranks.txt")
            with open(oif_txt, 'w') as f:
                for i, (index, comb, oif) in enumerate(oif_results):
                    self.print_to_scroll_area(
                        "OIF{}= {:>2}:  band{}  band{}  band{}  ({:.2f})".format(
                            index, i+1, comb[0]+1, comb[1]+1, comb[2]+1, oif))
                    
                    oif_string = "OIF{}= {:>2}:  band{}  band{}  band{}  ({:.2f})\n".format(
                        index, i+1, comb[0]+1, comb[1]+1, comb[2]+1, oif)
                    f.write(oif_string)

            self.print_to_scroll_area("\nOIF Calculation done successfully")
            self.print_to_scroll_area(f"OIF Ranks saved in <span style='color:green;'>{self.working_path}</span>")

    def oif_parallel(self, bands, correlations):
        """Parallelizes the OIF calculation for large data."""
        n_bands = len(bands)
        comb = list(itertools.combinations(range(n_bands), 3))
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.calculate_oif, bands, correlations, i, j, k) for i, j, k in comb]
            
            # Gather the results as they complete
            oif_values = [future.result() for future in concurrent.futures.as_completed(futures)]

        return list(zip(range(len(oif_values)), comb, oif_values))

    def calculate_oif(self, bands, correlations, i, j, k):
        """Calculates the OIF for a given combination of three bands."""
        Stdi = np.std(bands[i])
        Stdj = np.std(bands[j])
        Stdk = np.std(bands[k])
        Corrij = correlations[i][j]
        Corrik = correlations[i][k]
        Corrjk = correlations[j][k]
        oif = (Stdi + Stdj + Stdk) / (abs(Corrij) + abs(Corrik) + abs(Corrjk))
        return oif

    def calculate_pca(self):
        import numpy as np
        from sklearn.decomposition import PCA
        from osgeo import gdal
        import gc
        
        self.print_to_scroll_area("PCA Calculation started ...")
        
        # Define chunk size for processing
        CHUNK_SIZE = 1000
        
        def get_dataset_info(ds):
            """Get basic information about the dataset."""
            cols = ds.RasterXSize
            rows = ds.RasterYSize
            bands = ds.RasterCount
            return rows, cols, bands
        
        def process_chunk(data_chunk):
            """Process a chunk of data, handling NaN values."""
            # Replace NaN with mean of each band
            for i in range(data_chunk.shape[2]):
                band_data = data_chunk[:, :, i]
                mean_val = np.nanmean(band_data)
                band_data[np.isnan(band_data)] = mean_val
            return data_chunk
        
        try:
            # Open the dataset
            ds = gdal.Open(self.destfile)
            if ds is None:
                raise ValueError("Could not open the input file")
            
            # Get dataset dimensions
            rows, cols, n_bands = get_dataset_info(ds)
            
            # Calculate chunks
            n_chunks_y = (rows + CHUNK_SIZE - 1) // CHUNK_SIZE
            n_chunks_x = (cols + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            # First pass: Calculate mean and std for standardization
            self.print_to_scroll_area("Pass 1: Calculating statistics...")
            
            # Initialize arrays for running statistics
            sum_x = np.zeros(n_bands)
            sum_x2 = np.zeros(n_bands)
            n_samples = 0
            
            for chunk_y in range(n_chunks_y):
                y_offset = chunk_y * CHUNK_SIZE
                y_size = min(CHUNK_SIZE, rows - y_offset)
                
                for chunk_x in range(n_chunks_x):
                    x_offset = chunk_x * CHUNK_SIZE
                    x_size = min(CHUNK_SIZE, cols - x_offset)
                    
                    # Read chunk
                    chunk_data = np.zeros((y_size, x_size, n_bands), dtype=np.float32)
                    for b in range(n_bands):
                        band = ds.GetRasterBand(b + 1)
                        chunk_data[:, :, b] = band.ReadAsArray(x_offset, y_offset, x_size, y_size)
                    
                    # Process chunk
                    chunk_data = process_chunk(chunk_data)
                    chunk_reshaped = chunk_data.reshape(-1, n_bands)
                    
                    # Update running statistics
                    sum_x += np.nansum(chunk_reshaped, axis=0)
                    sum_x2 += np.nansum(chunk_reshaped ** 2, axis=0)
                    n_samples += chunk_reshaped.shape[0]
                    
                    del chunk_data, chunk_reshaped
                    gc.collect()
            
            # Calculate mean and std
            mean = sum_x / n_samples
            std = np.sqrt(sum_x2/n_samples - mean**2)
            
            # Initialize PCA
            pca = PCA(n_components=n_bands)
            
            # Second pass: Collect covariance statistics
            self.print_to_scroll_area("Pass 2: Computing PCA...")
            
            # Create output file
            pca_output = os.path.join(self.working_path, "PCA.tif")
            driver = gdal.GetDriverByName('GTiff')
            out_ds = driver.Create(pca_output, cols, rows, n_bands, gdal.GDT_Float32,
                                 options=['TILED=YES', 'COMPRESS=LZW'])
            
            if out_ds is None:
                raise ValueError("Could not create output file")
            
            # Copy projection and geotransform
            out_ds.SetProjection(ds.GetProjection())
            out_ds.SetGeoTransform(ds.GetGeoTransform())
            
            # Initialize arrays for PCA statistics
            cov_matrix = np.zeros((n_bands, n_bands))
            total_processed = 0
            
            # Compute covariance matrix
            for chunk_y in range(n_chunks_y):
                y_offset = chunk_y * CHUNK_SIZE
                y_size = min(CHUNK_SIZE, rows - y_offset)
                
                for chunk_x in range(n_chunks_x):
                    x_offset = chunk_x * CHUNK_SIZE
                    x_size = min(CHUNK_SIZE, cols - x_offset)
                    
                    # Read and process chunk
                    chunk_data = np.zeros((y_size, x_size, n_bands), dtype=np.float32)
                    for b in range(n_bands):
                        band = ds.GetRasterBand(b + 1)
                        chunk_data[:, :, b] = band.ReadAsArray(x_offset, y_offset, x_size, y_size)
                    
                    chunk_data = process_chunk(chunk_data)
                    chunk_reshaped = chunk_data.reshape(-1, n_bands)
                    
                    # Standardize data
                    chunk_standardized = (chunk_reshaped - mean) / std
                    
                    # Update covariance matrix
                    cov_matrix += np.dot(chunk_standardized.T, chunk_standardized)
                    total_processed += chunk_standardized.shape[0]
                    
                    progress = ((chunk_y * n_chunks_x + chunk_x + 1) / (n_chunks_y * n_chunks_x)) * 100
                    self.print_to_scroll_area(f"Progress: {progress:.1f}%")
                    
                    del chunk_data, chunk_reshaped, chunk_standardized
                    gc.collect()
            
            # Finalize covariance matrix
            cov_matrix /= total_processed
            
            # Fit PCA
            pca.fit(np.eye(n_bands))  # Initialize with identity matrix
            pca.components_ = np.linalg.eigh(cov_matrix)[1][::-1].T
            pca.explained_variance_ = np.linalg.eigvals(cov_matrix)[::-1]
            
            # Third pass: Transform data and write output
            self.print_to_scroll_area("Pass 3: Writing PCA results...")
            
            for chunk_y in range(n_chunks_y):
                y_offset = chunk_y * CHUNK_SIZE
                y_size = min(CHUNK_SIZE, rows - y_offset)
                
                for chunk_x in range(n_chunks_x):
                    x_offset = chunk_x * CHUNK_SIZE
                    x_size = min(CHUNK_SIZE, cols - x_offset)
                    
                    # Read and process chunk
                    chunk_data = np.zeros((y_size, x_size, n_bands), dtype=np.float32)
                    for b in range(n_bands):
                        band = ds.GetRasterBand(b + 1)
                        chunk_data[:, :, b] = band.ReadAsArray(x_offset, y_offset, x_size, y_size)
                    
                    chunk_data = process_chunk(chunk_data)
                    chunk_reshaped = chunk_data.reshape(-1, n_bands)
                    
                    # Transform chunk
                    chunk_standardized = (chunk_reshaped - mean) / std
                    chunk_transformed = np.dot(chunk_standardized, pca.components_.T)
                    chunk_transformed = chunk_transformed.reshape(y_size, x_size, n_bands)
                    
                    # Write transformed chunk
                    for b in range(n_bands):
                        band = out_ds.GetRasterBand(b + 1)
                        band.WriteArray(chunk_transformed[:, :, b], x_offset, y_offset)
                    
                    del chunk_data, chunk_reshaped, chunk_transformed
                    gc.collect()
            
            # Clean up
            ds = None
            out_ds = None
            
            self.print_to_scroll_area(f"PCA done successfully, PCA file: {pca_output}")
            
            # Calculate and display explained variance ratios
            explained_variance_ratio = pca.explained_variance_ / np.sum(pca.explained_variance_)
            for i, ratio in enumerate(explained_variance_ratio):
                self.print_to_scroll_area(f"PC{i+1} explains {ratio*100:.2f}% of variance")
                
        except MemoryError:
            self.print_to_scroll_area("Error: Unable to allocate memory for PCA computation.")
        except Exception as e:
            self.print_to_scroll_area(f"Error in Calculate PCA: {str(e)}")

        # QApplication.processEvents()


        # QApplication.processEvents()

    def calculate_mnf(self): #Working
        import numpy as np
        import rasterio
        import dask.array as da
        from unmixing.transform import mnf_rotation
        from unmixing.lsma import ravel_and_filter
        import pysptools.util as sp_utils
        from dask.diagnostics import ProgressBar
        import gc  # For explicit garbage collection
        
        self.print_to_scroll_area("MNF Calculation started ...")
        
        # Define chunk sizes for both reading and processing
        WINDOW_SIZE = 1000  # Size of windows to process at once
        
        # First, get the image dimensions and metadata
        with rasterio.open(self.destfile) as src:
            gt = src.transform
            crs = src.crs  # Store CRS directly
            n_bands = src.count
            height = src.height
            width = src.width
            
            # Calculate the number of windows needed
            n_windows_y = (height + WINDOW_SIZE - 1) // WINDOW_SIZE
            n_windows_x = (width + WINDOW_SIZE - 1) // WINDOW_SIZE
            
            # Initialize stats for noise calculation
            noise_stats = np.zeros((n_bands, n_bands))
            signal_stats = np.zeros((n_bands, n_bands))
            valid_pixels = 0
            
            # Process the image in windows
            windows_processed = 0
            total_windows = n_windows_y * n_windows_x
            
            # Create output file
            input_file_name = os.path.splitext(os.path.basename(self.destfile))[0]
            mnf_output = os.path.join(self.working_path, f"{input_file_name}_MNF.tif")
            
            profile = {
                'driver': 'GTiff',
                'dtype': 'float32',
                'count': n_bands,
                'height': height,
                'width': width,
                'crs': crs,  # Use CRS directly
                'transform': gt,
                'compress': 'lzw',
                'tiled': True,
                'blockxsize': 256,
                'blockysize': 256
            }
            
            # First pass: calculate statistics
            self.print_to_scroll_area("Pass 1: Calculating statistics...")
            running_mean = np.zeros(n_bands)
            running_cov = np.zeros((n_bands, n_bands))
            n_samples = 0
            
            for window_y in range(n_windows_y):
                for window_x in range(n_windows_x):
                    window = rasterio.windows.Window(
                        window_x * WINDOW_SIZE, 
                        window_y * WINDOW_SIZE,
                        min(WINDOW_SIZE, width - window_x * WINDOW_SIZE),
                        min(WINDOW_SIZE, height - window_y * WINDOW_SIZE)
                    )
                    
                    # Read the window
                    data = src.read(window=window)
                    data = data.astype(np.float32)
                    
                    # Reshape to (n_bands, pixels)
                    data_reshaped = data.reshape(n_bands, -1)
                    
                    # Filter valid pixels
                    valid_mask = ~np.isnan(data_reshaped[0])
                    valid_data = data_reshaped[:, valid_mask]
                    
                    if valid_data.size > 0:
                        # Update running statistics
                        n = valid_data.shape[1]
                        delta = valid_data - running_mean[:, None]
                        running_mean += np.sum(delta, axis=1) / (n_samples + n)
                        running_cov += np.dot(delta, delta.T)
                        n_samples += n
                    
                    del data, data_reshaped, valid_data
                    gc.collect()
            
            # Calculate final covariance
            if n_samples > 0:
                running_cov /= n_samples
            
            # Perform eigendecomposition
            eigenvals, eigenvecs = np.linalg.eigh(running_cov)
            idx = eigenvals.argsort()[::-1]
            eigenvals = eigenvals[idx]
            eigenvecs = eigenvecs[:, idx]
            
            # Second pass: apply MNF transformation
            self.print_to_scroll_area("Pass 2: Applying MNF transformation...")
            with rasterio.open(mnf_output, 'w', **profile) as dst:
                for window_y in range(n_windows_y):
                    for window_x in range(n_windows_x):
                        window = rasterio.windows.Window(
                            window_x * WINDOW_SIZE, 
                            window_y * WINDOW_SIZE,
                            min(WINDOW_SIZE, width - window_x * WINDOW_SIZE),
                            min(WINDOW_SIZE, height - window_y * WINDOW_SIZE)
                        )
                        
                        # Read the window
                        data = src.read(window=window)
                        data = data.astype(np.float32)
                        
                        # Apply MNF transformation
                        original_shape = data.shape
                        data_reshaped = data.reshape(n_bands, -1)
                        
                        # Transform the data
                        transformed = np.dot(eigenvecs.T, data_reshaped)
                        
                        # Reshape back to original shape
                        transformed = transformed.reshape(original_shape)
                        
                        # Write the transformed data
                        dst.write(transformed, window=window)
                        
                        windows_processed += 1
                        progress = (windows_processed / total_windows) * 100
                        self.print_to_scroll_area(f"Progress: {progress:.1f}%")
                        
                        del data, transformed
                        gc.collect()
        
        self.print_to_scroll_area(f"MNF done successfully, MNF file: {mnf_output}")






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

    def calculate_ica(self):
        from osgeo import gdal
        import numpy as np
        from sklearn.decomposition import FastICA
        import os
        import gc
        
        self.print_to_scroll_area("ICA Calculation started ...")
        
        try:
            # Open the dataset without using 'with'
            ds = gdal.Open(self.destfile)
            if ds is None:
                raise ValueError(f"Could not open the input file: {self.destfile}")
            
            try:
                # Get image dimensions
                x_size = ds.RasterXSize
                y_size = ds.RasterYSize
                n_bands = ds.RasterCount
                
                self.print_to_scroll_area(f"Image dimensions: {x_size}x{y_size} pixels, {n_bands} bands")
                
                # Check if image is too large
                if x_size > 3000 or y_size > 3000:
                    self.print_to_scroll_area('ICA not supported for large files (>3000 pixels in any dimension)')
                    self.print_to_scroll_area('Please consider cropping your image first')
                    return
                
                # Proceed with ICA if image size is acceptable
                self.print_to_scroll_area(f"Image size acceptable, proceeding with ICA...")
                
                try:
                    # Initialize output array
                    data = np.zeros((x_size * y_size, n_bands), dtype=np.float32)
                    
                    # Read bands
                    for i in range(n_bands):
                        band = ds.GetRasterBand(i + 1)
                        band_data = band.ReadAsArray()
                        if band_data is None:
                            raise ValueError(f"Failed to read band {i+1}")
                        
                        # Handle NoData values
                        nodata_value = band.GetNoDataValue()
                        if nodata_value is not None:
                            band_data = np.where(band_data == nodata_value, np.nan, band_data)
                        
                        # Reshape and store band data
                        data[:, i] = band_data.reshape(-1)
                        
                        # Clean up
                        band_data = None
                        gc.collect()
                    
                    self.print_to_scroll_area("Data loaded successfully, performing ICA...")
                    
                    # Handle NaN values
                    if np.isnan(data).any():
                        self.print_to_scroll_area("Handling NoData values...")
                        for i in range(n_bands):
                            column = data[:, i]
                            mean_val = np.nanmean(column)
                            column[np.isnan(column)] = mean_val
                    
                    # Perform ICA
                    n_components = min(7, n_bands)  # Ensure we don't exceed number of bands
                    ica = FastICA(n_components=n_components, random_state=42)
                    transformed = ica.fit_transform(data)
                    
                    # Clean up input data
                    data = None
                    gc.collect()
                    
                    # Create output file
                    ica_output = os.path.join(self.working_path, "ICA.tif")
                    driver = gdal.GetDriverByName("GTiff")
                    
                    # Create output dataset with compression
                    out_ds = driver.Create(
                        ica_output, 
                        x_size, 
                        y_size, 
                        n_components, 
                        gdal.GDT_Float32,
                        options=['COMPRESS=LZW', 'TILED=YES']
                    )
                    
                    if out_ds is None:
                        raise ValueError("Could not create output file")
                    
                    # Copy projection and geotransform
                    out_ds.SetGeoTransform(ds.GetGeoTransform())
                    out_ds.SetProjection(ds.GetProjection())
                    
                    # Write transformed data
                    for i in range(n_components):
                        out_band = out_ds.GetRasterBand(i + 1)
                        out_band.WriteArray(transformed[:, i].reshape(y_size, x_size))
                        out_band.SetNoDataValue(-9999)
                        
                        # Calculate statistics for each band
                        out_band.ComputeStatistics(False)
                        
                        # Update progress
                        progress = ((i + 1) / n_components) * 100
                        self.print_to_scroll_area(f"Writing band {i+1}/{n_components} ({progress:.1f}%)")
                    
                    # Clean up
                    transformed = None
                    out_ds = None
                    ds = None
                    gc.collect()
                    
                    self.print_to_scroll_area(f"ICA completed successfully!")
                    self.print_to_scroll_area(f"Output file: {ica_output}")
                    
                except MemoryError:
                    self.print_to_scroll_area("Error: Not enough memory to process this image")
                    self.print_to_scroll_area("Consider reducing the image size or freeing up system memory")
                    
                except Exception as e:
                    self.print_to_scroll_area(f"Error during ICA processing: {str(e)}")
                    
            finally:
                # Ensure dataset is properly closed
                if ds is not None:
                    ds = None
                    
        except Exception as e:
            self.print_to_scroll_area(f"Error opening input file: {str(e)}")
            if ds is not None:
                ds = None

            


    

    #Subset by a vector file : .shp / .kml / .kmz
    def subset_by_vector(self):
        self.print_to_scroll_area("Subset triggered")
        if not self.vector_file_path[0] or not self.destfile:
            self.print_to_scroll_area("<span style='color:red;'>LayerStack image and/or vector file is missing!</span>")
            return

        # Load the KML/KMZ or shapefile using QgsVectorLayer
        file_extension = os.path.splitext(self.vector_file_path[0])[1].lower()
        if file_extension in ['.kml', '.kmz', '.shp']:
            vector_layer = QgsVectorLayer(self.vector_file_path[0], "vector_layer", "ogr")
            if not vector_layer.isValid():
                self.print_to_scroll_area("<span style='color:red;'>Failed to load vector layer!</span>")
                return
        else:
            self.print_to_scroll_area("<span style='color:red;'>Unsupported file format. Please use .shp, .kml, or .kmz</span>")
            return

        # Load the raster
        raster_layer = gdal.Open(self.destfile)
        if not raster_layer:
            self.print_to_scroll_area("<span style='color:red;'>Failed to load raster file!</span>")
            return

        # Ensure CRS match between vector and raster
        raster_crs = QgsCoordinateReferenceSystem(raster_layer.GetProjection())
        vector_crs = vector_layer.crs()
        if vector_crs != raster_crs:
            transformer = QgsCoordinateTransform(vector_crs, raster_crs, QgsProject.instance())
            vector_layer.setCrs(raster_crs)

        # Define output file path for the subset
        output_file = os.path.join(self.working_path, "Subset.tif")

        # Subset the raster using the vector file
        try:
            gdal.Warp(
                output_file, self.destfile,
                cutlineDSName=self.vector_file_path[0],
                cropToCutline=True,
                dstNodata=-9999
            )
            self.destfile = output_file
            self.print_to_scroll_area(f"Subset done successfully, saved to {output_file}")
        except Exception as e:
            self.print_to_scroll_area(f"<span style='color:red;'>Error during subsetting: {str(e)}</span>")
            return

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
    def index_activated(self, indice_text):
        choice_text = ["Modified Normalized Difference Water Index (MNDWI)", 
        "Normalized Difference Enhanced Sand Index (NDESI)", 
        "Normalized Difference Vegetation Index (NDVI)", 
        "Normalized Difference Water Index (NDWI)", 
        "Clay Minerals Ratio", 
        "Ferrous Minerals Ratio", 
        "Iron Oxyde Ratio",
        "Modified Bare Soil Index (BSI)",
        "Enhanced Vegetation Index (EVI)",
        "Modified Soil Adjusted Vegetation Index (MSAVI)",
        "Normalized Burn Ratio (NBR)",
        "Normalized Burn Ratio 2 (NBR2)",
        "Normalized Difference Built-up Index (NDBI)",
        "Normalized Difference Snow Index (NDSI)", 
        "Soil Adjusted Vegetation Index (SAVI)"]

        self.selected_index = ""

        for code in choice_text:
            if indice_text == code:
                self.selected_index = code

    # Newli added indices ######################
    def calculate_mbi(self, input_path):
        with rasterio.open(input_path) as src:
            nir = src.read(5).astype('float32')
            swir1 = src.read(6).astype('float32')
            swir2 = src.read(7).astype('float32')

            mbi = ((swir1 - swir2 - nir) / (swir1 + swir2 + nir)) + 0.5

            return mbi
    
    def calculate_evi(self, input_path):
        import numpy
        with rasterio.open(input_path) as src:
            # Read bands
            nir = src.read(5).astype('float32')  # Band 5 (NIR)
            red = src.read(4).astype('float32')  # Band 4 (Red)
            blue = src.read(2).astype('float32') # Band 2 (Blue)
            
            # Create a mask for invalid values 
            # Landsat 8 uses 0 for NoData/fill values
            mask = (nir > 0) & (red > 0) & (blue > 0)
            
            # Landsat 8 scaling factors
            scale_factor = 0.0000275
            offset = -0.2
            
            # Convert DN to reflectance values
            nir = nir * scale_factor + offset
            red = red * scale_factor + offset
            blue = blue * scale_factor + offset
            
            # Additional mask for valid reflectance values
            # Reflectance values should be between 0 and 1
            mask = mask & (nir >= 0) & (red >= 0) & (blue >= 0) & (nir <= 1) & (red <= 1) & (blue <= 1)
            
            # Calculate EVI
            numerator = nir - red
            denominator = nir + 6.0 * red - 7.5 * blue + 1.0
            
            # Initialize EVI array
            evi = numpy.zeros_like(nir)
            
            # Calculate EVI only for valid pixels
            valid = (denominator != 0) & mask
            evi[valid] = 2.5 * (numerator[valid] / denominator[valid])
            
            # Clip values to valid EVI range (-1 to 1)
            evi = numpy.clip(evi, -1.0, 1.0)
            
            # Set non-valid pixels to NoData value
            evi[~valid] = numpy.nan
            
        return evi
    
    def calculate_msavi(self, input_path):
        import numpy as np
        with rasterio.open(input_path) as src:
            nir = src.read(5).astype('float32') #Band 5
            red = src.read(4).astype('float32') #Band 4

            msavi = (2 * nir + 1 - np.sqrt((2 * nir + 1)**2 - 8 * (nir - red))) / 2

            return msavi

    def calculate_nbr(self, input_path):
        with rasterio.open(input_path) as src:
            nir = src.read(5).astype('float32') #Band 5
            swir2 = src.read(7).astype('float32') #Band 7

            nbr = (nir - swir2) / (nir + swir2)

            return nbr

    def calculate_nbr2(self, input_path):
        with rasterio.open(input_path) as src:
            swir1 = src.read(6).astype('float32') #Band 7
            swir2 = src.read(7).astype('float32') #Band 7

            nbr2 = (swir1 - swir2) / (swir1 + swir2)

            return nbr2

    def calculate_ndbi(self, input_path):
        with rasterio.open(input_path) as src:
            nir = src.read(5).astype('float32')
            swir1 = src.read(6).astype('float32')

            ndbi = (swir1 - nir) / (swir1 + nir)

            return ndbi
    

    def calculate_ndsi(self, input_path): 
        with rasterio.open(input_path) as src:
        
            green = src.read(3).astype('float32')
            swir1 = src.read(6).astype('float32')

            ndsi = (green - swir1) / (green + swir1)

            return ndsi

    def calculate_savi(self, input_path):
        with rasterio.open(input_path) as src:
            red = src.read(4).astype('float32')
            nir = src.read(5).astype('float32')

            savi = ((nir - red) / (nir + red + 0.5)) * (1.5)

            return savi

    #############################################

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
        "Iron Oxyde Ratio": "Iron", 
        "Modified Bare Soil Index (BSI)" : "BSI",
            "Enhanced Vegetation Index (EVI)" : "EVI",
            "Modified Soil Adjusted Vegetation Index (MSAVI)" : "MSAVI",
            "Normalized Burn Ratio (NBR)" : "NBR",
            "Normalized Burn Ratio 2 (NBR2)" : "NBR2",
            "Normalized Difference Built-up Index (NDBI)" : "NDBI",
            "Normalized Difference Snow Index (NDSI)" : "NDSI", 
            "Soil Adjusted Vegetation Index (SAVI)" : "SAVI"
        }

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

                elif self.selected_index == "Modified Bare Soil Index (BSI)":
                    index_output = self.calculate_mbi(input_path)

                elif self.selected_index == "Enhanced Vegetation Index (EVI)":
                    index_output = self.calculate_evi(input_path)

                elif self.selected_index == "Modified Soil Adjusted Vegetation Index (MSAVI)":
                    index_output = self.calculate_msavi(input_path)

                elif self.selected_index == "Normalized Burn Ratio (NBR)":
                    index_output = self.calculate_nbr(input_path)

                elif self.selected_index == "Normalized Burn Ratio 2 (NBR2)":
                    index_output = self.calculate_nbr2(input_path)

                elif self.selected_index == "Normalized Difference Built-up Index (NDBI)":
                    index_output = self.calculate_ndbi(input_path)

                elif self.selected_index == "Normalized Difference Snow Index (NDSI)":
                    index_output = self.calculate_ndsi(input_path)

                elif self.selected_index == "Soil Adjusted Vegetation Index (SAVI)":
                    index_output = self.calculate_savi(input_path)
                
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

    def show_popup(self):
        import webbrowser
        # Create a QMessageBox instance
        self.msg_box = QMessageBox()

        # Set the title and message for the pop-up
        self.msg_box.setWindowTitle("PyGeoRS v0.2")
        self.msg_box.setText("All tasks were completed successfully. Do you want to open the output folder?")

        # Set the icon type (information, warning, etc.)
        self.msg_box.setIcon(QMessageBox.Information)

        # Add two buttons: one for opening the folder, one for closing
        open_button = self.msg_box.addButton("Open Folder", QMessageBox.AcceptRole)
        close_button = self.msg_box.addButton("Close", QMessageBox.RejectRole)

        # Show the pop-up and wait for the user to click the button
        self.msg_box.exec_()

        # Check which button was clicked
        if self.msg_box.clickedButton() == open_button:
            # Open the output folder location
            output_folder = self.working_path  # Assuming self.working_path is the output folder path
            if os.path.exists(output_folder):
                webbrowser.open(f"file:///{output_folder}")
            else:
                self.print_to_scroll_area("<span style='color:red;'>Output folder does not exist!</span>")
        elif self.msg_box.clickedButton() == close_button:
            # Close the pop-up and do nothing
            pass

    def set_folder_and_proceed(self):
        import time
        start_time = time.time()

        if self.working_path:
            # List of tasks, explicitly converting conditions to boolean
            tasks = [
                bool(self.dlg.cB_extract_archive.isChecked()),
                bool(self.dlg.cB_layer_stacking.isChecked()),
                bool(self.dlg.cB_dn_to_toa.isChecked() and self.loaded_file_is_archive),
                bool(self.dlg.cB_generate_fcc.isChecked()),
                bool(self.dlg.radioButton.isChecked() and self.vector_file_path and self.vector_file_path[0] and self.destfile),
                bool(self.dlg.cB_calculate_oif.isChecked()),
                bool(self.dlg.cB_calculate_pca.isChecked()),
                bool(self.dlg.cB_calculate_mnf.isChecked()),
                bool(self.dlg.cB_calculate_ica.isChecked()),
                bool(self.dlg.cB_calculate_index.isChecked()),
                bool(self.dlg.cB_calculate_br.isChecked()),
                bool(self.dlg.cB_calculate_all_br.isChecked()),
                bool(self.dlg.cB_abrams.isChecked()),
                bool(self.dlg.cB_sabins.isChecked()),
                bool(self.dlg.cB_kaufmann.isChecked()),
            ]

            # Count how many tasks are checked (i.e., need to be executed)
            total_tasks = sum(tasks)

            # Set progress bar maximum value to the number of tasks
            self.dlg.progressBar.setMaximum(total_tasks)
            self.dlg.progressBar.setValue(0)

            # Track the progress as tasks complete
            task_counter = 0

            if self.dlg.cB_extract_archive.isChecked():
                self.extract_landsat_archive()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_layer_stacking.isChecked():
                self.layer_stacking()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_dn_to_toa.isChecked() and self.loaded_file_is_archive:
                self.dn_to_toa_archive()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_generate_fcc.isChecked():
                self.set_fcc()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.radioButton.isChecked() and self.vector_file_path and self.vector_file_path[0] and self.destfile:
                self.subset_by_vector()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_oif.isChecked():
                self.global_oif()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_pca.isChecked():
                self.calculate_pca()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_mnf.isChecked():
                self.calculate_mnf()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_ica.isChecked():
                self.calculate_ica()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_index.isChecked():
                global input_is_tif
                self.save_index_image()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_br.isChecked():
                self.calculate_band_ratio()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_calculate_all_br.isChecked():
                self.calculate_all_band_ratios()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_abrams.isChecked():
                self.abrams()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_sabins.isChecked():
                self.sabins()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            if self.dlg.cB_kaufmann.isChecked():
                self.kaufmann()
                task_counter += 1
                self.dlg.progressBar.setValue(task_counter)
                QApplication.processEvents()

            self.print_to_scroll_area("<b><span style='color:Red;'>All tasks ended successfully</span></b>")

            end_time = time.time()
            processing_time = end_time - start_time
            self.print_to_scroll_area(f"Processing time: {processing_time:.2f} seconds")

            # Reset progress bar to 0 once all tasks are completed
            self.dlg.progressBar.setValue(0)

            self.show_popup()

        else:
            self.print_to_scroll_area('Input file or output folder not defined')


