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
from globals import *
from plugin  import Plugin

class Play:
    def __init__(self, sysARG, writer):
        with busy_dialog():
            log('Play: __init__, sysARG = %s'%(sysARG))
            Plugin(sysARG).contextPlay(writer,isPlaylist=False)
            
class Playlist:
    def __init__(self, sysARG, writer):
        with busy_dialog():
            log('Playlist: __init__, sysARG = %s'%(sysARG))
            Plugin(sysARG).contextPlay(writer,isPlaylist=True)
            
if __name__ == '__main__': 
    try:    param = sys.argv[1]
    except: param = None
    log('Play: __main__, param = %s'%(param))
    if param == 'play':
        Play(sys.argv,writer=decodeWriter(BUILTIN.getInfoLabel('Writer')))
    elif param == 'playlist':
        Playlist(sys.argv,writer=decodeWriter(BUILTIN.getInfoLabel('Writer')))