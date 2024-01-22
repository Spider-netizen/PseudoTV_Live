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
#
# -*- coding: utf-8 -*-

from globals import *
try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

def cacheit(expiration=datetime.timedelta(days=MIN_GUIDEDAYS), checksum=ADDON_VERSION, json_data=False):
    def decorator(func):
        def decorated(*args, **kwargs):
            method_class = args[0]
            cacheName    = "%s.%s"%(method_class.__class__.__name__, func.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            results = method_class.cache.get(cacheName.lower(), checksum, json_data)
            if results: return results
            return method_class.cache.set(cacheName.lower(), func(*args, **kwargs), checksum, expiration, json_data)
        return decorated
    return decorator

class Cache:
    cache = SimpleCache()
    
    @contextmanager
    def cacheLocker(self): #simplecache is not thread safe, threadlock not avoiding collisions? Hack/Lazy avoidance.
        if xbmcgui.Window(10000).getProperty('%s.cacheLocker'%(ADDON_ID)) == 'true':
            while not xbmc.Monitor().abortRequested():
                if xbmc.Monitor().waitForAbort(0.001): break
                elif not xbmcgui.Window(10000).getProperty('%s.cacheLocker'%(ADDON_ID)) == 'true': break
        xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'true')
        try: yield
        finally:
            xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'false')


    def __init__(self, mem_cache=False, is_json=False):
        self.cache.enable_mem_cache = mem_cache
        self.cache.data_is_json     = is_json  


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def set(self, name, data, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15), json_data=False):
        if data is not None or not DEBUG_CACHE:
            if not name.startswith(ADDON_ID): name = '%s.%s'%(ADDON_ID,name)
            with self.cacheLocker():
                self.log('set, name = %s, checksum = %s'%(name,checksum))
                self.cache.set(name.lower(),data,checksum,expiration,json_data)
        return data
        
    
    def get(self, name, checksum=ADDON_VERSION, json_data=False, default=None):
        if not DEBUG_CACHE:
            if not name.startswith(ADDON_ID): name = '%s.%s'%(ADDON_ID,name)
            with self.cacheLocker():
                self.log('get, name = %s, checksum = %s, default = %s'%(name,checksum,default))
                return (self.cache.get(name.lower(),checksum,json_data) or default)
        return default