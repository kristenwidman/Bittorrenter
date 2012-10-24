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
from pieces import *
from bitstring import BitArray
#from sys import stdout

max_requests = 15
request_length = 2**14

class BittorrentProtocol(Protocol):
    def __init__(self,torrent_info):
        #super(BittorrentProtocol, self).__init__()
        #Protocol.__init__(self)
        self.torrent_info = torrent_info
        self.peer_has_pieces = BitArray(len(torrent_info.pieces_array)) 
        self.pending_requests = 0
        self.message_buffer = bytearray()
        self.interested = False
        self.peer_interested = False
        self.choked = True
        self.peer_choked = True
        self.active_torrent = ActiveTorrent(torrent_info)

    def connectionMade(self):
        handshake_msg = repr(handshake(self.torrent_info))
        self.transport.write(handshake_msg)          
        #self.transport.loseConnection()

    def dataReceived(self,data):
        messages_to_send = self.deal_with_message(data)
        for message in messages_to_send:
            self.transport.write(message)

    def deal_with_message(self,data):
        messages_to_send_list = []
        if self.message_buffer:
            self.message_buffer.extend(bytearray(data))
            #print "message buffer had info. it is now: " + repr(self.message_buffer)
        else:
            self.message_buffer = bytearray(data)
            #print "message buffer was empty.  it is now: " + repr(self.message_buffer)
        if self.message_buffer[1:20].lower() == "BitTorrent Protocol".lower():
            print "handshake received"
            self.message_buffer = self.decode_handshake(self.message_buffer, self.torrent_info)
            messages_to_send_list.append(repr(Interested()))
            self.interested = True
            #perhaps have error handling for if handshake is cut short
        if len(self.message_buffer) >= 4:
            message_length = bytes_to_number(self.message_buffer[0:4]) + 4
            #print "length of message expected: " + repr(message_length)
            #print "length of message in buffer: " + repr(len(self.message_buffer))
            if len(self.message_buffer) < message_length:    #debugging line
                print "message shorter than expected"        #debugging line
            while len(self.message_buffer) >= message_length:
                self.message_buffer, messages_to_send_list = self.parse_messages(messages_to_send_list)
                #print "message_buffer is now: " + repr(self.message_buffer) 
        return messages_to_send_list

    def get_next_request(self):
        #get next request
        for i in range(len(self.have_blocks)): #should jump by request_length rather than every one
            if self.peer_has_pieces[active_torrent.piece_number] & active_torrent.have_blocks[i]==0 & active_torrent.requested_blocks[i]==0:
                print 'peer has piece ' + str(active_torrent.piece_number) + ' and I do not have and have not requested block ' + str(i)
                if self.pending_requests <= max_requests:
                    print 'creating a request object'
                    request = Request(index=active_torrent.piece_number, begin=i, length=request_length)
                    print 'request object created: ' + repr(request)
                    return repr(request)
        #pass  #use self.peer_has_pieces and self.torrent_info

    def parse_messages(self, messages_to_send_list):
        message_obj, message = parse_message_from_response(self.message_buffer)
        print 'message type: ' + repr(type(message_obj))
        if isinstance(message_obj, Choke):
            self.choked = True
        if isinstance(message_obj, Unchoke):
            self.choked = False
            if self.interested:
                #messages_to_send_list.append(self.get_next_request()
                pass
        if isinstance(message_obj, Interested):
            self.peer_interested = True
        if isinstance(message_obj, NotInterested):
            self.peer_interested = False
        if isinstance(message_obj, Have):
            piece_index = message_obj.index
            print 'piece index: ' + repr(piece_index)
            piece_index = bytes_to_number(piece_index)
            self.peer_has_pieces[piece_index] = 1
            print 'bitarray after have: ' + repr(self.peer_has_pieces.bin)
            print 'bitarray of index 2: ' + repr(self.peer_has_pieces[2]) + ' ' + repr(self.peer_has_pieces[1]) + ' ' + repr(self.peer_has_pieces[3]) + ' ' + repr(self.peer_has_pieces[4])
            #request = self.get_next_request() #will need bitarray and torrent_info
        if isinstance(message_obj, Bitfield):
            bitarray = BitArray(bytes=message_obj.bitfield)
            self.peer_has_pieces = bitarray[:len(self.peer_has_pieces)]
            print 'self.peer_has_pieces: ' + repr(self.peer_has_pieces)
#send request
        if isinstance(message_obj, Request):
            #if !self.peer_choked && self.peer_interested:
                #send piece
            pass
        if isinstance(message_obj, Piece):
            print 'piece'    # do something with this
#send request
        if isinstance(message_obj, Cancel):
            print 'cancel'
        if isinstance(message_obj, Port):
            print 'port'
            #parse port and switch connection to that port
        return message, messages_to_send_list


    def decode_handshake(self, response, torrentObj):
        handshake = Handshake(response)
        other = response[68:]
        expected_peer_id = torrentObj.peer_id
        expected_info_hash = torrentObj.info_hash
        if (expected_info_hash != handshake.info_hash):
            #instead of throwing exception, we should send a cancel message
            raise Exception('info_hash does not match expected. Info hash expected: ' +
                            repr(expected_info_hash) + '. Info hash found: ' + repr(handshake.info_hash))
        return other

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
    peer = peers[0]
    #print peer
    hostandport = peer.split(':')
    #other = decode_handshake(response, torrentObj)
    bittorrent_factory = BittorrentFactory(torrent_obj)

    reactor.connectTCP(hostandport[0], int(hostandport[1]),bittorrent_factory)
    reactor.run()

if __name__ == "__main__":
    main(sys.argv[1])


