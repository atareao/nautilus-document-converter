##!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-document-converter
#
# Copyright (c) 2016 Lorenzo Carbonell Cerezo <a.k.a. atareao>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GLib', '2.0')
    gi.require_version('GObject', '2.0')
    gi.require_version('Nautilus', '3.0')
except Exception as e:
    print(e)
    exit(-1)
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Nautilus as FileManager
import os
import locale
import gettext
from plumbum import local

APP = '$APP'
ICON = '$APP'
VERSION = '$VERSION$'
LANGDIR = os.path.join('usr', 'share', 'locale-langpack')

current_locale, encoding = locale.getdefaultlocale()
language = gettext.translation(APP, LANGDIR, [current_locale])
language.install()
_ = language.gettext


EXTENSIONS = ['.bib', '.dbf', '.dif', '.doc', '.docx', '.dxf', '.emf', '.eps',
              '.gif', '.html', '.jpg', '.ltx', '.met', '.odg', '.odp', '.ods',
              '.odt', '.otg', '.ott', '.pbm', '.pbm', '.pct', '.pdb', '.pdf',
              '.pgm', '.png', '.pot', '.ppm', '.ppt', '.pptx', '.psw', '.pts',
              '.pwp', '.pxl', '.ras', '.rtf', '.sda', '.sdc', '.sdd', '.sdw',
              '.slk', '.stc', '.std', '.sti', '.stp', '.stw', '.svg', '.svm',
              '.svm', '.swf', '.sxc', '.sxd', '.sxi', '.sxw', '.tiff', '.txt',
              '.vor', '.wmf', '.xhtml', '.xls', '.xlsx', '.xlt', '.xml',
              '.xpm']


class ConverterDIIB(DoItInBackground):
    def __init__(self, title, parent, files, extension):
        DoItInBackground.__init__(title, parent, files, ICON)
        self.extension = extension

    def process_item(self, file_in):
        head, tail = os.path.split(file_in)
        root, ext = os.path.splitext(tail)
        file_out = os.path.join(head, root + '.' + self.extension)
        unoconv = local['unoconv']
        unoconv['-f', 'self.extension', '-o', '"{}"'.format(file_out),
                '"{}"'.format(file_in)]()


