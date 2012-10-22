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
from torrent import Torrent
from messages import *
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from sys import stdout

class BittorrentProtocol(Protocol):
    def __init__(self,torrent_info):
        #super(BittorrentProtocol, self).__init__()
        #Protocol.__init__(self)
        self.torrent_info = torrent_info
        self.message_buffer = ''

    def connectionMade(self):
        handshake_msg = repr(handshake(self.torrent_info))
        self.transport.write(handshake_msg)          
        #self.transport.loseConnection()

    def dataReceived(self,data):
        if self.message_buffer:
            self.message_buffer += data
            print "message buffer had info. it is now: " + repr(self.message_buffer)
        else:
            self.message_buffer = data
            print "message buffer was empty.  it is now: " + repr(self.message_buffer)
        #have global variable buffer for data received and add to it each time we receive data?
        #then parse until buffer is empty or is not as long as its intended length in first 4 bytes
        if self.message_buffer[1:20].lower() == "BitTorrent Protocol".lower():
            print "handshake received"
            self.message_buffer = decode_handshake(self.message_buffer, self.torrent_info)
            self.transport.write(repr(Interested()))
            #perhaps have error handling for if handshake is cut short
        if len(self.message_buffer) >= 4:
            message_length = bytes_to_number(self.message_buffer[0:4]) + 4
            print "length of message expected: " + repr(message_length)
            print "length of message in buffer: " + repr(len(self.message_buffer))
            if len(self.message_buffer) < message_length:    #debugging line
                print "message shorter than expected"        #debugging line
            while len(self.message_buffer) >= message_length:
                #self.message_buffer = parse_messages(self.message_buffer)
                #print "message_buffer is now: " + repr(self.message_buffer) 
                message_obj, message = parse_message_from_response(self.message_buffer)
                #print type(message_obj)
                if isinstance(message_obj, Choke):
                    print 'choke' 
                    #set some field to false; don't request pieced
                if isinstance(message_obj, Unchoke):
                    print 'unchoke'  # set some field to be able to request pieces
                if isinstance(message_obj, Interested):
                    print 'interested' 
                if isinstance(message_obj, NotInterested):
                    print 'not interested'
                if isinstance(message_obj, Have):
                    print 'have!'
                if isinstance(message_obj, Bitfield):
                    print 'bitfield!'    #what to do with bitfield and/or haves?  create a representaion of what the peer has?
                if isinstance(message_obj, Request):
                    print 'request'
                if isinstance(message_obj, Piece):
                    print 'piece'    # do something with this
                if isinstance(message_obj, Cancel):
                    print 'cancel'
                if isinstance(message_obj, Port):
                    print 'port'
                    #parse port and switch connection to that port
                #return message
        
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

def parse_messages(message):    #pass in peer file representation and my file representation; need a way to send port back 
    message_obj, message = parse_message_from_response(message)
    #print type(message_obj)
    if isinstance(message_obj, Choke):
        print 'choke' 
        #set some field to false; don't request pieced
    if isinstance(message_obj, Unchoke):
        print 'unchoke'  # set some field to be able to request pieces
    if isinstance(message_obj, Interested):
        print 'interested' 
    if isinstance(message_obj, NotInterested):
        print 'not interested'
    if isinstance(message_obj, Have):
        print 'have!'
    if isinstance(message_obj, Bitfield):
        print 'bitfield!'    #what to do with bitfield and/or haves?  create a representaion of what the peer has?
    if isinstance(message_obj, Request):
        print 'request'
    if isinstance(message_obj, Piece):
        print 'piece'    # do something with this
    if isinstance(message_obj, Cancel):
        print 'cancel'
    if isinstance(message_obj, Port):
        print 'port'
        #parse port and switch connection to that port
    return message

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
    r = requests.get(torrentObj.announce_url, params=torrentObj.param_dict)
    peers = parse_response_from_tracker(r)
    return peers, torrentObj

def decode_handshake(response, torrentObj):
    handshake = Handshake(response)
    other = response[68:]
    expected_peer_id = torrentObj.peer_id
    expected_info_hash = torrentObj.info_hash
    if (expected_info_hash != handshake.info_hash):
	raise Exception('info_hash does not match expected.  Info hash expected: ' +  #instead of throwing exception, we should send a cancel message
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
    pstr = 'BitTorrent protocol'
    pstrlen = chr(19)
    reserved = '\x00\x00\x00\x00\x00\x00\x00\x00'
    #handshake = pstrlen+pstr+reserved+info_hash+peer_id
    print 'handshake sent: '+ repr(repr(handshake))
    hostname = socket.gethostname()
    s_send = socket.socket()
    hostandport = peer.split(':')
    s_send.connect((hostandport[0],int(hostandport[1])),)
    s_send.sendall(str(handshake))
    print "sent handshake to " + hostandport[0]+':'+hostandport[1]    
    response = s_send.recv(2000)
    print 'response: '+repr(response)
    response2 = s_send.recv(2000)
    print 'response 2: '+repr(response2)
    return response+response2
    '''
    return handshake

def decode_messages_in_loop(response):
    print 'other: ' + repr(response)
    message, response = determine_msg_type(response)
    print "other message type: " + repr(message.__class__.__name__) 
    print "any extra after other: "+ repr(response)
    print "message: " + repr(message) 


def main(torrentFile):
    f = open(torrentFile, 'r')
    metainfo = bencode.bdecode(f.read())
    f.close()
    peers, torrent_obj = get_peers(metainfo)

    print peers
    peer = peers[2]
    #print peer
    hostandport = peer.split(':')
    #other = decode_handshake(response, torrentObj)
    #decode_messages_in_loop(other)  #also need to add further responses received from peer
    bittorrent_factory = BittorrentFactory(torrent_obj)

    reactor.connectTCP(hostandport[0], int(hostandport[1]),bittorrent_factory)
    reactor.run()

if __name__ == "__main__":
    main(sys.argv[1])


