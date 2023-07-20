#   Copyright (C) 2022 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

from globals    import *
from producer   import Producer
from overlay    import Overlay, Background
from rules      import RulesList
from jsonrpc    import JSONRPC
from server     import HTTP, Discovery, Announcement
from threading  import enumerate

class Player(xbmc.Player):
    pvritem      = {}
    myService    = False
    pendingPlay  = False
    isPseudoTV   = False
    lastSubState = isSubtitle()
    rules        = RulesList()
    runActions   = rules.runActions
    
    def __init__(self):
        self.log('__init__')
        xbmc.Player.__init__(self)
        self.background = None
        
        """ 
        Player() Trigger Order
        Player: onPlayBackStarted
        Player: onAVChange (if playing)
        Player: onAVStarted
        Player: onPlayBackSeek (if seek)
        Player: onAVChange (if changed)
        Player: onPlayBackError
        Player: onPlayBackEnded
        Player: onPlayBackStopped
        """
              
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.pendingPlay = True
        

    def onAVChange(self):
        self.log('onAVChange')
        self.pendingPlay  = False
        self.lastSubState = isSubtitle()
            
        
    def onAVStarted(self):
        self.pvritem    = self.getPlayerPVRitem()
        self.isPseudoTV = not None in [self.pvritem.get('channelid'),self.pvritem.get('citem',{}).get('id')]
        self.log('onAVStarted, isPseudoTV = %s'%(self.isPseudoTV))
        if self.isPseudoTV: self._onPlay()
        
        
    def onPlayBackSeek(self, seek_time=None, seek_offset=None): #Kodi bug? `OnPlayBackSeek` no longer called by player during seek, limited to pvr?
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
    
    
    def onPlayBackError(self):
        self.log('onPlayBackError')
        if isPseudoTV: self._onError()
        
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        if self.isPseudoTV: self._onChange()

        
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        if self.isPseudoTV: self._onStop()
        self.pvritem     = {}
        self.isPseudoTV  = False
        self.pendingPlay = False
        
        
    def getPlayerPVRitem(self):
        try:    pvritem = loadJSON(self.getPlayingItem().getProperty('pvritem')) #Kodi v20.
        except: pvritem = {'citem':{}}
        pvritem.update({'citem':self.getPlayerCitem()})
        self.log('getPlayerPVRitem, pvritem = %s'%(pvritem))
        return pvritem
        
        
    def getPlayerCitem(self):
        try:    citem = loadJSON(self.getPlayingItem().getProperty('citem')) #Kodi v20.
        except: citem = decodeWriter(BUILTIN.getInfoLabel('Writer','VideoPlayer')).get('citem',{})
        self.log('getPlayerCitem, citem = %s'%(citem))
        return citem
        

    def getPlayerFile(self):
        try:    return self.getPlayingFile()
        except: return ''


    def getPlayerTime(self):
        try:    return self.getTotalTime()
        except: return 0
                
                
    def getPlayerProgress(self):
        try:    return float(BUILTIN.getInfoLabel('Player.Progress'))
        except: return 0.0


    def getElapsedTime(self):
        try:    return int(self.getTime() // 1000)
        except: return 0


    def getTimeRemaining(self):
        try:    return int(sum(x*y for x, y in zip(list(map(float, BUILTIN.getInfoLabel('TimeRemaining(hh:mm:ss)','Player').split(':')[::-1])), (1, 60, 3600, 86400))))
        except: return 0
   
   
    def getPVRTime(self):
        try:    return (sum(x*y for x, y in zip(list(map(float, BUILTIN.getInfoLabel('EpgEventElapsedTime(hh:mm:ss)','PVR').split(':')[::-1])), (1, 60, 3600, 86400))))
        except: return 0
        
        
    def setSubtitles(self, state):
        self.log('setSubtitles, state = %s'%(state))
        if state and (not hasSubtitle() or not self.isPseudoTV): return
        self.showSubtitles(state)

   
    def _onPlay(self):
        self.log('_onPlay')
        self.toggleBackground(False)
        if self.pvritem.get('citem',{}).get('id') != self.pvritem.get('citem',{}).get('id',random.random()): #playing new channel
            self.pvritem = self.runActions(RULES_ACTION_PLAYER_START, self.pvritem.get('citem'), self.pvritem, inherited=self)
            # self.setSubtitles(self.lastSubState) #todo allow rules to set sub preference per channel. 

        
    def _onChange(self):
        self.log('_onChange, channelid = %s,'%(self.pvritem.get("channelid",'')))
        self.toggleBackground()
        if not self.pvritem: self._onStop()
        else:
            try:
                if self.pvritem.get('isPlaylist',False):
                    broadcastnext = self.pvritem['broadcastnext']
                    self.pvritem['broadcastnow']  = broadcastnext.pop(0)
                    self.pvritem['broadcastnext'] = broadcastnext
                    self.log('_onChange, isPlaylist = %s, broadcastnext = %s'%(self.pvritem.get('isPlaylist'), len(self.pvritem['broadcastnext'])))
                    if len(broadcastnext) == 0: raise Exception('empty broadcastnext')
                else: raise Exception('using callback')
                # JSONRPC().playerOpen('{"item":{"channelid":%s}}'%(self.pvritem["channelid"])) #slower than playmedia
                # JSONRPC().playerOpen('{"item":{"broadcastid":%s}}'%(self.pvritem['broadcastnow']["broadcastid"])) #calls catchup vod
            except Exception as e:
                self.runActions(RULES_ACTION_PLAYER_STOP, self.pvritem.get('citem',{}), inherited=self)
                self.log('_onChange, callback = %s: %s'%(self.pvritem.get('callback'),e))
                BUILTIN.executebuiltin('PlayMedia(%s)'%(self.pvritem.get('callback')))
        
        
    def _onStop(self):
        self.log('_onStop')
        self.toggleBackground(False)
        self.runActions(RULES_ACTION_PLAYER_STOP, self.pvritem.get('citem',{}), inherited=self)
        if self.pvritem.get('isPlaylist',False): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()


    def _onError(self, pvritem):
        self.log('_onError, playing file = %s'%(self.getPlayerFile()))
        self.onPlayBackStopped()
        
        
    def toggleBackground(self, state=True):
        self.log('toggleBackground, state = %s'%(state))
        if state and not PROPERTIES.getEXTProperty('%s.OVERLAY_BACKGROUND'%(ADDON_ID)) == "true":
            self.background = Background("%s.background.xml"%(ADDON_ID), ADDON_PATH, "default", player=self)
            PROPERTIES.setEXTProperty('%s.OVERLAY_BACKGROUND'%(ADDON_ID),'true')
            self.background.show()
        elif not state and not self.background is None:
            self.background.close()
            PROPERTIES.setEXTProperty('%s.OVERLAY_BACKGROUND'%(ADDON_ID),'false')
            del self.background
            if self.isPlaying():
                BUILTIN.executebuiltin('ActivateWindow(fullscreenvideo)')
                    

class Monitor(xbmc.Monitor):
    def __init__(self):
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.pendingChange    = False
        self.pendingRestart   = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

  
    @contextmanager
    def idleLocker(self, wait=0.001):
        #only pause actions after init. firstrun
        dia     = None
        elapsed = 0
        while not self.abortRequested():
            if self.chkInterrupt(wait): break
            elif not isBusy(): break
            elapsed += wait
            if dia is None: dia = DIALOG.progressBGDialog(message='%s %s'%(LANGUAGE(32144),LANGUAGE(32145)))
            else:           dia = DIALOG.progressBGDialog(elapsed,dia)
        try: yield
        finally:
            if not dia is None: DIALOG.progressBGDialog(100,dia,'%s %s'%(LANGUAGE(32144),LANGUAGE(32146)))
        

    def chkSuspend(self, wait=0.001):
        pendingChange  = (isPendingChange()  | self.pendingChange)
        pendingRestart = (isPendingRestart() | self.pendingRestart)
        pendingSuspend = (self.waitForAbort(wait) | pendingChange | pendingRestart)
        self.log('chkSuspend, pendingSuspend = %s'%(pendingSuspend))
        return pendingSuspend
        
        
    def chkInterrupt(self, wait=0.001):
        pendingRestart   = (isPendingRestart() | self.pendingRestart)
        pendingInterrupt = (self.waitForAbort(wait) | pendingRestart)
        self.log('chkInterrupt, pendingInterrupt = %s'%(pendingInterrupt))
        return pendingInterrupt
        
        
    def chkChange(self):
        self.pendingChange = (isPendingChange() | self.pendingChange)
        self.log('chkChange, pendingChange = %s'%(self.pendingChange))
        setPendingChange(False)
        return self.pendingChange
        
        
    def chkRestart(self):
        self.pendingRestart = (isPendingRestart() | self.pendingRestart)
        self.log('chkRestart, pendingRestart = %s'%(self.pendingRestart))
        setPendingRestart(False)
        return self.pendingRestart


    def getIdle(self):
        try: idleTime = (int(xbmc.getGlobalIdleTime()) or 0)
        except: #Kodi raises error after sleep.
            log('globals: getIdleTime, Kodi waking up from sleep...')
            idleTime = 0
        idleState = (idleTime > OVERLAY_DELAY)
        if (idleTime == 0 or idleTime <= 5): log("globals: getIdle, idleState = %s, idleTime = %s"%(idleState,idleTime))
        return idleState,idleTime

        
    def toggleOverlay(self, state):
        self.log("toggleOverlay, state = %s"%(state))
        if state:
            conditions = SETTINGS.getSettingBool('Enable_Overlay') & self.myService.player.isPlaying() & self.myService.player.isPseudoTV
            if not conditions: return
            self.myService.overlay.open()
        elif not state:
            self.myService.overlay.close()


    def chkIdle(self):
        isIdle,idleTime = self.getIdle()
        sleepTime = (SETTINGS.getSettingInt('Idle_Timer') or 0)
        if self.myService.player.isPseudoTV:
            if sleepTime > 0 and (idleTime > (sleepTime * 10800)): #3hr increments
                if self.triggerSleep(): return False
        if isIdle: self.toggleOverlay(True)
        else:      self.toggleOverlay(False)
        return isIdle


    def triggerSleep(self):
        conditions = not isPaused() & self.myService.player.isPlaying() & self.myService.player.isPseudoTV
        self.log("triggerSleep, conditions = %s"%(conditions))
        if not conditions: return
        if self.sleepTimer():
            self.myService.player.stop()
            return True
        
        
    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/OVERLAY_DELAY)
        playSFX(NOTE_WAV)
        dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        while not self.abortRequested() and (sec < OVERLAY_DELAY):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(32039),LANGUAGE(32040)%((OVERLAY_DELAY-sec)))
            dia = DIALOG.progressDialog((inc*sec),dia, msg)
            if self.waitForAbort(1) or dia is None:
                cnx = True
                break
        DIALOG.progressDialog(100,dia)
        return not bool(cnx)

        
    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def isSettingsOpened(self):
        isSettingDialog = (PROPERTIES.getPropertyBool('addonsettings') or BUILTIN.getInfoBool('IsVisible(addonsettings)','Window'))
        isSelectDialog  = (PROPERTIES.getPropertyBool('selectdialog')  or BUILTIN.getInfoBool('IsVisible(selectdialog)' ,'Window'))
        return (isSettingDialog | isSelectDialog)

  
    def onSettingsChanged(self):
        self.log('onSettingsChanged, pendingChange = %s'%(self.pendingChange))
        if self.pendingChange: timerit(self._onSettingsChanged)(15.0)
                
                
    def _onSettingsChanged(self):
        self.log('_onSettingsChanged')
        self.pendingChange = False
        if not isClient(): self.myService.channels = self.myService.producer.chkChannelChange(self.myService.channels)  #check for channel change, rebuild if needed.
        self.myService.settings = self.myService.producer.chkSettingsChange(self.myService.settings) #check for settings change, take action if needed.


