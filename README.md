# PyGeoRS

**PyGeoRS** is a dynamic QGIS plugin tailored to enhance and automate your remote sensing tasks within the QGIS environment.

- **Version**: v0.1
- **Supported QGIS Version**: v3.X
## How to install
- Download the [beta release](https://github.com/AnassMarzouki/PyGeoRS/releases/download/v0.1/pygeors.zip).
- In QGIS, navigate to Plugins menu
- click 'Manage and Install plugins'
- From the left tabs, select 'Install from ZIP'
- load 'pygeors.zip' and hit Install
- When installation is finished, please restart QGIS

## Features

### Basic Tasks:
- **Automatic extraction** of Landsat archive and read its metadata.
- **Automatic LayerStacking** of bands 1 to 7.
- **Data subset** using a shapefile (*.shp).
- **Convert DN to ToA**.
  
### Advanced Tasks:
- **Calculate Optimum Index Factor (OIF)**
- **Principal Component Analysis (PCA)**
- **Minimum Noise Fraction (MNF)**
- **Spectral Indices** such as:
  - Normalized Difference Vegetation Index (NDVI)
  - Normalized Difference Water Index (NDWI)
  - Modified Normalized Difference Water Index (MNDWI)
  - Normalized Difference Enhanced Sand Index (NDESI)
- **Predefined Band Ratios** such as:
  - Abrams Ratio
  - Sabins Ratio
  - Kaufmann Ratio
- **Calculate Custom Band Ratio**
- **Calculate All possible Band Ratios**
- **Generate False Color images**

## Dependencies

Apart from the built-in libraries within QGIS, PyGeoRS requires the following external libraries:

- Rasterio
- Unmixing
- SciKit-learn
- EarthPy

These dependencies are set to be automatically installed with the plugin. If, for any reason, the plugin fails to install one or more packages, you can manually install them using the OSGeo4W shell:

```bash
pip install package_name
```

## Supported Data

- **Landsat Versions**: Landsat 8 and Landsat 9.
- **Processing Levels**: L1TP and L2SP.
- **File Type Support**: .TAR, .TAR.GZ, .TIF

## Feedback & Contribution

Your feedback and contributions are vital to the continued improvement and development of PyGeoRS. Kindly refer to the official documentation and latest updates on our GitHub repository. Dive in, explore, and let's make the world of remote sensing in QGIS even more vibrant!

## Authors
- **Anass MARZOUKI** - anass.marzouki@usmba.ac.ma
- **Abdallah DRIDRI** - abdallah.dridri@usmba.ac.ma
