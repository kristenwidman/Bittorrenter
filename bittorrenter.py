#!usr/bin/env python 
#kristen widman
#Oct 8, 2012

from struct import *
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from messages import *
from bitstring import BitArray

MAX_REQUESTS = 15
REQUEST_LENGTH = 2**14

class BittorrentProtocol(Protocol):
    def __init__(self, factory):
        self.factory = factory 
        self.peer_has_pieces = BitArray(len(self.factory.active_torrent.torrent_info.pieces_array)) 
        self.pending_requests = 0
        self.message_buffer = bytearray()
        self.interested = False
        self.peer_interested = False
        self.choked = True
        self.peer_choked = True

    def handshake(self, torrent_obj):
        '''Input: ip:port of a peer with the torrent files of interest
           Output: <fill this in>
           <fill this in>
        '''
        info_hash = torrent_obj.info_hash
        peer_id = torrent_obj.peer_id
        handshake = Handshake(info_hash, peer_id)
        return handshake
    
    def connectionMade(self):
        handshake_msg = str(self.handshake(self.factory.active_torrent.torrent_info))
        self.transport.write(handshake_msg)          

    def dataReceived(self,data):
        messages_to_send = self.deal_with_message(data)
        if messages_to_send:
            for message in messages_to_send:
                if message is not None:
                    print 'message to be sent: ' + repr(message)
                    self.transport.write(str(message))
    
    def deal_with_message(self,data):
        messages_to_send_list = []
        messages_add = []
        if self.message_buffer:
            self.message_buffer.extend(bytearray(data))
        else:
            self.message_buffer = bytearray(data)
        if self.message_buffer[1:20].lower() == "BitTorrent Protocol".lower():
            print "handshake received"
            self.message_buffer = self.decode_handshake(self.message_buffer, self.factory.active_torrent.torrent_info)
            messages_to_send_list.append(Interested())
            self.interested = True
            #perhaps have error handling for if handshake is cut short
        if len(self.message_buffer) >= 4:
            message_length = bytes_to_number(self.message_buffer[0:4]) + 4
            while len(self.message_buffer) >= message_length:
                self.message_buffer, messages_add = self.parse_messages(messages_to_send_list)
                message_length = bytes_to_number(self.message_buffer[0:4])+4
        if messages_add:
            messages_to_send_list.extend(messages_add)
        return messages_to_send_list

    def get_next_request(self):
        if self.interested == True and self.choked == False:
            for i in range(len(self.factory.active_torrent.have_blocks)): 
                blocks_per_piece = self.factory.active_torrent.torrent_info.piece_length / REQUEST_LENGTH#=
                piece_num = i / blocks_per_piece
                if (self.peer_has_pieces[piece_num] and 
                        self.factory.active_torrent.have_blocks[i]==0 and 
                        self.factory.active_torrent.requested_blocks[i]==0):
                    if self.pending_requests <= MAX_REQUESTS:
                        index_pack = pack('!l',piece_num)
                        b = i - piece_num * blocks_per_piece   
                        begin_pack = pack('!l', b)
                        length_pack = pack('!l',REQUEST_LENGTH) 
#will be smaller than REQUEST_LEN for last block - need to account for that!
                        request = Request(index=index_pack, begin=begin_pack, length=length_pack) 
                        print 'request object created: ' + repr(request)
                        self.factory.active_torrent.requested_blocks[i] = 1
                        return request

    def parse_messages(self, messages_to_send_list):
        message_obj, message = parse_message_from_response(self.message_buffer)
        print 'message type: ' + repr(type(message_obj))
        if isinstance(message_obj, Choke):
            print 'Choked'
            self.choked = True
        elif isinstance(message_obj, Unchoke):
            print 'Unchoked!'
            self.choked = False
            if self.interested:
                messages_to_send_list.append(self.get_next_request())
                pass
        elif isinstance(message_obj, Interested):
            self.peer_interested = True
        elif isinstance(message_obj, NotInterested):
            self.peer_interested = False
        elif isinstance(message_obj, Have):
            piece_index = message_obj.index
            piece_index = bytes_to_number(piece_index)
            self.peer_has_pieces[piece_index] = 1
            messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, Bitfield):
            bitarray = BitArray(bytes=message_obj.bitfield)
            self.peer_has_pieces = bitarray[:len(self.peer_has_pieces)]
#send request
        elif isinstance(message_obj, Request):
                #send piece
            pass
        elif isinstance(message_obj, Piece):
            print '\nPIECE!\n'    # do something with this
            #print 'piece is: ',str(message_obj)
#send request
        elif isinstance(message_obj, Cancel):
            print 'cancel'
        elif isinstance(message_obj, Port):
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
    #protocol = BittorrentProtocol

    def startedConnecting(self,connector):
        print 'Started to connect.'

    def __init__(self, active_torrent):
        self.protocols = []
        self.active_torrent = active_torrent

    def buildProtocol(self,addr):  #may need this again instead of protocol line at top to keep track of protocols
        print 'Connected.'
        protocol = BittorrentProtocol(self)
        self.protocols.append(protocol)
        return protocol
    
    def clientConnectionLost(self,connector,reason):
        print 'Lost connection. Reason: ', reason
        #reconnect?
        
    def clientConnectionFailed(self,connector,reason):
        print 'Connection failed. Reason: ', reason
