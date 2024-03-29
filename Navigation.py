from time import time
from os import path

from enigma import eServiceCenter, eServiceReference, eTimer, pNavigation, getBestPlayableServiceReference, iPlayableService

from Components.ParentalControl import parentalControl
from Components.config import config
from Tools.BoundFunction import boundFunction
from Tools.StbHardware import getFPWasTimerWakeup
import RecordTimer
import PowerTimer
import Screens.Standby
import NavigationInstance
import ServiceReference
from Screens.InfoBar import InfoBar, MoviePlayer


# TODO: remove pNavgation, eNavigation and rewrite this stuff in python.
class Navigation:
	def __init__(self, nextRecordTimerAfterEventActionAuto=False, nextPowerManagerAfterEventActionAuto=False):
		if NavigationInstance.instance is not None:
			raise NavigationInstance.instance

		NavigationInstance.instance = self
		self.ServiceHandler = eServiceCenter.getInstance()

		import Navigation as Nav
		Nav.navcore = self

		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.dispatchEvent)
		self.pnav.m_record_event.get().append(self.dispatchRecordEvent)
		self.event = [ ]
		self.record_event = [ ]
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		self.currentlyPlayingService = None
		self.RecordTimer = RecordTimer.RecordTimer()
		self.PowerTimer = PowerTimer.PowerTimer()
		self.__wasTimerWakeup = False
		if getFPWasTimerWakeup():
			self.__wasTimerWakeup = True
			if nextRecordTimerAfterEventActionAuto and abs(self.RecordTimer.getNextRecordingTime() - time()) <= 360:
				print 'RECTIMER: wakeup to standby detected.'
				f = open("/tmp/was_rectimer_wakeup", "w")
				f.write('1')
				f.close()
				# as we woke the box to record, place the box in standby.
				self.standbytimer = eTimer()
				self.standbytimer.callback.append(self.gotostandby)
				self.standbytimer.start(15000, True)

			elif nextPowerManagerAfterEventActionAuto:
				print 'POWERTIMER: wakeup to standby detected.'
				f = open("/tmp/was_powertimer_wakeup", "w")
				f.write('1')
				f.close()
				# as a PowerTimer WakeToStandby was actiond to it.
				self.standbytimer = eTimer()
				self.standbytimer.callback.append(self.gotostandby)
				self.standbytimer.start(15000, True)

	def wasTimerWakeup(self):
		return self.__wasTimerWakeup

	def gotostandby(self):
		print 'TIMER: now entering standby'
		from Tools import Notifications
		Notifications.AddNotification(Screens.Standby.Standby)

	def dispatchEvent(self, i):
		for x in self.event:
			x(i)
		if i == iPlayableService.evEnd:
			self.currentlyPlayingServiceReference = None
			self.currentlyPlayingServiceOrGroup = None
			self.currentlyPlayingService = None

	def dispatchRecordEvent(self, rec_service, event):
