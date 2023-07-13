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

# -*- coding: utf-8 -*-

from globals    import *
from jsonrpc    import JSONRPC
from predefined import Predefined
from resources  import Resources
from channels   import Channels

#constants
REG_KEY    = 'PseudoTV_Recommended.%s'

TYPE_TEMP  = {"enabled": False,
			  "type"   : "",
			  "name"   : "",
			  "logo"   : "",
			  "path"   : []}
            
IMPORT_TEMP = {"enabled": False,
			   "type"   : "",
			   "name"   : "",
			   "logo"   : "",
			   "item"   : {"id"   : "",
				           "type" : "",
                           "name" : "",
				           "icon" : "",
				           "m3u"  : {"path": "",
					                 "slug": ""},
				           "xmltv": {"path": ""}}}
    
class Library:
    def __init__(self, service=None):
        self.parserCount  = 0
        self.parserMSG    = ''
        self.parserDialog = None
        
        self.service      = service
        self.cache        = Cache()
        self.jsonRPC      = JSONRPC()
        self.predefined   = Predefined()
        self.channels     = Channels()
        self.resources    = Resources(self.jsonRPC,self.cache)
        self.libraryDATA  = getJSON(LIBRARYFLE_DEFAULT)
        self.libraryDATA.update(self._load())

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def _load(self):
        return getJSON(LIBRARYFLEPATH)
    
    
    def _save(self):
        return setJSON(LIBRARYFLEPATH,self.libraryDATA)
        
        
    def getLibrary(self, type):
        self.log('getLibrary, type = %s'%(type))
        return self.libraryDATA.get('library',{}).get(type,[])
        
        
    def setLibrary(self, type, data=[]):
        self.log('setLibrary')
        self.libraryDATA['library'][type] = data
        SETTINGS.setSetting('Select_%s'%(slugify(type)),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(self.getEnabled(type)),len(data)))
        return self._save()


    def getEnabled(self, type):
        return [item for item in self.getLibrary(type) if item.get('enabled',False)]

    
    def fillItems(self):
        def fillItem(type):
            funcs = {"Playlists"    :self.getPlaylists,
                     "TV Networks"  :self.getNetworks,
                     "TV Shows"     :self.getTVShows,
                     "TV Genres"    :self.getTVGenres,
                     "Movie Genres" :self.getMovieGenres,
                     "Movie Studios":self.getMovieStudios,
                     "Mixed Genres" :self.getMixedGenres,
                     "Mixed"        :self.getMixed,
                     "Recommended"  :self.getRecommend,
                     "Services"     :self.getServices,
                     "Music Genres" :self.getMusicGenres}
            try: return funcs[type]()
            except Exception as e: 
                self.log('fillItem failed! %s'%(e), xbmc.LOGERROR)
                return []
                
        self.parserDialog = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
        for idx, type in enumerate(AUTOTUNE_TYPES):
            if self.service.monitor.chkSuspend():
                self.log('fillItems, suspended')
                break
            
            with self.service.monitor.idleLocker():
                self.parserMSG    = AUTOTUNE_TYPES[idx]
                self.parserCount  = int((idx+1)*100//len(AUTOTUNE_TYPES))
                self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,self.parserMSG,'%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                yield (type,fillItem(type))
                
        
    @timeit
    def updateLibrary(self):
        self.log('updateLibrary')
        def _updateItem(type,item):
            entry = TYPE_TEMP.copy()
            entry.update(item)
            #check existing library for enabled items
            for item in self.getEnabled(type):
                if entry.get('name').lower() == item.get('name').lower():
                    entry['enabled'] = True
            #check existing channels for enabled items
            for channel in self.channels.getType(type):
                if entry.get('name').lower() == channel.get('name').lower():
                    entry['enabled'] = True
            return entry
           
        complete = True 
        libraryItems = dict(self.fillItems())
        dia = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32022),LANGUAGE(32041))))
        for idx,type in enumerate(AUTOTUNE_TYPES):
            dia = DIALOG.progressBGDialog(int(idx*100//len(AUTOTUNE_TYPES)),dia,AUTOTUNE_TYPES[idx],'%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32022),LANGUAGE(32041))))
            if self.service.monitor.chkSuspend(): 
                self.log('updateLibrary, suspended')
                complete = False
                break
            else:
                items = libraryItems.get(type,[])
                PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.%s'%(slugify(type)),str(len(items)>0).lower())
                self.setLibrary(type, [_updateItem(type,item) for item in items])
        DIALOG.progressBGDialog(100,dia,LANGUAGE(32025)) 
        return complete
        

    def resetLibrary(self, ATtypes=AUTOTUNE_TYPES):
        self.log('resetLibrary')
        for ATtype in ATtypes: 
            items = self.getLibrary(ATtype)
            for item in items: item['enabled'] = False #disable everything before selecting new items.
            self.setLibrary(ATtype, items)


    @cacheit(json_data=True)
    def getNetworks(self):
        return self.getTVInfo().get('studios',[])
        
        
    @cacheit(json_data=True)
    def getTVGenres(self):
        return self.getTVInfo().get('genres',[])
 
 
    @cacheit(expiration=datetime.timedelta(hours=int(REAL_SETTINGS.getSetting('Max_Days'))),json_data=True)
    def getTVShows(self):
        return self.getTVInfo().get('shows',[])
        
        
    @cacheit(json_data=True)
    def getMovieStudios(self):
        return self.getMovieInfo().get('studios',[])
        
        
    @cacheit(json_data=True)
    def getMovieGenres(self):
        return self.getMovieInfo().get('genres',[])
              
 
    @cacheit(json_data=True)
    def getMusicGenres(self):
        return self.getMusicInfo().get('genres',[])
 
         
    @cacheit(json_data=True)
    def getMixedGenres(self):
        MixedGenreList = [{'name':tv.get('name'),'type':"Mixed Genres",'path':self.predefined.createProvisional(tv.get('name')),'logo':tv.get('logo')}
        for tv in self.getTVGenres() for movie in self.getMovieGenres() if tv.get('name','').lower() == movie.get('name','').lower()]
        self.log('getMixedGenres, genres = %s' % (len(MixedGenreList)))
        return sorted(MixedGenreList,key=lambda x:x['name'])


    @cacheit(json_data=True)
    def getMixed(self):
        def hasRecordings():
            return self.jsonRPC.walkListDirectory('pvr://recordings/tv/active/',verify_runtime=True) #todo add infobool to Kodi core.
               
        MixedList = []
        if hasTV() or hasMovie():
            MixedList.append({'name':LANGUAGE(32001), 'type':"Mixed",'path':self.predefined.createMixedRecent()  ,'logo':self.resources.getLogo(LANGUAGE(32001),"Mixed")}) #"Recently Added"
            MixedList.append({'name':LANGUAGE(32002), 'type':"Mixed",'path':self.predefined.createSeasonal()     ,'logo':self.resources.getLogo(LANGUAGE(32002),"Mixed")}) #"Seasonal"
        
        if hasRecordings():
            MixedList.append({'name':LANGUAGE(32003), 'type':"Mixed",'path':self.predefined.createPVRRecordings(),'logo':self.resources.getLogo(LANGUAGE(32003),"Mixed")}) #"PVR Recordings"
        
        self.log('getMixed, mixed = %s' % (len(MixedList)))
        return sorted(MixedList,key=lambda x:x['name'])
    
    
    @cacheit(expiration=datetime.timedelta(minutes=int(REAL_SETTINGS.getSetting('Max_Days'))),json_data=True)
    def getPlaylists(self):
        PlayList = []
        types    = ['video','mixed','music']
        for type in types:
            results = self.jsonRPC.getDirectory(param={"directory":"special://profile/playlists/%s"%(type)})
            for idx, result in enumerate(results.get('files',[])):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s (%s): %s'%(self.parserMSG,type.title(),int((idx+1)*100//len(results.get('files',[]))))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                
                if not result.get('label'): continue
                logo = (result.get('thumbnail') or self.resources.getLogo(result.get('label'),"Playlists"))
                PlayList.append({'name':result.get('label'),'type':"%s Playlist"%(type.title()),'path':[result.get('file')],'logo':logo})
        self.log('getPlaylists, PlayList = %s' % (len(PlayList)))
        PlayList = sorted(PlayList,key=lambda x:x['name'])
        PlayList = sorted(PlayList,key=lambda x:x['type'])
        return PlayList


    def getTVInfo(self, sortbycount=True):
        self.log('getTVInfo')
        if hasTV():
            NetworkList   = Counter()
            ShowGenreList = Counter()
            TVShows       = Counter()
            json_response = self.jsonRPC.getTVshows()
            
            for idx, info in enumerate(json_response):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s: %s'%(self.parserMSG,int((idx+1)*100//len(json_response)))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                
                if not info.get('label'): continue
                TVShows.update({json.dumps({'name': info.get('label'), 'type':"TV Shows", 'path': self.predefined.createProvisional(info.get('label')), 'logo': info.get('art', {}).get('clearlogo', '')}): info.get('episode', 0)})
                NetworkList.update([studio for studio in info.get('studio', [])])
                ShowGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                TVShows = [json.loads(x[0]) for x in sorted(TVShows.most_common(250))]
                NetworkList = [x[0] for x in sorted(NetworkList.most_common(50))]
                ShowGenreList = [x[0] for x in sorted(ShowGenreList.most_common(25))]
            else:
                TVShows = (sorted(map(json.loads, list(TVShows.keys())), key=lambda k: k['name']))
                del TVShows[250:]
                NetworkList = (sorted(set(list(NetworkList.keys()))))
                del NetworkList[250:]
                ShowGenreList = (sorted(set(list(ShowGenreList.keys()))))
                
            #search resources for studio/genre logos
            NetworkList   = [{'name':network, 'type':"TV Networks", 'path': self.predefined.createProvisional(network),'logo':self.resources.getLogo(network,"TV Networks")} for network in NetworkList]
            ShowGenreList = [{'name':tvgenre, 'type':"TV Genres"  , 'path': self.predefined.createProvisional(tvgenre),'logo':self.resources.getLogo(tvgenre,"TV Genres")}   for tvgenre in ShowGenreList]
            
        else: NetworkList = ShowGenreList = TVShows = []
        self.log('getTVInfo, networks = %s, genres = %s, shows = %s' % (len(NetworkList), len(ShowGenreList), len(TVShows)))
        return {'studios':NetworkList,'genres':ShowGenreList,'shows':TVShows}


    def getMovieInfo(self, sortbycount=True):
        self.log('getMovieInfo')
        if hasMovie():        
            StudioList     = Counter()
            MovieGenreList = Counter()
            json_response  = self.jsonRPC.getMovies()

            for idx, info in enumerate(json_response):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s: %s'%(self.parserMSG,int((idx+1)*100//len(json_response)))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                    
                StudioList.update([studio for studio in info.get('studio', [])])
                MovieGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                StudioList = [x[0] for x in sorted(StudioList.most_common(25))]
                MovieGenreList = [x[0] for x in sorted(MovieGenreList.most_common(25))]
            else:
                StudioList = (sorted(set(list(StudioList.keys()))))
                del StudioList[250:]
                MovieGenreList = (sorted(set(list(MovieGenreList.keys()))))
                
            #search resources for studio/genre logos
            StudioList     = [{'name':studio, 'type':"Movie Studios", 'path': self.predefined.createProvisional(studio) ,'logo':self.resources.getLogo(studio,"Movie Studios")} for studio in StudioList]
            MovieGenreList = [{'name':genre,  'type':"Movie Genres" , 'path': self.predefined.createProvisional(genre)  ,'logo':self.resources.getLogo(genre ,"Movie Genres")} for genre in MovieGenreList]
            
        else: StudioList = MovieGenreList = []
        self.log('getMovieInfo, studios = %s, genres = %s' % (len(StudioList), len(MovieGenreList)))
        return {'studios':StudioList,'genres':MovieGenreList}
        
        
    def getMusicInfo(self, sortbycount=True):
        self.log('getMusicInfo')
        if hasMusic():
            MusicGenreList = Counter()
            json_response  = self.jsonRPC.getMusicGenres()
            
            for idx, info in enumerate(json_response):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s: %s'%(self.parserMSG,int((idx+1)*100//len(json_response)))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                
                MusicGenreList.update([genre for genre in info.get('label','').split(';')])
            
            if sortbycount:
                MusicGenreList = [x[0] for x in sorted(MusicGenreList.most_common(50))]
            else:
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))
                del MusicGenreList[250:]
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))

            #search resources for studio/genre logos
            MusicGenreList = [{'name':genre, 'type':"Music Genres", 'path': self.predefined.createMusicGenrePlaylist(genre),'logo':self.resources.getLogo(genre,"Music Genres")} for genre in MusicGenreList]

        else: MusicGenreList = []
        self.log('getMusicInfo, found genres = %s' % (len(MusicGenreList)))
        return {'genres':MusicGenreList}
        
        
    def getRecommend(self):
        self.log('getRecommend')
        PluginList = []
        WhiteList  = self.getWhiteList()
        AddonsList = self.searchRecommended()
        for addonid, item in list(AddonsList.items()):
            if addonid not in WhiteList: continue
            items = item.get('data',{}).get('vod',[])
            items.extend(item.get('data',{}).get('live',[]))
            for vod in items:
                path = vod.get('path')
                if not isinstance(path,list): path = [path]
                PluginList.append({'id':item['meta'].get('name'), 'name':vod.get('name'), 'type':"Recommended", 'path': path, 'logo':vod.get('icon',item['meta'].get('thumbnail'))})
        self.log('getRecommend, found (%s) vod items.' % (len(PluginList)))
        PluginList = sorted(PluginList,key=lambda x:x['name'])
        PluginList = sorted(PluginList,key=lambda x:x['id'])
        return PluginList
            

    def getRecommendInfo(self, addonid):
        self.log('getRecommendInfo, addonid = %s'%(addonid))
        return self.searchRecommended().get(addonid,{})
        

    def searchRecommended(self):
        def _search(addonid):
            cacheName = 'searchRecommended.%s'%(getMD5(addonid))
            addonMeta = self.jsonRPC.getAddonDetails(addonid)
            payload   = PROPERTIES.getEXTProperty(REG_KEY%(addonid))
            if not payload: #startup services may not be broadcasting beacon; use last cached beacon instead.
                payload = self.cache.get(cacheName, checksum=addonMeta.get('version',ADDON_VERSION), json_data=True)
            else:
                payload = loadJSON(payload)
                self.cache.set(cacheName, payload, checksum=addonMeta.get('version',ADDON_VERSION), expiration=datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days'))), json_data=True)
            
            if payload:
                self.log('searchRecommended, found addonid = %s, payload = %s'%(addonid,payload))
                return addonid,{"data":payload,"meta":addonMeta}
                
        if not SETTINGS.getSettingBool('Enable_Recommended') or isClient(): return []
        addonList = sorted(list(set([_f for _f in [addon.get('addonid') for addon in list([k for k in self.jsonRPC.getAddons() if k.get('addonid','') not in self.getBlackList()])] if _f])))
        return dict([_f for _f in [_search(addonid) for addonid in addonList] if _f])


    def getServices(self):
        self.log('getServices')
        return []


    def getWhiteList(self):
        #whitelist - prompt shown, added to import list and/or manager dropdown.
        return self.libraryDATA.get('whitelist',[])
        
        
    def setWhiteList(self, data=[]):
        self.libraryDATA['whitelist'] = sorted(list(set(data)))
        return self._save()
        
        
    def getBlackList(self):
        #blacklist - plugin ignored for the life of the list.
        return self.libraryDATA.get('blacklist',[])
    
        
    def setBlackList(self, data=[]):
        self.libraryDATA['blacklist'] = sorted(list(set(data)))
        return self._save()
        
        
    def addWhiteList(self, addonid):
        self.log('addWhiteList, addonid = %s'%(addonid))
        whiteList = self.getWhiteList()
        whiteList.append(addonid)
        whiteList = list(set(whiteList))
        if len(whiteList) > 0: PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.WhiteList',len(whiteList) > 0)
        return self.setWhiteList(whiteList)
        

    def addBlackList(self, addonid):
        self.log('addBlackList, addonid = %s'%(addonid))
        blackList = self.getBlackList()
        blackList.append(addonid)
        blackList = list(set(blackList))
        return self.setBlackList(blackList)


    def clearBlackList(self):
        return self.setBlackList()

               
    def importPrompt(self):
        if isClient(): return
        addonList = self.searchRecommended()
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList()) #filter addons previously parsed.
        addonNames = sorted(list(set([_f for _f in [item.get('meta',{}).get('name') for addonid, item in list(addonList.items()) if not addonid in ignoreList] if _f])))
        self.log('importPrompt, addonNames = %s'%(len(addonNames)))
        
        try:
            if len(addonNames) > 1:
                retval = DIALOG.yesnoDialog('%s'%(LANGUAGE(32055)%(ADDON_NAME,', '.join(addonNames))), customlabel=LANGUAGE(32056), autoclose=90)
                self.log('importPrompt, prompt retval = %s'%(retval))
                if   retval == 1: raise Exception('Single Entry')
                elif retval == 2: 
                    for addonid, item in list(addonList.items()):
                        if item.get('meta',{}).get('name') in addonNames:
                            self.addWhiteList(addonid)
            else: raise Exception('Single Entry')
        except Exception as e:
            self.log('importPrompt, %s'%(e))
            for addonid, item in list(addonList.items()):
                if item.get('meta',{}).get('name') in addonNames:
                    if not DIALOG.yesnoDialog('%s'%(LANGUAGE(32055)%(ADDON_NAME,item['meta'].get('name',''))), autoclose=90):
                        self.addBlackList(addonid)
                    else:
                        self.addWhiteList(addonid)
                
        PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.WhiteList',str(len(self.getWhiteList()) > 0).lower())
        PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.BlackList',str(len(self.getBlackList()) > 0).lower())
        SETTINGS.setSetting('Clear_BlackList','|'.join(self.getBlackList()))
        
