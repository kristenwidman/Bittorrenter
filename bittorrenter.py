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
from TorrentClass import Torrent
from messages import *

#message types - calling these methods below will give a string message to send
def keep_alive():
    return '\x00\x00\x00\x00'

def choke():
    return '\x00\x00\x00\x01\x00'

def unchoke():
    return '\x00\x00\x00\x01\x01'

def interested():
    return '\x00\x00\x00\x01\x02'

def not_interested():
    return '\x00\x00\x00\x01\x03'

'''
def have(index):
    return '\x00\x00\x00\x05\x04'+index  #check format that 'index' comes in; should be 4 bytes?

def bitfield(bfield):
    blength = len(bfield)
    length = determine_length(blength+1)
    return length+'\x05'+bfield   #is bfield already a string or should we cast it to one?

def request(index, begin, length):
    return '\x00\x00\x01\x03\x06'+index+begin+length  #do these terms need formatting?

def piece(index, begin, block):
    blength = len(block)
    length = determine_length(blength+9)
    return length+'\x07'+index+begin+block  #do these terms need formatting?

def cancel(index,begin,length):
    return '\x00\x00\x01\x03\x08'+index+begin+length  #do these terms need formatting?

def port(listen_port):
    return '\x00\x00\x00\x03\x09'+str(listen_port)  #do these terms need formatting?
'''
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
    print 'protocol name length: ' + ord(handshake.pstrlen)
    print 'protocol: ' + handshake.pstr
    print 'reserved: ' + repr(handshake.reserved)
    #print 'reserved: ' + "".join("%02x" % ord(c) for c in handshake.reserved)
    print 'info_hash: '+ repr(handshake.info_hash)
    print 'peer_id: '+repr(hankshake.peer_id)
    
    other = response[68:]
    print 'other: ' + repr(other)
    print 'type: ' + determine_msg_type(other)
    expected_peer_id = torrentObj.peer_id
    expected_info_hash = torrentObj.info_hash
    if (expected_info_hash != peer_info_hash):
	raise Exception('info_hash does not match expected.  Info hash expected: ' +  #instead of throwing exception, we should send a cancel message
			expected_info_hash + '. Info hash found: ' + peer_info_hash)
#protocol indicates that we should check the peer_id too and that we should have gotten
#this from the tracker.


def handshake(peer,torrentObj):
    '''Input: ip:port of a peer with the torrent files of interest
       Output: <fill this in>
       <fill this in>
    '''
    pstrlen = chr(19)
    pstr = "BitTorrent protocol"
    reserved = '\x00\x00\x00\x00\x00\x00\x00\x00' 
    info_hash = torrentObj.info_hash
    print 'info_hash requested: '+repr(info_hash)
    peer_id = torrentObj.peer_id
    handshake = pstrlen+pstr+reserved+info_hash+peer_id
    print 'handshake sent: '+ repr(handshake)
    #s_listen = socket.socket()
    hostname = socket.gethostname()
    #s_listen.bind((hostname, torrentObj.port),)
    #s_listen.listen(10)   # read about buffer size 
    s_send = socket.socket()
    hostandport = peer.split(':')
    #print hostandport[0]
    #print hostandport[1]
    s_send.connect((hostandport[0],int(hostandport[1])),)
    s_send.sendall(handshake)
    print "sent handshake to " + hostandport[0]+':'+hostandport[1]    
    response = s_send.recv(2000)
    print 'response: '+repr(response)
    response2 = s_send.recv(2000)
    print 'response 2: '+repr(response2)
    decode_handshake(response+response2, torrentObj)
    

    #decode(response2)
    #for i in range(10):
	#r3 = s_send.recv(1000)
	#print repr(r3)
    #s_listen.accept()   # read about 'accept' - does s2 need to be set up first? or will it assign to random port?
    #print 'a'
    #response = s_listen.recv(200)
    #print response
    #setup_socket_listening(torrentObj.port)
    
    #s_send.send('00012')
    #response3 = s_send.recv(100)
    #print repr(response3)

def main(torrentFile):
    f = open(torrentFile, 'r')
    metainfo = bencode.bdecode(f.read())
    f.close()
    #f2 = open('/Users/kristenwidman/Documents/Programs/Bittorrenter/metainfo.txt','w')
    #f2.write(str(metainfo))
    peers, torrentObj = get_peers(metainfo)
    print peers
    peer = peers[4]
    #print peer
    handshake(peer, torrentObj)
    #f2.close()
    bitf = Bitfield('\x00\x00\x00!\x05\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff')
    #bitf2 = Bitfield('\x00\x00\x00!','\x05','\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff')
    print bitf

if __name__ == "__main__":
    main(sys.argv[1])


