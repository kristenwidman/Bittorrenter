#!/usr/bin/env python

from pieces import *
from messages import *
from bitstring import BitArray

class ActiveTorrent(object):
    def __init__(self, torrent_info):
        self.torrent_info = torrent_info
        self.piece_downloading = MyPiece(self.torrent_info.piece_length)  #clear and restart when creating a new piece
        self.piece_number = 0   #increment this (by 8?) when creating a new piece?
        self.requested_blocks = BitArray(self.piece_downloading.block_number)
        self.have_blocks = BitArray(self.piece_downloading.block_number)

