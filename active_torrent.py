#!/usr/bin/env python

import sys
import bencode
import requests
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from torrent import Torrent
from active_torrent import ActiveTorrent
from messages import *
from pieces import *
from bitstring import BitArray

number_peers = 5

class ActiveTorrent(object):
    def __init__(self, torrent_file):
        self.peers, self.torrent_info = get_peers(torrent_file)
        self.torrent_info = torrent_info
        self.piece_downloading = MyPiece(self.torrent_info.piece_length)  #clear and restart when creating a new piece
#!! self.file_downloading = TorrentFile(#number pieces, piece size)
        self.piece_number = 0   #increment this (by 8?) when creating a new piece?
        self.requested_blocks = BitArray(self.piece_downloading.block_number)
        self.have_blocks = BitArray(self.piece_downloading.block_number)

    def connect(number_peers):
        number_connections = 0
        for peer in self.peers:
            if number_connections < number_peers:
                hostandport = peer.split(':')
                print hostandport[0] + ':' + hostandport[1]
                bittorrent_factory = BittorrentFactory(self.torrent_info)
                reactor.connectTCP(hostandport[0], int(hostandport[1]),bittorrent_factory)
                number_connections += 1

    def parse_response_from_tracker(r):
        '''Input: http response from our request to the tracker
           Output: a list of peer_ids
           Takes the http response from the tracker and parses the peer ids from the 
           response. This involves changing the peer string from unicode (binary model)
           to a network(?) model(x.x.x.x:y). From the spec: 'First 4 bytes are the IP address and
           last 2 bytes are the port number'
        '''
        response = bencode.bdecode(r.content)
        peers = response['peers']
        i=1
        peer_address = ''
        peer_list = []
        for c in peers:
            if i%6 == 5:
                port_large = ord(c)*256
            elif i%6 == 0:
                port_small = ord(c)
                port = port_large+port_small
                peer_address += ':'+str(port)
                peer_list.append(peer_address)
                peer_address = ''
                i = 0
            elif i%6 == 4:
                peer_address += str(ord(c))
            else:
                peer_address += str(ord(c))+'.'
            i += 1
        return peer_list

    def get_peers(torrent_file):
        '''Input: metainfo file (.torrent file)
           Output: a list of peer_ids (strings) returned from the tracker
           Calls methods to send an http request to the tracker, parse the returned
           result message and return a list of peer_ids
        '''
        f = open(torrent_file, 'r')
        metainfo = bencode.bdecode(f.read())
        f.close()
        torrent_info = Torrent(metainfo)
        r = requests.get(torrent_info.announce_url, params=torrent_info.param_dict)
        peers = parse_response_from_tracker(r)
        return peers, torrent_info

    def handshake(torrent_obj):
        '''Input: ip:port of a peer with the torrent files of interest
           Output: <fill this in>
           <fill this in>
        '''
        info_hash = torrent_obj.info_hash
        peer_id = torrent_obj.peer_id
        handshake = Handshake(info_hash, peer_id)
        return handshake

def main():  #torrent list passed in eventually
    t = ActiveTorrent('test.torrent')
    print t.peers
    t.connect(number_peers)

    reactor.run()

if __name__ == "__main__":
    #main(sys.argv[1])
    main()

