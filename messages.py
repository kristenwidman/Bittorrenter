#!usr/bin/env python

#kristen widman
#Oct 15, 2012


def number_to_bytes(blength):  #determine_length(blength):
    if blength < 255:
	length = '\x00\x00\x00' + chr(blength)
    elif blength < 256**2:
	length = '\x00\x00' + chr((blength)/256) + chr((blength) % 256)
    elif blength < 256**3:
	length = ('\x00'+ chr((blength)/256**2) + chr(((blength) % 256**2) / 256) +
		    chr(((blength) % 256**2) % 256))
    else:
	length = (chr((blength)/256**3) + chr(((blength)%256**3)/256**2) + chr((((blength)%256**3)%256**2)/256) + chr((((blength)%256**3)%256**2)%256))
    return length

def bytes_to_number(bytestring):  #assumed to be 4 bytes long
    number = 0
    i = 3
    for byte in bytestring:
	number += ord(byte) * 256**i
	i -= 1

class Handshake(object):
    def __init__(self,*args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 5: self.__setup2(*args)

    def __setup1(self,payload):
	self.pstrlen = payload[0]
	self.pstr = payload[1:20]  #may not always be 19
	self.reserved = payload[20:28]
	self.info_hash = payload[28:48]
	self.peer_id = payload[48:68]

    def __setup2(self,pstrlen,pstr,reserved,info_hash,peer_id):
	self.pstrlen = pstrlen
	self.pstr = pstr
	self.reserved = reserved
	self.info_hash = info_hash
	self.peer_id = peer_id

    def __repr__(self):
	return repr(self.pstrlen+self.pstr+self.reserved+self.info_hash+self.peer_id)

    def __len__(self):
	return 49+ord(self.pstrlen)

class Message(object):
    def __init__(self,*args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) > 1: self.__setup2(*args)
    
    def __setup1(self,payload):
	self.length = payload[0:4]
	if len(payload) > 4:
	    self.msg_id = payload[4]
    
    def __setup2(self,length,msg_id):
	self.length = length
	self.msg_id = msg_id

    def __repr__(self):
	return self.length + self.msg_id

    def __len__(self):
	return bytes_to_number(self.length) + 4

class Have(Message):
    def __init__(self,**kwargs):
	self.length = '\x00\x00\x00\x05'  #or '5'
	self.index = '\x00\x00\x00\x04'   #or '4'
	if index in kwargs:
	    self.byte_index = number_to_bytes(index) 
	elif response in kwargs:
	    self.byte_index = response[5:9]
    def __repr__(self):
	return repr(self.length + self.msg_id + self.byte_index)

    @property
    def index(self):
	return bytes_to_number(self.byte_index)

'''
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 3: self.__setup2(*args)
    
    def __setup1(self,payload):
	Message.__init__(self,payload)
	self.byte_index = payload[5:9]   #maybe this should not go to end -- should it only go to length of payload in case of overlappying messages?

    def __setup2(self, length, msg_id, byte_index):
	Message.__init__(self,length,msg_id)
	self.byte_index = byte_index
'''

class Bitfield(Message):
    def __init__(self, *args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 3: self.__setup2(*args)
	
    def __setup1(self, payload):
	Message.__init__(self,payload)
	self.bitfield = payload[5:]
    
    def __setup2(self, length, msg_id, bitfield):
	Message.__init__(self,length,msg_id)
	self.bitfield = bitfield

    def __repr__(self):
	return repr(self.length + self.msg_id + self.bitfield) 


class Request(Message):
    def __init__(self,*args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 5: self.__setup2(*args)

    def __setup1(self, payload):
	Message.__init__(self,payload)
	self.index = payload[5:9]
	self.begin = payload[9:13]
	self.msg_length = payload[13:]

    def __setup2(self, length, msg_id, index, begin, msg_length):
	Message.__init__(self,length,msg_id)
	self.index = index
	self.begin = begin
	self.msg_length = msg_length

    def __repr__(self):
	return repr(self.length + self.msg_id + self.index + self.begin + self.msg_length)

class Piece(Message):
    def __init__(self, *args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 5: self.__setup2(*args)

    def __setup1(self, payload):
	Message.__init__(self,payload)
	self.index = payload[5:9]
	self.begin = payload[9:13]
	self.block = payload[13:]

    def __setup2(self, length, msg_id, index, begin, block):
	Message.__init__(self,length, msg_id)
	self.index = index
	self.begin = begin
	self.block = block

    def __repr__(self):
	return repr(self.length + self.msg_id + self.index + self.begin + self.block)

class Cancel(Message):   
    def __init__(self,*args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 5: self.__setup2(*args)

    def __setup1(self, payload):
	Message.__init__(self,payload)
	self.index = payload[5:9]
	self.begin = payload[9:13]	
	self.msg_length = payload[13:]

    def __setup2(self, length, msg_id, index, begin, msg_length):
	Message.__init__(self,length,msg_id)
	self.index = index
	self.begin = begin
	self.msg_length = msg_length

    def __repr__(self):
	return repr(self.length + self.msg_id + self.index + self.begin + self.msg_length)

class Port(Message):
    def __init__(self, *args):
	if len(args) == 1: self.__setup1(*args)
	elif len(args) == 3: self.__setup2(*args)

    def __setup1(self,payload):
	Message.__init__(self,payload)
	self.port = payload[5:]

    def __setup2(self, length, msg_id, port):
	Message.__init__(self,length,msg_id)
	self.port = port

    def __repr__(self):
	return repr(self.length + self.msg_id + self.port)

