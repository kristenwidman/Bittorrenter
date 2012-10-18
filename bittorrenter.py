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
from protocol import *
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from sys import stdout

class BittorrentProtocol(Protocol):
    def dataReceived(self,data):
        stdout.write(data)
        #parse data
        #if certain type of data, do something
        

class BittorrentFactory(ClientFactory):
    def startedConnecting(self,connector):
        print 'Started to connect.'

    def buildProtocol(self,addr):
        print 'Connected.'
        return BittorrentProtocol()
        #handshake

    def clientConnectionLost(self,connector,reason):
        print 'Lost connection. Reason: ', reason
        #reconnect?
        
    def clientConnectionFailed(self,connector,reason):
        print 'Connection failed. Reason: ', reason

reactor.connectTCP('www.google.com',80,EchoClientFactory())
reactor.run()



def deal_with_incoming_message(msg):
    msg_type = determine_msg_type(msg)
    if msg_type == "bitfield":
	bitf_obj = bitfield(msg)
	#do something with this abject
    elif msg_type == "piece":
	piece_obj = piece(msg)
	#store this piece info somewhere and gradually build up obj


    elif msg_type == "port":
	port_obj = port(msg)
	#change the port we are sending to; implement when dealing with incoming requests 
    elif msg_type == "request":
	request_obj = request(msg)
	#do something with this when dealing with incoming requests
    elif msg_type == "cancel":
	cancel_obj = cancel(msg)
	#do something with this when dealing with incoming requests

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
    #print peers
    #print [str(ord(x))+x for x in peers]
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
    #print 'r.content: '+r.content
    #print 'r.text: '+r.text
    peers = parse_response_from_tracker(r)
    return peers, torrentObj

def decode_handshake(response, torrentObj):
    handshake = Handshake(response)
    print 'handshake received: ' + repr(repr(handshake))
    #print 'protocol name length: ' + ord(handshake.pstrlen)
    #print 'protocol: ' + handshake.pstr
    #print 'reserved: ' + repr(handshake.reserved)
    #print 'reserved: ' + "".join("%02x" % ord(c) for c in handshake.reserved)
    #print 'info_hash from handshake: '+ repr(handshake.info_hash)
    #print 'peer_id: '+repr(handshake.peer_id)
    
    other = response[68:]
    expected_peer_id = torrentObj.peer_id
    expected_info_hash = torrentObj.info_hash
    if (expected_info_hash != handshake.info_hash):
	raise Exception('info_hash does not match expected.  Info hash expected: ' +  #instead of throwing exception, we should send a cancel message
			repr(expected_info_hash) + '. Info hash found: ' + repr(handshake.info_hash))
#protocol indicates that we should check the peer_id too and that we should have gotten
#this from the tracker.
    return other

def handshake(peer,torrentObj):
    '''Input: ip:port of a peer with the torrent files of interest
       Output: <fill this in>
       <fill this in>
    '''
    info_hash = torrentObj.info_hash
    peer_id = torrentObj.peer_id
    handshake = Handshake(info_hash, peer_id)
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
    peers, torrentObj = get_peers(metainfo)

    print peers
    peer = peers[3]
    #print peer
    response = handshake(peer, torrentObj)
    other = decode_handshake(response, torrentObj)
    decode_messages_in_loop(other)  #also need to add further responses received from peer

if __name__ == "__main__":
    main(sys.argv[1])


