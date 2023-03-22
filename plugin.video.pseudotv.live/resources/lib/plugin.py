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
from globals     import *
from jsonrpc     import JSONRPC
from rules       import RulesList
from infotagger.listitem import ListItemInfoTag

PAGE_LIMIT = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))
SEEK_TOLER = SETTINGS.getSettingInt('Seek_Tolerance')
SEEK_THRED = SETTINGS.getSettingInt('Seek_Threshold')

class Plugin:
    def __init__(self, sysARG=sys.argv):
        self.cache   = Cache(mem_cache=True)
        self.jsonRPC    = JSONRPC()
        self.rules      = RulesList()
        self.runActions = self.rules.runActions

        self.sysARG     = sysARG
        self.sysInfo    = {'name'   : BUILTIN.getInfoLabel('ChannelName'),
                           'number' : BUILTIN.getInfoLabel('ChannelNumberLabel'),
                           'path'   : BUILTIN.getInfoLabel('FileNameAndPath'),
                           'fitem'  : decodeWriter(BUILTIN.getInfoLabel('Writer')),
                           'citem'  : decodeWriter(BUILTIN.getInfoLabel('Writer')).get('citem',{})}
        
        self.log('__init__, sysARG = %s\nsysInfo = %s'%(sysARG,self.sysInfo))
        self.channelPlaylist  = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.channelPlaylist.clear()
        xbmc.sleep(100)

                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def buildWriterItem(self, item, media='video'):
        return LISTITEMS.buildItemListItem(decodeWriter(item.get('writer','')), media)


    def getCallback(self, chname, id, radio=False):
        self.log('getCallback, id = %s, radio = %s'%(id,radio))
        def _match():
            dir = quoteString('radio/%s (Radio)'%(ADDON_NAME) if radio else 'tv/%s'%(ADDON_NAME))
            results = self.jsonRPC.getDirectory(param={"directory":"pvr://channels/{dir}/".format(dir=dir)}, cache=False).get('files',[])
            for result in results:
                if result.get('label','').lower() == chname.lower() and result.get('uniqueid','') == id:
                    self.log('getCallback, found = %s'%(result.get('file')))
                    return result.get('file')

        cacheName = 'getCallback.%s.%s'%(getMD5(chname),id)
        cacheResponse = self.cache.get(cacheName, checksum=getInstanceID())
        if not cacheResponse:
            callback = _match()
            if callback is None: return forceBrute()
            cacheResponse = self.cache.set(cacheName, callback, checksum=getInstanceID(), expiration=datetime.timedelta(minutes=OVERLAY_DELAY))
        return cacheResponse
        
        
    def matchChannel(self, chname, id, radio=False):
        self.log('matchChannel, id = %s, radio = %s'%(id,radio))
        def _match():
            channels = self.jsonRPC.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label').lower() == chname.lower():
                    for key in ['broadcastnow', 'broadcastnext']:
                        chid = decodeWriter(channel.get(key,{}).get('writer','')).get('citem',{}).get('id')
                        if chid == id:
                            channel['broadcastnext'] = [channel.get('broadcastnext',{})]
                            self.log('matchChannel, found = %s'%(channel))
                            return channel
        
        cacheName = 'matchChannel.%s.%s'%(chname,id)
        cacheResponse = self.cache.get(cacheName, checksum=getInstanceID(), json_data=True)
        if not cacheResponse:
            pvritem = _match()
            if pvritem is None: return forceBrute()
            cacheResponse = self.cache.set(cacheName, pvritem, checksum=getInstanceID(), expiration=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
        return cacheResponse


    @cacheit(expiration=datetime.timedelta(seconds=OVERLAY_DELAY),checksum=getInstanceID(),json_data=True) #channel surfing short term cache.
    def extendProgrammes(self, pvritem, limit=PAGE_LIMIT):
        channelItem = {}
        def _parseBroadcast(broadcast):
            if broadcast['progresspercentage'] > 0 and broadcast['progresspercentage'] != 100:
                channelItem['broadcastnow'] = broadcast
            elif broadcast['progresspercentage'] == 0 and len(channelItem.get('broadcastnext',[])) < limit:
                channelItem.setdefault('broadcastnext',[]).append(broadcast)
        poolit(_parseBroadcast)(self.jsonRPC.getPVRBroadcasts(pvritem.get('channelid')))
        pvritem['broadcastnext'] = channelItem.get('broadcastnext',pvritem['broadcastnext'])
        return pvritem


    def playVOD(self, name, id):
        path = decodeString(id)
        self.log('playVOD, id = %s\npath = %s'%(id,path))
        liz = xbmcgui.ListItem(name,path=path)
        liz.setProperty("IsPlayable","true")
        self.resolveURL(True, liz)


    def playChannel(self, name, id, isPlaylist=False):
        self.log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.
        
        pvritem = self.matchChannel(name,id)
        if pvritem is None: return self.playError()
        
        pvritem['isPlaylist'] = isPlaylist
        pvritem['callback']   = self.getCallback(pvritem.get('channel'),pvritem.get('uniqueid'))
        
        try:    pvritem['epgurl']  = 'pvr://guide/%s/{starttime}.epg'%(re.compile('pvr://guide/(.*)/', re.IGNORECASE).search(self.sysInfo.get('path')).group(1)) #"pvr://guide/1197/2022-02-14 18:22:24.epg"
        except: pvritem['epgurl']  = ''
            
        pvritem['citem']       = (self.sysInfo.get('citem') or decodeWriter(pvritem.get('broadcastnow',{}).get('writer','')).get('citem',{}))
        pvritem['playcount']   = SETTINGS.getCacheSetting('playingPVRITEM', checksum=pvritem.get('id','-1'), json_data=True, default={}).get('playcount',0)
        if isPlaylist: pvritem = self.extendProgrammes(pvritem)

        nowitem   = pvritem.get('broadcastnow',{})  # current item
        nextitems = pvritem.get('broadcastnext',[]) # upcoming items
        del nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.

        if nowitem:
            found = True
            if nowitem.get('broadcastid',random.random()):# != SETTINGS.getCacheSetting('PLAYCHANNEL_LAST_BROADCAST_ID',checksum=id):# and not nowitem.get('isStack',False): #new item to play
                nowitem = self.runActions(RULES_ACTION_PLAYBACK, pvritem['citem'], nowitem, inherited=self)
                timeremaining = ((nowitem['runtime'] * 60) - nowitem['progress'])
                self.log('playChannel, runtime = %s, timeremaining = %s'%(nowitem['progress'],timeremaining))
                self.log('playChannel, progress = %s, Seek_Tolerance = %s'%(nowitem['progress'],SEEK_TOLER))
                self.log('playChannel, progresspercentage = %s, Seek_Threshold = %s'%(nowitem['progresspercentage'],SEEK_THRED))
                
                if round(nowitem['progress']) <= SEEK_TOLER: # near start or new content, play from the beginning.
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                    self.log('playChannel, progress start at the beginning')
                    
                elif round(nowitem['progresspercentage']) > SEEK_THRED: # near end, avoid callback; override nowitem and queue next show.
                    self.log('playChannel, progress near the end, queue nextitem')
                    nowitem = nextitems.pop(0) #remove first element in nextitems keep playlist order

            elif round(nowitem['progresspercentage']) > SEEK_THRED:
                self.log('playChannel, progress near the end playing nextitem')
                nowitem = nextitems.pop(0)
                
            elif pvritem['playcount'] > 2:
                found = False
                self.playError(pvritem)
                
            if found:
                writer = decodeWriter(nowitem.get('writer',{}))
                liz    = LISTITEMS.buildItemListItem(writer)
                path   = liz.getPath()
                self.log('playChannel, nowitem = %s\ncitem = %s\nwriter = %s'%(nowitem,pvritem['citem'],writer))
                
                if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                    self.log('playChannel, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                    liz.setProperty('startoffset', str(nowitem['progress'])) #secs
                    infoTag = ListItemInfoTag(liz, 'video')
                    infoTag.set_resume_point({'ResumeTime':nowitem['progress'],'TotalTime':(nowitem['runtime'] * 60)})

                pvritem['broadcastnow']  = nowitem   # current item
                pvritem['broadcastnext'] = nextitems # upcoming items
                liz.setProperty('pvritem',dumpJSON(pvritem))
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems))
                SETTINGS.setCacheSetting('playingPVRITEM', pvritem, checksum=pvritem.get('id','-1'), life=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
                
                if isPlaylist:
                    for idx,lz in enumerate(listitems):
                        self.channelPlaylist.add(lz.getPath(),lz,idx)
                    self.log('playChannel, Playlist size = %s'%(self.channelPlaylist.size()))
                    if isPlaylistRandom(): self.channelPlaylist.unshuffle()
                    PLAYER.play(self.channelPlaylist)
                    return

        else: self.playError(pvritem)
        self.resolveURL(found, listitems[0])


    def playRadio(self, name, id):
        self.log('playRadio, id = %s'%(id))
        found     = False
        listitems = [LISTITEMS.getListItem()] #empty listitem required to pass failed playback.
        
        pvritem = self.matchChannel(name,id,radio=True)
        if pvritem is None: return self.playError()
        
        pvritem['isPlaylist']  = True
        pvritem['callback']    = '%s%s'%(self.sysARG[0],self.sysARG[2])
        pvritem['citem']       = (self.sysInfo.get('citem') or decodeWriter(pvritem.get('broadcastnow',{}).get('writer','')).get('citem',{}))
        pvritem['playcount']   = SETTINGS.getCacheSetting('playingPVRITEM', checksum=pvritem.get('id','-1'), json_data=True, default={}).get('playcount',0)

        nowitem = pvritem.get('broadcastnow',{})  # current item
        if nowitem:
            found = True
            if nowitem.get('broadcastid',random.random()):# != SETTINGS.getCacheSetting('PLAYCHANNEL_LAST_BROADCAST_ID',checksum=id):# and not nowitem.get('isStack',False): #new item to play
                nowitem  = self.runActions(RULES_ACTION_PLAYBACK, pvritem['citem'], nowitem, inherited=self)
                fileList = [self.jsonRPC.requestList(pvritem['citem'], path, 'music', page=RADIO_ITEM_LIMIT) for path in pvritem['citem'].get('path',[])]#todo replace RADIO_ITEM_LIMIT with cacluated runtime to EPG_HRS
                fileList = list(interleave(fileList))
                if len(fileList) > 0:
                    random.shuffle(fileList)
                    listitems = []
                    # listitems.extend(poolit(LISTITEMS.buildItemListItem)(fileList)(**{media:'music'}))
                    for item in fileList: listitems.append(LISTITEMS.buildItemListItem(item,media='music'))
                    
                    for idx,lz in enumerate(listitems):
                        self.channelPlaylist.add(lz.getPath(),lz,idx)
                        
                    self.log('playRadio, Playlist size = %s'%(self.channelPlaylist.size()))
                    if not isPlaylistRandom(): self.channelPlaylist.shuffle()
                    if PLAYER.isPlayingVideo(): PLAYER.stop()
                    return PLAYER.play(self.channelPlaylist)
        else: self.playError(id, playCount)
        self.resolveURL(False, xbmcgui.ListItem())


    def contextPlay(self, writer={}, isPlaylist=False):
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.

        if writer.get('citem',{}): 
            found = True
            citem = writer.get('citem')
            pvritem = self.matchChannel(citem.get('name'),citem.get('id'))
            if pvritem is None: return self.playError()
        
            pvritem['isPlaylist']  = isPlaylist
            pvritem['callback']    = self.getCallback(pvritem.get('channel'),pvritem.get('uniqueid'))
            pvritem['citem']       = (self.sysInfo.get('citem') or decodeWriter(pvritem.get('broadcastnow',{}).get('writer','')).get('citem',{}))
            pvritem['playcount']   = SETTINGS.getCacheSetting('playingPVRITEM', checksum=pvritem.get('id','-1'), json_data=True, default={}).get('playcount',0)
            if isPlaylist: pvritem = self.extendProgrammes(pvritem)
            self.log('contextPlay, citem = %s\npvritem = %s\nisPlaylist = %s'%(citem,pvritem,isPlaylist))

            if isPlaylist:
                nowitem   = pvritem.get('broadcastnow',{})  # current item
                nowitem   = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem, inherited=self)
                nextitems = pvritem.get('broadcastnext',[]) # upcoming items
                nextitems.insert(0,nowitem)

                for pos, nextitem in enumerate(nextitems):
                    if decodeWriter(nextitem.get('writer',{})).get('file') == writer.get('file'):
                        del nextitems[0:pos]      # start array at correct position
                        del nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
                        break
                       
                nowitem = nextitems.pop(0)
                writer  = decodeWriter(nowitem.get('writer',{}))
                liz = LISTITEMS.buildItemListItem(writer)
                
                if round(nowitem['progress']) <= SEEK_TOLER or round(nowitem['progresspercentage']) > SEEK_THRED:
                    self.log('contextPlay, progress start at the beginning')
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                    
                if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                    self.log('contextPlay, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                    liz.setProperty('startoffset', str(nowitem['progress'])) #secs
                    infoTag = ListItemInfoTag(liz, 'video')
                    infoTag.set_resume_point({'ResumeTime':nowitem['progress'],'TotalTime':(nowitem['runtime'] * 60)})
                    
                pvritem['broadcastnow']  = nowitem   # current item
                pvritem['broadcastnext'] = nextitems # upcoming items
                liz.setProperty('pvritem',dumpJSON(pvritem))
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems))
            else:
                liz = LISTITEMS.buildItemListItem(writer)
                liz.setProperty('pvritem', dumpJSON(pvritem))
                listitems = [liz]
                
            for idx,lz in enumerate(listitems):
                path = lz.getPath()
                self.channelPlaylist.add(lz.getPath(),lz,idx)
                
            self.log('contextPlay, Playlist size = %s'%(self.channelPlaylist.size()))
            if isPlaylistRandom(): self.channelPlaylist.unshuffle()
            SETTINGS.setCacheSetting('playingPVRITEM', pvritem, checksum=pvritem.get('id','-1'), life=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
            return PLAYER.play(self.channelPlaylist, startpos=0)
            
        else: return self.playError(pvritem)
        self.resolveURL(found, listitems[0])
        

    def playError(self, pvritem={}):
        self.resolveURL(False, xbmcgui.ListItem()) #release pending play.
        if not pvritem: pvritem = SETTINGS.getCacheSetting('playingPVRITEM', checksum=pvritem.get('id','-1'), json_data=True, default={})
        channelPlaycount = pvritem.get('playcount',0)
        channelPlaycount += 1
        pvritem['playcount'] = channelPlaycount
        SETTINGS.setCacheSetting('playingPVRITEM', pvritem, checksum=pvritem.get('id','-1'), life=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
        self.log('playError, id = %s, attempt = %s'%(pvritem.get('id','-1'),channelPlaycount))
        if channelPlaycount == 1: setInstanceID() #reset instance and force cache flush.
        if channelPlaycount <= 2:
            with busy_dialog():
                DIALOG.notificationWait(LANGUAGE(32038),wait=OVERLAY_DELAY)
            BUILTIN.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2]))
        elif channelPlaycount == 3: forceBrute()
        else: DIALOG.notificationWait(LANGUAGE(32000))


    def resolveURL(self, found, listitem):
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitem)

