# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CurviCoord
                                 A QGIS plugin
 Plugin for river data conversion from Cartesian to curvilinear orthogonal system
                             -------------------
        begin                : 2024-05-24
        copyright            : (C) 2024 by Sergei Freiman
        email                : freimansgy@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CurviCoord class from file CurviCoord.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .curvilinear_coordinator import CurviCoord
    return CurviCoord(iface)
