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
        self.message_buffer = bytearray()
        self.pending_requests = 0
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
            self.message_buffer = self.decode_handshake(self.factory.active_torrent.torrent_info)
            messages_to_send_list.append(Interested())
            self.interested = True
            #perhaps have error handling for if handshake is cut short
        if len(self.message_buffer) >= 4:
            message_length = bytes_to_number(self.message_buffer[0:4]) + 4
            while len(self.message_buffer) >= message_length:
                messages_add = self.parse_messages(messages_to_send_list)
                message_length = bytes_to_number(self.message_buffer[0:4])+4
        if messages_add: messages_to_send_list.extend(messages_add)
        return messages_to_send_list

    def get_next_request(self):
        for i in range(len(self.factory.active_torrent.have_blocks)): 
            blocks_per_piece = self.factory.active_torrent.torrent_info.piece_length / REQUEST_LENGTH
            piece_num = i / blocks_per_piece
            if (self.peer_has_pieces[piece_num] and 
                    self.factory.active_torrent.have_blocks[i]==0 and 
                    self.factory.active_torrent.requested_blocks[i]==0):
#need checking (elsewhere) for pending requests that have expired and set back to 0
                self.factory.active_torrent.requested_blocks[i] = 1
                if self.pending_requests <= MAX_REQUESTS:
                    index_pack = pack('!l',piece_num)
                    begin_index = (i - piece_num) * blocks_per_piece   
                    begin_pack = pack('!l', begin_index)
                    length_pack = pack('!l',REQUEST_LENGTH) 
                    print 'generating request for piece: ' + str(piece_num)+' and block: ' + str(begin_index)
#will be smaller than REQUEST_LEN for last block - need to account for that!
                    request = Request(index=index_pack, begin=begin_pack, length=length_pack) 
                    print 'request object created: ' + repr(request)
                    return request

    def parse_messages(self, messages_to_send_list):
        message_obj = self.parse_message_from_response()
        print 'message type: ' + repr(type(message_obj))
        if isinstance(message_obj, Choke):
            print 'Choked'
            self.choked = True
        elif isinstance(message_obj, Unchoke):
            print 'Unchoked!'
            self.choked = False
            if self.interested == True and self.choked == False:
                messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, Interested):
            self.peer_interested = True
        elif isinstance(message_obj, NotInterested):
            self.peer_interested = False
        elif isinstance(message_obj, Have):
            piece_index = message_obj.index
            piece_index = bytes_to_number(piece_index)
            self.peer_has_pieces[piece_index] = 1
            if self.interested == True and self.choked == False:
                messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, Bitfield):
            bitarray = BitArray(bytes=message_obj.bitfield)
            self.peer_has_pieces = bitarray[:len(self.peer_has_pieces)]
            if self.interested == True and self.choked == False:
                messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, Request):
            pass  #send piece
        elif isinstance(message_obj, Piece):
            print '\nPIECE!\n'    # do something with this
            #print 'piece is: ' + repr(message_obj)
            print 'piece #: ' + repr(message_obj.index)
            print 'block # within piece: ' + repr(message_obj.begin)
            print 'piece block, first 100 bytes: ' + str(message_obj.block[0:100])
            #block_number = 
            #self.factory.active_torrent.have_blocks[] = 1
            
            #if self.interested == True and self.choked == False:
                #messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, Cancel):
            print 'cancel'
        elif isinstance(message_obj, Port):
            print 'port'
            #parse port and switch connection to that port
        return messages_to_send_list


    def decode_handshake(self, torrent_obj):
        handshake = Handshake(self.message_buffer)
        other = self.message_buffer[68:]
        expected_peer_id = torrent_obj.peer_id
        expected_info_hash = torrent_obj.info_hash
        if (expected_info_hash != handshake.info_hash):
            #instead of throwing exception, we should send a cancel message
            raise Exception('info_hash does not match expected. Info hash expected: ' +
                            repr(expected_info_hash) + '. Info hash found: ' + repr(handshake.info_hash))
        return other

    def parse_message_from_response(self):
        if len(self.message_buffer) < 4:  #don't have full message
            return None
        length = bytes_to_number(self.message_buffer[0:4]) + 4  #length indicated by the first 4 bytes + 4 for those first 4 bytes
        bytestring = self.message_buffer[:length]
        if len(self.message_buffer) < length:   #don't have full message, so send back and wait to be combined with rest of message
            return None
        elif self.message_buffer[0:4] == '\x00\x00\x00\x00':  #no msg_id
            message_obj = KeepAlive(response=bytestring)
        else:
            result = {
              0: lambda: Choke(response=bytestring),
              1: lambda: Unchoke(response=bytestring),
              2: lambda: Interested(response=bytestring),
              3: lambda: NotInterested(response=bytestring),
              4: lambda: Have(response=bytestring),
              5: lambda: Bitfield(response=bytestring),
              6: lambda: Request(response=bytestring),
              7: lambda: Piece(response=bytestring),
              8: lambda: Cancel(response=bytestring),
              9: lambda: Port(response=bytestring),
            }[self.message_buffer[4]]()     #response[4] is the msg_id
            message_obj = result
            #print repr(message_obj)
        self.message_buffer = self.message_buffer[length:]
        return message_obj

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
