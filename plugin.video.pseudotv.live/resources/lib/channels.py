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

class Channels:
             
    def __init__(self):
        self.cache       = Cache()
        self.channelDATA = getJSON(CHANNELFLE_DEFAULT)
        self.channelTEMP = self.channelDATA.get('channels',[]).pop(0)
        self.channelDATA.update(self._load())
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def _load(self, file=CHANNELFLEPATH):
        return getJSON(file)
    
    
    def _save(self, file=CHANNELFLEPATH):
        self.channelDATA['channels'] = sorted(self.channelDATA['channels'], key=lambda k: k['number'])
        return setJSON(file,self.channelDATA)

        
    def getTemplate(self):
        return self.channelTEMP.copy()
        
        
    def getChannels(self):
        return self.channelDATA.get('channels',[])
        

    def getPredefinedChannels(self):
        return list(filter(lambda citem:citem.get('number') > CHANNEL_LIMIT, self.getChannels()))

                
    def popChannels(self, type, channels=[]):
        return [self.channelDATA['channels'].pop(self.channelDATA['channels'].index(citem)) for citem in list(filter(lambda c:c.get('type') == type, channels))]
        
        
    def getAutotuned(self):
        return list(filter(lambda citem:citem.get('number') > CHANNEL_LIMIT, self.getChannels()))
        

    def getChannelbyID(self, id):
        channels = self.getChannels()
        return list(filter(lambda c:c.get('id') == id, channels))
        
        
    def getType(self, type):
        return list(filter(lambda citem:citem.get('type') == type, self.getChannels()))


    def setChannels(self, channels=[]):
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(channels)))
        return self._save()

    
    def getImports(self):
        return self.channelDATA.get('imports',[])
        
        
    def setImports(self, data=[]):
        self.channelDATA['imports'] = data
        return self._save()
        
        
    def getUUID(self):
        return (self.channelDATA.get('uuid','') or self.getMYUUID())
        
        
    def setUUID(self, data=[]):
        self.channelDATA['uuid'] = data
        return self._save()
         
    
    # def getChannel(self, item):
        # if item.get('id')

    def delChannel(self, citem):
        self.log('delChannel, id = %s'%(citem['id']), xbmc.LOGINFO)
        idx, channel = self.findChannel(citem)
        if idx is not None: self.channelDATA['channels'].pop(idx)
        return True
    
    
    def addChannel(self, citem):
        idx, channel   = self.findChannel(citem)
        if idx is not None:
            for key in ['id','rules','number','favorite','logo']: 
                if channel.get(key): citem[key] = channel[key] # existing id found, reuse channel meta.
                
            if citem.get('favorite',False):
                citem['group'].append(LANGUAGE(32019))
                citem['group'] = list(set(citem['group']))
                
            self.log('addChannel, updating channel %s, id %s'%(citem["number"],citem["id"]), xbmc.LOGINFO)
            self.channelDATA['channels'][idx] = citem
        else:
            self.log('addChannel, adding channel %s, id %s'%(citem["number"],citem["id"]), xbmc.LOGINFO)
            self.channelDATA.setdefault('channels',[]).append(citem)
        return True
        
        
    def findChannel(self, citem, channels=[]):
        if len(channels) == 0: channels = self.getChannels()
        for idx, eitem in enumerate(channels):
            if (citem.get('id') == eitem.get('id',str(random.random()))) or (citem.get('type') == eitem.get('type',str(random.random())) and citem.get('name').lower() == eitem.get('name',str(random.random())).lower()):
                return idx, eitem
        return None, {}
            
