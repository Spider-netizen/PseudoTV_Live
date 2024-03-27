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
from globals import *
from plugin  import Plugin
     
if __name__ == '__main__': 
    try:    mode = sys.argv[1]
    except: mode = None
    citem = decodePlot(BUILTIN.getInfoLabel('Plot')).get('citem',{})
    sys.argv.append('?mode=%s&name=%s&chid=%s'%(mode,quoteString(citem.get('name')),quoteString(citem.get('id'))))
    log('Context_Play: __main__, mode = %s, param = %s'%(mode, sys.argv))
    if   mode == 'play':     Plugin(sys.argv).playTV(citem.get('name'),citem.get('id'))
    elif mode == 'playlist': Plugin(sys.argv).playPlaylist(citem.get('name'),citem.get('id'))
        
        
        