class Service():
    setClient(isClient())
    player   = Player()
    monitor  = Monitor()
    overlay  = Overlay(player)
    http     = HTTP(monitor)
    announce = Announcement(monitor)
    disco    = Discovery(monitor)
    
    def __init__(self):
        self.log('__init__')
        debugNotification()
        DIALOG.notificationWait('%s...'%(LANGUAGE(32054)),wait=OVERLAY_DELAY)#startup delay; give Kodi PVR time to initialize. 
        if self.player.isPlaying(): self.player.onAVStarted() #if playback already in-progress run onAVStarted tasks.
        self.producer = Producer(service=self)
        self.channels = self.producer.getChannels()       #startup channels
        self.settings = dict(self.producer.getSettings()) #startup settings
        self.player.myService  = self
        self.monitor.myService = self
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def _start(self):
        self.log('_start')
        self.producer._startProcess()
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(1): 
                self.log('_start, waitForAbort')
                DIALOG.notificationDialog(LANGUAGE(32141)%(ADDON_NAME))
                return self._stop()
            elif self.monitor.chkRestart():
                self.log('_start, pending restart')
                DIALOG.notificationDialog(LANGUAGE(32049)%(ADDON_NAME))
                return self._restart()
            elif self.monitor.isSettingsOpened():
                self.log('_start, pending change')
                self.monitor.pendingChange = True
                timerit(self.monitor.onSettingsChanged)(15.0) #onSettingsChanged() not called when kodi settings cancelled. call timer instead.
            elif not self.monitor.chkChange():
                self._tasks()
        
                
    def _tasks(self):
        isIdle = self.monitor.chkIdle()
        if (isLowPower()) and hasFirstrun(): setBusy(not bool(isIdle)) #pause background building after first-run while low power devices are in use/not idle.
        if not isClient(): self.producer._taskManager() #chk/run scheduled tasks.
                    
        
    def _restart(self):
        if self._stop():
            Service()._start()
        
        
    def _stop(self):
        for thread in enumerate():
            try: 
                if thread.name == "MainThread": continue
                self.log("_stop, joining thread %s"%(thread.name))
                try: 
                    thread.cancel()
                    thread.join(1.0)
                except: pass
            except Exception as e: log("_start, failed! %s"%(e), xbmc.LOGERROR)
        self.log('_stop, finished, exiting %s...'%(ADDON_NAME))
        return True

        
if __name__ == '__main__': Service()._start()