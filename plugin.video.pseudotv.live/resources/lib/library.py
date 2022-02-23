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

# -*- coding: utf-8 -*-

from resources.lib.globals     import *
from resources.lib.predefined  import Predefined 

REG_KEY = 'PseudoTV_Recommended.%s'

class Library:
    def __init__(self, writer=None):
        self.chkLibraryThread = threading.Timer(30.0, self.chkLibraryTimer)
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        else: self.chkLibraryThread.start()
            
        self.writer      = writer
        self.cache       = writer.cache
        self.pool        = writer.pool
        self.channels    = writer.channels
        self.predefined  = Predefined()
        self.recommended = Recommended(library=self)

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _withdraw(self):
        self.log('_withdraw')
        return self.writer.vault.get_libraryItems()
     
 
    def _deposit(self):
        self.log('_deposit')
        self.writer.vault.set_libraryItems(self.writer.vault.libraryItems)
        return True
        
    
    def _clear(self):
        self.log('_clear')
        self.writer.vault.libraryItems = None
        return self._deposit()
        
        
    def _save(self):
        filePath = LIBRARYFLEPATH
        self.log('_save, saving to %s'%(filePath))
        with fileLocker(self.writer.globalFileLock):
            fle = FileAccess.open(filePath, 'w')
            fle.write(dumpJSON(self.writer.vault.libraryItems, idnt=4, sortkey=False))
            fle.close()
        return self._deposit()
        

    @cacheit()
    def getNetworks(self):
        return self.writer.jsonRPC.getTVInfo().get('studios',[])
        
        
    @cacheit()
    def getTVGenres(self):
        return self.writer.jsonRPC.getTVInfo().get('genres',[])
 
 
    @cacheit(expiration=datetime.timedelta(hours=REAL_SETTINGS.getSettingInt('Max_Days')))
    def getTVShows(self):
        return self.writer.jsonRPC.getTVInfo().get('shows',[])
 
 
    @cacheit()
    def getMovieStudios(self):
        return self.writer.jsonRPC.getMovieInfo().get('studios',[])
        
        
    @cacheit()
    def getMovieGenres(self):
        return self.writer.jsonRPC.getMovieInfo().get('genres',[])
              
 
    @cacheit()
    def getMusicGenres(self):
        return self.writer.jsonRPC.getMusicInfo().get('genres',[])
 
         
    def getMixedGenres(self):
        return [tv for tv in self.getTVGenres() for movie in self.getMovieGenres() if tv.lower() == movie.lower()]


    def getMixed(self):
        return [LANGUAGE(30078),#"Recently Added"
                LANGUAGE(30141),#"Seasonal"
                LANGUAGE(30079)]#"PVR Recordings"


    def fillTypeItems(self, type):
        funcs = {LANGUAGE(30002):self.getNetworks,
                 LANGUAGE(30003):self.getTVShows,
                 LANGUAGE(30004):self.getTVGenres,
                 LANGUAGE(30005):self.getMovieGenres,
                 LANGUAGE(30007):self.getMovieStudios,
                 LANGUAGE(30006):self.getMixedGenres,
                 LANGUAGE(30080):self.getMixed,
                 LANGUAGE(30097):self.getMusicGenres,
                 LANGUAGE(30026):self.recommended.fillRecommended,
                 LANGUAGE(30033):self.recommended.fillImports}
        return funcs[type]()

            
    def chkLibraryTimer(self, wait=LIBRARY_OFFSET):
        self.log('chkLibraryTimer, wait = %s'%(wait))
        if self.chkLibraryThread.is_alive(): 
            try: 
                self.chkLibraryThread.cancel()
                self.chkLibraryThread.join()
            except: pass
                
        if isBusy(): wait = 30.0
        else: 
            with busy(): 
                self.fillLibraryItems()
            
        self.chkLibraryThread = threading.Timer(wait, self.chkLibraryTimer)
        self.chkLibraryThread.name = "chkLibraryThread"
        self.chkLibraryThread.start()
                    
                
    def fillLibraryItems(self):
        self.log('fillLibraryItems')
        ## parse kodi for items, convert to library item, update logo,vfs path. save to library.json
        def fillType(type):
            items      = self.fillTypeItems(type)
            existing   = self.getLibraryItems(type)
            enabled    = self.getEnabledItems(existing)
            channels   = self.channels.getPredefinedChannelsByType(type)
            cacheName  = 'fillType.%s'%(type)
            cacheCHK   = '%s.%s.%s'%(getMD5(dumpJSON(items)),getMD5(dumpJSON(enabled)),getMD5(dumpJSON(channels)))
            
            if existing: msg = LANGUAGE(30328)
            else:        msg = LANGUAGE(30159) 
               
            results = self.writer.cache.get(cacheName, checksum=cacheCHK, json_data=True)
            if not results or not existing:
                results  = []
                if type == LANGUAGE(30003): #meta doesn't need active refresh, except for tv shows which may change more often than genres.
                    life = datetime.timedelta(hours=REAL_SETTINGS.getSettingInt('Max_Days'))
                else:
                    life = datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Max_Days'))
                    
                self.log('fillType, type = %s, items = %s, existing = %s, enabled = %s'%(type, len(items),len(existing),len(enabled)))
                pDialog = self.writer.dialog.progressBGDialog(header='%s, %s'%(ADDON_NAME,LANGUAGE(30332)))
                for idx, item in enumerate(items):
                    if self.writer.monitor.waitForAbort(0.001) or self.writer.monitor.isSettingsOpened() or isClient(): return
                    pCount  = int((CHAN_TYPES.index(type)*100)//len(CHAN_TYPES))
                    pDialog = self.writer.dialog.progressBGDialog(pCount, pDialog, message='%s: %s'%(type,int(((idx+1)*100)//len(items)))+'%',header='%s, %s'%(ADDON_NAME,msg))
                    
                    name = item
                    if isinstance(item,dict):
                        name = (item.get('name','') or item.get('label',''))
                    if not name: continue
                        
                    #enabled library item (same as existing, except only "enabled":True items).
                    try:    enabled_item = list(filter(lambda k:k['name'] == name, enabled))[0]
                    except: enabled_item = {}

                    #channel item (fallback). Use channels.json to restore missing enabled library items.
                    try:    channel_item = list(filter(lambda k:k['name'] == name, channels))[0]
                    except: channel_item = {}
                        
                    if not enabled_item and channel_item:
                        enabled_item = channel_item
                         
                    if isinstance(item,dict):
                        if type in [LANGUAGE(30026),LANGUAGE(30033)]: 
                            logo = item.get('icon','')
                        else: 
                            logo = self.writer.jsonRPC.resources.getLogo(name, type, item.get('file',''), item)
                    else: 
                        logo = self.writer.jsonRPC.resources.getLogo(name, type, item=enabled_item)

                    tmpItem = {'enabled':len(enabled_item) > 0,
                               'name':name,
                               'type':type,
                               'logo':logo}
                               
                    if    type == LANGUAGE(30026): tmpItem['path'] = item['path'] #Recommended
                    elif  type == LANGUAGE(30033): tmpItem['item'] = item
                    else: tmpItem['path'] = self.predefined.pathTypes[type](name) #Predefined
                    results.append(tmpItem) 
                    
                if results: #only cache found items.
                    self.setLibraryItems(type,results)
                    self.writer.cache.set(cacheName, results, checksum=cacheCHK, expiration=life, json_data=True)
                self.writer.dialog.progressBGDialog(100, pDialog, message=LANGUAGE(30053))
                    
            if not PROPERTIES.getPropertyBool('has.Predefined'): 
                PROPERTIES.setPropertyBool('has.Predefined',(len(results) > 0))
            PROPERTIES.setPropertyBool('has.%s'%(type.replace(' ','_')),(len(results) > 0))
           
        for type in CHAN_TYPES: 
            fillType(type)
            
        setLibraryRun(True)
        return self.writer.buildPredefinedChannels()
        

    def setLibraryItems(self, type, items):
        self.log('setLibraryItems, type = %s, items = %s'%(type,len(items)))
        self.writer.vault.libraryItems.get('library',{})[type] = sorted(items, key=lambda k:k['name'])
        SETTINGS.setSetting('Select_%s'%(type.replace(' ','_')),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(self.getEnabledItems(items)),len(items)))
        return self._save()


    def getLibraryItems(self, type, enabled=False):
        self.log('getLibraryItems, type = %s, enabled = %s'%(type,enabled))
        items = self.writer.vault.libraryItems.get('library',{}).get(type,[])
        if enabled: return self.getEnabledItems(items)
        return sorted(items, key=lambda k: k['name'])
        
        
    def getEnabledItems(self, items):
        if not items: return []
        self.log('getEnabledItems, items = %s'%(len(items)))
        def chkEnabled(item):
            if item.get('enabled',False): 
                return item
            else:
                return None
        return sorted(self.pool.poolList(chkEnabled,items), key=lambda k: k['name'])
        # return sorted(filter(lambda k:k.get('enabled',False) == True, items), key=lambda k: k.get('name'))


    def buildLibraryListitem(self, data):
        if isinstance(data,tuple): data = list(data)
        return self.writer.dialog.buildMenuListItem(data[0]['name'],data[1],iconImage=data[0]['logo'])


    def setEnableStates(self, type, selects, items=None):
        if items is None: items = self.getLibraryItems(type)
        self.log('setEnableStates, type = %s, items = %s, selects = %s'%(type, len(items), selects))
        for idx, item in enumerate(items):
            if idx in selects: item['enabled'] = True
            else:              item['enabled'] = False
        return self.setLibraryItems(type,items)

        
    def clearLibraryItems(self, type=None):
        self.log('clearLibraryItems, type = %s'%(type))
        def setDisabled(item):
            item['enabled'] = False
            return item
            
        if type is None: types = CHAN_TYPES
        else:            types = [type]
        for type in types:
            self.setLibraryItems(type,self.pool.poolList(setDisabled,self.getLibraryItems(type)))
        return True
        

class Recommended:
    def __init__(self, library):
        self.library = library
        self.cache   = library.cache
        self.pool    = library.pool
        
        if self.library.chkLibraryThread.is_alive(): 
            self.chkRecommendedThread = threading.Timer(15.0, self.chkRecommendedTimer)
            self.chkRecommendedThread.start()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def getRecommendedItems(self):
        return self.library.writer.vault.libraryItems.get('recommended',{})


    def getWhiteList(self):
        #whitelist - prompt shown, added to import list and/or manager dropdown.
        return list(set(self.getRecommendedItems().get('whitelist',[])))
        
        
    def getBlackList(self):
        #blacklist - plugin ignored for the life of the list.
        return list(set(self.getRecommendedItems().get('blacklist',[])))
    
    
    def addWhiteList(self, addonid):
        self.log('addWhiteList, addonid = %s'%(addonid))
        whiteList = self.getWhiteList()
        whiteList.append(addonid)
        self.library.writer.vault.libraryItems.get('recommended',{})['whitelist'] = list(set(whiteList))
        if len(whiteList) > 0: 
            PROPERTIES.setPropertyBool('has.WhiteList',len(whiteList) > 0)
        return True
        

    def addBlackList(self, addonid):
        self.log('addBlackList, addonid = %s'%(addonid))
        blackList = self.getBlackList()
        blackList.append(addonid)
        self.library.writer.vault.libraryItems.get('recommended',{})['blacklist'] = list(set(blackList))
        self.setBlackList(self.library.writer.vault.libraryItems.get('recommended',{})['blacklist'])
        return True


    def clearBlackList(self):
        self.library.writer.vault.libraryItems.get('recommended',{})['blacklist'] = []
        if self.library.save(): self.setBlackList(self.getBlackList())
        return True
        
        
    def chkRecommendedTimer(self, wait=RECOMMENDED_OFFSET):
        self.log('chkRecommendedTimer, wait = %s'%(wait))
        if self.chkRecommendedThread.is_alive(): 
            try: 
                self.chkRecommendedThread.cancel()
                self.chkRecommendedThread.join()
            except: pass
                
        if isBusy(): wait = 15.0
        else: 
            with busy(): 
                self.importPrompt()
            
        self.chkRecommendedThread = threading.Timer(wait, self.chkRecommendedTimer)
        self.chkRecommendedThread.name = "chkRecommendedThread"
        self.chkRecommendedThread.start()
                    
      
    def searchRecommendedAddons(self):
        if not SETTINGS.getSettingBool('Enable_Recommended'): return []
        blackList = self.getBlackList()
        addonList = [addon.get('addonid') for addon in list(filter(lambda k:k.get('addonid','') not in blackList, self.library.writer.jsonRPC.getAddons()))]
        return (self.pool.poolList(self.searchRecommendedAddon, addonList) or [])
        
        
    # @cacheit(expiration=datetime.timedelta(seconds=RECOMMENDED_OFFSET),json_data=True)
    def searchRecommendedAddon(self, addonid):
        addonData = PROPERTIES.getEXTProperty(REG_KEY%(addonid))
        if addonData:
            self.log('searchRecommendedAddon, found addonid = %s, payload = %s'%(addonid,addonData))
            return {addonid:{"id":addonid,"data":loadJSON(addonData),"meta":self.library.writer.jsonRPC.getPluginMeta(addonid)}}
        

    def findbyType(self, type='iptv'):
        self.log('findbyType, type = %s'%(type))
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        return sorted([item[addonid]['data'][type] for addonid in whiteList for item in recommendedAddons if item.get(addonid,{}).get('data',{}).get(type,[])],key=lambda x:x['name'])


    def fillImports(self):
        items = self.findbyType(type='iptv')
        self.log('fillImports, found = %s'%(len(items)))
        return items


    def fillRecommended(self):
        tmpLST = []
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        items = sorted((item.get(addonid) for item in recommendedAddons for addonid in whiteList if item.get(addonid,{})),key=lambda x:x['id'])
        [tmpLST.extend(item['data'][key]) for item in items for key in item['data'].keys() if key != 'iptv']
        tmpLST = sorted(tmpLST,key=lambda x:x.get('name'))
        tmpLST = sorted(tmpLST,key=lambda x:x['id'])
        self.log('fillRecommended, found = %s'%(len(tmpLST)))
        return tmpLST


    def importSingles(self, recommendedAddons):
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        for item in recommendedAddons:
            addon = list(item.keys())[0]
            self.log('importSingles, adding %s'%(addon))
            if not addon in ignoreList:
                if not self.library.writer.dialog.yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,item[addon]['meta'].get('name',''))), autoclose=90000):  
                    self.addBlackList(addon)
                else:
                    self.addWhiteList(addon)
        return True
        

    def importMulti(self, recommendedAddons):
        addons     = []
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        for item in recommendedAddons: 
            addon = list(item.keys())[0]
            if not addon in ignoreList: 
                addons.append(item[addon]['meta'].get('name',''))
        
        if len(addons) > 0:
            retval = self.library.writer.dialog.yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,', '.join(addons))), customlabel=LANGUAGE(30214), autoclose=90000)
            self.log('importMulti, retval = %s'%(retval))
            if   retval == 1: return self.importSingles(recommendedAddons)
            elif retval == 2: 
                for item in recommendedAddons:
                    addon = list(item.keys())[0]
                    self.log('importMulti, adding %s'%(addon))
                    self.addWhiteList(addon)
                return True
            else:
                return False


    def importPrompt(self):
        if isClient(): return
        recommendedAddons = self.searchRecommendedAddons()
        self.log('importPrompt, recommendedAddons = %s'%(len(recommendedAddons)))
        if len(recommendedAddons) > 1: 
            changed = self.importMulti(recommendedAddons)
        else: 
            changed = self.importSingles(recommendedAddons)
            
        PROPERTIES.setPropertyBool('has.WhiteList',len(self.getWhiteList()) > 0)
        PROPERTIES.setPropertyBool('has.BlackList',len(self.getBlackList()) > 0)
        SETTINGS.setSetting('Clear_BlackList','|'.join(self.getBlackList()))
        
        if changed: self.library._save()
        return changed