class DocumentConverterMenuProvider(GObject.GObject, FileManager.MenuProvider):
    """
    Implements the 'Replace in Filenames' extension to the nautilus
    right-click menu
    """

    def __init__(self):
        """
        The FileManager crashes if a plugin doesn't implement the __init__
        method
        """
        GObject.GObject.__init__(self)

    def process(self, menu, selected, window, extension):
        files = get_files(selected)
        diib = ConverterDIIB(_('Convert file'), window, files, extension)
        diib.run()

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the FileManager
        right-click menu, connects its 'activate' signal to the 'run' method
        passing the selected Directory/File
        """
        files = []
        for file_in in sel_items:
            if not file_in.is_directory():
                fileName, fileExtension = os.path.splitext(
                        file_in.get_location().get_path())
                if fileExtension.lower() in EXTENSIONS:
                    files.append(file_in)
        if files:
            return
        top_menuitem = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter',
            label=_('Document converter'),
            tip=_('Tools to convert documents'),
            icon='Gtk-find-and-replace')
        #
        submenu = FileManager.Menu()
        top_menuitem.set_submenu(submenu)
        #
        sub_menuitem_doc = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-doc',
            label=_('to DOC'),
            tip=_('Convert to DOC'),
            icon='Gtk-find-and-replace')
        sub_menuitem_doc.connect('activate',
                                 self.process,
                                 files,
                                 window,
                                 'doc')
        submenu.append_item(sub_menuitem_doc)
        #
        sub_menuitem_docx = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-docx',
            label=_('to DOCX'),
            tip=_('Convert to DOCX'),
            icon='Gtk-find-and-replace')
        sub_menuitem_docx.connect('activate',
                                  self.convert_to_extension,
                                  files,
                                  window,
                                  'docx')
        submenu.append_item(sub_menuitem_docx)
        #
        sub_menuitem_html = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-html',
            label=_('to HTML'),
            tip=_('Convert to HTML'),
            icon='Gtk-find-and-replace')
        sub_menuitem_html.connect('activate',
                                  self.convert_to_extension,
                                  files,
                                  window,
                                  'html')
        submenu.append_item(sub_menuitem_html)
        #
        sub_menuitem_odp = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-odp',
            label=_('to ODP'),
            tip=_('Convert to ODP'),
            icon='Gtk-find-and-replace')
        sub_menuitem_odp.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'odp')
        submenu.append_item(sub_menuitem_odp)
        #
        sub_menuitem_ods = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-ods',
            label=_('to ODS'),
            tip=_('Convert to ODS'),
            icon='Gtk-find-and-replace')
        sub_menuitem_ods.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'ods')
        submenu.append_item(sub_menuitem_ods)
        #
        sub_menuitem_odt = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-odt',
            label=_('to ODT'),
            tip=_('Convert to ODT'),
            icon='Gtk-find-and-replace')
        sub_menuitem_odt.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'odt')
        submenu.append_item(sub_menuitem_odt)
        #
        sub_menuitem_jpg = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-jpg',
            label=_('to JPG'),
            tip=_('Convert to JPG'),
            icon='Gtk-find-and-replace')
        sub_menuitem_jpg.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'jpg')
        submenu.append_item(sub_menuitem_jpg)
        #
        sub_menuitem_pdf = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-pdf',
            label=_('to PDF'),
            tip=_('Convert to PDF'),
            icon='Gtk-find-and-replace')
        sub_menuitem_pdf.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'pdf')
        submenu.append_item(sub_menuitem_pdf)
        #
        sub_menuitem_png = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-png',
            label=_('to PNG'),
            tip=_('Convert to PNG'),
            icon='Gtk-find-and-replace')
        sub_menuitem_png.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'png')
        submenu.append_item(sub_menuitem_png)
        #
        sub_menuitem_ppt = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-ppt',
            label=_('to PPT'),
            tip=_('Convert to PPT'),
            icon='Gtk-find-and-replace')
        sub_menuitem_ppt.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'ppt')
        submenu.append_item(sub_menuitem_ppt)
        #
        sub_menuitem_pptx = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-pptx',
            label=_('to PPTX'),
            tip=_('Convert to PPTX'),
            icon='Gtk-find-and-replace')
        sub_menuitem_pptx.connect('activate',
                                  self.convert_to_extension,
                                  files,
                                  window,
                                  'pptx')
        submenu.append_item(sub_menuitem_pptx)
        #
        sub_menuitem_rtf = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-rtf',
            label=_('to RTF'),
            tip=_('Convert to RTF'),
            icon='Gtk-find-and-replace')
        sub_menuitem_rtf.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'rtf')
        submenu.append_item(sub_menuitem_rtf)
        #
        sub_menuitem_svg = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-svg',
            label=_('to SVG'),
            tip=_('Convert to SVG'),
            icon='Gtk-find-and-replace')
        sub_menuitem_svg.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'svg')
        submenu.append_item(sub_menuitem_svg)
        #
        sub_menuitem_swf = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-swf',
            label=_('to SWF'),
            tip=_('Convert to SWF'),
            icon='Gtk-find-and-replace')
        sub_menuitem_swf.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'swf')
        submenu.append_item(sub_menuitem_swf)
        #
        sub_menuitem_txt = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-txt',
            label=_('to TXT'),
            tip=_('Convert to TXT'),
            icon='Gtk-find-and-replace')
        sub_menuitem_txt.connect('activate',
                                 self.convert_to_extension,
                                 files,
                                 window,
                                 'txt')
        submenu.append_item(sub_menuitem_txt)
        #
        sub_menuitem_10 = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-10',
            label=_('to XLS'),
            tip=_('Convert to XLS'),
            icon='Gtk-find-and-replace')
        sub_menuitem_10.connect('activate',
                                self.convert_to_extension,
                                files,
                                window,
                                'xls')
        submenu.append_item(sub_menuitem_10)
        #
        sub_menuitem_11 = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-11',
            label=_('to XLSX'),
            tip=_('Convert to XLSX'),
            icon='Gtk-find-and-replace')
        sub_menuitem_11.connect('activate',
                                self.convert_to_extension,
                                files,
                                window,
                                'xlsx')
        submenu.append_item(sub_menuitem_11)
        #
        sub_menuitem_98 = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-none', label='')
        submenu.append_item(sub_menuitem_98)
        #
        sub_menuitem_99 = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-99',
            label=_('About'),
            tip=_('About'),
            icon='Gtk-find-and-replace')
        sub_menuitem_99.connect('activate', self.about, window)
        submenu.append_item(sub_menuitem_99)
        #
        return top_menuitem,

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APP)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2016\nLorenzo Carbonell')
        ad.set_comments(APP)
        ad.set_license('''
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')
        ad.set_website('https://www.atareao.es')
        ad.set_website_label('atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <a.k.a. atareao>'])
        ad.set_documenters([
            'Lorenzo Carbonell <a.k.a. atareao>'])
        ad.set_icon_name(ICON)
        ad.set_logo_icon_name(APP)
        ad.run()
        ad.destroy()
