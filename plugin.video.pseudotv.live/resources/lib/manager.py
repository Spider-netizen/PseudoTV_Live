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

from resources.lib.globals     import *

class Manager(xbmcgui.WindowXMLDialog):
    madeChanges = False
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        if isClient():
            Dialog().notificationDialog(LANGUAGE(30288))
            return openAddonSettings(0,1)
        elif isManagerRunning():
            Dialog().notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return openAddonSettings(0,1)
        
        with busy_dialog():
            setManagerRunning(True)
            setLegacyPseudoTV(True)
            
            self.cntrlStates    = {}
            self.showingList    = True
            
            self.channel_idx    = (kwargs.get('channel',1) - 1) #Convert from Channel to array index
            self.writer         = kwargs.get('writer')
            self.cache          = self.writer.cache
            self.pool           = self.writer.pool
            self.dialog         = self.writer.dialog
            self.channels       = self.writer.channels
            self.jsonRPC        = self.writer.jsonRPC
            self.rules          = self.writer.rules
            
            self.newChannel     = self.channels.getCitem()
            self.channelList    = sorted(self.createChannelList(self.buildArray(), self.channels.getChannels()), key=lambda k: k['number'])
            self.channelList.extend(self.channels.getPredefinedChannels())
            self.newChannels    = self.channelList.copy()
              
            try:    self.doModal()
            except: self.closeManager()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def onInit(self):
        self.log('onInit')
        try:
            self.focusItems    = {}
            self.spinner       = self.getControl(4)
            self.chanList      = self.getControl(5)
            self.itemList      = self.getControl(6)
            self.ruleList      = self.getControl(7)
            self.right_button1 = self.getControl(9001)
            self.right_button2 = self.getControl(9002)
            self.right_button3 = self.getControl(9003)
            self.right_button4 = self.getControl(9004)
            self.fillChanList(self.newChannels,focus=self.channel_idx) #all changes made to self.newChannels before final save to self.channellist
        except Exception as e: 
            log("onInit, Failed! %s"%(e), xbmc.LOGERROR)
            self.closeManager()
        
        
    def buildArray(self):
        self.log('buildArray')
        ## Create blank array of citem templates. 
        for idx in range(CHANNEL_LIMIT):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            yield newChannel
  
        
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList')
        ## Fill blank array with citems from channels.json.
        for item in channelArray:
            for channel in channelList:
                if item["number"] == channel["number"]:
                    item.update(channel)
            yield item


    def fillChanList(self, channelList, reset=False, focus=None):
        self.log('fillChanList')
        ## Fill chanList listitem for display. *reset draws new control list. *focus list index for channel position.
        self.togglechanList(True,reset=reset)
        self.toggleSpinner(self.chanList,True)
        listitems = (self.pool.poolList(self.buildChannelListItem,channelList))
        self.chanList.addItems(listitems)
        
        if focus is None: self.chanList.selectItem(self.setFocusPOS(listitems))
        else:             self.chanList.selectItem(focus)
        self.toggleSpinner(self.chanList,False)


    def toggleSpinner(self, ctrl, state):
        self.setVisibility(self.spinner,state)
        # getSpinControl() #todo when avail.
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__control__list.html#ga9b9ac0cd03a6d14c732050f707943d42
        # ctrl.setPageControlVisible(state)


    def togglechanList(self, state, focus=0, reset=False):
        self.log('togglechanList, state = %s, focus = %s, reset = %s'%(state,focus,reset))
        if state: # channellist
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.chanList,True)
            if reset: 
                self.chanList.reset()
                xbmc.sleep(100)
            self.chanList.selectItem(focus)
            self.setFocus(self.chanList)
            if self.madeChanges:
                self.setLabels(self.right_button1,LANGUAGE(30119))#save
                self.setLabels(self.right_button2,LANGUAGE(30120))#cancel
                self.setLabels(self.right_button3,LANGUAGE(30133))#Delete
            else:
                self.setLabels(self.right_button1,LANGUAGE(30117))#close
                self.setLabels(self.right_button2,'')
                self.setLabels(self.right_button3,LANGUAGE(30133))#Delete
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.chanList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.reset()
            xbmc.sleep(100)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
            self.setLabels(self.right_button1,LANGUAGE(30118))#ok
            self.setLabels(self.right_button2,LANGUAGE(30120))#cancel
            self.setLabels(self.right_button3,'')
        
        
    def toggleruleList(self, state, focus=0):
        self.log('toggleruleList, state = %s, focus = %s'%(state,focus))
        if self.isVisible(self.chanList): 
            return self.dialog.notificationDialog(LANGUAGE(30001))
        
        if state: # rulelist
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.ruleList,True)
            self.ruleList.selectItem(focus)
            self.setFocus(self.ruleList)
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
        
        
    def hasChannelContent(self, channelData):
        paths = channelData.get('path',[])
        if not isinstance(paths,list): paths.split('|')
        for path in paths:
            limits = (self.jsonRPC.autoPagination(channelData.get('id'), path) or {})
            self.log('hasChannelContent, channel = %s, path = %s, limits = %s'%(channelData.get('id'),path,limits))
            if limits.get('total',0) > 0: return True
        return False
        

    def buildChannelListItem(self, channelData):
        chnum        = channelData["number"]
        chname       = channelData.get("name",'')
        isPredefined = chnum > CHANNEL_LIMIT
        isFavorite   = channelData.get('favorite',False)
        isRadio      = channelData.get('radio',False)
        isLocked     = isPredefined #todo parse channel lock rule
        hasContent   = self.hasChannelContent(channelData)
        
        COLOR_UNAVAILABLE_CHANNEL = 'dimgray'
        COLOR_AVAILABLE_CHANNEL   = 'white'
        COLOR_LOCKED_CHANNEL      = 'orange'
        COLOR_WARNING_CHANNEL     = 'red'
        COLOR_RADIO_CHANNEL       = 'cyan'
        COLOR_FAVORITE_CHANNEL    = 'yellow'
        
        channelColor = COLOR_UNAVAILABLE_CHANNEL
        labelColor   = COLOR_UNAVAILABLE_CHANNEL
        
        if chname:
            if isPredefined: 
                channelColor = COLOR_LOCKED_CHANNEL
            else:
                labelColor   = COLOR_AVAILABLE_CHANNEL
                
                if not hasContent: channelColor = COLOR_WARNING_CHANNEL
                elif isLocked:     channelColor = COLOR_LOCKED_CHANNEL
                elif isFavorite:   channelColor = COLOR_FAVORITE_CHANNEL
                elif isRadio:      channelColor = COLOR_RADIO_CHANNEL
                else:              channelColor = COLOR_AVAILABLE_CHANNEL
        
        label  = '[COLOR=%s][B]%s.[/COLOR][/B]'%(channelColor,chnum)
        label2 = '[COLOR=%s]%s[/COLOR]'%(labelColor,chname)
        path   = '|'.join(channelData.get("path",[]))
        prop   = {'description':LANGUAGE(30122)%(chnum),'channelData':dumpJSON(channelData, sortkey=False),'chname':chname,'chnumber':chnum}
        return self.dialog.buildMenuListItem(label,label2,iconImage=channelData.get("logo",''),url=path,propItem=prop)
        

    def setDescription(self, stid):#todo use control id and label
        PROPERTIES.setProperty('manager.description',LANGUAGE(stid))


    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(cleanLabel(listitem.getLabel()))
            if  ignore and chnumber > CHANNEL_LIMIT: continue
            elif chnum is not None and chnum == chnumber: return idx
            elif chnum is None and cleanLabel(listitem.getLabel2()): return idx
        return 0
        
        
    def buildChannelItem(self, channelData, selkey='path'):
        self.log('buildChannelItem, channelData = %s'%(channelData))
        if self.isVisible(self.ruleList): return
        self.togglechanList(False)
        self.toggleSpinner(self.itemList,True)
        
        LABEL  = {'name'    : LANGUAGE(30087),
                  'path'    : LANGUAGE(30088),
                  'group'   : LANGUAGE(30089),
                  'rules'   : LANGUAGE(30090),
                  'radio'   : LANGUAGE(30114),
                  'favorite': LANGUAGE(30021),
                  'clear'   : LANGUAGE(30092)}
                  
        DESC   = {'name'    : LANGUAGE(30123),
                  'path'    : LANGUAGE(30124),
                  'group'   : LANGUAGE(30125),
                  'rules'   : LANGUAGE(30126),
                  'radio'   : LANGUAGE(30127),
                  'favorite': LANGUAGE(30032),
                  'clear'   : LANGUAGE(30128)}
                  
        listItems   = []
        channelProp = dumpJSON(channelData, sortkey=False)
        for key in self.channels.getCitem().keys():
            value = channelData.get(key)
            print(key, value)
            if   key in ["number","type","logo","id","catchup"]: continue # keys to ignore, internal use only.
            elif isinstance(value,list): 
                if   key == "group" :    value = ' / '.join(list(set(value)))
                elif key == "path"  :    value = '|'.join(value)
            elif isinstance(value,bool): value = str(value)
            value = (value or '')
            listItems.append(self.dialog.buildMenuListItem(LABEL.get(key,''),value,url='|'.join(channelData.get("path",[])),iconImage=channelData.get("logo",COLOR_LOGO),propItem={'key':key,'value':value,'channelData':channelProp,'description':DESC.get(key,''),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}))
        
        listItems.append(self.dialog.buildMenuListItem(LABEL['clear'],'',propItem={'key':'clear','channelData':channelProp,'description':DESC['clear']}))
        self.toggleSpinner(self.itemList,False)
        self.itemList.addItems(listItems)
        self.itemList.selectItem([idx for idx, liz in enumerate(listItems) if liz.getProperty('key')== selkey][0])
        self.setFocus(self.itemList)


    def itemInput(self, channelListItem):
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        channelData = loadJSON(channelListItem.getProperty('channelData'))
        self.log('itemInput, channelData = %s, value = %s, key = %s'%(channelData,value,key))
        KEY_INPUT = {"name"     : {'func':self.dialog.inputDialog         ,'kwargs':{'message':LANGUAGE(30123),'default':value}},
                     "path"     : {'func':self.dialog.browseDialog        ,'kwargs':{'heading':LANGUAGE(30124),'default':value,'monitor':True}},
                     "group"    : {'func':self.dialog.selectDialog        ,'kwargs':{'list':getGroups(),'header':LANGUAGE(30125),'preselect':findItemsInLST(getGroups(),value.split(' / ')),'useDetails':False}},
                     "rules"    : {'func':self.selectRules                ,'kwargs':{'channelData':channelData}},
                     "radio"    : {'func':self.toggleBool                 ,'kwargs':{'state':channelData.get('radio',False)}},
                     "favorite" : {'func':self.toggleBool                 ,'kwargs':{'state':channelData.get('favorite',False)}},
                     "clear"    : {'func':self.clearChannel               ,'kwargs':{'item':channelData}}}
           
        func   = KEY_INPUT[key.lower()]['func']
        kwargs = KEY_INPUT[key.lower()]['kwargs']
        retval, channelData = self.validateInput(func(**kwargs),key, channelData)
        print('itemInput',retval,type(retval))
        if retval and retval is not None:
            self.madeChanges = True
            if isinstance(retval,list):
                retval = [kwargs.get('list',[])[idx] for idx in retval]
            if key in self.newChannel:
                channelData[key] = retval
            elif key == 'clear':
                channelData = retval
        return channelData
   

    def toggleBool(self, state):
        self.log('toggleBool, state = %s'%(state))
        return not state


    def openEditor(self, path):
        self.log('openEditor, path = %s'%(path))
        if '|' in path: 
            path = path.split('|')
            path = path[0]#prompt user to select:
        media = 'video' if 'video' in path else 'music'
        if   '.xsp' in path: return self.openEditor(path,media)
        elif '.xml' in path: return self.openNode(path,media)
       
   
    def getChannelName(self, path, channelData):
        self.log('getChannelName, path = %s'%(path))
        if path.strip('/').endswith(('.xml','.xsp')):
            channelData['name'] = self.getSmartPlaylistName(path)
        elif path.startswith(('plugin://','upnp://','videodb://','musicdb://','library://','special://')):
            channelData['name'] = self.getMontiorList().getLabel()
        else:
            channelData['name'] = os.path.basename(os.path.dirname(path)).strip('/')
        return channelData


    def getMontiorList(self, key='label'):
        self.log('getMontiorList')
        try:
            def getItem(item):
                return self.dialog.buildMenuListItem(label1=item.get(key,''),iconImage=item.get('icon',COLOR_LOGO))
                
            infoList = self.dialog.getInfoMonitor()
            itemList = [getItem(info) for info in infoList if info.get('label')]
            select   = self.dialog.selectDialog(itemList,LANGUAGE(30121)%(key.title()),useDetails=True,multi=False)
            if select is not None: return itemList[select]
        except Exception as e: 
            self.log("getMontiorList, Failed! %s\ninfoList = %s"%(e,infoList), xbmc.LOGERROR)
            return xbmcgui.ListItem()


    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        try:
            name = ''
            fle = fle.strip('/').replace('library://','special://userdata/library/')
            xml = FileAccess.open(fle, "r")
            string = xml.read()
            xml.close()
            if fle.endswith('xml'): key = 'label'
            else: key = 'name'
            match = re.compile('<%s>(.*?)\</%s>'%(key,key), re.IGNORECASE).search(string)
            if match: name =  unescapeString(match.group(1))
            log("getSmartPlaylistName fle = %s, name = %s"%(fle,name))
        except: log("getSmartPlaylistName return unable to parse %s"%(fle))
        return name


    def getChannelIcon(self, channelData, path=None, name=None, force=False):
        self.log('getChannelIcon, path = %s'%(path))
        if name is None: name = channelData.get('name','')
        if path is None: path = channelData.get('path','')
        if not name: return channelData
        if force: logo = ''
        else:     logo = channelData.get('logo','')
        if not logo or logo in [LOGO,COLOR_LOGO,MONO_LOGO,ICON]:
            type = channelData.get('type',LANGUAGE(30171))
            channelData['logo'] = self.jsonRPC.resources.getLogo(name, type, path)
        return channelData
        
    
    def validateInput(self, retval, key, channelData):
        self.log('validateInput, retval = %s'%(retval))
        print(retval, key)
        if retval is None:   return None  , channelData
        elif key == 'rules': return None  , channelData
        elif key == 'clear': return retval, channelData
        elif key == 'path':
            retval, channelData = self.validatePath(channelData, retval, key)
            if retval is not None:
                channelData = self.getChannelName(retval, channelData)
                channelData = self.getChannelIcon(channelData, path=retval[0])
        elif key == 'name':
            if not self.validateLabel(key,retval): 
                retval = None
            else:
                channelData = self.getChannelIcon(channelData, name=retval,force=True)
        if retval is not None: channelData = self.getID(channelData)
        return retval, channelData
        
        
    def validateLabel(self, key, label=''):
        self.log('validateLabel, key = %s, label = %s'%(key,label))
        if not label or len(label) < 1: 
            return False
        elif len(label) < 3 or len(label) > 128:
            self.dialog.notificationDialog(LANGUAGE(30112)%key.title())
            return False
        else:
            return True
    
    
    def validatePlaylist(self, path, channelData):
        self.log('validatePlaylist, path = %s'%(path))
        #cache playlists to PLS_LOC?
        # if path.strip('/').endswith('.xml'):
            # newPath = path.strip('/').replace('library://','special://userdata/library/')
            # dir, file = (os.path.split(newPath))
            # cachefile = os.path.join(dir.replace('special://userdata/library',PLS_LOC),file)
        # elif path.endswith('.xsp'):
            # cachefile = os.path.join(PLS_LOC,os.path.basename(path))
        # else: 
            # return path, channelData
        # self.log('validatePlaylist, path = %s, cachefile = %s'%(path,cachefile))
        # FileAccess.copy(path, cachefile): 


    def validatePath(self, channelData, path, key, spinner=True):
        self.log('validatePath, path = %s'%path)
        if not path: return None, channelData
        radio = (channelData.get('radio','') or (channelData['type'] == LANGUAGE(30097) or path.startswith('musicdb://')))
        media = 'music' if radio else 'video'
        channelData['radio'] = radio
        
        if spinner: self.toggleSpinner(self.itemList,True)
        fitem = self.jsonRPC.isVFSPlayable(path, media)
        if fitem is not None:
            seek = fitem.get('seek',False) #todo set adv. chan rule to disable seek if false.
            self.log('validatePath, path = %s, seek = %s'%(path,seek))
            if path.strip('/').endswith(('.xml','.xsp')):
                self.validatePlaylist(path, channelData)
            if spinner: self.toggleSpinner(self.itemList,False)
            return path, channelData
           
        self.dialog.notificationDialog('%s\n%s'%(LANGUAGE(30112)%key.title(),LANGUAGE(30115))) 
        if spinner: self.toggleSpinner(self.itemList,False)
        return None, channelData
        
        
    def getID(self, channelData):
        if channelData.get('name','') and channelData.get('path',''): 
            channelData['id'] = getChannelID(channelData['name'], channelData['path'], channelData['number'])
            self.log('getID, id = %s'%(channelData['id']))
        return channelData
        
        
    def validateChannel(self, channelData):
        if not channelData.get('name','') or not channelData.get('path',[]): 
            return None
        channelData = self.getID(channelData)
        if channelData['number'] <= CHANNEL_LIMIT: 
            channelData['type'] = LANGUAGE(30171) #custom
        if not channelData.get('logo',''):
            channelData = self.getChannelIcon(channelData)
        return channelData
    
    
    def validateChannels(self, channelList):
        self.log('validateChannels')
        return sorted(self.pool.poolList(self.validateChannel,channelList), key=lambda k: k['number'])
              

    def saveChannelItems(self, channelData, channelPOS):
        self.log('saveChannelItems, channelPOS = %s'%(channelPOS))
        self.newChannels[channelPOS] = channelData
        self.fillChanList(self.newChannels,reset=True,focus=channelPOS)
        
    
    def saveChanges(self):
        self.log("saveChanges")
        if self.dialog.yesnoDialog("Changes Detected, Do you want to save?"): return self.saveChannels() 
        else: self.closeManager()


    def saveChannels(self):
        if   not self.madeChanges: return
        elif not self.dialog.yesnoDialog(LANGUAGE(30073)): return
        self.toggleSpinner(self.chanList,True)
        self.newChannels = self.validateChannels(self.newChannels)
        self.channelList = self.validateChannels(self.channelList)
        difference = sorted(diffLSTDICT(self.channelList,self.newChannels), key=lambda k: k['number'])
        log('saveChannels, difference = %s'%(len(difference)))
        
        pDialog = self.dialog.progressDialog(message=LANGUAGE(30152))
        for idx, citem in enumerate(difference):
            print('citem',citem)
            pCount = int(((idx + 1)*100)//len(difference))
            if citem in self.channelList: 
                self.channels.removeChannel(citem)
            if citem in self.newChannels:
                pDialog = self.dialog.progressDialog(pCount,pDialog,message="%s: %s"%(LANGUAGE(30337),citem.get('name')),header='%s, %s'%(ADDON_NAME,LANGUAGE(30152)))
                self.channels.addChannel(citem)

        self.channels._save()
        self.toggleSpinner(self.chanList,False)
        self.closeManager()
            
        
    def clearChannel(self, item, prompt=True):
        self.log('clearChannel')
        if prompt and not self.dialog.yesnoDialog(LANGUAGE(30092)): return item
        self.madeChanges = True
        nitem = self.newChannel.copy()
        nitem['number'] = item['number'] #preserve channel number
        return nitem


    def selectRuleItems(self, item):
        self.log('selectRuleItems')
        print('selectRuleItems',item)
        channelData = loadJSON(item['item'].getProperty('channelData'))
        
        if item['position'] == 0:
            ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) #all rule instances with channel settings applied
        else:
            ruleInstances = [item['item']]
        
        print(ruleInstances)
        listitems   = self.pool.poolList(self.buildRuleListItem,ruleInstances,channelData)
        optionIDX   = self.dialog.selectDialog(listitems,LANGUAGE(30135),multi=False)

        # ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) #all rule instances with channel settings applied
        # print(ruleInstances)

        # if not append:
            # ruleInstances = channelRules.copy()
        # else:    
            # ruleInstances = ruleList.copy()
            # for channelRule in channelRules:
                # for idx, ruleInstance in enumerate(ruleInstances):
                    # if channelRule.get('id') == ruleInstance.get('id'):
                        # ruleInstance.pop(idx)
                        
        # listitems = self.pool.poolList(self.buildRuleListItem,ruleInstances,channelData)
        

        if optionIDX is not None:
            ruleSelect    = loadJSON(listitems[optionIDX].getProperty('rule'))
            ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) # all rules
            ruleInstance  = [ruleInstance for ruleInstance in ruleInstances if ruleInstance.myId == ruleSelect.get('id')][0]
            print(ruleSelect,ruleInstance)
        
            #todo create listitem using ruleInstance and rule.py action map.
            listitems     = [self.dialog.buildMenuListItem(ruleInstance.optionLabels[idx],str(ruleInstance.optionValues[idx]),iconImage=channelData.get("logo",''),url=str(ruleInstance.myId),propItem={'channelData':dumpJSON(channelData)}) for idx, label in enumerate(ruleInstance.optionLabels)]
            self.ruleList.addItems(listitems)
            
            # optionIDX    = self.dialog.selectDialog(listitems,LANGUAGE(30135),multi=False)
            # print(ruleSelect)
            # ruleSelect['options'][str(optionIDX)].update({'value':ruleInstance.onAction(optionIDX)})
            # print(ruleSelect)
            # self.selectRuleItems(channelData, rules, ruleSelect)
            
            
    def selectRules(self, channelData):
        self.log('selectRules')
        if not self.validateChannel(channelData): return self.dialog.notificationDialog(LANGUAGE(30139))
        listitems = self.buildRuleItems(channelData)
        print('selectRules listitems',[listitem.getLabel() for listitem in listitems],channelData)
        self.toggleruleList(True)
        self.ruleList.addItems(listitems)
        
        # select = self.dialog.selectDialog(listitems,LANGUAGE(30135),useDetails=True,multi=False)
        # if select is None: return self.dialog.notificationDialog(LANGUAGE(30001))
        # print(listitems[select].getLabel())
        
        # self.ruleList.addItems(listitems)
        
        # return channelData
        # select = self.dialog.selectDialog(listitems,LANGUAGE(30135),useDetails=True,multi=False)
        # if select is None: return self.dialog.notificationDialog(LANGUAGE(30001))
        # return listitems[select]
        
        # ruleid   = int(listitem.getPath())
        # if ruleid < 0: 
            # rules    = sorted(self.fillRules(channelData), key=lambda k: k['id'])
            # listitem = self.buildRuleItems(rules, channelData)
            # ruleid   = int(listitem.getPath())
        # ruleSelect = [idx for idx, rule in enumerate(self.channels.ruleList) if rule['id'] == ruleid]
        # self.selectRuleItems(channelData, rules, self.channels.ruleList[ruleSelect[0]])
        
        self.toggleruleList(False)
        return channelData['rules']


    def buildRuleItems(self, channelData, append=True):
        self.log('buildRuleItems, append = %s'%(append))
        self.toggleSpinner(self.ruleList,True)
        channelRules = self.rules.loadRules([channelData]).get(channelData['id'],[]) # all channel rule instances only.
        listitems = self.pool.poolList(self.buildRuleListItem,channelRules,channelData)
        if append: listitems.insert(0,self.dialog.buildMenuListItem('','Add New Rule',url='-1',propItem={'channelData':dumpJSON(channelData)}))
        self.toggleSpinner(self.ruleList,False)
        self.ruleList.reset()
        xbmc.sleep(100)
        return listitems
        

    def buildRuleListItem(self, data):
        ruleInstance, channelData = data
        rule = {'id':ruleInstance.myId,'name':ruleInstance.name,'description':ruleInstance.description,'labels':ruleInstance.optionLabels,'values':ruleInstance.optionValues,'title':ruleInstance.getTitle()}
        print(rule)
        prop = {'description':rule['description'],'rule':dumpJSON(rule),'channelData':dumpJSON(channelData),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}
        return self.dialog.buildMenuListItem(rule['title'],rule['description'],iconImage=channelData.get("logo",''),url=str(rule['id']),propItem=prop)


    def saveRuleList(self, items):
        self.log('saveRuleList')
        self.toggleruleList(False)
            
            
    def fillRules(self, channelData): # prepare "new" rule list, remove existing.
        ...
        # chrules  = sorted(self.channels.getChannelRules(channelData, self.newChannels), key=lambda k: k['id'])
        # ruleList = self.channels.rules.copy()
        # for rule in ruleList:
            # for chrule in chrules:
                # if rule['id'] == chrule['id']: continue
            # yield rule


    def getLogo(self, channelData, channelPOS):
        def cleanLogo(chlogo):
            return unquoteImage(chlogo)
            #todo convert resource from vfs to fs
            # return chlogo.replace('resource://','special://home/addons/')
            # resource = path.replace('/resources','').replace(,)
            # resource://resource.images.studios.white/Amazon.png
        
        def select(chname):
            self.toggleSpinner(self.itemList,True)
            logos = self.jsonRPC.resources.findLogos(chname, LANGUAGE(30171))
            listitems = [self.dialog.buildMenuListItem(logo['label'],logo['label2'],iconImage=logo['path'],url=logo['path']) for logo in logos]
            self.toggleSpinner(self.itemList,False)
            if listitems:
                select = self.dialog.selectDialog(listitems,'Select Channel Logo',useDetails=True,multi=False)
                if select is not None:
                    return listitems[select].getPath()

        def browse(chname):
            retval = self.dialog.browseDialog(type=1,heading='%s for %s'%(LANGUAGE(30111),chname),default=channelData.get('icon',''), shares='files',mask=xbmc.getSupportedMedia('picture'),prompt=False)
            image  = os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')
            if FileAccess.copy(cleanLogo(retval), image): 
                if FileAccess.exists(image): 
                    return image

        def match(chname):
            return self.jsonRPC.resources.getLogo(chname)

        if self.isVisible(self.ruleList): return
        chname = channelData.get('name')
        if not chname: return self.dialog.notificationDialog(LANGUAGE(30084))
            
        chlogo = None
        retval = self.dialog.yesnoDialog('%s Source'%LANGUAGE(30111), 
                                             nolabel=LANGUAGE(30321),     #Select
                                             yeslabel=LANGUAGE(30308),    #Browse
                                             customlabel=LANGUAGE(30322)) #Match
                                             
        if   retval == 0: chlogo = select(chname)
        elif retval == 1: chlogo = browse(chname)
        elif retval == 2: chlogo = match(chname)
        else: self.dialog.notificationDialog(LANGUAGE(30325))
        self.log('getLogo, chname = %s, chlogo = %s'%(chname,chlogo))
        
        if chlogo:
            self.madeChanges = True
            channelData['logo'] = chlogo
            if self.isVisible(self.itemList): self.buildChannelItem(channelData)
            else:
                self.newChannels[channelPOS] = channelData
                self.fillChanList(self.newChannels,reset=True,focus=channelPOS)
            

    def isVisible(self, cntrl):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            state = cntrl.isVisible()
        except: state = self.cntrlStates.get(cntrl.getId(),False)
        self.log('isVisible, cntrl = %s, state = %s'%(cntrl.getId(),state))
        return state
        
        
    def setVisibility(self, cntrl, state):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setVisible(state)
            self.cntrlStates[cntrl.getId()] = state
            self.log('setVisibility, cntrl = ' + str(cntrl.getId()) + ', state = ' + str(state))
        except Exception as e: self.log("setVisibility, failed! %s"%(e), xbmc.LOGERROR)
    
    
    def setLabels(self, cntrl, label='', label2=''):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setLabel(str(label), str(label2))
            self.setVisibility(cntrl,(len(label) > 0 or len(label2) > 0))
        except Exception as e: self.log("setLabels, failed! %s"%(e), xbmc.LOGERROR)
    
    
    def getLabels(self, cntrl):
        try:
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            return cntrl.getLabel(), cntrl.getLabel2()
        except Exception as e: return '',''
        
        
    def setImages(self, cntrl, image='NA.png'):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setImage(image)
        except Exception as e: self.log("setImages, failed! %s"%(e), xbmc.LOGERROR)
 

    def closeManager(self):
        self.log('closeManager')
        setLegacyPseudoTV(False)
        setManagerRunning(False)
        if self.madeChanges:
            setInstanceID()
            setUpdatePending()
        self.close()


    def getFocusVARS(self, controlId=None):
        if controlId not in [5,6,7,10,9001,9002,9003]: return self.focusItems
        self.log('getFocusVARS, controlId = %s'%(controlId))
        try:
            channelitem     = (self.chanList.getSelectedItem()     or xbmcgui.ListItem())
            channelPOS      = (self.chanList.getSelectedPosition() or 0)
            channelListItem = (self.itemList.getSelectedItem()     or xbmcgui.ListItem())
            itemPOS         = (self.itemList.getSelectedPosition() or 0)
            ruleListItem    = (self.ruleList.getSelectedItem()     or xbmcgui.ListItem())
            rulePOS         = (self.ruleList.getSelectedPosition() or 0)

            self.focusItems = {'chanList':{'item'    :channelitem,
                                           'position':channelPOS},
                               'itemList':{'item'    :channelListItem,
                                           'position':itemPOS},
                               'ruleList':{'item'    :ruleListItem,
                                           'position':rulePOS}}
            if controlId is not None: 
                label, label2 = self.getLabels(controlId)
                self.focusItems.update({'label':label,'label2':label2})
                
            self.focusItems['chanList']['citem'] = loadJSON(channelitem.getProperty('channelData'))
            self.focusItems['itemList']['citem'] = loadJSON(channelListItem.getProperty('channelData'))
            self.focusItems['ruleList']['citem'] = loadJSON(ruleListItem.getProperty('channelData'))
            
            chnumber = cleanLabel(channelitem.getLabel())
            if chnumber.isdigit(): 
                try:
                    self.focusItems['number'] = int(chnumber)
                except:
                    self.focusItems['number'] = float(chnumber)
            elif self.focusItems['chanList']['citem'].get('number',''):
                self.focusItems['number'] = self.focusItems['chanList']['citem']['number']
            else:
                self.focusItems['number'] = channelPOS + 1
            return self.focusItems
        except: return {}

    
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        items = self.getFocusVARS()
        if actionId in ACTION_PREVIOUS_MENU:
            if xbmcgui.getCurrentWindowDialogId() == "13001":
                xbmc.executebuiltin("ActivateWindow(Action(Back)")
            elif self.isVisible(self.ruleList): self.toggleruleList(False)
            elif self.isVisible(self.itemList): self.togglechanList(True,focus=items['chanList']['position'])
            elif self.isVisible(self.chanList):
                if    self.madeChanges: 
                    self.saveChanges()
                else: 
                    self.closeManager()
        
        
    def onClick(self, controlId):
        items = self.getFocusVARS(controlId)
        if controlId <= 9000 and items['number'] > CHANNEL_LIMIT: 
            return self.dialog.notificationDialog(LANGUAGE(30110))
            
        self.log('onClick: controlId = %s\nitems = %s'%(controlId,items))
        if self.isVisible(self.chanList):
            channelData = items['chanList']['citem'] 
        else:
            channelData = items['itemList']['citem']
            
        if   controlId == 0: self.closeManager()
        elif controlId == 5: 
            self.buildChannelItem(channelData)
        elif controlId == 6:
            self.buildChannelItem(self.itemInput(items['itemList']['item']),items['itemList']['item'].getProperty('key'))
        elif controlId == 7:
            self.selectRuleItems(items['ruleList'])
        elif controlId == 10: 
            self.getLogo(channelData,items['chanList']['position'] )
        elif controlId == 9001:
            if   items['label'] == LANGUAGE(30117):#'Close'
                self.closeManager()
            elif items['label'] == LANGUAGE(30119):#'Save'
                self.saveChannels()
            elif items['label'] == LANGUAGE(30118):#'OK'
                if self.isVisible(self.itemList) and self.madeChanges:
                    self.saveChannelItems(channelData,items['chanList']['position'])
                elif self.isVisible(self.ruleList): 
                    self.toggleruleList(False)
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9002:
            if items['label'] == LANGUAGE(30120):#'Cancel'
                if self.isVisible(self.chanList) and self.madeChanges:  
                    self.saveChanges()
                elif self.isVisible(self.ruleList): 
                    self.toggleruleList(False)
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9003:
            self.saveChannelItems(self.clearChannel(channelData),items['chanList']['position'])