#		print "record_event", rec_service, event
		for x in self.record_event:
			x(rec_service, event)

	def playService(self, ref, checkParentalControl=True, forceRestart=False, adjust=True):
		oldref = self.currentlyPlayingServiceOrGroup
		if ref and oldref and ref == oldref and not forceRestart:
			print "ignore request to play already running service(1)"
			return 0
		print "playing", ref and ref.toString()
		if path.exists("/proc/stb/lcd/symbol_signal") and config.lcd.mode.value == '1':
			try:
				if '0:0:0:0:0:0:0:0:0' not in ref.toString():
					signal = 1
				else:
					signal = 0
				f = open("/proc/stb/lcd/symbol_signal", "w")
				f.write(str(signal))
				f.close()
			except:
				f = open("/proc/stb/lcd/symbol_signal", "w")
				f.write("0")
				f.close()
		elif path.exists("/proc/stb/lcd/symbol_signal") and config.lcd.mode.value == '0':
			f = open("/proc/stb/lcd/symbol_signal", "w")
			f.write("0")
			f.close()

		# Venton series
		if path.exists("/proc/stb/lcd/symbol_scrambled") and config.lcd.mode.getValue() == '1':
			try:
				if ref.toString().find('0:0:0:0:0:0:0:0:0') == -1:
					signal = 1
				else:
					signal = 0
				open("/proc/stb/lcd/symbol_scrambled", "w").write(str(signal))
			except:
				open("/proc/stb/lcd/symbol_scrambled", "w").write("0")
		elif path.exists("/proc/stb/lcd/symbol_scrambled") and config.lcd.mode.getValue() == '0':
			open("/proc/stb/lcd/symbol_scrambled", "w").write("0")

		# Venton series
		if path.exists("/proc/stb/lcd/symbol_mp3") and config.lcd.mode.getValue() == '1':
			try:
				if ref.toString().endswith('.mp3'):
					mp3 = 1
				else:
					mp3l = 0
				open("/proc/stb/lcd/symbol_mp3", "w").write(str(mp3))
			except:
				open("/proc/stb/lcd/symbol_mp3", "w").write("0")
		elif path.exists("/proc/stb/lcd/symbol_mp3") and config.lcd.mode.getValue() == '0':
			open("/proc/stb/lcd/symbol_mp3", "w").write("0")
			
		if ref is None:
			self.stopService()
			return 0
		from Components.ServiceEventTracker import InfoBarCount
		InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
		if not checkParentalControl or parentalControl.isServicePlayable(ref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=adjust)):
			if ref.flags & eServiceReference.isGroup:
				oldref = self.currentlyPlayingServiceReference or eServiceReference()
				playref = getBestPlayableServiceReference(ref, oldref)
				print "playref", playref
				if playref and oldref and playref == oldref and not forceRestart:
					print "ignore request to play already running service(2)"
					return 0
				if not playref or (checkParentalControl and not parentalControl.isServicePlayable(playref, boundFunction(self.playService, checkParentalControl = False))):
					self.stopService()
					return 0
			else:
				playref = ref
			if self.pnav:
				self.pnav.stopService()
				self.currentlyPlayingServiceReference = playref
				self.currentlyPlayingServiceOrGroup = ref
				if InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(ref, adjust):
					self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
				if self.pnav.playService(playref):
					print "Failed to start", playref
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
				return 0
		elif oldref and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(oldref, adjust):
			self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
		return 1

	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference

	def getCurrentlyPlayingServiceOrGroup(self):
		return self.currentlyPlayingServiceOrGroup

	def isMovieplayerActive(self):
		MoviePlayerInstance = MoviePlayer.instance
		if MoviePlayerInstance is not None and '0:0:0:0:0:0:0:0:0' in self.currentlyPlayingServiceReference.toString():
			from Screens.InfoBarGenerics import setResumePoint
			setResumePoint(MoviePlayer.instance.session)
			MoviePlayerInstance.close()
			
	def recordService(self, ref, simulate=False):
		service = None
		if not simulate: print "recording service: %s" % (str(ref))
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		if ref:
			if ref.flags & eServiceReference.isGroup:
				ref = getBestPlayableServiceReference(ref, eServiceReference(), simulate)
			service = ref and self.pnav and self.pnav.recordService(ref, simulate)
			if service is None:
				print "record returned non-zero"
		return service

	def stopRecordService(self, service):
		ret = self.pnav and self.pnav.stopRecordService(service)
		return ret

	def getRecordings(self, simulate=False):
		return self.pnav and self.pnav.getRecordings(simulate)

	def getCurrentService(self):
		if not self.currentlyPlayingService:
			self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
		return self.currentlyPlayingService

	def stopService(self):
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		if path.exists("/proc/stb/lcd/symbol_signal"):
			f = open("/proc/stb/lcd/symbol_signal", "w")
			f.write("0")
			f.close()

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def shutdown(self):
		self.RecordTimer.shutdown()
		self.PowerTimer.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()
