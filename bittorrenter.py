#!usr/bin/env python 
#kristen widman
#Oct 8, 2012

import sys
import socket
import bencode
import hashlib
import binascii
import requests
import urllib
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from torrent import Torrent
from active_torrent import ActiveTorrent
from messages import *
#from sys import stdout

class BittorrentProtocol(Protocol):
    def __init__(self,torrent_info):
        #super(BittorrentProtocol, self).__init__()
        #Protocol.__init__(self)
        self.torrent_info = torrent_info
        self.active_torrent = ActiveTorrent(torrent_info)

    def connectionMade(self):
        handshake_msg = repr(handshake(self.torrent_info))
        self.transport.write(handshake_msg)          
        #self.transport.loseConnection()

    def dataReceived(self,data):
        messages_to_send = self.active_torrent.deal_with_message(data)
        for message in messages_to_send:
            self.transport.write(message)
        
class BittorrentFactory(ClientFactory):
    def __init__(self,torrent_info):
        #super(BittorrentFactory, self).__init__()
        #ClientFactory.__init__(self)
        self.torrent_info = torrent_info

    def startedConnecting(self,connector):
        print 'Started to connect.'

    def buildProtocol(self,addr):
        print 'Connected.'
        return BittorrentProtocol(self.torrent_info)

    def clientConnectionLost(self,connector,reason):
        print 'Lost connection. Reason: ', reason
        #reconnect?
        
    def clientConnectionFailed(self,connector,reason):
        print 'Connection failed. Reason: ', reason

def set_up_file(torrent_info):
    number_pieces = len(torrent_info.pieces_array)
    print 'number of pieces for torrent: ' + str(number_pieces)
    print 'piece length: ' + str(torrent_info.piece_length)
    piece_list = []
    for piece in range(number_pieces):
        piece_list.append(MyPiece(torrent_info.piece_length))
    #print 'piece list: ' + repr(piece_list)
    print 'object created'
    return piece_list

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

def get_peers(metainfo):
    '''Input: metainfo file (.torrent file)
       Output: a list of peer_ids (strings) returned from the tracker
       Calls methods to send an http request to the tracker, parse the returned
       result message and return a list of peer_ids
    '''
    torrentObj = Torrent(metainfo)
    #print "torrent peer hash: " + repr(torrentObj.pieces_array)
    #print 'length of peer hash: ' + str(len(torrentObj.pieces_array))
    r = requests.get(torrentObj.announce_url, params=torrentObj.param_dict)
    peers = parse_response_from_tracker(r)
    return peers, torrentObj

def handshake(torrentObj):
    '''Input: ip:port of a peer with the torrent files of interest
       Output: <fill this in>
       <fill this in>
    '''
    info_hash = torrentObj.info_hash
    peer_id = torrentObj.peer_id
    handshake = Handshake(info_hash, peer_id)
    '''
    hostname = socket.gethostname()
    s_send = socket.socket()
    hostandport = peer.split(':')
    s_send.connect((hostandport[0],int(hostandport[1])),)
    s_send.sendall(str(handshake))
    response = s_send.recv(2000)
    response2 = s_send.recv(2000)
    print 'response 2: '+repr(response2)
    return response+response2
    '''
    return handshake

def main(torrentFile):
    f = open(torrentFile, 'r')
    metainfo = bencode.bdecode(f.read())
    f.close()
    peers, torrent_obj = get_peers(metainfo)

    print peers
    peer = peers[1]
    #print peer
    hostandport = peer.split(':')
    #other = decode_handshake(response, torrentObj)
    bittorrent_factory = BittorrentFactory(torrent_obj)

    reactor.connectTCP(hostandport[0], int(hostandport[1]),bittorrent_factory)
    reactor.run()

if __name__ == "__main__":
    main(sys.argv[1])


