#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
#
__author__="atareao"
__date__ ="$01-november-2013$"
#
#
# Copyright (C) 2013 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
from gi.repository import Nautilus
from gi.repository import GObject
from gi.repository import Gtk
import os
import sys
import subprocess
import urllib
import locale
import gettext
import time
import threading
from Queue import Queue

NUM_THREADS = 4

LANGDIR = '/usr/share/locale-langpack'
APP = 'nautilus-document-converter'
VERSION = '0.0.6-0extras15.10.0'

try:
	current_locale, encoding = locale.getdefaultlocale()
	language = gettext.translation('nautilus-document-converter', '/usr/share/locale-langpack', [current_locale])
	language.install()
	if sys.version_info[0] == 3:
		_ = language.gettext
	else:
		_ = language.ugettext
except Exception as e:
	print(e)
	_ = str	
	
EXTENSIONS = ['.bib','.dbf','.dif','.doc','.dxf','.emf','.eps','.gif','.html','.jpg','.ltx','.met','.odg','.odp','.ods','.odt','.otg','.ott','.pbm','.pbm','.pct','.pdb','.pdf','.pgm','.png','.pot','.ppm','.ppt','.psw','.pts','.pwp','.pxl','.ras','.rtf','.sda','.sdc','.sdd','.sdw','.slk','.stc','.std','.sti','.stp','.stw','.svg','.svm','.svm','.swf','.sxc','.sxd','.sxi','.sxw','.tiff','.txt','.vor','.wmf','.xhtml','.xls','.xlt','.xml','.xpm']

########################################################################

class Manager(GObject.GObject):
	def __init__(self,files, convert_to):
		self.files = files
		self.convert_to = convert_to
		
	def process(self):
		total = len(self.files)
		if total>0:
			print(self.files)
			workers = []
			print(1)
			cua = Queue(maxsize=total+1)
			progreso = Progreso('Converting files...',None,total)
			total_workers = total if NUM_THREADS > total else NUM_THREADS
			for i in range(total_workers):
				worker = Worker(cua,self.convert_to)
				worker.connect('converted',progreso.increase)
				worker.start()
				workers.append(worker)
			print(2)
			for afile in self.files:
				cua.put(afile)
			# block until all tasks are done
			print(3)
			cua.join()
			# stop workers
			print(4)
			for i in range(total_workers):
				cua.put(None)
			for worker in workers:
				worker.join()
				while Gtk.events_pending():
					Gtk.main_iteration()				
			print(5)


class Worker(GObject.GObject,threading.Thread):
	__gsignals__ = {
		'converted':(GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE,(object,)),
		}
	
	def __init__(self,cua,convert_to):
		threading.Thread.__init__(self)
		GObject.GObject.__init__(self)		
		self.setDaemon(True)
		self.cua = cua
		self.convert_to = convert_to

	def run(self):
		while True:
			file_in = self.cua.get()
			if file_in is None:
				break
			try:
				basefile,extile = os.path.splitext(file_in)
				outputfile = os.path.splitext(file_in)[0]+'.'+self.convert_to					
				print('************************************************')
				print('convert file: %s'%file_in)
				convert_file(self.convert_to,outputfile,file_in)
				print('converted file: %s'%file_in)
				print('************************************************')
			except Exception as e:
				print(e)
			self.emit('converted',file_in)
			self.cua.task_done()

class Progreso(Gtk.Dialog):
	def __init__(self,title,parent,max_value):
		#
		Gtk.Dialog.__init__(self,title,parent)
		self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
		self.set_size_request(330, 40)
		self.set_resizable(False)
		self.connect('destroy', self.close)
		#
		vbox1 = Gtk.VBox(spacing = 5)
		vbox1.set_border_width(5)
		self.get_content_area().add(vbox1)
		#
		self.progressbar = Gtk.ProgressBar()
		vbox1.pack_start(self.progressbar,True,True,0)
		#
		self.show_all()
		#
		self.max_value=max_value
		self.value=0.0
		self.map()
		while Gtk.events_pending():
			Gtk.main_iteration()


	def set_value(self,value):
		if value >=0 and value<=self.max_value:
			self.value = value
			fraction=self.value/self.max_value
			self.progressbar.set_fraction(fraction)
			self.map()
			while Gtk.events_pending():
				Gtk.main_iteration()
			if self.value==self.max_value:
				self.hide()		
	def close(self,widget=None):
		self.destroy()

	def increase(self,w,a):
		self.value+=1.0
		fraction=self.value/self.max_value
		self.progressbar.set_fraction(fraction)
		while Gtk.events_pending():
			Gtk.main_iteration()
		if self.value==self.max_value:
			self.hide()

	def decrease(self):
		self.value-=1.0
		fraction=self.value/self.max_value
		self.progressbar.set_fraction(fraction)
		self.map()
		while Gtk.events_pending():
			Gtk.main_iteration()

