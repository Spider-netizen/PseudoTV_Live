  # Copyright (C) 2022 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

import os, json, traceback, threading

from kodi_six                  import xbmc, xbmcgui, xbmcvfs, xbmcaddon
from datetime                  import timedelta
from resources.lib.cache       import Cache
from resources.lib.concurrency import PoolHelper

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
COLOR_LOGO    = os.path.join(ADDON_PATH,'resources','skins','default','media','logo.png')
PROMPT_DELAY  = 4000 #msecs

def dumpJSON(item):
    try:    return json.dumps(item)
    except: return ''
    
def loadJSON(item):
    try:    return json.loads(item)
    except: return {}

def setDictLST(lst):
    sLST = [dumpJSON(d) for d in lst]
    sLST = set(sLST)
    return [loadJSON(s) for s in sLST]

def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true" and level != xbmc.LOGERROR: return
    if not isinstance(msg,str): msg = str(msg)
    if level == xbmc.LOGERROR: msg = '%s\n%s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
def getThumb(item,opt=0): #unify thumbnail artwork
    keys = {0:['landscape','fanart','thumb','thumbnail','poster','clearlogo','logo','folder','icon'],
            1:['poster','clearlogo','logo','landscape','fanart','thumb','thumbnail','folder','icon']}[opt]
    for key in keys:
        art = (item.get('art',{}).get('album.%s'%(key),'')       or 
               item.get('art',{}).get('albumartist.%s'%(key),'') or 
               item.get('art',{}).get('artist.%s'%(key),'')      or 
               item.get('art',{}).get('season.%s'%(key),'')      or 
               item.get('art',{}).get('tvshow.%s'%(key),'')      or 
               item.get('art',{}).get(key,'')                    or
               item.get(key,''))
        if art: return art
    return {0:FANART,1:COLOR_LOGO}[opt]

