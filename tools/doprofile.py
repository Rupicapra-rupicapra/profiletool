# -*- coding: utf-8 -*-
#-----------------------------------------------------------
#
# Profile
# Copyright (C) 2008  Borys Jurgiel
# Copyright (C) 2012  Patrice Verchere
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, print to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qt import *
from PyQt4.QtSvg import * # required in some distros
from qgis.core import *
from plottingtool import PlottingTool

from math import sqrt
#from profilebase import Ui_ProfileBase
from dataReaderTool import DataReaderTool
import platform
import sys
from PyQt4.QtCore import SIGNAL,SLOT,pyqtSignature

has_dxfwrite = False
try:
	from dxfwrite import DXFEngine as dxf
	has_dxfwrite = True
except:
	pass

class DoProfile(QWidget):

	def __init__(self, iface, dockwidget1 , tool1 , plugin, parent = None):
		QWidget.__init__(self, parent)
		self.profiles = None		#dictionary where is saved the plotting data {"l":[l],"z":[z], "layer":layer1, "curve":curve1}
		self.iface = iface
		self.tool = tool1
		self.dockwidget = dockwidget1
		self.pointstoDraw = None
		self.plugin = plugin
		#init scale widgets
		self.dockwidget.sbMaxVal.setValue(0)
		self.dockwidget.sbMinVal.setValue(0)
		self.dockwidget.sbMaxVal.setEnabled(False)
		self.dockwidget.sbMinVal.setEnabled(False)
		self.dockwidget.sbMinVal.valueChanged.connect(self.reScalePlot)
		self.dockwidget.sbMaxVal.valueChanged.connect(self.reScalePlot)


	#**************************** function part *************************************************

	# remove layers which were removed from QGIS
	def removeClosedLayers(self, model1):
		qgisLayerNames = []
		for i in range(0, self.iface.mapCanvas().layerCount()):
			qgisLayerNames.append(self.iface.mapCanvas().layer(i).name())

		for i in range(0 , model1.rowCount()):
			layerName = model1.item(i,2).data(Qt.EditRole)
			if not layerName in qgisLayerNames:
				self.plugin.removeLayer(i)
				self.removeClosedLayers(model1)
				break

	def calculateProfil(self, points1, model1, library, vertline = True):
		self.pointstoDraw = points1

		self.removeClosedLayers(model1)
		if self.pointstoDraw == None:
			return
		PlottingTool().clearData(self.dockwidget, self.profiles, library)
		self.profiles = []
		if vertline:						#Plotting vertical lines at the node of polyline draw
			PlottingTool().drawVertLine(self.dockwidget, self.pointstoDraw, library)

		#creating the plots of profiles
		for i in range(0 , model1.rowCount()):
			self.profiles.append( {"layer": model1.item(i,4).data(Qt.EditRole) } )
			self.profiles[i]["band"] = model1.item(i,3).data(Qt.EditRole) - 1
			self.profiles[i] = DataReaderTool().dataReaderTool(self.iface, self.tool, self.profiles[i], self.pointstoDraw, self.dockwidget.checkBox.isChecked())
		PlottingTool().attachCurves(self.dockwidget, self.profiles, model1, library)
		PlottingTool().reScalePlot(self.dockwidget, self.profiles, library)

		#*********************** Table tab *************************************************
		try:																	#Reinitializing the table tab
			self.VLayout = self.dockwidget.scrollAreaWidgetContents.layout()
			while 1:
				child = self.VLayout.takeAt(0)
				if not child:
					break
				child.widget().deleteLater()
		except:
			self.VLayout = QVBoxLayout(self.dockwidget.scrollAreaWidgetContents)
			self.VLayout.setContentsMargins(9, -1, -1, -1)
		#Setup the table tab
		self.groupBox = []
		self.profilePushButton = []
		self.coordsPushButton = []
		self.dxfPushButton = []
		self.tableView = []
		self.verticalLayout = []

		for i in range(0 , model1.rowCount()):
			self.groupBox.append( QGroupBox(self.dockwidget.scrollAreaWidgetContents) )
			sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
			sizePolicy.setHorizontalStretch(0)
			sizePolicy.setVerticalStretch(0)
			sizePolicy.setHeightForWidth(self.groupBox[i].sizePolicy().hasHeightForWidth())
			self.groupBox[i].setSizePolicy(sizePolicy)
			self.groupBox[i].setMinimumSize(QSize(0, 150))
			self.groupBox[i].setMaximumSize(QSize(16777215, 150))
			self.groupBox[i].setTitle(QApplication.translate("GroupBox" + str(i), self.profiles[i]["layer"].name(), None, QApplication.UnicodeUTF8))
			self.groupBox[i].setObjectName("groupBox" + str(i))

			self.verticalLayout.append( QVBoxLayout(self.groupBox[i]) )
			self.verticalLayout[i].setObjectName("verticalLayout")
			#The table
			self.tableView.append( QTableView(self.groupBox[i]) )
			self.tableView[i].setObjectName("tableView" + str(i))
			font = QFont("Arial", 8)
			column = len(self.profiles[i]["l"])
			self.mdl = QStandardItemModel(2, column)
			for j in range(len(self.profiles[i]["l"])):
				self.mdl.setData(self.mdl.index(0, j, QModelIndex())  ,self.profiles[i]["l"][j])
				self.mdl.setData(self.mdl.index(0, j, QModelIndex())  ,font ,Qt.FontRole)
				self.mdl.setData(self.mdl.index(1, j, QModelIndex())  ,self.profiles[i]["z"][j])
				self.mdl.setData(self.mdl.index(1, j, QModelIndex())  ,font ,Qt.FontRole)
			self.tableView[i].verticalHeader().setDefaultSectionSize(18)
			self.tableView[i].horizontalHeader().setDefaultSectionSize(60)
			self.tableView[i].setModel(self.mdl)
			self.verticalLayout[i].addWidget(self.tableView[i])

			self.horizontalLayout = QHBoxLayout()

			#the copy to clipboard button
			self.profilePushButton.append( QPushButton(self.groupBox[i]) )
			sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
			sizePolicy.setHorizontalStretch(0)
			sizePolicy.setVerticalStretch(0)
			sizePolicy.setHeightForWidth(self.profilePushButton[i].sizePolicy().hasHeightForWidth())
			self.profilePushButton[i].setSizePolicy(sizePolicy)
			self.profilePushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard", None, QApplication.UnicodeUTF8))
			self.profilePushButton[i].setObjectName(str(i))
			self.horizontalLayout.addWidget(self.profilePushButton[i])

			#button to copy to clipboard with coordinates
			self.coordsPushButton.append(QPushButton(self.groupBox[i]))
			sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
			sizePolicy.setHorizontalStretch(0)
			sizePolicy.setVerticalStretch(0)
			sizePolicy.setHeightForWidth(self.coordsPushButton[i].sizePolicy().hasHeightForWidth())
			self.coordsPushButton[i].setSizePolicy(sizePolicy)
			self.coordsPushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard (with coordinates)", None, QApplication.UnicodeUTF8))
			self.coordsPushButton[i].setObjectName(str(i))
			self.horizontalLayout.addWidget(self.coordsPushButton[i])

			# button to export to DXF
			self.dxfPushButton.append(QPushButton(self.groupBox[i]))
			sizePolicy.setHeightForWidth(self.dxfPushButton[i].sizePolicy().hasHeightForWidth())
			self.dxfPushButton[i].setSizePolicy(sizePolicy)
			self.dxfPushButton[i].setText(QApplication.translate("GroupBox", "Export to DXF", None, QApplication.UnicodeUTF8))
			self.dxfPushButton[i].setObjectName(str(i))
			self.horizontalLayout.addWidget(self.dxfPushButton[i])

			self.horizontalLayout.addStretch(0)
			self.verticalLayout[i].addLayout(self.horizontalLayout)

			self.VLayout.addWidget(self.groupBox[i])
			self.profilePushButton[i].clicked.connect(self.copyTable)
			self.coordsPushButton[i].clicked.connect(self.copyTableAndCoords)
			self.dxfPushButton[i].clicked.connect(self.exportDXF)
			#QObject.connect(self.profilePushButton[i], SIGNAL("clicked()"), self.copyTable)
			#QObject.connect(self.coordsPushButton[i], SIGNAL("clicked()"), self.copyTableAndCoords)



	def copyTable(self):							#Writing the table to clipboard in excel form
		nr = int( self.sender().objectName() )
		self.clipboard = QApplication.clipboard()
		text = ""
		for i in range( len(self.profiles[nr]["l"]) ):
			text += str(self.profiles[nr]["l"][i]) + "\t" + str(self.profiles[nr]["z"][i]) + "\n"
		self.clipboard.setText(text)

	def copyTableAndCoords(self):					#Writing the table with coordinates to clipboard in excel form
		nr = int( self.sender().objectName() )
		self.clipboard = QApplication.clipboard()
		text = ""
		for i in range( len(self.profiles[nr]["l"]) ):
			text += str(self.profiles[nr]["l"][i]) + "\t" + str(self.profiles[nr]["x"][i]) + "\t"\
			+ str(self.profiles[nr]["y"][i]) + "\t" + str(self.profiles[nr]["z"][i]) + "\n"
		self.clipboard.setText(text)

	def exportDXF(self):
		if has_dxfwrite:
			# Drawing initialization
			dxfFileName = QFileDialog.getSaveFileName(self, "Save DXF File", "Profile.dxf", "Drawing eXchange Format (*.dxf)")
			drawing = dxf.drawing(dxfFileName)
			drawing.add_layer('Profile')
			profile = dxf.polyline()
			profile['layer'] = 'Profile'

			# Getting points coordinates (in 2D)
			nr = int(self.sender().objectName())
			vertices = []
			for i in range(len(self.profiles[nr]["l"])):
				vertices.append((profiles[nr]["l"][i], profiles[nr]["z"][i]))

			profile.add_vertices(vertices)
			drawing.add(profile)
			drawing.save()
			QMessageBox.information(self, "Profile saved", "Your profile was saved")



	def reScalePlot(self, param): 						# called when a spinbox value changed
		if type(param) != int:
			# don't execute it twice, for both valueChanged(int) and valueChanged(str) signals
			return
		if self.dockwidget.sbMinVal.value() == self.dockwidget.sbMaxVal.value() == 0:
			# don't execute it on init
			return
		PlottingTool().reScalePlot(self.dockwidget, self.profiles, self.dockwidget.cboLibrary.currentText () )


	def getProfileCurve(self,nr):
		try:
			return self.profiles[nr]["curve"]
		except:
			return None


