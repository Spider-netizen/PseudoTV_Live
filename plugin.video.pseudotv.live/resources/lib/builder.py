#   Copyright (C) 2021 Lunatixz
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

class Builder:
    def __init__(self, writer=None):
        self.log('__init__')
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        self.writer           = writer
        
        #globals
        self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
        self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
        self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
        self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
        self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
        
        self.ruleList         = {}
        self.filter           = {}
        self.sort             = {}
        self.limits           = {}
        self.loopback         = {}
        self.limit            = PAGE_LIMIT
        self.progDialog       = None
        self.progress         = 0
        self.channelCount     = 0
        self.dirCount         = 0
        self.chanName         = ''
        self.chanError        = []
        self.diaMSG           = LANGUAGE(30051)
        
        self.bctTypes         = {"ratings"    :{"min":SETTINGS.getSettingInt('Fillers_Ratings')    ,"max":1,"enabled":SETTINGS.getSettingInt('Fillers_Ratings') > 0    ,"paths":(SETTINGS.getSetting('Resource_Ratings')).split(',')},
                                 "bumpers"    :{"min":SETTINGS.getSettingInt('Fillers_Bumpers')    ,"max":1,"enabled":SETTINGS.getSettingInt('Fillers_Bumpers') > 0    ,"paths":(SETTINGS.getSetting('Resource_Bumpers')).split(',')},
                                 "commercials":{"min":SETTINGS.getSettingInt('Fillers_Commercials'),"max":4,"enabled":SETTINGS.getSettingInt('Fillers_Commercials') > 0,"paths":(SETTINGS.getSetting('Resource_Commericals')).split(',')},
                                 "trailers"   :{"min":SETTINGS.getSettingInt('Fillers_Trailers')   ,"max":4,"enabled":SETTINGS.getSettingInt('Fillers_Trailers') > 0   ,"paths":(SETTINGS.getSetting('Resource_Trailers')).split(',')}}#todo check adv. rules get settings

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): return parameter
        ruleList = self.ruleList.get(citem['id'],[])
        for rule in ruleList:
            if action in rule.actions:
                self.log("runActions performing channel rule: %s"%(rule.name))
                return rule.runAction(action, self, parameter)
        return parameter
        

    def verifyChannelItems(self):
        #check channel configuration, verify and update paths, logos.
        items = self.writer.channels.getChannels()
        for idx, item in enumerate(items):
            if self.writer.monitor.waitForAbort(0.001) or isDialog(): 
                break
                
            self.log('verifyChannelItems, %s: %s'%(idx,item))
            if (not item.get('name','') or not item.get('path',None) or item.get('number',0) < 1): 
                self.log('verifyChannelItems; skipping, missing channel path and/or channel name\n%s'%(item))
                continue

            if item['number'] >= CHANNEL_LIMIT: #update dynamic pre-defined channels
                item['logo'] = (self.writer.jsonRPC.resources.getLogo(item['name'],item['type'],item['path'],item, featured=True, lookup=True) or item.get('logo',LOGO)) #all logos are dynamic re-parse for changes.
                # item['path'] = self.writer.library.predefined.pathTypes[item['type']](item['name'])
            
            if not isinstance(item.get('path',[]),list): 
                item['path'] = [item['path']]
                
            item['id']      = (item.get('id','')             or getChannelID(item['name'], item['path'], item['number'])) # internal use only; create unique PseudoTV ID.
            item['radio']   = (item.get('radio','')          or (item['type'] == LANGUAGE(30097) or 'musicdb://' in item['path']))
            item['catchup'] = (item.get('catchup','')        or ('vod' if not item['radio'] else ''))
            item['group']   = list(set((item.get('group',[]) or [])))
            yield self.runActions(RULES_ACTION_CHANNEL_CREATION, item, item)


    def buildService(self):
        if isClient() or isDialog(): 
            self.log('buildService, Client mode enabled/Settings Opened; returning!')
            return False
                       
        channels = sorted(self.verifyChannelItems(), key=lambda k: k['number'])
        self.log('buildService, channels = %s'%(len(channels)))
        if not channels:
            self.writer.dialog.notificationDialog(LANGUAGE(30056))
            return

        if not isLegacyPseudoTV(): # legacy setting to disable/enable support in third-party applications. 
            setLegacyPseudoTV(True)
            
        self.progress     = 0
        self.progDialog   = self.writer.dialog.progressBGDialog()
        self.channelCount = len(channels)
        self.ruleList     = self.writer.rules.loadRules(channels)
        start             = roundTimeDown(getLocalTime(),offset=60)#offset time to start top of the hour
        endTimes          = dict(self.writer.xmltv.loadEndTimes(fallback=datetime.datetime.fromtimestamp(start).strftime(DTFORMAT)))
        self.log('buildService, endTimes = %s'%(endTimes))

        for idx, channel in enumerate(channels):
            if self.writer.monitor.waitForAbort(0.001) or isDialog(): 
                self.progDialog = self.writer.dialog.progressBGDialog(100, self.progDialog, message=LANGUAGE(30204))
                self.log('buildService, interrupted')
                return
                
            channel         = self.runActions(RULES_ACTION_START, channel, channel)
            self.chanName   = channel['name']
            self.chanError  = []
            
            if endTimes.get(channel['id']):
                self.diaMSG = LANGUAGE(30051) #Updating
            else:
                self.diaMSG = LANGUAGE(30329) #Building
        
            self.progress   = int(idx*100//len(channels))
            self.progDialog = self.writer.dialog.progressBGDialog(self.progress, self.progDialog, message='%s'%(self.chanName),header='%s, %s'%(ADDON_NAME,self.diaMSG))

            cacheResponse   = self.getFileList(channel, endTimes.get(channel['id'], start) , channel['radio'])#cacheResponse = {True:'Valid Channel (exceed MAX_DAYS)',False:'In-Valid Channel (No guidedata)',list:'fileList (guidedata)'}
            cacheResponse   = self.runActions(RULES_ACTION_STOP, channel, cacheResponse)
             
            if cacheResponse:
                self.writer.addChannelLineup(channel, radio=channel['radio'], catchup=not bool(channel['radio'])) #create m3u/xmltv station entry.
                if isinstance(cacheResponse,list) and len(cacheResponse) > 0: #write new lineup meta to xmltv
                    self.writer.addProgrammes(channel, cacheResponse, radio=channel['radio'], catchup=not bool(channel['radio']))
            else: 
                self.log('buildService, In-Valid Channel (No guidedata) %s '%(channel['id']))
                self.progDialog = self.writer.dialog.progressBGDialog(self.progress, self.progDialog, message='%s, %s'%(self.chanName,' | '.join(list(set(self.chanError)))),header='%s, %s'%(ADDON_NAME,LANGUAGE(30330)))
                self.writer.removeChannelLineup(channel)
                self.writer.monitor.waitForAbort(PROMPT_DELAY/1000)

        if not self.writer.saveChannelLineup(): 
            self.writer.dialog.notificationDialog(LANGUAGE(30001))
                     
        self.progDialog = self.writer.dialog.progressBGDialog(100, self.progDialog, message=LANGUAGE(30053))
           
        if isLegacyPseudoTV() and not self.writer.player.isPlaying():
            setLegacyPseudoTV(False)
            
        self.log('buildService, finished')
        return True


    def addScheduling(self, channel, fileList, start):
        self.log("addScheduling; channel = %s, fileList = %s, start = %s"%(channel,len(fileList),start))
        #todo insert adv. scheduling rules here or move to adv. rules.py
        tmpList  = []
        fileList = self.runActions(RULES_ACTION_CHANNEL_PRE_TIME, channel, fileList)
        for idx, item in enumerate(fileList):
            if not item.get('file',''):
                self.log("addScheduling, id: %s, IDX = %s skipping missing playable file!"%(channel['id'],idx),xbmc.LOGINFO)
                continue
                
            item["idx"]   = idx
            item['start'] = start
            item['stop']  = start + item['duration']
            start = item['stop']
            tmpList.append(item)
        return self.runActions(RULES_ACTION_CHANNEL_POST_TIME, channel, tmpList)
            

    def getFileList(self, citem, start, radio=False):
        self.log('getFileList, citem = %s, radio = %s'%(citem,radio))
        try:
            # global values prior to channel rules
            self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
            self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
            self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
            self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
            self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
            
            self.filter   = {}#{"and": [{"operator": "contains", "field": "title", "value": "Star Wars"},{"operator": "contains", "field": "tag", "value": "Good"}]}
            self.sort     = {}#{"order":"ascending","ignorefolders":"false","method":"random"}
            self.limits   = {}#{"end":0,"start":0,"total":0}
            self.limit    = PAGE_LIMIT
            
            valid         = False
            self.dirCount = 0
            self.loopback = {}
            self.runActions(RULES_ACTION_CHANNEL_START, citem)
            
            if start > (getLocalTime() + (SETTINGS.getSettingInt('Max_Days') * 86400)): #max guidedata days to seconds.
                self.log('getFileList, id: %s programmes exceed MAX_DAYS: endtime = %s'%(citem['id'],datetime.datetime.fromtimestamp(start)),xbmc.LOGINFO)
                return True# prevent over-building
                
            citem = self.runActions(RULES_ACTION_CHANNEL_JSON, citem, citem)
            if isinstance(citem['path'], list): 
                path = citem['path']
            else: 
                path = [citem['path']]
                
            mixed  = len(path) > 1
            media  = 'music' if radio else 'video'
            self.log('getFileList, id: %s, mixed = %s, media = %s'%(citem['id'],mixed,media),xbmc.LOGINFO)
            
            if radio:
                cacheResponse = self.buildRadio(citem) #build radio as on-the-fly playlist que.
            else:         
                cacheResponse = [(self.buildFileList(citem, file, media, self.limit, self.sort, self.filter, self.limits)) for file in path] # build multi-paths as induvial arrays for easier interleaving.
                valid = list(filter(lambda k:k, cacheResponse)) #check that at least one filelist array contains meta.
                if not valid:
                    self.log("getFileList, id: %s skipping channel cacheResponse empty!"%(citem['id']),xbmc.LOGINFO)
                    return False
                
                cacheResponse = self.runActions(RULES_ACTION_CHANNEL_LIST, citem, cacheResponse)
                cacheResponse = list(interleave(*cacheResponse))# interleave multi-paths, while keeping filelist order.
                cacheResponse = list(filter(lambda filelist:filelist != {}, filter(None,cacheResponse))) # filter None/empty filelist elements (probably unnecessary, if empty element is adding during interleave or injection rules remove).
                self.log('getFileList, id: %s, cacheResponse = %s'%(citem['id'],len(cacheResponse)),xbmc.LOGINFO)
                
                if len(cacheResponse) < self.limit:
                    cacheResponse = self.fillCells(cacheResponse)
                    if self.sort.get("method","") == 'random' and len(cacheResponse) > 0:
                        random.shuffle(cacheResponse)
                    
            cacheResponse = self.addScheduling(citem, cacheResponse, start)
            self.fillBCTs = False #temp debug force disabled
            if self.fillBCTs and not citem.get('radio',False): 
                cacheResponse = self.injectBCTs(citem, cacheResponse) 
                
            self.runActions(RULES_ACTION_CHANNEL_STOP, citem)
            return sorted(cacheResponse, key=lambda k: k['start'])
        except Exception as e: self.log("getFileList, Failed! " + str(e), xbmc.LOGERROR)
        return False
            
    
    def buildRadio(self, channel):
        self.log("buildRadio; channel = %s"%(channel))
        #todo insert custom radio labels,plots based on genre type?
        channel['genre'] = [channel['name']]
        channel['art']   = {'thumb':channel['logo'],'icon':channel['logo'],'fanart':channel['logo']}
        channel['plot']  = LANGUAGE(30098)%(channel['name'])
        return self.buildFile(channel,type='music')
                
                
    def buildFile(self, channel, duration=EPG_HRS, type='video', entries=3):
        self.log("buildFile; channel = %s"%(channel))
        tmpItem  = {'label'       : (channel.get('label','') or channel['name']),
                    'episodetitle': channel.get('episodetitle',''),
                    'plot'        : (channel.get('plot' ,'') or LANGUAGE(30161)),
                    'genre'       : channel.get('genre',['Undefined']),
                    'type'        : type,
                    'duration'    : duration,
                    'file'        : channel['path'],
                    'start'       : 0,
                    'stop'        : 0,
                    'art'         : channel.get('art',{"thumb":COLOR_LOGO,"fanart":FANART,"logo":LOGO})}
        return [tmpItem.copy() for idx in range(entries)]
        
        
    def fillCells(self, fileList):
         # balance media limits, by filling randomly with duplicates to meet EPG_HRS
        self.log("fillCells; fileList = %s"%(len(fileList)))
        totRuntime = sum([item.get('duration') for item in fileList])
        iters = cycle(fileList)
        while not self.writer.monitor.abortRequested() and totRuntime < EPG_HRS:
            item = next(iters).copy()
            totRuntime += item.get('duration')
            fileList.append(item)
        return fileList


    def buildFileList(self, channel, path, media='video', limit=PAGE_LIMIT, sort={}, filter={}, limits={}):
        self.log("buildFileList, id: %s, path = %s, limit = %s, sort = %s, filter = %s, limits = %s"%(channel['id'],path,limit,sort,filter,limits))
        if path.startswith(LANGUAGE(30174)):#seasonal
            def getSeason():
                try:    return {'September':'startrek',
                                'October'  :'horror',
                                'December' :'xmas',
                                'May'      :'starwars'}[datetime.datetime.now().strftime('%B')]
                except: return  'none'
            path = path.format(list=getSeason(),limit=250)
            
        # sort = self.runActions('', channel) #todo set secondary sort rules via adv. rules. ex. Mixed Path - TV (sort=episode) & Movies (sort=random)
        if not sort: #set fallback method 
            if   path.startswith('videodb://tvshows'): sort = {"method": "episode"}
            elif path.startswith('videodb://movies'):  sort = {"method": "random"}
            else:                                      sort = {"method": "random"}
                      
        id = channel['id']
        fileList      = []
        seasoneplist  = []
        method        = sort.get("method","random")

        json_response = self.writer.jsonRPC.requestList(id, path, media, limit, sort, filter, limits)
        # malformed vfs jsonrpc will return root response, catch a reparse of same folder and quit. 
        if json_response == self.loopback:
            self.chanError.append(LANGUAGE(30318))
            self.log("buildFileList, loopback detected returning")
            return fileList
        elif json_response:
            self.loopback = json_response
        else:
            self.chanError.append(LANGUAGE(30317))
            
        for idx, item in enumerate(json_response):
            if self.writer.monitor.waitForAbort(0.001) or isDialog():
                break
                
            file     = item.get('file','')
            fileType = item.get('filetype','file')

            if fileType == 'file':
                if not file:
                    self.chanError.append(LANGUAGE(30316))
                    self.log("buildFileList, id: %s, IDX = %s skipping missing playable file!"%(id,idx),xbmc.LOGINFO)
                    continue
                elif (file.lower().endswith('strm') and not self.incStrms): 
                    self.chanError.append('%s STRM'%(LANGUAGE(30315)))
                    self.log("buildFileList, id: %s, IDX = %s skipping strm!"%(id,idx),xbmc.LOGINFO)
                    continue
                elif (is3D(item) and not self.inc3D): 
                    self.chanError.append('%s 3D'%(LANGUAGE(30315)))
                    self.log("buildFileList, id: %s, IDX = %s skipping 3D!"%(id,idx),xbmc.LOGINFO)
                    continue

               
                if not item.get('streamdetails',{}).get('video',[]): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                    item['streamdetails'] = self.writer.jsonRPC.getStreamDetails(file, media)

                dur = self.writer.jsonRPC.getDuration(file, item, self.accurateDuration)
                if dur > 0:
                    item['duration'] = dur
                    if int(item.get("year","0")) == 1601: #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554.
                        item['year'] = 0
                        
                    mType   = item['type']
                    label   = item['label']
                    title   = (item.get("title",'') or label)
                    tvtitle = (item.get("showtitle","") or item.get("tvshowtitle",""))

                    if tvtitle or mType in ['tvshow','episode']:
                        # This is a TV show
                        seasonval = int(item.get("season","0"))
                        epval     = int(item.get("episode","0"))
                        if not file.startswith(('plugin://','upnp://','pvr://')) and not self.incExtras and (seasonval == 0 or epval == 0) and item.get("episode",None) is not None: 
                            self.log("buildFileList, id: %s skipping extras!"%(id),xbmc.LOGINFO)
                            continue

                        label = tvtitle
                        item["tvshowtitle"]  = tvtitle
                        item["episodetitle"] = title
                        item["episodelabel"] = '%s (%sx%s)'%(title,seasonval,str(epval).zfill(2))
                        
                    else: # This is a Movie
                        label = title
                        item["episodetitle"] = item.get("tagline","")
                        item["episodelabel"] = item.get("tagline","")
                        seasonval = None
            
                    if not label: continue
                    item['label'] = splitYear(label)[0]
                    item['plot']  = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(30161))
                    item.get('art',{})['icon']  = channel['logo']
                
                    if self.progDialog is not None:
                        chprog = int((len(fileList)*100)//limit)
                        self.progDialog = self.writer.dialog.progressBGDialog(self.progress, self.progDialog, message='%s: %s'%(self.chanName,chprog)+'%',header='%s, %s'%(ADDON_NAME,self.diaMSG))

                    if method == 'episode' and seasonval is not None: 
                        seasoneplist.append([seasonval, epval, item])
                    else: fileList.append(item)
                        
                    if len(fileList) >= limit:
                        break
                        
                else: 
                    self.chanError.append(LANGUAGE(30314))
                    self.log("buildFileList, id: %s skipping no duration meta found!"%(id),xbmc.LOGINFO)
                    
            elif fileType == 'directory' and (len(fileList) < limit) and (self.dirCount < roundupDIV(limit,2)): #extend fileList by parsing child folders, limit folder parsing to half limit to avoid runaways/loopbacks.
                self.dirCount += 1
                fileList.extend(self.buildFileList(channel, file, media, limit, sort, filter, limits))

        self.log("buildFileList, id: %s sorting by %s"%(id,method))
        if method == 'episode':
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist: 
                fileList.append(seepitem[2])
        elif method == 'random' and len(fileList) > 0:
            random.shuffle(fileList)
                
        self.log("buildFileList, id: %s returning fileList %s / %s"%(id,len(fileList),limit),xbmc.LOGINFO)
        return fileList


    def buildLocalTrailers(self, citem, fileList):
        self.log("buildLocalTrailers, citem = %s, fileList = %s"%(citem,len(fileList)))
        def getItem(item):
            file = item.get('trailer','')
            if file: return {'label':item['label'],'duration':self.writer.jsonRPC.parseDuration(file, item),'path':'','file':file}
        return list(filter(None,list(set([getItem(fileItem) for fileItem in fileList]))))
    
    
    def injectBCTs(self, citem, fileList):
        self.log("injectBCTs, citem = %s, fileList = %s"%(citem,len(fileList)))
        # todo use zip to inject bcts?
        # for r, b, f, c, t in zip(ratings, bumpers, filelist, commercials, trailers):
        
        #bctTypes ex. {"ratings" :{"min":1,"max":1,"enabled":True  ,"paths":[SETTINGS.getSetting('Resource_Ratings')]}}
        if not fileList: return fileList
        lstop            = 0
        nfileList        = list()
        bctItems         = {key:(self.writer.jsonRPC.resources.buildResourceType(key, self.bctTypes.get(key,{}).get("paths",[]))) for key in self.bctTypes.keys() if self.bctTypes.get(key,{}).get('enabled',False)}
        print('bctItems',bctItems)
        
        chname           = citem.get('name','')
        chcats           = citem.get('groups',[])
        print('chname',chname,'chcats',chcats)
        
        if 'ratings' in bctItems:
            ratings = bctItems.get('ratings',{})
            print('ratings',ratings)
        else: ratings = {}
        
        if 'bumpers' in bctItems:
            bumpers = bctItems.get('bumpers',{}).get(chname.lower(),[])
            # bumpers = bctItems.get('bumpers',{})
            # if isinstance(bumpers,list): bumpers = bumpers[0].get(chname.lower(),[])
            bumpers.extend(bctItems.get('bumpers',{}).get('root',[]))
            print('bumpers',bumpers)
        else: bumpers = []
        
        min_commercials  = self.bctTypes.get('commercials',{}).get('min',0) #0==Disabled,1==Auto
        max_commercials  = self.bctTypes.get('commercials',{}).get('max',4)
        auto_commercials = min_commercials == 1
        if 'commercials' in bctItems:
            commercials = bctItems.get('commercials',{}).get(chname.lower(),[])
            commercials.extend(bctItems.get('commercials',{}).get('root',[]))
            if isinstance(commercials,list) and len(commercials) > 0: random.shuffle(commercials)
            print('commercials',commercials)
        else: 
            commercials = []
            auto_commercials = False
                  
        min_trailers  = self.bctTypes.get('trailers',{}).get('min',0) #0==Disabled,1==Auto
        max_trailers  = self.bctTypes.get('trailers',{}).get('max',4)
        auto_trailers = min_trailers == 1
        if 'trailers' in bctItems:  
            trailers = []   
            for chcat in chcats: trailers.extend(bctItems.get('trailers',{}).get(chcat.lower(),[]))
            trailers.extend(bctItems.get('trailers',{}).get('root',[]))
            trailers.extend(self.buildLocalTrailers(citem, fileList))
            if isinstance(trailers,list) and len(trailers) > 0: random.shuffle(trailers)
            print('trailers',trailers)
        else: 
            trailers = []
            auto_trailers = False
        
        for idx,fileItem in enumerate(fileList):
            file = fileItem.get('file','')
            fileItem['originalfile'] = file
            fileItem['start'] = fileItem['start'] if lstop == 0 else lstop
            fileItem['stop']  = fileItem['start'] + fileItem['duration']
            
            if not file.startswith(('pvr://','upnp://','plugin://')): #stacks not compatible
                if isStack(file): 
                    paths = splitStacks(file)
                else: 
                    paths = [file]
                    
                oPaths = paths.copy()
                stop   = fileItem['stop']
                end    = abs(roundTimeUp(stop) - stop) #auto mode
                
                print('duration',fileItem['duration'])
                print('start',datetime.datetime.fromtimestamp(fileItem['start']))
                print('stop',datetime.datetime.fromtimestamp(stop))
                print('end',end)
                
                #ratings (auto&max == 1)
                mpaa = cleanMPAA(fileItem.get('mpaa',''))
                if is3D(fileItem): mpaa += ' (3DSBS)'  
                rating = ratings.get(mpaa.lower(), {})
                if rating:
                    paths.insert(0,rating.get('file'))
                    end -= rating.get('duration')
                    print('end ratings', end)
                    print('mpaa',mpaa)  
                    print('rating',rating) 
                    
                #bumpers(auto&max == 1)
                if bumpers:
                    bumper = random.choice(bumpers)
                    paths.insert(0,bumper.get('file'))
                    end -= bumper.get('duration')
                    print('end bumper', end)
                    print('chname',chname)
                    print('bumper',bumper)
                    
                CTItems = set()
                cnt_commercials = 0
                cnt_trailers    = 0
                #commercials
                if commercials and not auto_commercials:
                    for cnt in range(min_commercials):
                        commercial = random.choice(commercials)
                        CTItems.add(commercial.get('file'))
                        end -= commercial.get('duration')
                        print('end commercial', end)
                        print('commercial',commercial)
                            
                #trailers
                if trailers and not auto_trailers:
                    for cnt in range(min_trailers):
                        trailer = random.choice(trailers)
                        CTItems.add(trailer.get('file'))
                        end -= trailer.get('duration')
                        print('end trailer', end)
                        print('trailer',trailer)
                        
                #auto fill POST_ROLL
                if auto_commercials | auto_trailers:
                    while end > 0 and not self.writer.monitor.abortRequested():
                        if self.writer.monitor.waitForAbort(0.001): break
                        print('autofill while loop',end)
                        stpos = end
                        if commercials and auto_commercials and cnt_commercials <= max_commercials:
                            commercial = random.choice(commercials)
                            CTItems.add(commercial.get('file'))
                            end -= commercial.get('duration')
                            print('end commercial', end)
                            print('commercial',commercial)
                        
                        if trailers and auto_trailers and cnt_trailers <= max_trailers:
                            trailer = random.choice(trailers)
                            CTItems.add(trailer.get('file'))
                            end -= trailer.get('duration')
                            print('end trailer', end)
                            print('trailer',trailer)
                            
                        if stpos == end: break #empty list
                        
                CTItems = list(CTItems)
                print('CTItems',CTItems)
                if len(CTItems) > 0:
                    random.shuffle(CTItems)#shuffle, then random sample for increased diversity. 
                    paths.extend(random.sample(CTItems, len(CTItems)))
                    
                #todo trailers, commercials when "Auto" loop fill till end time close to 0. else fill random min,max count.
                #trailers, commercials do not match by chname, random.choice from list, for variation users change resource folder in adv. rules.
                #trailers always incorporate local_trailers from the media in current fileList playlist.
                
                print('oPaths',oPaths)
                print('paths',paths)
                    
                if oPaths != paths:
                    fileItem['file'] = buildStack(paths)
                    fileItem['stop'] = abs(roundTimeUp(stop) - abs(end))
                    fileItem['duration'] = (datetime.datetime.fromtimestamp(fileItem['stop']) - datetime.datetime.fromtimestamp(fileItem['start'])).seconds
                    print('end',end,'lstop',datetime.datetime.fromtimestamp(fileItem['stop']),'dur',fileItem['duration'])
                    print('fileItem',fileItem)

            lstop = fileItem['stop']  #new stop time, offset next start time.
            nfileList.append(fileItem)
        return nfileList