########################################################################


def convert_file(extension,outputfile,afile):	
	args = ['unoconv','-f',extension,'-o',outputfile,afile]
	p = subprocess.Popen(args, bufsize=10000, stdout=subprocess.PIPE)
	ans = p.communicate()[0]
	return ans
	
def convert_files(files,extension):	
	if len(files)>0:
		manager = Manager(files,extension)
		ft = time.time()
		manager.process()
		print('--------------------------------------------------------')
		print('--------------------------------------------------------')
		print('--------------------------------------------------------')
		print(time.time()-ft)
		print('--------------------------------------------------------')
		print('--------------------------------------------------------')
		print('--------------------------------------------------------')

def get_files(files_in):
	files = []
	for file_in in files_in:
		file_in = urllib.unquote(file_in.get_uri()[7:])
		fileName, fileExtension = os.path.splitext(file_in)
		if fileExtension.lower() in EXTENSIONS and os.path.isfile(file_in):
			files.append(file_in)
	return files

########################################################################

"""
Tools to manipulate pdf
"""	
class DocumentConverterMenuProvider(GObject.GObject, Nautilus.MenuProvider):
	"""Implements the 'Replace in Filenames' extension to the nautilus right-click menu"""

	def __init__(self):
		"""Nautilus crashes if a plugin doesn't implement the __init__ method"""
		pass

	def all_files_are_document(self,items):
		for item in items:
			fileName, fileExtension = os.path.splitext(item.get_uri()[7:])
			if fileExtension.lower() in EXTENSIONS:
				return True
		return False

	def about(self,menu,selected):
		ad=Gtk.AboutDialog()
		ad.set_name('Nautilus Document Converter')
		ad.set_icon_name('nautilus_document_converter')
		ad.set_version(VERSION)
		ad.set_copyright('Copyrignt (c) 2013-2016\nLorenzo Carbonell')
		ad.set_comments(_('Tools to convert document files'))
		ad.set_license(''+
		'This program is free software: you can redistribute it and/or modify it\n'+
		'under the terms of the GNU General Public License as published by the\n'+
		'Free Software Foundation, either version 3 of the License, or (at your option)\n'+
		'any later version.\n\n'+
		'This program is distributed in the hope that it will be useful, but\n'+
		'WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY\n'+
		'or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for\n'+
		'more details.\n\n'+
		'You should have received a copy of the GNU General Public License along with\n'+
		'this program.  If not, see <http://www.gnu.org/licenses/>.')
		ad.set_website('http://www.atareao.es')
		ad.set_website_label('http://www.atareao.es')
		ad.set_authors(['Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
		ad.set_documenters(['Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
		ad.set_program_name('Nautilus Document Converter')
		ad.set_logo_icon_name('nautilus_document_converter')
		ad.run()
		ad.destroy()		
		
	def convert_to_extension(self, menu, extension, selected):
		files = get_files(selected)
		convert_files(files,extension)

	def get_file_items(self, window, sel_items):
		"""Adds the 'Replace in Filenames' menu item to the Nautilus right-click menu,
		   connects its 'activate' signal to the 'run' method passing the selected Directory/File"""
		if not self.all_files_are_document(sel_items):
			return
		top_menuitem = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter',
								 label=_('Document converter'),
								 tip=_('Tools to convert documents'),
								 icon='Gtk-find-and-replace')
		#
		submenu = Nautilus.Menu()
		top_menuitem.set_submenu(submenu)
		sub_menus = []
		#
		sub_menuitem_doc = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-doc',
								 label=_('to DOC'),
								 tip=_('Convert to DOC'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_doc.connect('activate', self.convert_to_extension, 'doc', sel_items)
		submenu.append_item(sub_menuitem_doc)
		#
		sub_menuitem_docx = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-docx',
								 label=_('to DOCX'),
								 tip=_('Convert to DOCX'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_docx.connect('activate', self.convert_to_extension, 'docx', sel_items)
		submenu.append_item(sub_menuitem_docx)
		#
		sub_menuitem_html = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-html',
								 label=_('to HTML'),
								 tip=_('Convert to HTML'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_html.connect('activate', self.convert_to_extension, 'html', sel_items)
		submenu.append_item(sub_menuitem_html)
		#
		sub_menuitem_odp = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-odp',
								 label=_('to ODP'),
								 tip=_('Convert to ODP'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_odp.connect('activate', self.convert_to_extension, 'odp', sel_items)
		submenu.append_item(sub_menuitem_odp)
		#
		sub_menuitem_ods = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-ods',
								 label=_('to ODS'),
								 tip=_('Convert to ODS'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_ods.connect('activate', self.convert_to_extension, 'ods', sel_items)
		submenu.append_item(sub_menuitem_ods)
		#
		sub_menuitem_odt = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-odt',
								 label=_('to ODT'),
								 tip=_('Convert to ODT'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_odt.connect('activate', self.convert_to_extension, 'odt', sel_items)
		submenu.append_item(sub_menuitem_odt)
		#
		sub_menuitem_jpg = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-jpg',
								 label=_('to JPG'),
								 tip=_('Convert to JPG'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_jpg.connect('activate', self.convert_to_extension, 'jpg', sel_items)
		submenu.append_item(sub_menuitem_jpg)
		#
		sub_menuitem_pdf = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-pdf',
								 label=_('to PDF'),
								 tip=_('Convert to PDF'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_pdf.connect('activate', self.convert_to_extension, 'pdf', sel_items)
		submenu.append_item(sub_menuitem_pdf)
		#
		sub_menuitem_png = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-png',
								 label=_('to PNG'),
								 tip=_('Convert to PNG'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_png.connect('activate', self.convert_to_extension, 'png', sel_items)
		submenu.append_item(sub_menuitem_png)
		#
		sub_menuitem_ppt = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-ppt',
								 label=_('to PPT'),
								 tip=_('Convert to PPT'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_ppt.connect('activate', self.convert_to_extension, 'ppt', sel_items)
		submenu.append_item(sub_menuitem_ppt)
		#
		sub_menuitem_pptx = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-pptx',
								 label=_('to PPTX'),
								 tip=_('Convert to PPTX'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_pptx.connect('activate', self.convert_to_extension, 'pptx', sel_items)
		submenu.append_item(sub_menuitem_pptx)
		#
		sub_menuitem_rtf = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-rtf',
								 label=_('to RTF'),
								 tip=_('Convert to RTF'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_rtf.connect('activate', self.convert_to_extension, 'rtf', sel_items)
		submenu.append_item(sub_menuitem_rtf)
		#
		sub_menuitem_svg = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-svg',
								 label=_('to SVG'),
								 tip=_('Convert to SVG'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_svg.connect('activate', self.convert_to_extension, 'svg', sel_items)
		submenu.append_item(sub_menuitem_svg)
		#
		sub_menuitem_swf = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-swf',
								 label=_('to SWF'),
								 tip=_('Convert to SWF'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_swf.connect('activate', self.convert_to_extension, 'swf', sel_items)
		submenu.append_item(sub_menuitem_swf)
		#
		sub_menuitem_txt = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-txt',
								 label=_('to TXT'),
								 tip=_('Convert to TXT'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_txt.connect('activate', self.convert_to_extension, 'txt', sel_items)
		submenu.append_item(sub_menuitem_txt)
		#
		sub_menuitem_10 = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-10',
								 label=_('to XLS'),
								 tip=_('Convert to XLS'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_10.connect('activate', self.convert_to_extension, 'xls', sel_items)
		submenu.append_item(sub_menuitem_10)
		#
		sub_menuitem_11 = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-11',
								 label=_('to XLSX'),
								 tip=_('Convert to XLSX'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_11.connect('activate', self.convert_to_extension, 'xlsx', sel_items)
		submenu.append_item(sub_menuitem_11)
		
		#		
		sub_menuitem_98 = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-none',
								 label='')
		submenu.append_item(sub_menuitem_98)
		#		
		sub_menuitem_99 = Nautilus.MenuItem(name='DocumentConverterMenuProvider::Gtk-document-converter-99',
								 label=_('About'),
								 tip=_('About'),
								 icon='Gtk-find-and-replace')
		sub_menuitem_99.connect('activate', self.about, sel_items)
		submenu.append_item(sub_menuitem_99)
		#		
		return top_menuitem,

if __name__ == '__main__':
	if len(sys.argv) < 2:
		import glob
		files = glob.glob('*.pdf')
		print(files)
		print(os.getcwd())
		tmpfiles = []
		for afile in files:
			tmpfiles.append(os.path.join(os.getcwd(),afile))
		convert_files(tmpfiles,'odt')
	else:
		convert_files(sys.argv[1:],'pdf')
	exit(0)
