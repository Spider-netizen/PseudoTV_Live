#   Copyright (C) 2024 Lunatixz
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
from channels   import Channels
from rules      import RulesList
from xmltvs     import XMLTVS
from xsp        import XSP
from m3u        import M3U
from fillers    import Fillers
from resources  import Resources
from seasonal   import Seasonal 

class Builder:
    loopback   = {}
    
    def __init__(self, service=None):
        #global dialog
        self.pDialog    = None
        self.pCount     = 0
        self.pMSG       = ''
        self.pName      = ''
        self.pErrors    = []
        
        #global rules
        self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
        self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
        self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
        self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
        self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
        self.saveDuration     = SETTINGS.getSettingBool('Store_Duration')
        self.epgArt           = SETTINGS.getSettingInt('EPG_Artwork')
        self.enableGrouping   = SETTINGS.getSettingBool('Enable_Grouping')
        self.minDuration      = SETTINGS.getSettingInt('Seek_Tolerance')
        self.limit            = SETTINGS.getSettingInt('Page_Limit')
        
        self.filters          = {} #{"and": [{"operator": "contains", "field": "title", "value": "Star Wars"},{"operator": "contains", "field": "tag", "value": "Good"}],"or":[]}
        self.sort             = {"ignorearticle":True,"method":"random","order":"ascending","useartistsortname":True}
        self.limits           = {"end":-1,"start":0,"total":0}
        self.maxDays          = MAX_GUIDEDAYS
        self.minEPG           = EPG_DURATION
        
        self.cache            = SETTINGS.cacheDB
        self.service          = service
        self.jsonRPC          = service.jsonRPC
        self.runActions       = service.player.runActions
        
        self.channels         = Channels()
        self.xmltv            = XMLTVS()
        self.xsp              = XSP()
        self.m3u              = M3U()
        self.resources        = Resources(self.jsonRPC)
           
        
        self.bctTypes = {"ratings" :{"min":-1,"max":SETTINGS.getSettingInt('Enable_Preroll') ,"auto":SETTINGS.getSettingInt('Enable_Preroll')  == -1,"enabled":bool(SETTINGS.getSettingInt('Enable_Preroll')) ,
                         "sources" :{"ids":SETTINGS.getSetting('Resource_Ratings').split('|'),"paths":[os.path.join(FILLER_LOC,'Ratings' ,'')]},"items":{}},
                         "bumpers" :{"min":-1,"max":SETTINGS.getSettingInt('Enable_Preroll') ,"auto":SETTINGS.getSettingInt('Enable_Preroll')  == -1,"enabled":bool(SETTINGS.getSettingInt('Enable_Preroll')) ,
                         "sources" :{"ids":SETTINGS.getSetting('Resource_Bumpers').split('|'),"paths":[os.path.join(FILLER_LOC,'Bumpers' ,'')]},"items":{}},
                         "adverts" :{"min":-1,"max":SETTINGS.getSettingInt('Enable_Postroll'),"auto":SETTINGS.getSettingInt('Enable_Postroll') == -1,"enabled":bool(SETTINGS.getSettingInt('Enable_Postroll')),
                         "sources" :{"ids":SETTINGS.getSetting('Resource_Adverts').split('|'),"paths":[os.path.join(FILLER_LOC,'Adverts' ,'')]},"items":{},
                         "incIspot":SETTINGS.getSettingBool('Include_Adverts_iSpot')},
                         "trailers":{"min":-1,"max":SETTINGS.getSettingInt('Enable_Postroll'),"auto":SETTINGS.getSettingInt('Enable_Postroll') == -1,"enabled":bool(SETTINGS.getSettingInt('Enable_Postroll')),
                         "sources" :{"ids":SETTINGS.getSetting('Resource_Trailers').split('|'),"paths":[os.path.join(FILLER_LOC,'Trailers','')]},"items":{},
                         "incKODI":SETTINGS.getSettingBool('Include_Trailers_KODI'),
                         "incIMDB":SETTINGS.getSettingBool('Include_Trailers_IMDB')}}


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def verify(self, channels: list=[]):
        if not channels: channels = self.channels.getChannels()
        PROPERTIES.setEXTProperty('%s.has.Channels'%(ADDON_ID),str(len(channels)>0).lower())
        
        for idx, citem in enumerate(channels):
            if self.service._interrupt(): break
            elif not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('verify, skipping - missing necessary channel meta\n%s'%(citem))
                continue
            else:
                citem['name'] = validString(citem['name']) #todo temp. correct existing file names; drop by v.0.6
                citem['logo'] = self.resources.getLogo(citem['name'],citem['type'],logo=Seasonal().getHoliday().get('logo') if citem['name'] == LANGUAGE(32002) else None)
                self.log('verify, channel %s: %s - %s'%(citem['number'],citem['name'],citem['id']))
                yield self.runActions(RULES_ACTION_CHANNEL_CITEM, citem, citem, inherited=self)

            
    def build(self):
        with PROPERTIES.legacy():
            channels = sorted(self.verify(self.channels.getChannels()), key=itemgetter('number'))
            if not channels:
                self.log('build, no verified channels found!')
                return False, False
                
            now       = getUTCstamp()
            start     = roundTimeDown(getUTCstamp(),offset=60)#offset time to start bottom of the hour
            stopTimes = dict(self.xmltv.loadStopTimes(fallback=datetime.datetime.fromtimestamp(start).strftime(DTFORMAT)))
            self.pDialog = DIALOG.progressBGDialog()
            self.completeBuild = True
            
            updated = False
            for idx, citem in enumerate(channels):
                if self.service._interrupt() or self.service._suspend():
                    self.pErrors = [LANGUAGE(32160)]
                    self.completeBuild = False
                    break
                else:
                    self.runActions(RULES_ACTION_CHANNEL_START, citem, inherited=self)
                    self.pName  = citem['name']
                    self.pCount = int(idx*100//len(channels))
                    
                    if   (stopTimes.get(citem['id']) or start) > (now + ((self.maxDays * 86400) - 43200)): self.pMSG = '%s %s'%(LANGUAGE(32028),LANGUAGE(32023)) #Checking
                    elif  stopTimes.get(citem['id']):                                                      self.pMSG = '%s %s'%(LANGUAGE(32022),LANGUAGE(32023)) #Updating
                    else:                                                                                  self.pMSG = '%s %s'%(LANGUAGE(32021),LANGUAGE(32023)) #Building
                    
                    cacheResponse = self.getFileList(citem, now, (stopTimes.get(citem['id']) or start))# {False:'In-Valid Channel w/o programmes)', True:'Valid Channel that exceeds MAX_DAYS', list:'Valid Channel w/ programmes}
                    if cacheResponse:
                        if self.addChannelStation(citem) and (isinstance(cacheResponse,list) and len(cacheResponse) > 0):
                            updated = self.addChannelProgrammes(citem, cacheResponse) #added xmltv lineup entries.
                    else: 
                        if self.completeBuild: self.pErrors.append(LANGUAGE(32026))
                        chanErrors = ' | '.join(list(sorted(set(self.pErrors))))
                        self.log('build, In-Valid Channel (%s) %s - %s'%(chanErrors, citem['id'],self.pName))
                        self.pDialog = DIALOG.progressBGDialog(self.pCount, self.pDialog, message='%s: %s'%(self.pName,chanErrors),header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32027),LANGUAGE(32023))))
                        self.delChannelStation(citem)
                    self.runActions(RULES_ACTION_CHANNEL_STOP, citem, inherited=self)
                        
            self.pDialog = DIALOG.progressBGDialog(100, self.pDialog, message='%s %s'%(self.pMSG,LANGUAGE(32025) if self.completeBuild else LANGUAGE(32135)))
            self.log('build, completeBuild = %s, updated = %s, saved = %s'%(self.completeBuild,updated,self.saveChannelLineups()))
            return self.completeBuild, updated

        
    def getFileList(self, citem: dict, now: time, start: time) -> bool and list:
        self.log('getFileList, id: %s, start = %s'%(citem['id'],start))
        try:
            if start > (now + ((self.maxDays * 86400) - 43200)): #max guidedata days to seconds.
                self.log('getFileList, id: %s programmes over MAX_DAYS: start = %s'%(citem['id'],datetime.datetime.fromtimestamp(start)),xbmc.LOGINFO)
                return True# prevent over-building
            
            multi = len(citem.get('path',[])) > 1 #multi-path source
            radio = True if citem.get('radio',False) else False
            media = 'music' if radio else 'video'
            self.log('getFileList, id: %s, multipath = %s, radio = %s, media = %s, path = %s'%(citem['id'],multi,radio,media,citem.get('path')),xbmc.LOGINFO)

            if radio: cacheResponse = self.buildRadio(citem)
            else:     cacheResponse = self.buildChannel(citem)
            
            if cacheResponse:
                if self.fillBCTs and not radio: cacheResponse = Fillers(self).injectBCTs(citem, cacheResponse)
                return sorted(self.addScheduling(citem, cacheResponse, start), key=itemgetter('start'))
            return cacheResponse
        except Exception as e: self.log("getFileList, failed! %s"%(e), xbmc.LOGERROR)
        return False


    def buildCells(self, citem: dict={}, duration: int=10800, type: str='video', entries: int=3, info: dict={}) -> list:
        self.log("buildCells; id: %s"%(citem.get('id')))
        tmpItem  = {'label'       : (info.get('title','')        or citem['name']),
                    'episodetitle': (info.get('episodetitle','') or '|'.join(citem['group'])),
                    'plot'        : (info.get('plot' ,'')        or LANGUAGE(30161)),
                    'genre'       : (info.get('genre','')        or ['Undefined']),
                    'file'        : (info.get('path','')         or '|'.join(citem.get('path'))),
                    'art'         : (info.get('art','')          or {"thumb":COLOR_LOGO,"fanart":FANART,"logo":LOGO,"icon":LOGO}),
                    'type'        : type,
                    'duration'    : duration,
                    'start'       : 0,
                    'stop'        : 0}
        return [tmpItem.copy() for idx in range(entries)]


    def addScheduling(self, citem: dict, fileList: list, start: time) -> list:
        self.log("addScheduling; id: %s, fileList = %s, start = %s"%(citem['id'],len(fileList),start))
        totDur  = 0
        tmpList = []

        for idx, item in enumerate(self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_PRE, citem, fileList, inherited=self)):
            item["idx"]   = idx
            item['start'] = start
            item['stop']  = start + item['duration']
            start = item['stop']
            totDur += item['duration']
            tmpList.append(item)
            
        iters = cycle(fileList) #todo adv. rule and global opt. 
        while self.service.monitor.abortRequested() and totDur < self.minEPG:
            if self.service._interrupt(): break
            else: 
                idx += 1
                item = next(iters).copy()
                item["idx"]   = idx
                item['start'] = start
                item['stop']  = start + item['duration']
                start = item['stop']
                totDur += item['duration']
                tmpList.append(item)
            
        #force removal of channel with no current programmes
        if len(tmpList) > 0:
            if tmpList[-1].get('stop') < getUTCstamp():
                self.log("addScheduling; id: %s, last stop = %s, returning empty tmpList\nNo Current Programs!!"%(citem['id'],fileList[-1].get('stop')))
                tmpList = []
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_POST, citem, tmpList, inherited=self) #adv. scheduling second pass and cleanup.
        
        
    def buildRadio(self, citem: dict) -> list:
        self.log("buildRadio; id: %s"%(citem.get('id')))
        #todo insert custom radio labels,plots based on genre type?
        # https://www.musicgenreslist.com/
        # https://www.musicgateway.com/blog/how-to/what-are-the-different-genres-of-music
        return self.buildCells(citem, self.minEPG, 'music', ((self.maxDays * 8)), info={'genre':["Music"],'art':{'thumb':citem['logo'],'icon':citem['logo'],'fanart':citem['logo']},'plot':LANGUAGE(32029)%(citem['name'])})
        

    def buildChannel(self, citem: dict) -> bool and list:
        def _validFileList(fileArray):
            for fileList in fileArray:
                if len(fileList) > 0: return True
                
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, citem, list(), inherited=self)
        if not _validFileList(fileArray):
            for idx, file in enumerate(citem.get('path',[])):
                if self.service._interrupt() or self.service._suspend(): break
                else: 
                    if len(citem.get('path',[])) > 1: self.pName = '%s %s/%s'%(citem['name'],idx+1,len(citem.get('path',[])))
                    fileArray.append(self.buildFileList(citem, self.runActions(RULES_ACTION_CHANNEL_BUILD_PATH, citem, file, inherited=self), 'video', self.limit, self.sort, self.limits))

        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, citem, fileArray, inherited=self)
        if not _validFileList(fileArray):#check that at least one fileList in array contains meta
            self.log("buildChannel, id: %s skipping channel fileArray empty!"%(citem['id']),xbmc.LOGINFO)
            return False
            
        self.log("buildChannel, id: %s fileArray arrays = %s"%(citem['id'],len(fileArray)))
        fileList = interleave(fileArray) #todo move intervleaving to adv. rules. RULES_ACTION_CHANNEL_BUILD_FILELIST
        #Primary rule for handling adv. interleaving, must return single list to avoid default interleave() below. Add avd. rule to setDictLST duplicates.
        fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST, citem, fileList, inherited=self)
        self.log('buildChannel, id: %s, fileList items = %s'%(citem['id'],len(fileList)),xbmc.LOGINFO)
        return fileList

          
    def buildFileList(self, citem: dict, path: str, media: str='video', limit: int=SETTINGS.getSettingInt('Page_Limit'), sort: dict={}, limits: dict={}) -> list: #build channel via vfs path.
        self.log("buildFileList, id: %s, media = %s, path = %s\nlimit = %s, sort = %s limits = %s"%(citem['id'],media,path,limit,sort,limits))
        if path.endswith('.xsp'): #smartplaylist - parse xsp for path, filter and sort info
            paths, media, sort, filter, limit = self.xsp.parseXSP(path, media, sort, {}, limit)
            if len(paths) > 0: return interleave([self.buildFileList(citem, file, media, limit, sort, limits) for file in paths if not self.service._interrupt()])
            
        elif 'db://' in path and '?xsp=' in path: #dynamicplaylist - parse xsp for path, filter and sort info
            path, media, sort, filter = self.xsp.parseDXSP(path, sort, {}, self.incExtras) #todo filter adv. rules.
            
        fileList = []
        dirList  = [{'file':path}]
        self.loopback = {}
        self.log("buildFileList, id: %s, limit = %s, sort = %s, limits = %s\npath = %s"%(citem['id'],limit,sort,limits,path))
        
        while not self.service.monitor.abortRequested() and (len(fileList) < limit):
            #Not all results are flat hierarchies; walk all paths until fileList limit is reached. ie. Plugins with [NEXT PAGE]
            if self.service._interrupt() or self.service._suspend():
                self.completeBuild = False
                break
            elif len(dirList) == 0:
                self.log('buildFileList, id: %s, no more folders to parse'%(citem['id']))
                break
            elif len(dirList) > 0:
                dir = dirList.pop(0)
                subfileList, subdirList = self.buildList(citem, dir.get('file'), media, limit, sort, limits, dir)
                fileList += subfileList
                dirList = setDictLST(dirList + subdirList)
                self.log('buildFileList, id: %s, parsing %s, fileList = %s'%(citem['id'],dir.get('file'),len(fileList)))
               
        self.log("buildFileList, id: %s returning fileList %s / %s"%(citem['id'],len(fileList),limit))
        return fileList


    def buildList(self, citem: dict, path: str, media: str='video', page: int=SETTINGS.getSettingInt('Page_Limit'), sort: dict={}, limits: dict={}, dirItem: dict={}, query: dict={}) -> tuple:
        self.log("buildList, id: %s, media = %s, path = %s\npage = %s, sort = %s, query = %s, limits = %s\ndirItem = %s"%(citem['id'],media,path,page,sort,query,limits,dirItem))
        dirList, fileList, seasoneplist, trailersdict = [], [], [], {}
        items, nlimits, errors = self.jsonRPC.requestList(citem, path, media, page, sort, limits, query)
        if errors.get('message'):
            self.pErrors.append(errors['message'])
            return fileList, dirList
        elif items == self.loopback and limits != nlimits:# malformed jsonrpc queries will return root response, catch a re-parse and return.
            self.log("buildList, id: %s, loopback detected using path = %s\nreturning: fileList (%s), dirList (%s)"%(citem['id'],path,len(fileList),len(dirList)))
            self.pErrors.append(LANGUAGE(32030))
            return fileList, dirList
        elif not items and len(fileList) == 0:
            self.log("buildList, id: %s, no request items found using path = %s\nreturning: fileList (%s), dirList (%s)"%(citem['id'],path,len(fileList),len(dirList)))
            self.pErrors.append(LANGUAGE(32026))
            return fileList, dirList
        elif items:
            self.loopback = items
            for idx, item in enumerate(items):
                if self.service._interrupt() or self.service._suspend():
                    self.pErrors = [LANGUAGE(32160)]
                    self.completeBuild = False
                    self.jsonRPC.autoPagination(citem['id'], '|'.join([path,dumpJSON(query)]), limits) #rollback pagination limits
                    return [], []
                else:
                    file         = item.get('file','')
                    fileType     = item.get('filetype','file')
                    if not item.get('type'): item['type'] = query.get('key','')

                    if fileType == 'directory':
                        dirList.append(item)
                        self.log("buildList, id: %s, IDX = %s, appending directory: %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        
                    elif fileType == 'file':
                        if not file:
                            self.pErrors.append(LANGUAGE(32031))
                            self.log("buildList, id: %s, IDX = %s, skipping missing playable file! path = %s"%(citem['id'],idx,path),xbmc.LOGINFO)
                            continue
                            
                        elif (file.lower().endswith('strm') and not self.incStrms): 
                            self.pErrors.append('%s STRM'%(LANGUAGE(32027)))
                            self.log("buildList, id: %s, IDX = %s, skipping strm file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                            continue
                            
                        if not item.get('streamdetails',{}).get('video',[]) and not file.startswith(tuple(VFS_TYPES)): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                            item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

                        if (self.is3D(item) and not self.inc3D): 
                            self.pErrors.append('%s 3D'%(LANGUAGE(32027)))
                            self.log("buildList, id: %s, IDX = %s skipping 3D file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                            continue

                        dur = self.jsonRPC.getDuration(file, item, self.accurateDuration, self.saveDuration)
                        if dur > self.minDuration: #include media that's duration is above the players seek tolerance & users adv. rule.
                            item['duration']     = dur
                            item['media']        = media
                            item['originalpath'] = path #use for path sorting/playback verification 
                            if item.get("year",0) == 1601: item['year'] = 0 #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554
                            if self.pDialog:
                                self.pDialog = DIALOG.progressBGDialog(self.pCount, self.pDialog, message='%s: %s'%(self.pName,int(idx*100)//page)+'%',header='%s, %s'%(ADDON_NAME,self.pMSG))

                            title   = (item.get("title",'')     or item.get("label",'') or dirItem.get('label',''))
                            tvtitle = (item.get("showtitle",'') or item.get("label",'') or dirItem.get('label',''))

                            if (item['type'].startswith(tuple(TV_TYPES)) or item.get("showtitle")):# This is a TV show
                                season  = int(item.get("season","0"))
                                episode = int(item.get("episode","0"))
                                if not file.startswith(tuple(VFS_TYPES)) and not self.incExtras and (season == 0 or episode == 0):
                                    self.pErrors.append('%s Extras'%(LANGUAGE(32027)))
                                    self.log("buildList, id: %s, IDX = %s skipping extras! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                                    continue

                                label = tvtitle
                                item["tvshowtitle"]  = tvtitle
                                item["episodetitle"] = title
                                item["episodelabel"] = '%s (%sx%s)'%(title,season,str(episode).zfill(2)) #Episode Title (SSxEE) Mimic Kodi's PVR label format
                                item["showlabel"]    = '%s %s'%(item["tvshowtitle"], '- %s'%(item['episodelabel']) if item['episodelabel'] else '')
                            else: # This is a Movie
                                label = title
                                item["episodetitle"] = item.get("tagline","")
                                item["episodelabel"] = item.get("tagline","")
                                item["showlabel"]    = '%s %s'%(item["title"], '- %s'%(item['episodelabel']) if item['episodelabel'] else '')
                        
                            if not label: continue
                            spTitle, spYear = splitYear(label)
                            item['label'] = spTitle
                            if item.get('year',0) == 0 and spYear: #replace missing item year with one parsed from show title
                                item['year'] = spYear
                                
                            item['plot'] = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(30161)).strip()
                            if query.get('holiday'):
                                citem['holiday'] = query.get('holiday')
                                holiday = "[B]%s[/B] - [I]%s[/I]"%(query["holiday"]["name"],query["holiday"]["tagline"]) if query["holiday"]["tagline"] else "[B]%s[/B]"%(query["holiday"]["name"])
                                item["plot"] = "%s \n%s"%(holiday,item["plot"])

                            item['art']  = (item.get('art',{}) or dirItem.get('art',{}))
                            item.get('art',{})['icon'] = citem['logo']
                            
                            if item.get('trailer') and self.bctTypes['trailers'].get('enabled',False) and self.bctTypes['trailers'].get('incKODI',False):
                                titem = item.copy()
                                tdur  = self.jsonRPC.getDuration(titem.get('trailer'), accurate=True, save=False)
                                if tdur > 0:
                                    titem.update({'duration':tdur, 'runtime':tdur, 'file':titem['trailer'], 'streamdetails':{}})
                                    [trailersdict.setdefault(genre.lower(),[]).append(titem) for genre in (titem.get('genre',[]) or ['resources'])]
                            
                            if sort.get("method","") == 'episode' and (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                                seasoneplist.append([int(item.get("season","0")), int(item.get("episode","0")), item])
                            else: 
                                fileList.append(item)
                        else: 
                            self.pErrors.append(LANGUAGE(32032))
                            self.log("buildList, id: %s, IDX = %s skipping content no duration meta found! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)

            if sort.get("method","") == 'episode':
                self.log("buildList, id: %s, sorting by episode"%(citem['id']))
                seasoneplist.sort(key=lambda seep: seep[1])
                seasoneplist.sort(key=lambda seep: seep[0])
                for seepitem in seasoneplist: 
                    fileList.append(seepitem[2])
                    
            elif sort.get("method","") == 'random':
                self.log("buildList, id: %s, random shuffling"%(citem['id']))
                if len(dirList)  > 0: dirList  = randomShuffle(dirList)
                if len(fileList) > 0: fileList = randomShuffle(fileList)
                
            if len(trailersdict) > 0: self.kodiTrailers(trailersdict)
            self.log("buildList, id: %s returning (%s) files, (%s) dirs."%(citem['id'],len(fileList),len(dirList)))
            return fileList, dirList

 
    def isHD(self, item: dict) -> bool:
        if 'isHD' in item: return item['isHD']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth >= 1280 or videoheight >= 720: return True
        return False


    def isUHD(self, item: dict) -> bool:
        if 'isUHD' in item: return item['isUHD']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth > 1920 or videoheight > 1080: return True
        return False
        
        
    def is3D(self, item: dict) -> bool:
        if 'is3D' in item: return item['is3D']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and details.get('video') != [] and len(details.get('video')) > 0:
            stereomode = (details['video'][0]['stereomode'] or [])
            if len(stereomode) > 0: return True
        return False


    def addChannelStation(self, citem: dict) -> bool:
        self.log('addChannelStation, id: %s'%(citem['id']))
        citem['logo']  = self.kodiImage(citem['logo'])
        citem['group'] = cleanGroups(citem, self.enableGrouping)
        sitem = self.m3u.getStationItem(citem)
        self.m3u.addStation(sitem)
        return self.xmltv.addChannel(sitem)
        
        
    def addChannelProgrammes(self, citem: dict, fileList: list):
        self.log('addChannelProgrammes, id: %s, fileList = %s'%(citem['id'],len(fileList)))
        for idx, item in enumerate(fileList):
            self.xmltv.addProgram(citem['id'], self.xmltv.getProgramItem(citem, item))
        return True
        
        
    def delChannelStation(self, citem: dict) -> bool:
        self.log('delChannelStation, id: %s'%(citem['id']))
        return self.m3u.delStation(citem) & self.xmltv.delBroadcast(citem)
        
        
    def saveChannelLineups(self) -> bool:
        self.log('saveChannelLineups')
        return self.xmltv._save() & self.m3u._save()


    def kodiTrailers(self, nitems: dict={}) -> dict:
        items = (self.cache.get('kodiTrailers', json_data=True) or {})
        if nitems: items = self.cache.set('kodiTrailers', mergeDictLST(items,nitems), expiration=datetime.timedelta(days=28), json_data=True)
        return items


    def kodiImage(self, image):
        return self.resources.buildWebImage(cleanImage(image))