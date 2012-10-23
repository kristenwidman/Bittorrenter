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
import bitstring
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from torrent import Torrent
from messages import *
#from sys import stdout
from pieces import *

max_requests = 15

class BittorrentProtocol(Protocol):
    def __init__(self,torrent_info):
        #super(BittorrentProtocol, self).__init__()
        #Protocol.__init__(self)
        self.torrent_info = torrent_info
        self.message_buffer = bytearray()
        self.interested = False
        self.peer_interested = False
        self.choked = True
        self.peer_choked = True
        self.peer_bitarray = bitstring.BitArray(len(torrent_info.pieces_array))
        self.pending_requests = 0
        self.file_downloaded = set_up_file(self.torrent_info)

    def connectionMade(self):
        handshake_msg = repr(handshake(self.torrent_info))
        self.transport.write(handshake_msg)          
        #self.transport.loseConnection()

    def dataReceived(self,data):
        if self.message_buffer:
            self.message_buffer.extend(bytearray(data))
            #print "message buffer had info. it is now: " + repr(self.message_buffer)
        else:
            self.message_buffer = bytearray(data)
            #print "message buffer was empty.  it is now: " + repr(self.message_buffer)
        #have global variable buffer for data received and add to it each time we receive data?
        #then parse until buffer is empty or is not as long as its intended length in first 4 bytes
        if self.message_buffer[1:20].lower() == "BitTorrent Protocol".lower():
            print "handshake received"
            self.message_buffer = decode_handshake(self.message_buffer, self.torrent_info)
            self.transport.write(repr(Interested()))
            self.interested = True
            #perhaps have error handling for if handshake is cut short
        if len(self.message_buffer) >= 4:
            message_length = bytes_to_number(self.message_buffer[0:4]) + 4
            #print "length of message expected: " + repr(message_length)
            #print "length of message in buffer: " + repr(len(self.message_buffer))
            if len(self.message_buffer) < message_length:    #debugging line
                print "message shorter than expected"        #debugging line
            while len(self.message_buffer) >= message_length:
                #self.message_buffer = parse_messages(self.message_buffer)
                #print "message_buffer is now: " + repr(self.message_buffer) 
                message_obj, message = parse_message_from_response(self.message_buffer)
                #print type(message_obj)
                if isinstance(message_obj, Choke):
                    print 'choke' 
                    self.choked = True
                if isinstance(message_obj, Unchoke):
                    print 'unchoke'  # set some field to be able to request pieces
                    self.choked = False
                    if self.interested:
                        #send interested
                        pass
                if isinstance(message_obj, Interested):
                    print 'interested' 
                    self.peer_interested = True
                if isinstance(message_obj, NotInterested):
                    print 'not interested'
                    self.peer_interested = False
                if isinstance(message_obj, Have):
                    print 'have!'
                    piece_index = message_obj.index
                    print 'piece index: ' + piece_index
                    piece_index = bytes_to_number(piece_index)
                    self.peer_bitarray[piece_index] = 1
                    print 'bitarray after have: ' + repr(self.peer_bitarray)
                    request = get_next_request(self.peer_bitarray, self.torrent_info)
                if isinstance(message_obj, Bitfield):
                    print 'bitfield!'    #what to do with bitfield and/or haves?  create a representaion of what the peer has?
                    #print 'self.peer_bitarray: '+ repr(self.peer_bitarray)
                    #print 'bitfield:          ' + repr(message_obj.bitfield)
                    bitarray = bitstring.BitArray(bytes=message_obj.bitfield)
                    #print 'bitarray:           ' + repr(bitarray)
                    self.peer_bitarray = bitarray[:len(self.peer_bitarray)]
                    print 'self.peer_bitarray: ' + repr(self.peer_bitarray)
#send request
                if isinstance(message_obj, Request):
                    print 'request'
                    #if !self.peer_choked && self.peer_interested:
                        #send piece
                        #pass
                if isinstance(message_obj, Piece):
                    print 'piece'    # do something with this
#send request
                if isinstance(message_obj, Cancel):
                    print 'cancel'
                if isinstance(message_obj, Port):
                    print 'port'
                    #parse port and switch connection to that port
                return message
        
        #parse bitfield
        #send request?

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
        piece_list.append(Piece(torrent_info.piece_length))
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

def decode_handshake(response, torrentObj):
    handshake = Handshake(response)
    other = response[68:]
    expected_peer_id = torrentObj.peer_id
    expected_info_hash = torrentObj.info_hash
    if (expected_info_hash != handshake.info_hash):
    #instead of throwing exception, we should send a cancel message
	raise Exception('info_hash does not match expected.  Info hash expected: ' +  
                    repr(expected_info_hash) + '. Info hash found: ' + repr(handshake.info_hash))
    return other

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
    peer = peers[6]
    #print peer
    hostandport = peer.split(':')
    #other = decode_handshake(response, torrentObj)
    bittorrent_factory = BittorrentFactory(torrent_obj)

    reactor.connectTCP(hostandport[0], int(hostandport[1]),bittorrent_factory)
    reactor.run()

if __name__ == "__main__":
    main(sys.argv[1])


