from Plugins.Plugin import PluginDescriptor

#------------------------------------------------------------------------------------------

def Pic_Thumb(*args, **kwa):
	import ui
	return ui.Pic_Thumb(*args, **kwa)

def picshow(*args, **kwa):
	import ui
	return ui.picshow(*args, **kwa)

def main(session, **kwargs):
	from ui import picshow
	session.open(picshow)

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("Picture player"), main, "picture_player", 1)]
	return []
      
def filescan_open(list, session, **kwargs):
	# Recreate List as expected by PicView
	filelist = [((file.path, False), None) for file in list]
	from ui import Pic_Full_View
	session.open(Pic_Full_View, filelist, 0, file.path)

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	import os

	# Overwrite checkFile to only detect local
	class LocalScanner(Scanner):
		def checkFile(self, file):
			return os.path.exists(file.path)

	return \
		LocalScanner(mimetypes = ["image/jpeg", "image/png", "image/gif", "image/bmp"],
			paths_to_scan =
				[
					ScanPath(path = "DCIM", with_subdirs = True),
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Pictures",
			description = _("View photos..."),
			openfnc = filescan_open,
		)

def Plugins(**kwargs):
	return \
		[PluginDescriptor(name=_("PicturePlayer"), where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan)]

