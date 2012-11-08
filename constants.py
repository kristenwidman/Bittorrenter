#!/usr/bin/env python

#constants file for bittorrent client

NUMBER_PEERS = 15
REQUEST_LENGTH = 2**14
PENDING_TIMEOUT = 15    #number seconds til pending request is considered too old and a new request is made
MAX_REQUESTS = 20
KEEP_ALIVE_TIMEOUT = 110  #in seconds
