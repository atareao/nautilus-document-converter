##!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-document-converter
#
# Copyright (C) 2013-2016 Lorenzo Carbonell
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

import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('Nautilus', '3.0')
except Exception as e:
    print(e)
    exit(-1)
import os
import subprocess
import shlex
import tempfile
import shutil
from threading import Thread
from urllib import unquote_plus
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Nautilus as FileManager
import re


LANGDIR = '/usr/share/locale-langpack'
APP = 'nautilus-document-converter'
VERSION = '0.0.6-0extras15.10.0'

try:
    current_locale, encoding = locale.getdefaultlocale()
    language = gettext.translation(
        'nautilus-document-converter',
        '/usr/share/locale-langpack',
        [current_locale])
    language.install()
    if sys.version_info[0] == 3:
        _ = language.gettext
    else:
        _ = language.ugettext
except Exception as e:
    print(e)
    _ = str

EXTENSIONS = ['.bib', '.dbf', '.dif', '.doc', '.dxf', '.emf', '.eps', '.gif',
              '.html', '.jpg', '.ltx', '.met', '.odg', '.odp', '.ods', '.odt',
              '.otg', '.ott', '.pbm', '.pbm', '.pct', '.pdb', '.pdf', '.pgm',
              '.png', '.pot', '.ppm', '.ppt', '.psw', '.pts', '.pwp', '.pxl',
              '.ras', '.rtf', '.sda', '.sdc', '.sdd', '.sdw', '.slk', '.stc',
              '.std', '.sti', '.stp', '.stw', '.svg', '.svm', '.svm', '.swf',
              '.sxc', '.sxd', '.sxi', '.sxw', '.tiff', '.txt', '.vor', '.wmf',
              '.xhtml', '.xls', '.xlt', '.xml', '.xpm']


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class DoItInBackground(IdleObject, Thread):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, files, extension):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.files = files
        self.extension = extension
        self.stopit = False
        self.ok = True
        self.daemon = True
        self.process = None

    def stop(self, *args):
        self.stopit = True

    def get_output_filename(self, file_in):
        head, tail = os.path.split(file_in)
        root, ext = os.path.splitext(tail)
        file_out = os.path.join(head, root + '.' + self.extension)
        return file_out

    def convert_file(self, file_in):
        file_out = self.get_output_filename(file_in)
        runtime = 'unoconv -f %s -o %s %s' % (self.extension,
                                              file_out,
                                              file_in)
        args = shlex.split(rutine)
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
        out, err = self.process.communicate()
        print(out, err)

    def run(self):
        total = 0
        for afile in self.files:
            total += os.path.getsize(afile)
        self.emit('started', total)
        try:
            total = 0
            for afile in self.files:
                if self.stopit is True:
                    self.ok = False
                    break
                self.emit('start_one', afile)
                self.convert_file(afile)
                self.emit('end_one', os.path.getsize(afile))
        except Exception as e:
            self.ok = False
        try:
            if self.process is not None:
                self.process.terminate()
                self.process = None
        except Exception as e:
            print(e)
        self.emit('ended', self.ok)


