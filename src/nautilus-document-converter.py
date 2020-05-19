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
from concurrent import futures

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


class Progreso(Gtk.Dialog):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent):
        Gtk.Dialog.__init__(self, title, parent)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_resizable(False)
        self.set_icon_name(ICON)
        self.set_size_request(330, 30)
        self.connect('destroy', self.close)
        self.connect('realize', self.on_realize)
        self.init_ui()
        self.stop = False
        self.show_all()
        self.value = 0.0

    def init_ui(self):
        vbox = Gtk.Box(Gtk.Orientation.VERTICAL, 5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)

        frame1 = Gtk.Frame()
        vbox.add(frame1)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_top(10)
        frame1.add(grid)

        self.label = Gtk.Label()
        grid.attach(self.label, 0, 0, 2, 1)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        grid.attach(self.progressbar, 0, 1, 1, 1)

        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        grid.attach(button_stop, 1, 1, 1, 1)

    def on_realize(self, *_):
        monitor = Gdk.Display.get_primary_monitor(Gdk.Display.get_default())
        scale = monitor.get_scale_factor()
        monitor_width = monitor.get_geometry().width / scale
        monitor_height = monitor.get_geometry().height / scale
        width = self.get_preferred_width()[0]
        height = self.get_preferred_height()[0]
        self.move((monitor_width - width)/2, (monitor_height - height)/2)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self, widget=None, x=1.0):
        self.value += float(x)
        if round(self.value, 5) >= 1.0:
            GLib.idle_add(self.destroy)
        else:
            GLib.idle_add(self.progressbar.set_fraction, self.value)

    def set_element(self, widget=None, element=''):
        GLib.idle_add(self.label.set_text, str(element))


class DoItInBackground(GObject.GObject):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, title, parent, files, extension):
        GObject.GObject.__init__(self)
        self.files = files
        self.stopit = False
        self.ok = True
        self.total_duration = get_total_duration(files)
        self.extension = extension
        self.progreso = Progreso(title, parent)
        self.progreso.connect('i-want-stop', self.stop)
        self.connect('start_one', self.progreso.set_element)
        self.connect('end_one', self.progreso.increase)
        self.connect('ended', self.progreso.close)
        self.tasks = []

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def stop(self, *args):
        self.stopit = True

    def run(self):
        try:
            executor = futures.ThreadPoolExecutor()
            for afile in self.files:
                if self.stopit is True:
                    break
                task = executor.submit(process_item, afile, self)
                self.tasks.append({'file': afile,
                                   'task': task})
            if self.stopit is True:
                for task in self.tasks:
                    if task['task'].is_running():
                        task['task'].cancel()
                        self.emit(
                            'end_one',
                            get_duration(task['file']) / self.total_duration)
            self.progreso.run()
        except Exception as e:
            self.ok = False
            print(e)
        self.emit('ended', self.ok)


def get_total_duration(files):
    total_duration = 0.0
    for afile in files:
        total_duration += float(os.path.getsize(afile))
    return total_duration


def get_duration(file_in):
    return float(os.path.getsize(file_in))


def get_files(files_in):
    files = []
    for file_in in files_in:
        if not file_in.is_directory():
            fileName, fileExtension = os.path.splitext(
                    file_in.get_location().get_path())
            if fileExtension.lower() in EXTENSIONS:
                files.append(file_in)
    return files


def process_item(file_in, extension, diib):
    duration = get_duration(file_in)
    diib.emit('start_one', os.path.basename(file_in))
    head, tail = os.path.split(file_in)
    root, ext = os.path.splitext(tail)
    file_out = os.path.join(head, root + '.' + diib.extension)
    unoconv = local['unoconv']
    unoconv['-f', 'self.extension', '-o', '"{}"'.format(file_out),
            '"{}"'.format(file_in)]()
    diib.emit('end_one', duration / diib.total_duration)


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
        diib = DoItInBackground(_('Convert file'), window, files, extension)
        diib.run()

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the FileManager
        right-click menu, connects its 'activate' signal to the 'run' method
        passing the selected Directory/File
        """
        if get_files(items) == 0:
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
                                 sel_items,
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
                                  sel_items,
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
                                  sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                  sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                 sel_items,
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
                                sel_items,
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
                                sel_items,
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
