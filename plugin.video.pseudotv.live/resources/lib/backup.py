 #   Copyright (C) 2023 Lunatixz
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
# https://github.com/kodi-community-addons/script.module.simplecache/blob/master/README.md
# -*- coding: utf-8 -*-
 
from globals    import *
from library    import Library
from channels   import Channels

BACKUP_TIME_FORMAT = '%Y-%m-%d %I:%M %p'

class Backup:
    def __init__(self, sysARG=sys.argv):
        self.sysARG   = sysARG
        self.channels = Channels()
        
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getFileDate(self, file):
        try:
            fname = pathlib.Path(xbmcvfs.translatePath(file))
            mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime)
            stime = mtime.strftime(BACKUP_TIME_FORMAT)
            self.log('getFileDate, modified %s on %s'%(file,stime))
            return stime
        except:
            return LANGUAGE(32105) #Unknown
        
        
    def hasBackup(self):
        with busy_dialog():
            self.log('hasBackup')
            if FileAccess.exists(CHANNELFLE_BACKUP) and not isClient():
                PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.Backup',"true")
                backup_channel = (SETTINGS.getSetting('Backup_Channels') or 'Last Backup: Unknown')
                if backup_channel == 'Last Backup: Unknown':
                    SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),self.getFileDate(CHANNELFLE_BACKUP)))
                if not SETTINGS.getSetting('Recover_Channels'):
                    SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(self.getChannels())))
                return True
            PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.Backup',"false")
            SETTINGS.setSetting('Backup_Channels'  ,'')
            SETTINGS.setSetting('Recover_Channels' ,'')
            return False
            
            
    def getChannels(self, file=CHANNELFLE_BACKUP):
        self.log('getChannels')
        return self.channels._load(file).get('channels',[])


    def backupChannels(self):
        self.log('backupChannels')
        if   isClient(): return DIALOG.notificationDialog(LANGUAGE(32058))
        elif FileAccess.exists(CHANNELFLE_BACKUP):
            if not DIALOG.yesnoDialog('%s\n%s?'%(LANGUAGE(32108),SETTINGS.getSetting('Backup_Channels'))): 
                return False
                
        with busy_dialog():
            if FileAccess.copy(CHANNELFLEPATH,CHANNELFLE_BACKUP):
                PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.Backup',"true")
                SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),datetime.datetime.now().strftime(BACKUP_TIME_FORMAT)))
                SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(self.getChannels())))
                return DIALOG.notificationDialog('%s %s'%(LANGUAGE(32110),LANGUAGE(32025)))
        return self.hasBackup()
        
        
    def recoverChannels(self, file=CHANNELFLE_BACKUP):
        self.log('recoverChannels, file = %s'%(file))
        if   isClient(): return DIALOG.notificationDialog(LANGUAGE(32058))
        elif not DIALOG.yesnoDialog('%s'%(LANGUAGE(32109)%(SETTINGS.getSetting('Recover_Channels').replace(LANGUAGE(30216),''),SETTINGS.getSetting('Backup_Channels')))): 
            return False
        with busy_dialog():
            self.recoverChannelsFromBackup(file)
        return True
        
        
    def recoverChannelsFromBackup(self, file=CHANNELFLE_BACKUP):
        newChannels = self.getChannels()
        difference  = sorted(diffLSTDICT(self.getChannels(CHANNELFLE_DEFAULT),newChannels), key=lambda k: k['number'])
        self.log('recoverChannelsFromBackup, file = %s, difference = %s'%(file,len(difference)))
        
        if len(difference) > 0:
            pDialog = DIALOG.progressDialog(message=LANGUAGE(32113))

            for idx, citem in enumerate(difference):
                pCount = int(((idx + 1)*100)//len(difference))
                if citem in newChannels: 
                    pDialog = DIALOG.progressDialog(pCount,pDialog,message="%s: %s"%(LANGUAGE(32113),citem.get('name')),header='%s, %s'%(ADDON_NAME,LANGUAGE(30338)))
                    self.channels.addChannel(citem)
                else: 
                    self.channels.delChannel(citem)
            Library().resetLibrary()
            return self.channels.setChannels()
        return False
        
  
    def run(self):  
        ctl = (0,2) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))

        if   param == 'Backup_Channels':  self.backupChannels()
        elif param == 'Recover_Channels': self.recoverChannels()
        return openAddonSettings(ctl)
        
if __name__ == '__main__': Backup(sys.argv).run()