class Progreso(Gtk.Dialog):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent, max_value):
        Gtk.Dialog.__init__(self, title, parent)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 30)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        self.set_modal(True)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)
        #
        frame1 = Gtk.Frame()
        vbox.pack_start(frame1, True, True, 0)
        table = Gtk.Table(2, 2, False)
        frame1.add(table)
        #
        self.label = Gtk.Label()
        table.attach(self.label, 0, 2, 0, 1,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        #
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        table.attach(self.progressbar, 0, 1, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        table.attach(button_stop, 1, 2, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK)
        self.stop = False
        self.show_all()
        self.max_value = float(max_value)
        self.value = 0.0

    def set_max_value(self, anobject, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self, anobject, value):
        self.value += float(value)
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value >= self.max_value:
            self.hide()

    def set_element(self, anobject, element):
        self.label.set_text(_('Converting: %s') % element)


def get_files(files_in):
    files = []
    for file_in in files_in:
        file_in = urllib.unquote(file_in.get_uri()[7:])
        fileName, fileExtension = os.path.splitext(file_in)
        if fileExtension.lower() in EXTENSIONS and os.path.isfile(file_in):
            files.append(file_in)
    return files

########################################################################


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
        pass

    def all_files_are_document(self, items):
        for item in items:
            fileName, fileExtension = os.path.splitext(item.get_uri()[7:])
            if fileExtension.lower() in EXTENSIONS:
                return True
        return False

    def about(self, menu, selected):
        ad = Gtk.AboutDialog()
        ad.set_name('Nautilus Document Converter')
        ad.set_icon_name('nautilus_document_converter')
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2013-2016\nLorenzo Carbonell')
        ad.set_comments(_('Tools to convert document files'))
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option
any later version.
This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.
You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_program_name('Nautilus Document Converter')
        ad.set_logo_icon_name('nautilus_document_converter')
        ad.run()
        ad.destroy()

    def convert(self, menu, extension, selected):
        files = get_files(selected)
        diib = DoItInBackground(files, extension)
        progreso = Progreso(_('Convert to %s' % (extension)), None, len(files))
        diib.connect('started', progreso.set_max_value)
        diib.connect('start_one', progreso.set_element)
        diib.connect('end_one', progreso.increase)
        diib.connect('ended', progreso.close)
        progreso.connect('i-want-stop', diib.stop)
        diib.start()
        progreso.run()

    def convert_to_extension(self, menu, extension, selected):
        files = get_files(selected)
        convert_files(files, extension)

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the FileManager
        right-click menu, connects its 'activate' signal to the 'run' method
        passing the selected Directory/File
        """
        if not self.all_files_are_document(sel_items):
            return
        top_menuitem = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter',
            label=_('Document converter'),
            tip=_('Tools to convert documents'),
            icon='Gtk-find-and-replace')
        #
        submenu = FileManager.Menu()
        top_menuitem.set_submenu(submenu)
        sub_menus = []
        #
        sub_menuitem_doc = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-doc',
            label=_('to DOC'),
            tip=_('Convert to DOC'),
            icon='Gtk-find-and-replace')
        sub_menuitem_doc.connect('activate',
                                 self.convert_to_extension,
                                 'doc',
                                 sel_items)
        submenu.append_item(sub_menuitem_doc)
        #
        sub_menuitem_docx = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-docx',
            label=_('to DOCX'),
            tip=_('Convert to DOCX'),
            icon='Gtk-find-and-replace')
        sub_menuitem_docx.connect('activate',
                                  self.convert_to_extension,
                                  'docx',
                                  sel_items)
        submenu.append_item(sub_menuitem_docx)
        #
        sub_menuitem_html = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-html',
            label=_('to HTML'),
            tip=_('Convert to HTML'),
            icon='Gtk-find-and-replace')
        sub_menuitem_html.connect('activate',
                                  self.convert_to_extension,
                                  'html',
                                  sel_items)
        submenu.append_item(sub_menuitem_html)
        #
        sub_menuitem_odp = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-odp',
            label=_('to ODP'),
            tip=_('Convert to ODP'),
            icon='Gtk-find-and-replace')
        sub_menuitem_odp.connect('activate',
                                 self.convert_to_extension,
                                 'odp',
                                 sel_items)
        submenu.append_item(sub_menuitem_odp)
        #
        sub_menuitem_ods = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-ods',
            label=_('to ODS'),
            tip=_('Convert to ODS'),
            icon='Gtk-find-and-replace')
        sub_menuitem_ods.connect('activate',
                                 self.convert_to_extension,
                                 'ods',
                                 sel_items)
        submenu.append_item(sub_menuitem_ods)
        #
        sub_menuitem_odt = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-odt',
            label=_('to ODT'),
            tip=_('Convert to ODT'),
            icon='Gtk-find-and-replace')
        sub_menuitem_odt.connect('activate',
                                 self.convert_to_extension,
                                 'odt',
                                 sel_items)
        submenu.append_item(sub_menuitem_odt)
        #
        sub_menuitem_jpg = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-jpg',
            label=_('to JPG'),
            tip=_('Convert to JPG'),
            icon='Gtk-find-and-replace')
        sub_menuitem_jpg.connect('activate',
                                 self.convert_to_extension,
                                 'jpg',
                                 sel_items)
        submenu.append_item(sub_menuitem_jpg)
        #
        sub_menuitem_pdf = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-pdf',
            label=_('to PDF'),
            tip=_('Convert to PDF'),
            icon='Gtk-find-and-replace')
        sub_menuitem_pdf.connect('activate',
                                 self.convert_to_extension,
                                 'pdf',
                                 sel_items)
        submenu.append_item(sub_menuitem_pdf)
        #
        sub_menuitem_png = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-png',
            label=_('to PNG'),
            tip=_('Convert to PNG'),
            icon='Gtk-find-and-replace')
        sub_menuitem_png.connect('activate',
                                 self.convert_to_extension,
                                 'png',
                                 sel_items)
        submenu.append_item(sub_menuitem_png)
        #
        sub_menuitem_ppt = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-ppt',
            label=_('to PPT'),
            tip=_('Convert to PPT'),
            icon='Gtk-find-and-replace')
        sub_menuitem_ppt.connect('activate',
                                 self.convert_to_extension,
                                 'ppt',
                                 sel_items)
        submenu.append_item(sub_menuitem_ppt)
        #
        sub_menuitem_pptx = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-pptx',
            label=_('to PPTX'),
            tip=_('Convert to PPTX'),
            icon='Gtk-find-and-replace')
        sub_menuitem_pptx.connect('activate',
                                  self.convert_to_extension,
                                  'pptx',
                                  sel_items)
        submenu.append_item(sub_menuitem_pptx)
        #
        sub_menuitem_rtf = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-rtf',
            label=_('to RTF'),
            tip=_('Convert to RTF'),
            icon='Gtk-find-and-replace')
        sub_menuitem_rtf.connect('activate',
                                 self.convert_to_extension,
                                 'rtf',
                                 sel_items)
        submenu.append_item(sub_menuitem_rtf)
        #
        sub_menuitem_svg = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-svg',
            label=_('to SVG'),
            tip=_('Convert to SVG'),
            icon='Gtk-find-and-replace')
        sub_menuitem_svg.connect('activate',
                                 self.convert_to_extension,
                                 'svg',
                                 sel_items)
        submenu.append_item(sub_menuitem_svg)
        #
        sub_menuitem_swf = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-swf',
            label=_('to SWF'),
            tip=_('Convert to SWF'),
            icon='Gtk-find-and-replace')
        sub_menuitem_swf.connect('activate',
                                 self.convert_to_extension,
                                 'swf',
                                 sel_items)
        submenu.append_item(sub_menuitem_swf)
        #
        sub_menuitem_txt = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-txt',
            label=_('to TXT'),
            tip=_('Convert to TXT'),
            icon='Gtk-find-and-replace')
        sub_menuitem_txt.connect('activate',
                                 self.convert_to_extension,
                                 'txt',
                                 sel_items)
        submenu.append_item(sub_menuitem_txt)
        #
        sub_menuitem_10 = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-10',
            label=_('to XLS'),
            tip=_('Convert to XLS'),
            icon='Gtk-find-and-replace')
        sub_menuitem_10.connect('activate',
                                self.convert_to_extension,
                                'xls',
                                sel_items)
        submenu.append_item(sub_menuitem_10)
        #
        sub_menuitem_11 = FileManager.MenuItem(
            name='DocumentConverterMenuProvider::Gtk-document-converter-11',
            label=_('to XLSX'),
            tip=_('Convert to XLSX'),
            icon='Gtk-find-and-replace')
        sub_menuitem_11.connect('activate',
                                self.convert_to_extension,
                                'xlsx',
                                sel_items)
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
            tmpfiles.append(os.path.join(os.getcwd(), afile))
        convert_files(tmpfiles, 'odt')
    else:
        convert_files(sys.argv[1:], 'pdf')
    exit(0)
