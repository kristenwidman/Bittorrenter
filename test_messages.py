#!usr/bin/env python

#kristen widman
#Oct 17, 2012

from messages import *

if __name__ == '__main__':
    btn = (257 == bytes_to_number('\x00\x00\x01\x01'))
    print 'bytes_to_number test: ' + str(btn)
#keep adlive tests
    kamessage, response = parse_message_from_response('\x00\x00\x00\x00trainling')
    #print "\nKeepAlive Tests: From response string, message type is " + str(kamessage.__class__.__name__)  #message.kind
    #print "message: " +str(kamessage) + ", left-over: " +  response
    ka = KeepAlive()
    #print "From declaring object, message type is " + str(ka.__class__.__name__)
    #print "message: " + str(ka)
    ka_type = kamessage.__class__.__name__ == 'KeepAlive'
    kamessage_tf = kamessage == '\x00\x00\x00\x00'
    karesponse_tf = response == 'trainling'
    ka_obj_type = ka.__class__.__name__ == "KeepAlive"
    ka_obj_message = str(ka) == '\x00\x00\x00\x00'
    print '\nKeepAlive Tests: \n'+str(ka_type)+'\n'+str(kamessage_tf)+'\n'+str(karesponse_tf)+'\n'+str(ka_obj_type)+'\n'+str(ka_obj_message) 

    cmessage, cresponse = parse_message_from_response('\x00\x00\x00\x01\x00trainling')
    print '\nChoke tests: from response string, message type is ' + str(cmessage.__class__.__name__)
    print "message: " +str(cmessage) + ", left-over: " +  cresponse
    choke = Choke() 
    print "From declaring object, message type is " + str(choke.__class__.__name__)
    print "message: " + str(choke)

    ucmessage, ucresponse = parse_message_from_response('\x00\x00\x00\x01\x01trainling')
    print '\nUnchoke tests: from response string, message type is ' + str(ucmessage.__class__.__name__)
    print "message: " +str(ucmessage) + ", left-over: " +  ucresponse
    unchoke = Unchoke() 
    print "From declaring object, message type is " + str(unchoke.__class__.__name__)
    print "message: " + str(unchoke)

    imessage, iresponse = parse_message_from_response('\x00\x00\x00\x01\x02trainling')
    print '\nInterested tests: from response string, message type is ' + str(imessage.__class__.__name__)
    print "message: " +str(imessage) + ", left-over: " +  iresponse
    interested = Interested() 
    print "From declaring object, message type is " + str(interested.__class__.__name__)
    print "message: " + str(interested)

    nimessage, niresponse = parse_message_from_response('\x00\x00\x00\x01\x03trainling')
    print '\nNot Interested tests: from response string, message type is ' + str(nimessage.__class__.__name__)
    print "message: " +str(nimessage) + ", left-over: " +  niresponse
    n_interested = NotInterested() 
    print "From declaring object, message type is " + str(n_interested.__class__.__name__)
    print "message: " + str(n_interested)

    hmessage, hresponse = parse_message_from_response('\x00\x00\x00\x05\x04\x00\x00\x00\xfftrainling')
    print '\nHave tests: from response string, message type is ' + str(hmessage.__class__.__name__)
    print "message: " +str(hmessage) + ", left-over: " +  hresponse
    have = Have(index='\x00\x00\x00\xff') 
    print "From declaring object, message type is " + str(have.__class__.__name__)
    print "message: " + str(have)

    bmessage, bresponse = parse_message_from_response('\x00\x00\x00\x10\x05\x00\x00\x00\xff\x00\xff\x01\x02\x55\xef\x90\x12\x14\x11\x01trainling')
    print '\nBitfield tests: from response string, message type is ' + str(bmessage.__class__.__name__)
    print "message: " +str(bmessage) + ", left-over: " +  bresponse
    bitfield = Bitfield(bitfield='\x00\x00\x00\xff\x00\xff\x01\x02\x55\xef\x90\x12\x14\x11\x01') 
    print "From declaring object, message type is " + str(bitfield.__class__.__name__)
    print "message: " + str(bitfield)

    rmessage, rresponse = parse_message_from_response('\x00\x00\x00\x0d\x06\x00\x00\x00\xff\x00\xff\x01\x02\x00\xef\x90\x00trainling')
    print '\nRequest tests: from response string, message type is ' + str(rmessage.__class__.__name__)
    print "message: " +str(rmessage) + ", left-over: " +  rresponse
    request = Request(index='\x00\x00\x00\xff', begin='\x00\xff\x01\x02', length='\x00\xef\x90\x00') 
    print "From declaring object, message type is " + str(request.__class__.__name__)
    print "message: " + str(request)

    pmessage, presponse = parse_message_from_response('\x00\x00\x00\x15\x07\x00\x00\x01\xff\x00\x00\x01\x02\x00\xef\x90\x00\x00\x00\x03\x05\x01\x93\xab\x33trainling')
    print '\nPiece tests: from response string, message type is ' + str(pmessage.__class__.__name__)
    print "message: " +str(pmessage) + ", left-over: " +  presponse
    piece = Piece(index='\x00\x00\x01\xff', begin='\x00\x00\x01\x02', block='\x00\xef\x90\x00\x00\x00\x03\x05\x01\x93\xab\x33') 
    print "From declaring object, message type is " + str(piece.__class__.__name__)
    print "message: " + str(piece)

    camessage, caresponse = parse_message_from_response('\x00\x00\x00\x0d\x08\x00\x00\x01\xff\x00\x00\x01\x02\x00\xef\x90\x00trainling')
    print '\nCancel tests: from response string, message type is ' + str(camessage.__class__.__name__)
    print "message: " +str(camessage) + ", left-over: " +  caresponse
    cancel = Cancel(index='\x00\x00\x01\xff', begin='\x00\x00\x01\x02', length='\x00\xef\x90\x00') 
    print "From declaring object, message type is " + str(cancel.__class__.__name__)
    print "message: " + str(cancel)

    pomessage, poresponse = parse_message_from_response('\x00\x00\x00\x03\x09\x11\x01trainling')
    print '\nPort tests: from response string, message type is ' + str(pomessage.__class__.__name__)
    print "message: " +str(pomessage) + ", left-over: " +  poresponse
    port = Port(listen_port='\x11\x01') 
    print "From declaring object, message type is " + str(port.__class__.__name__)
    print "message: " + str(port)

    print
    print parse_message_from_response('\x00\x00\x00\x01\x02trailing')
    print parse_message_from_response('\x00\x00\x00\x01\x03trailing')
    print 'have', repr(parse_message_from_response('\x00\x00\x00\x05\x04\x00\x00\x00\x01trailing'))
    print 'have from args:', repr(Have(index='\x00\x00\x00\x03'))
#    print 'bitfield', parse_message_from_response('\x00\x00\x00\x03\x05\xff\x00trailing')
#    print 'request', parse_message_from_response('\x00\x00\x00\x0d\x06\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03trailing')

