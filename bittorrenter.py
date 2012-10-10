#!usr/bin/env python

#kristen widman
#Oct 8, 2012

import sys
import socket
import bencode
import hashlib
import requests
import urllib
from TorrentClass import Torrent

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

def handshake(peer,torrentObj):
    '''Input: ip:port of a peer with the torrent files of interest
       Output: <fill this in>
       <fill this in>
    '''
    pstrlen = chr(19)
    pstr = "BitTorrent protocol"
    reserved = '\x00\x00\x00\x00\x00\x00\x00\x00' 
    info_hash = torrentObj.info_hash 
    peer_id = torrentObj.peer_id
    handshake = pstrlen+pstr+reserved+info_hash+peer_id
    print repr(handshake)
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
    print repr(response)
    response2 = s_send.recv(2000)
    print repr(response2)
    for i in range(10):
	r3 = s_send.recv(1000)
	print repr(response3)
    #s_listen.accept()   # read about 'accept' - does s2 need to be set up first? or will it assign to random port?
    #print 'a'
    #response = s_listen.recv(200)
    #print response
    #setup_socket_listening(torrentObj.port)

def main(torrentFile):
    f = open(torrentFile, 'r')
    metainfo = bencode.bdecode(f.read())
    f.close()
    #f2 = open('/Users/kristenwidman/Documents/Programs/Bittorrenter/metainfo.txt','w')
    #f2.write(str(metainfo))
    peers, torrentObj = get_peers(metainfo)
    #print peers
    peer = peers[3]
    #print peer
    handshake(peer, torrentObj)
    #f2.close()

if __name__ == "__main__":
    main(sys.argv[1])