class Settings:   
    realSetting = REAL_SETTINGS
    
    def __init__(self):
        self.cache    = Cache()
        self.property = Properties()

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
                
    def updateSettings(self):
        self.log('updateSettings')
        #todo build json of addon settings
        # self.pluginMeta.setdefault(addonID,{})['settings'] = [{'key':'value'}]
 
        
    def getRealSettings(self):
        try:    return xbmcaddon.Addon(id=ADDON_ID)
        except: return self.realSetting


    def openSettings(self):     
        self.realSetting.openSettings()
    
    
    def _getSetting(self, func, key):
        try: return func(key)
        except Exception as e: 
            self.log("_getSetting, Failed! %s - key = %s"%(e,key), xbmc.LOGERROR)

        
    def getSettingBool(self, key):
        try:    return self._getSetting(self.getRealSettings().getSettingBool,key)
        except: return self._getSetting(self.getRealSettings().getSetting,key).lower() == "true" 


    def getSettingInt(self, key):
        try: return self._getSetting(self.getRealSettings().getSettingInt,key)
        except:
            value = self._getSetting(self.getRealSettings().getSetting,key)
            if value.isdecimal():
                return int(value)
            elif value.isdigit(): 
                return int(value)  
            elif value.isnumeric():
                return int(value)
              
              
    def getSettingNumber(self, key): 
        try: return self._getSetting(self.getRealSettings().getSettingNumber,key)
        except:
            value = self._getSetting(self.getRealSettings().getSetting,key)
            if value.isdecimal():
                return float(value)
            elif value.isdigit(): 
                return int(value)    
            elif value.isnumeric():
                return int(value)
        

    def getSetting(self, key):
        return self._getSetting(self.getRealSettings().getSetting,key)
        
        
    def getSettingString(self, key):
        return self._getSetting(self.getRealSettings().getSettingString,key)
  
  
    def getSettingFloat(self, key):
        value = self._getSetting(self.getRealSettings().getSetting,key)
        if value.isdecimal():
            return float(value)
        elif value.isdigit(): 
            return float(value)  
        elif value.isnumeric():
            return float(value)
              

    def getSettingList(self, key):
        return self.getSetting(key).split('|')
    
    
    def getSettingDict(self, key):
        return loadJSON(self.getSetting(key))
    
    
    def getCacheSetting(self, key, checksum=ADDON_VERSION, json_data=False):
        value = self.cache.get(key, checksum, json_data)
        return value
        
        
    def getPropertySetting(self, key):
        return self.property.getProperty(key)
    
    
    def setCacheSetting(self, key, value, checksum=ADDON_VERSION, life=timedelta(days=84), json_data=False):
        self.log('setCacheSetting, key = %s, value = %s'%(key,value))
        self.cache.set(key, value, checksum, life, json_data)
        
            
    def setPropertySetting(self, key, value):
        return self.property.setProperty(key, value)
        
        
    def _setSetting(self, func, key, value):
        try:
            self.log('%s, key = %s, value = %s'%(func.__name__,key,value))
            func(key, value)
        except Exception as e: 
            self.log("_setSetting, Failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
        
        
    def setSetting(self, key, value=""):  
        if not isinstance(value,str): value = str(value)
        self._setSetting(self.getRealSettings().setSetting,key,value)
            
            
    def setSettingBool(self, key, value):  
        if not isinstance(value,bool): value = value.lower() == "true"
        self._setSetting(self.getRealSettings().setSettingBool,key,value)
        
           
    def setSettingInt(self, key, value):  
        if not isinstance(value,int): value = int(value)
        self._setSetting(self.getRealSettings().setSettingInt,key,value)
         
            
    def setSettingNumber(self, key, value):  
        if not isinstance(value,(int,float,log)): value = float(value)
        self._setSetting(self.getRealSettings().setSettingNumber,key,value)
        
            
    def setSettingString(self, key, value):  
        if not isinstance(value,str): value = str(value)
        self._setSetting(self.getRealSettings().setSettingString,key,value)
        
            
    def setSettingFloat(self, key, value):  
        if not isinstance(value,(float,log)): value = float(value)
        self._setSetting(self.getRealSettings().setSetting,key,value)
        
        
    def setSettingDict(self, key, values):
        self.setSetting(key, dumpJSON(values))
            
            
    def setSettingList(self, key, values):
        self.setSetting(key, '|'.join(values))
        
        
class Properties:
    def __init__(self, winID=10000):
        self.winID  = winID
        self.window = xbmcgui.Window(winID)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def getKey(self, key):
        if self.winID == 10000: #create unique id 
            return '%s.%s'%(ADDON_ID,key)
        else:
            return key


    def clearProperties(self):
        return self.window.clearProperties()
        
        
    def clearProperty(self, key):
        return self.window.clearProperty(self.getKey(key))


    def getPropertyList(self, key):
        return self.getProperty(key).split('|')

        
    def getPropertyBool(self, key):
        return self.getProperty(key).lower() == "true"
        
        
    def getPropertyDict(self, key):
        return loadJSON(self.getProperty(key))
        
        
    def getPropertyInt(self, key):
        value = self.getProperty(key)
        if isinstance(value,(int,float)):
            return int(value)
        elif value.isdecimal():
            return int(value)
        elif value.isdigit(): 
            return int(value) 
        elif value.isnumeric():
            return int(value)
            
        
    def getPropertyFloat(self, key):
        value = self.getProperty(key)
        if isinstance(value,(int,float)):
            return float(value)
        if value.isdecimal():
            return float(value)
        elif value.isdigit(): 
            return float(value)  
        elif value.isnumeric():
            return float(value)
        

    def getProperty(self, key):
        value = self.window.getProperty(self.getKey(key))
        return value
        
        
    def clearEXTProperty(self, key):
        return self.window.clearProperty(key)
        
        
    def getEXTProperty(self, key):
        return self.window.getProperty(key)
        
        
    def setEXTProperty(self, key, value):
        if not isinstance(value,str): value = str(value)
        return self.window.setProperty(key,value)
        
        
    def setPropertyList(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyBool(self, key, value):
        if not isinstance(value,bool): value = value.lower() == "true"
        return self.setProperty(key, value)
        
        
    def setPropertyDict(self, key, value):
        return self.setProperty(key, dumpJSON(value))
        
                
    def setPropertyInt(self, key, value):
        if not isinstance(value,int): value = int(value)
        return self.setProperty(key, value)
                
                
    def setPropertyFloat(self, key, value):
        if not isinstance(value,float): value = float(value)
        return self.setProperty(key, value)
        
        
    def setProperty(self, key, value):
        if not isinstance(value,str): value = str(value)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        self.window.setProperty(self.getKey(key), value)
        return True


class Dialog:
    monitor    = xbmc.Monitor()
    settings   = Settings()
    properties = Properties()
    pool       = PoolHelper()
    
    def __init__(self):
        self.infoMonitorThread = threading.Timer(0.5, self.doInfoMonitor)
        self.okDialogThread    = threading.Timer(0.5, self.okDialog)
        self.textviewerThread  = threading.Timer(0.5, self.textviewer)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def chkInfoMonitor(self):
        return self.properties.getPropertyBool('chkInfoMonitor')
        
    
    def getInfoMonitor(self):
        return self.properties.getPropertyDict('monitor.montiorList').get('info',[])
    
    
    def setInfoMonitor(self, items):
        return self.properties.setPropertyDict('monitor.montiorList',{'info':setDictLST(items)})


    def toggleInfoMonitor(self, state):
        self.properties.setPropertyBool('chkInfoMonitor',state)
        if state: 
            self.properties.clearProperty('monitor.montiorList')
            if not self.infoMonitorThread.is_alive():
                self.infoMonitorThread = threading.Timer(.5, self.doInfoMonitor)
                self.infoMonitorThread.name = "infoMonitorThread"
                self.infoMonitorThread.start()


    def doInfoMonitor(self):
        while not self.monitor.abortRequested():
            if self.monitor.waitForAbort(1): break
            elif not self.fillInfoMonitor(): break
            

    def fillInfoMonitor(self, type='ListItem'):
        if not self.chkInfoMonitor(): return False
        item = {'name'  :xbmc.getInfoLabel('%s.Label'%(type)),
                'label' :xbmc.getInfoLabel('%s.Label'%(type)),
                'label2':xbmc.getInfoLabel('%s.Label2'%(type)),
                'path'  :xbmc.getInfoLabel('%s.Path'%(type)),
                'writer':xbmc.getInfoLabel('%s.Writer'%(type)),
                'logo'  :xbmc.getInfoLabel('%s.Icon'%(type)),
                'thumb' :xbmc.getInfoLabel('%s.Thumb'%(type))}   
        if item.get('label'):
            montiorList = self.getInfoMonitor()
            montiorList.insert(0,item)
            self.setInfoMonitor(montiorList)
        return True
        
        
    @staticmethod
    def buildItemListItem(item, mType='video', oscreen=False, playable=True):
        LISTITEM_TYPES = {'label': (str,list),'genre': (list,str),
                          'country': (str,list),'year': (int,),'episode': (int,),
                          'season': (int,),'sortepisode': (int,),'sortseason': (int,),
                          'episodeguide': (str,),'showlink': (str,list),'top250': (int,),
                          'setid': (int,),'tracknumber': (int,),'rating': (float,),'userrating': (int,),
                          'playcount': (int,),'overlay': (int,),'cast': (list,),'castandrole': (list,),
                          'director': (str,list),'mpaa': (str,),'plot': (str,),'plotoutline': (str,),
                          'title': (str,),'originaltitle': (str,),'sorttitle': (str,),'duration': (int,),
                          'studio': (str,list),'tagline': (str,),'writer': (str,list),'tvshowtitle': (str,),
                          'premiered': (str,),'status': (str,),'set': (str,),'setoverview': (str,),'tag': (list,str),
                          'imdbnumber': (str,),'code': (str,),'aired': (str,),'credits': (str,list),'lastplayed': (str,),
                          'album': (str,),'artist': (list,),'votes': (str,),'path': (str,),'trailer': (str,),'dateadded': (str,),
                          'mediatype': (str,),'dbid': (int,),'track': (int,),'aspect': (float,),'codec': (str,),'language': (str,),
                          'width': (int,),'height': (int,),'duration': (int,),'channels': (int,),'audio': (list,),'video': (list,),
                          'subtitle': (list,),'stereomode': (str,),'count': (int,),'size': (int,),'date': (str,),'lyrics': (str,),
                          'musicbrainztrackid': (str,),'musicbrainzartistid': (str,),'musicbrainzalbumid': (str,),'musicbrainzalbumartistid': (str,),
                          'comment': (str,),'discnumber': (int,),'listeners': (int,)}
                          
        info       = item.copy()
        art        = info.pop('art'                ,{})
        cast       = info.pop('cast'               ,[])
        uniqueid   = info.pop('uniqueid'           ,{})
        streamInfo = info.pop('streamdetails'      ,{})
        properties = info.pop('customproperties'   ,{})
        properties.update(info.get('citem'         ,{}))# write induvial props for keys 
        properties['citem']   = info.pop('citem'   ,{}) # write dump to single key
        properties['pvritem'] = info.pop('pvritem' ,{}) # write dump to single key
        
        if mType != 'video': #unify default artwork for music.
            art['thumb']  = getThumb(info,opt=1)
            art['fanart'] = getThumb(info)
        
        def cleanInfo(ninfo):
            tmpInfo = ninfo.copy()
            for key, value in tmpInfo.items():
                types = LISTITEM_TYPES.get(key,None)
                if not types:# key not in json enum, move to customproperties
                    ninfo.pop(key)
                    properties[key] = value
                    continue
                    
                elif not isinstance(value,types):# convert to schema type
                    ninfo[key] = types[0](value)
                    
                if isinstance(ninfo[key],list):
                    for n in ninfo[key]:
                        if isinstance(n,dict):
                            n = cleanInfo(n)
                            
                if isinstance(ninfo[key],dict):
                    ninfo[key] = cleanInfo(ninfo[key])
            return ninfo
                
        def cleanProp(pvalue):
            if isinstance(pvalue,dict):
                return dumpJSON(pvalue)
            elif isinstance(pvalue,list):
                return '|'.join(map(str, pvalue))
            elif not isinstance(pvalue,str):
                return str(pvalue)
            else:
                return pvalue
                
        listitem = xbmcgui.ListItem(offscreen=oscreen)
        if info.get('label'):  listitem.setLabel(info.pop('label',''))
        if info.get('label2'): listitem.setLabel2(info.pop('label2',''))
        if info.get('file'):   listitem.setPath(item.get('file','')) # (item.get('file','') or item.get('url','') or item.get('path',''))
        
        listitem.setInfo(type=mType, infoLabels=cleanInfo(info))
        listitem.setArt(art)
        listitem.setCast(cast)
        listitem.setUniqueIDs(uniqueid)
        # listitem.setProperties({})
        # listitem.setIsFolder(True)
    
        for ainfo in streamInfo.get('audio',[]):    listitem.addStreamInfo('audio'   , ainfo)
        for vinfo in streamInfo.get('video',[]):    listitem.addStreamInfo('video'   , vinfo)
        for sinfo in streamInfo.get('subtitle',[]): listitem.addStreamInfo('subtitle', sinfo)
        for key, pvalue in properties.items():      listitem.setProperty(key, cleanProp(pvalue))
        if playable: listitem.setProperty("IsPlayable","true")
        return listitem
             
             
    def colorDialog(self, xml='', items=[], preselect=[], heading=ADDON_NAME):
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#ga571ffd3c58c38b1f81d4f98eedb78bef
        # <colors>
          # <color name="white">ffffffff</color>
          # <color name="grey">7fffffff</color>
          # <color name="green">ff00ff7f</color>
        # </colors>
        # dialog.colorpicker('Select color', 'ff00ff00', 'os.path.join(xbmcaddon.Addon().getAddonInfo("path"),"colors.xml")')
        return xbmcgui.Dialog().colorpicker(heading, colorfile=xml, colorlist=items, selectedcolor=preselect)
             
        
    def _okDialog(self, msg, heading):
        if self.okDialogThread.is_alive():
            try:
                self.okDialogThread.cancel()
                self.okDialogThread.join()
            except: pass
                
        self.okDialogThread = threading.Timer(0.5, self.okDialog, [msg, heading])
        self.okDialogThread.name = "okDialogThread"
        self.okDialogThread.start()
        
        
    def okDialog(self, msg, heading=ADDON_NAME, usethread=False):
        if usethread: return self._okDialog(msg, heading)
        else:         return xbmcgui.Dialog().ok(heading, msg)
        
        
    def _textviewer(self, msg, heading, usemono):
        if self.textviewerThread.is_alive():
            try:
                self.textviewerThread.cancel()
                self.textviewerThread.join()
            except: pass
                
        self.textviewerThread = threading.Timer(0.5, self.textviewer, [msg, heading, usemono])
        self.textviewerThread.name = "textviewerThread"
        self.textviewerThread.start()
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False, usethread=False):
        if usethread: return self._textviewer(msg, heading, usemono)
        else:         return xbmcgui.Dialog().textviewer(heading, msg, usemono)
        
    
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0): 
        if customlabel:
            # Returns the integer value for the selected button (-1:cancelled, 0:no, 1:yes, 2:custom)
            return xbmcgui.Dialog().yesnocustom(heading, message, customlabel, nolabel, yeslabel, autoclose)
        else: 
            # Returns True if 'Yes' was pressed, else False.
            return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, autoclose)


    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=COLOR_LOGO):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except: xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             
             
    def selectDialog(self, list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=0, multi=True, custom=False):
        if multi == True:
            if preselect is None: preselect = [-1]
            if custom: ... #todo domodel custom selectDialog for library select.
            else:
                select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
        else:
            if preselect is None: preselect = -1
            if custom: ... #todo domodel custom selectDialog for library select.
            else:
                select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
                if select == -1:  select = None
        return select
      
      
    def inputDialog(self, message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
        ## - xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - xbmcgui.INPUT_NUMERIC (format: #)
        ## - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - xbmcgui.INPUT_TIME (format: HH:MM)
        ## - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        return xbmcgui.Dialog().input(message, default, key, opt, close)
        
        
    def buildMenuListItem(self, label1="", label2="", iconImage=None, url="", infoItem=None, artItem=None, propItem=None, oscreen=False, mType='video'):
        listitem  = xbmcgui.ListItem(label1, label2, path=url, offscreen=oscreen)
        iconImage = (iconImage or COLOR_LOGO)
        if propItem: 
            listitem.setProperties(propItem)
        if infoItem: 
            if infoItem.get('label'):  listitem.setLabel(infoItem.pop('label',''))
            if infoItem.get('label2'): listitem.setLabel2(infoItem.pop('label2',''))
            listitem.setInfo(mType, infoItem)
        else: 
            listitem.setLabel(label1)
            listitem.setLabel2(label2)
            listitem.setInfo(mType, {'mediatype': 'video', 'Title' : label1})
                                         
        if artItem: 
            listitem.setArt(artItem)
        else: 
            listitem.setArt({'thumb': iconImage,
                             'logo' : iconImage,
                             'icon' : iconImage})
        return listitem
        
        
    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False, monitor=False):
        def buildMenuItem(option):
            return self.buildMenuListItem(option['label'],option['label2'],iconImage=COLOR_LOGO)
            
        if prompt:
            if options is None:
                options = [{"label":"Video Playlists" , "label2":"Video Playlists"               , "default":"special://videoplaylists/"          , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Music Playlists" , "label2":"Music Playlists"               , "default":"special://musicplaylists/"          , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Video"           , "label2":"Video Sources"                 , "default":"library://video/"                   , "mask":xbmc.getSupportedMedia('video')   , "type":0, "multi":False},
                           {"label":"Music"           , "label2":"Music Sources"                 , "default":"library://music/"                   , "mask":xbmc.getSupportedMedia('music')   , "type":0, "multi":False},
                           {"label":"Pictures"        , "label2":"Picture Sources"               , "default":""                                   , "mask":xbmc.getSupportedMedia('picture') , "type":0, "multi":False},
                           {"label":"Files"           , "label2":"File Sources"                  , "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Local"           , "label2":"Local Drives"                  , "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Network"         , "label2":"Local Drives and Network Share", "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Resources"       , "label2":"Resource Plugins"              , "default":"resource://"                        , "mask":""                                , "type":0, "multi":False}]
                if default:
                    default, file = os.path.split(default)
                    if file: type = 1
                    else:    type = 0
                    options.insert(0,{"label":"Existing Path", "label2":default, "default":default , "mask":"", "type":type, "multi":False})
                    
            listitems = self.pool.poolList(buildMenuItem,options)
            select    = self.selectDialog(listitems, LANGUAGE(30116), multi=False)
            if select is not None:
                # if options[select]['default'] == "resource://": #TODO PARSE RESOURCE JSON, LIST PATHS
                    # listitems = self.pool.poolList(buildMenuItem,options)
                    # select    = self.selectDialog(listitems, LANGUAGE(30116), multi=False)
                    # if select is not None:
                # else:    
                shares    = options[select]['label'].lower().replace("network","")
                mask      = options[select]['mask']
                type      = options[select]['type']
                multi     = options[select]['multi']
                default   = options[select]['default']
            else: return
                
        self.log('browseDialog, type = %s, heading= %s, shares= %s, mask= %s, useThumbs= %s, treatAsFolder= %s, default= %s'%(type, heading, shares, mask, useThumbs, treatAsFolder, default))
        if monitor: self.toggleInfoMonitor(True)
        if multi == True:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
            ## type integer - the type of browse dialog.
            ## 1	ShowAndGetFile
            ## 2	ShowAndGetImage
            retval = xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        else:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
            ## type integer - the type of browse dialog.
            ## 0	ShowAndGetDirectory
            ## 1	ShowAndGetFile
            ## 2	ShowAndGetImage
            ## 3	ShowAndGetWriteableDirectory
            retval = xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        if monitor: self.toggleInfoMonitor(False)
        if options is not None and default == retval: return
        return retval
        
        
    def notificationWait(self, message, header=ADDON_NAME, wait=4):
        pDialog = self.progressBGDialog(message=message,header=header)
        for idx in range(wait):
            pDialog = self.progressBGDialog((((idx) * 100)//wait),control=pDialog,header=header)
            if self.monitor.waitForAbort(1): break
        return self.progressBGDialog(100,control=pDialog)


    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME, silent=None):
        if not isinstance(percent,int): percent = int(percent)
        if silent is None:
            silent = (self.settings.getSettingBool('Silent_OnPlayback') & (self.properties.getPropertyBool('OVERLAY') | xbmc.getCondVisibility('Player.Playing')))
        
        if silent and hasattr(control, 'close'): 
            control.close()
            return
        elif control is None and percent == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if percent == 100 or control.isFinished(): 
                if hasattr(control, 'close'): control.close()
                return
            elif hasattr(control, 'update'): control.update(percent, header, message)
        return control
        

    def progressDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if not isinstance(percent,int): percent = int(percent)
        if control is None and percent == 0:
            control = xbmcgui.DialogProgress()
            control.create(header, message)
        elif control:
            if percent == 100 or control.iscanceled(): 
                if hasattr(control, 'close'): control.close()
                return
            elif hasattr(control, 'update'): control.update(percent, message)
        return control
        
   
    def infoDialog(self, listitem):
        xbmcgui.Dialog().info(listitem)
        
        
class ListItems: #TODO move listitem funcs. here.
    def __init__(self):
        ...
