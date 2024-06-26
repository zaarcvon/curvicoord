# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CurviCoord
                                 A QGIS plugin
 Plugin for river data conversion from Cartesian to curvilinear orthogonal system
                              -------------------
        begin                : 2024-05-24
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Sergei Freiman
        email                : freimansgy@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsField, QgsGeometry, QgsPointXY, QgsMapLayerProxyModel, QgsMessageLog, Qgis
from qgis.gui import QgsFileWidget
from qgis import processing
from PyQt5.QtCore import QVariant, Qt
from qgis.utils import iface
import geopandas as gpd

import time
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .curvilinear_coordinator_dialog import CurviCoordDialog
import os.path
import numpy as np


class CurviCoord:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CurviCoord_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Curvilinear Coordinator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CurviCoord', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/curvilinear_coordinator/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Curvilinear coordinate'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Curvilinear Coordinator'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started



        if self.first_start == True:
            self.first_start = False
            self.dlg = CurviCoordDialog()
            self.dlg.bounding_polygone_generate_button.clicked.connect(self.generate_bounding_polygone)
            self.dlg.centerline_generate_button.clicked.connect(self.generate_centerline)
            self.dlg.transform_button.clicked.connect(self.transform)
            self.dlg.CreateGrid_PushButton.clicked.connect(self.create_grid)
            self.dlg.Interpolate_PushButton.clicked.connect(self.interpolate)
            self.dlg.SN_Coordinates_RadioButton.toggled.connect(self.SN_coordinates_output)
            self.dlg.XY_Coordinates_RadioButton.toggled.connect(self.XY_coordinates_output)
            self.dlg.InputMeasurements_Widget.fileChanged.connect(self.change_Field_comboBox)
        # Fetch the currently loaded layer
            self.dlg.measurements_input.setFilters(QgsMapLayerProxyModel.PointLayer)
            self.dlg.boundary_polygone_input.setFilters(QgsMapLayerProxyModel.PolygonLayer)
            self.dlg.centerline_input.setFilters(QgsMapLayerProxyModel.LineLayer)
            self.dlg.regular_grid_input.setFilters(QgsMapLayerProxyModel.PointLayer)


            #dialogue stay always on top
            self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
            #QgsFileWidget has mode Save instead of basic Open
            self.dlg.OutputMeasurements_Widget.setStorageMode(QgsFileWidget.SaveFile)
            self.dlg.OutputGrid_Widget.setStorageMode(QgsFileWidget.SaveFile)

        self.bounding_polygone_generate_counts = 0
        self.river_centerline_generate_counts = 0
        self.log_list = []
        self.output_format = 'XY'

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.



            pass

    def generate_bounding_polygone(self):
        '''
        wrapper for concavehull function
        '''
        QgsMessageLog.logMessage("Bounding polygone creation....", 'Messages', level=Qgis.Info)
        self.dlg.bounding_polygone_generate_button.setEnabled(False)
        QCoreApplication.processEvents()
        measurements_name = self.dlg.measurements_input.currentText()
        measurements_layer = QgsProject.instance().mapLayersByName(measurements_name)[0]
        alpha = self.dlg.bounding_polygone_alpha_textfield.text()
        try:
            alpha = float(alpha)
            if alpha>1:
                iface.messageBar().pushMessage("Algorithm failed!", "Alpha should be less or equal 1",
                                               level=Qgis.Critical)
            else:
                bounding_polygone = processing.run("qgis:concavehull", {'INPUT': measurements_layer,
                                                                        'ALPHA': alpha,
                                                                        'HOLES': False,
                                                                        'NO_MULTIGEOMETRY': False,
                                                                        'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
                self.bounding_polygone_generate_counts += 1
                bounding_polygone.setName('Bounding polygone v.' + str(self.bounding_polygone_generate_counts))
                QgsProject.instance().addMapLayer(bounding_polygone)


        except ValueError:
            iface.messageBar().pushMessage("Algorithm failed!", "Alpha should be a float value", level=Qgis.Critical)
            pass

        self.dlg.bounding_polygone_generate_button.setEnabled(True)

    def generate_centerline(self):
        '''
        wrapper for voronoi skeleton function
        '''
        self.dlg.centerline_generate_button.setEnabled(False)
        QgsMessageLog.logMessage("River centerline creation....", 'Messages', level=Qgis.Info)
        QCoreApplication.processEvents()
        smoothness = self.dlg.centerline_smoothness_textfield.text()
        try:
            float(smoothness)
            boundary_polygone_name = self.dlg.boundary_polygone_input.currentText()
            boundary_polygone_layer = QgsProject.instance().mapLayersByName(boundary_polygone_name)[0]
            river_centerline_filename = processing.run("grass7:v.voronoi.skeleton",
                           {'input': boundary_polygone_layer, 'smoothness': smoothness, 'thin': -1, '-a': False, '-s': True,
                            '-l': False, '-t': False,
                            'output': 'TEMPORARY OUTPUT', 'GRASS_REGION_PARAMETER': None,
                            'GRASS_SNAP_TOLERANCE_PARAMETER': -1, 'GRASS_MIN_AREA_PARAMETER': 0.0001,
                            'GRASS_OUTPUT_TYPE_PARAMETER': 0, 'GRASS_VECTOR_DSCO': '', 'GRASS_VECTOR_LCO': '',
                            'GRASS_VECTOR_EXPORT_NOCAT': False})['output']
            self.river_centerline_generate_counts += 1
            river_centerline = QgsVectorLayer(river_centerline_filename, "River centerline v."+ str(self.river_centerline_generate_counts), "ogr")
            QgsProject.instance().addMapLayer(river_centerline)
        except ValueError:
            iface.messageBar().pushMessage("Algorithm failed!", "Smoothness should be a float value", level=Qgis.Critical,
                                           duration=10)
            pass
        self.dlg.centerline_generate_button.setEnabled(True)

    def transform(self):
        '''
        the main function for coordinate transformation
        '''
        measurements_name = self.dlg.measurements_input.currentText()
        selectedmeasurements = QgsProject.instance().mapLayersByName(measurements_name)[0]
        measurements_fieldnames = [field.name() for field in selectedmeasurements.fields()]

        boundary_polygone_name = self.dlg.boundary_polygone_input.currentText()
        selectedpolygone= QgsProject.instance().mapLayersByName(boundary_polygone_name)[0]

        centerline_name = self.dlg.centerline_input.currentText()
        selectedcenterline = QgsProject.instance().mapLayersByName(centerline_name)[0]

        regular_grid_name = self.dlg.regular_grid_input.currentText()
        selected_regular_grid = QgsProject.instance().mapLayersByName(regular_grid_name)[0]

        output_measurements_filename = self.dlg.OutputMeasurements_Widget.filePath()
        output_grid_filename = self.dlg.OutputGrid_Widget.filePath()

        QgsMessageLog.logMessage("Splitting the bounding polygone onto a left and right sides", 'Messages', level=Qgis.Info)

        river_sides = processing.run("native:splitwithlines", {'INPUT': selectedpolygone,
                                                               'LINES': selectedcenterline,
                                                               'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        river_sides_provider = river_sides.dataProvider()
        river_sides_provider.deleteAttributes([i for i in range(len(river_sides.fields()))])
        river_sides_provider.addAttributes([QgsField("Side", QVariant.String)])
        river_sides.updateFields()

        river_sides.startEditing()
        river_sides_provider.changeAttributeValues({1: {0: 'right'}, 2: {0: 'left'}})
        river_sides.commitChanges()

        QgsMessageLog.logMessage("Calculating S coordinate", 'Messages', level=Qgis.Info)

        along_centerline_points = processing.run("native:pointsalonglines", {'INPUT': selectedcenterline,
                                                            'DISTANCE': 0.1, 'START_OFFSET': 0,
                                                            'END_OFFSET': 0,
                                                            'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        QgsMessageLog.logMessage("Calculating N coordinate for input points", 'Messages', level=Qgis.Info)
        pts_riverCS = processing.run("native:joinbynearest", {'INPUT': selectedmeasurements,
                                                              'INPUT_2': along_centerline_points,
                                                              'FIELDS_TO_COPY': [], 'DISCARD_NONMATCHING': False,
                                                              'PREFIX': '', 'NEIGHBORS': 1, 'MAX_DISTANCE': None,
                                                              'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        pts_riverCS = processing.run("native:joinattributesbylocation", {'INPUT': pts_riverCS, 'PREDICATE': [5],
                                                                         'JOIN': river_sides, 'JOIN_FIELDS': [],
                                                                         'METHOD': 0, 'DISCARD_NONMATCHING': False,
                                                                         'PREFIX': '',
                                                                         'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        QgsMessageLog.logMessage("Performing attribute manipulation", 'Messages', level=Qgis.Info)
        # Dealing with column names
        measurements_fieldnames.extend(['distance','distance_2','Side'])
        pts_riverCS = processing.run("native:retainfields", {'INPUT': pts_riverCS,
                                                             'FIELDS': measurements_fieldnames, 'OUTPUT': 'TEMPORARY_OUTPUT'})[
            'OUTPUT']
        pts_riverCS = processing.run("native:renametablefield",
                                     {'INPUT': pts_riverCS, 'FIELD': 'distance', 'NEW_NAME': 'S',
                                      'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        pts_riverCS = processing.run("native:renametablefield",
                                     {'INPUT': pts_riverCS, 'FIELD': 'distance_2', 'NEW_NAME': 'N',
                                      'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']


        provider = pts_riverCS.dataProvider()
        check_outlined_points = 0
        for feature in pts_riverCS.getFeatures():
            side = feature['Side']
            if side == 'left':
                N_coord = feature['N']
            elif side == 'right':
                N_coord = -feature['N']
            else:
                N_coord = -9999
                check_outlined_points += 1
                pts_riverCS.deleteFeature(feature.id())

            provider.changeAttributeValues({feature.id(): {provider.fieldNameMap()['N']: N_coord}})

        if check_outlined_points > 0:
            iface.messageBar().pushMessage("Warning!", '{} track points are outside of the river polygone! They have been deleted!'.format(check_outlined_points), level=Qgis.Warning)
        pts_riverCS.commitChanges()

        QgsMessageLog.logMessage("Input points transformation completed successfully", 'Messages', level=Qgis.Info)
        QgsMessageLog.logMessage("Calculating N coordinate for grid points", 'Messages', level=Qgis.Info)
        regular_grid = processing.run("native:joinattributesbylocation", {'INPUT': selected_regular_grid, 'PREDICATE': [5],
                                                                          'JOIN': river_sides, 'JOIN_FIELDS': [],
                                                                          'METHOD': 0, 'DISCARD_NONMATCHING': False,
                                                                          'PREFIX': '',
                                                                          'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

        regular_grid = processing.run("native:joinbynearest", {'INPUT': regular_grid,
                                                               'INPUT_2': along_centerline_points,
                                                               'FIELDS_TO_COPY': [], 'DISCARD_NONMATCHING': False,
                                                               'PREFIX': '', 'NEIGHBORS': 1, 'MAX_DISTANCE': None,
                                                               'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

        regular_grid = processing.run("native:retainfields",
                                      {'INPUT': regular_grid, 'FIELDS': ['distance', 'distance_2', 'Side'],
                                       'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        regular_grid = processing.run("native:renametablefield",
                                      {'INPUT': regular_grid, 'FIELD': 'distance', 'NEW_NAME': 'S',
                                       'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
        regular_grid = processing.run("native:renametablefield",
                                      {'INPUT': regular_grid, 'FIELD': 'distance_2', 'NEW_NAME': 'N',
                                       'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

        provider = regular_grid.dataProvider()
        check_outlined_points = 0
        regular_grid.startEditing()

        for feature in regular_grid.getFeatures():
            side = feature['Side']
            if side == 'left':
                N_coord = feature['N']
            elif side == 'right':
                N_coord = -feature['N']
            else:
                N_coord = -9999
                check_outlined_points += 1
                regular_grid.deleteFeature(feature.id())
            provider.changeAttributeValues({feature.id(): {provider.fieldNameMap()['N']: N_coord}})

        if check_outlined_points > 0:
            iface.messageBar().pushMessage("Warning!", '{} grid points are outside of the river polygone!'.format(check_outlined_points), level=Qgis.Warning)

        regular_grid.commitChanges()


        if self.output_format == 'SN':
            for lyr in [regular_grid, pts_riverCS]:

                lyr.startEditing()
                lyr.dataProvider().addAttributes([QgsField('X', QVariant.Double),QgsField('Y', QVariant.Double)])
                lyr.updateFields()
                x_index = lyr.fields().indexFromName('X')
                y_index = lyr.fields().indexFromName('Y')
                for feature in lyr.getFeatures():
                    geom = feature.geometry()
                    lyr.changeAttributeValue(feature.id(), x_index, geom.asPoint().x())
                    lyr.changeAttributeValue(feature.id(), y_index, geom.asPoint().y())

                    lyr.changeGeometry(feature.id(), QgsGeometry.fromPointXY(QgsPointXY(feature['S'],feature['N'])))

                lyr.commitChanges()

        settings = QgsVectorFileWriter.SaveVectorOptions()
        settings.driverName = "ESRI Shapefile"
        settings.fileEncoding = 'UTF-8'
        _writer = QgsVectorFileWriter.writeAsVectorFormatV3(regular_grid, output_grid_filename,
                                                            QgsProject.instance().transformContext(), settings)
        _writer = QgsVectorFileWriter.writeAsVectorFormatV3(pts_riverCS, output_measurements_filename,
                                                            QgsProject.instance().transformContext(), settings)
        layer_name = os.path.splitext(os.path.basename(output_measurements_filename))[0]
        pts_riverCS = QgsVectorLayer(output_measurements_filename, layer_name, "ogr")
        QgsProject.instance().addMapLayer(pts_riverCS)

        layer_name = os.path.splitext(os.path.basename(output_grid_filename))[0]
        regular_grid =  QgsVectorLayer(output_grid_filename, layer_name, "ogr")
        QgsProject.instance().addMapLayer(regular_grid)

        self.dlg.InputMeasurements_Widget.setFilePath(output_measurements_filename)
        self.dlg.InputGrid_Widget.setFilePath(output_grid_filename)

    def create_grid(self):
        self.dlg.CreateGrid_PushButton.setEnabled(False)
        QgsMessageLog.logMessage("Creating regular point grid......", 'Messages', level=Qgis.Info)
        QCoreApplication.processEvents()
        point_spacing = self.dlg.PointSpacing_LineEdit.text()
        extent = self.dlg.Extent_Widget.outputExtent()
        try:
            regular_grid = processing.run("qgis:regularpoints",
                                          {'EXTENT': extent, 'SPACING': point_spacing, 'INSET': 0, 'RANDOMIZE': False,
                                           'IS_SPACING': True, 'CRS': QgsProject.instance().crs(),
                                           'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']

            regular_grid.setName('Regular point grid sp.' + str(point_spacing)+'m.')
            QgsProject.instance().addMapLayer(regular_grid)
        except ValueError:
            iface.messageBar().pushMessage('Point spacing should be a float value, abort....', level=Qgis.Critical)
            pass
        self.dlg.CreateGrid_PushButton.setEnabled(True)

    def idw(self, row, field_name, id_power=2, min_points = 1, max_points=500, aniso_ratio=1):
        calc_arr = np.zeros(shape=(len(self.measurements), 5))  # create an empty array shape of (total no. of observation * 4)
        calc_arr[:, 0] = self.measurements['S']  # First column will be Longitude of known data points.
        calc_arr[:, 1] = self.measurements['N']  # Second column will be Latitude of known data points.
        calc_arr[:, 2] = self.measurements[field_name]

        # Weight value from idw formula " w = 1 / (d(x, x_i)^power + 1)"
        # >> constant 1 is to prevent int divide by zero when distance is zero.
        calc_arr[:, 3] = 1 / (np.sqrt(
            (1/aniso_ratio) * (calc_arr[:, 0] - row['S']) ** 2 + (calc_arr[:, 1] - row['N']) ** 2) ** id_power + 1)

        # Sort the array in ascending order based on weight "np.argsort(calc_arr[:,4])"
        calc_arr = calc_arr[np.argsort(calc_arr[:, 3])][-int(max_points):]

        # 4 column is multiplicative product of inverse distant weight and actual value.
        calc_arr[:, 4] = calc_arr[:, 2] * calc_arr[:, 3]
        # Divide sum of weighted value by sum of weights to get IDW interpolation.
        #if len(calc_arr)>min_points:
        idw = calc_arr[:, 4].sum() / calc_arr[:, 3].sum()
        #else:
        #    idw = np.NaN
        return idw

    def interpolate(self):

        self.dlg.Interpolate_PushButton.setEnabled(False)
        QgsMessageLog.logMessage("Interpolating data", 'Messages', level=Qgis.Info)

        grid_filename = self.dlg.InputGrid_Widget.filePath()
        measurements_filename = self.dlg.InputMeasurements_Widget.filePath()
        id_power = float(self.dlg.Power_LineEdit.text())
        #search_distance = float(self.dlg.SearcDistance_LineEdit.text())
        min_points = float(self.dlg.MinimumPoints_LineEdit.text())
        max_points = float(self.dlg.MaximumPoints_LineEdit.text())
        elliptical_idw = self.dlg.Elliptical_CheckBox.isChecked()
        if elliptical_idw == True:
            epsilon = float(self.dlg.Epsilon_LineEdit.text())
        else:
            epsilon = 1
        grid = gpd.read_file(grid_filename)
        field_name = self.dlg.Field_comboBox.currentText()
        grid[field_name] = grid.apply(self.idw, axis=1, args=(field_name, id_power, min_points, max_points, epsilon))
        grid.to_file(grid_filename)
        self.dlg.Interpolate_PushButton.setEnabled(True)

    def SN_coordinates_output(self):
        self.output_format = 'SN'

    def XY_coordinates_output(self):
        self.output_format = 'XY'

    def change_Field_comboBox(self):
        measurements_filename = self.dlg.InputMeasurements_Widget.filePath()
        self.measurements = gpd.read_file(measurements_filename)
        for col in self.measurements.columns:
            self.dlg.Field_comboBox.addItem(col)
        pass