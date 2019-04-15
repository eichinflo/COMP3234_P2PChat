#!/usr/bin/python3

# Student name and No.: Simon Howard 3035614018
# Student name and No.: Florian Eichin 3035524902
# Development platform: Mac OS/Linux
# Python version: 3.7.x
# Version: 0.2

# ISSUES:
# do_Quit() freezes when attempting to quit POKE_THREAD
# Have nothing figured outputs why yet...

import re
from tkinter import *
import sys
import socket
import threading
import select
import time

#
# Global variables
#

UPDATE_INTERVAL = 0.3

USERNAME = None
SERVER_ADDRESS = None
SERVER_PORT = None
MY_PORT = None
MY_SOCKET = None
MY_HASH = None
KEEPALIVE_THREAD = None
POKE_SOCKET = None
POKE_THREAD = None
CURRENT_CHATROOM = None
MEMBERS_LIST = None
FORWARD_LINK_SOCKET = None
FORWARD_LINK_THREAD = None
BACKWARD_LINKS = {}
BACKWARD_LINK_SOCKET = None
BACKWARD_LINK_THREAD = None
MSGID = 0
MESSAGE_LISTENER_THREAD = None
PEERS_MESSAGE_IDS = {}

#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address),
# and str(Port) to form a string that be the input
# to this hash function
#
def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff


#
# Functions to handle user input
#

def do_User():
    """
    This function implements the [User]-button:
    Before joining any chatroom groups the end-user must register with
    the P2PChat program his/her nickname (username), which will appear
    in all messages sent by the end-user to the chatroom group as well as
    be appeared in the member list of that chatroom group stored in the
    Room server. The end-user can rename his/her username by using this
    button only before joining any chatroom group. After the end-user has
    registered his/her username, the program prints a message in the Command
    Window.
    Usernames consist of a single word with a length of at most 32 printable
    ASCII characters (excluding the ‘:’ character which is being used as the
    sentinel symbol in our prototol).
    """
    username = userentry.get()
    if can_update_username(username):
        global USERNAME
        USERNAME = username
        CmdWin.insert(1.0, 'Succesfully changed username to: %s\n' % USERNAME)
        userentry.delete(0, END)


def do_List():
    """
    This function implements the [List]-button:
    To get the list of chatroom groups registered in the Room server by
    sending a LIST request to the Room server. After receiving the list of
    chatroom groups from the Room server, the program outputs the chatroom
    names to the Command Window.
    """
    global MS
    global MY_SOCKET
    global SERVER_ADDRESS
    global SERVER_PORT
    if not MY_SOCKET:
        MY_SOCKET = socket.socket()
        MY_SOCKET = connect_socket(MY_SOCKET, SERVER_ADDRESS,
                                   SERVER_PORT, 'KEEPALIVE')

    if MY_SOCKET:
        # send list request
        print('[DEBUG] Sending LIST request.')
        send_message(MY_SOCKET, 'L::\r\n', 'LIST')
        response = receive_message(MY_SOCKET, 'LIST')

        # decode_list returns a list object with contents and boolean that is
        # True iff we received an error message from the server
        message, error_occured = decode_list(response)
        if error_occured:
            print('[SERVER_ERROR]: ' + message[0])
            CmdWin.insert(1.0, 'Error.\n')
        else:
            print('[DEBUG] Succesfully received list of names.')
            CmdWin.insert(1.0, 'Current rooms:\n' + '\n'.join(message) + '\n')


def do_Join():
    """
    This function implements the [Join]-button:
    To join a target chatroom group. The end-user must provide the target
    chatroom name via the user input field; otherwise, the program
    displays an error message in the Command Window. If the P2PChat
    program has already joined a chatroom group, the system should reject
    this request and display an error message in the Command Window. After
    getting the chatroom name, the P2PChat program sends a JOIN request to
    the Room server, and if succeeded, the Room server should send back
    the list of members in that chatroom together with their contact info.
    The member list should include this newly joined P2PChat program.
    Once, the P2PChat program gets the member list, it tries to join the
    chatroom network by initiating a TCP connection to one of the
    chatroom’s members. Once successfully linked to a member, this P2PChat
    program is considered as successfully CONNECTED to the chatroom network
    and it reports the status to the end-user via the Command Window. More
    details on the interactions between the P2PChat program, the Room
    server, and another peer will be covered in the communication protocol
    section.
    """
    chatroom = userentry.get()
    userentry.delete(0, END)
    if can_join_chatroom(chatroom):
        global CURRENT_CHATROOM
        CURRENT_CHATROOM = chatroom
        response = join_request()
        if response.startswith('M:') and response.endswith(':\r\n'):
            # valid response, we joined a chatroom
            print('[DEBUG] Joined a chatroom.')
            global MY_HASH
            global MY_SOCKET
            my_address = MY_SOCKET.getsockname()
            global MY_PORT
            MY_HASH = sdbm_hash(USERNAME + my_address[0] + str(MY_PORT))
            global POKE_THREAD
            POKE_THREAD = poke_listener(1, 'pokeListenerThread')
            POKE_THREAD.start()
            global KEEPALIVE_THREAD
            KEEPALIVE_THREAD = keepalive(1, 'keepaliveThread')
            KEEPALIVE_THREAD.start()
            global BACKWARD_LINK_THREAD
            BACKWARD_LINK_THREAD = backward_link_listener(
                1, 'backwardLinkListenerThread')
            BACKWARD_LINK_THREAD.start()
            global MEMBERS_LIST
            CmdWin.insert(1.0, 'Successfully joined chatroom.\n' +
                          'List of members:\n' +
                          '\n'.join(['%s\t\t%s\t\t%d'
                                     % u[0:3] for u in MEMBERS_LIST]) + '\n')
            global FORWARD_LINK_THREAD
            FORWARD_LINK_THREAD = connect_to_peers(1, 'connectToPeersThread')
            FORWARD_LINK_THREAD.start()
        elif response.startswith('F:') and response.endswith(':\r\n'):
            # error message
            error = response.strip('{M:|::\r\n}')
            print('[DEBUG] Received Error ' + error)
            CmdWin.insert(1.0, error + '\n')
        else:
            # not a valid response
            print('[DEBUG] Did nothing receive valid response from server')
            CmdWin.insert(1.0, 'Error\n')


def do_Send():
    """
    This function implements the [Send]-button:
    To send a message to the chatroom network, i.e., to everyone in the
    chatroom. The P2PChat program must be CONNECTED to the chatroom network
    before sending a message. The message is sent to the chatroom network
    via all peers that are currently connected (forward link and backward
    links) to this P2PChat program. The program also displays the message to
    the Message Window together with the username to identify who gave out
    this message. You may assume the length of the text content is less than
    500 bytes, but it is possible that the ‘:’ character may appear as text
    content in the message.
    """
    global MSGID
    MSGID += 1

    text = userentry.get()
    userentry.delete(0, END)
    message = make_text_message(text)

    global USERNAME
    if not connected():
        # we don't have to send the message to anyone
        MsgWin.insert(1.0, '[%s] %s\n' % (USERNAME, text))
        return
    send_message_to_all(message, get_all_links())
    MsgWin.insert(1.0, '[%s] %s\n' % (USERNAME, text))


def make_text_message(text):
    """
    Create text message according to protocol specifications. Returns
    string representation of message.
    """
    global CURRENT_CHATROOM
    global USERNAME
    global MEMBERS_LIST
    global MSGID
    message = 'T:' + CURRENT_CHATROOM + ':'
    myIndex = [member[3] for member in MEMBERS_LIST].index(MY_HASH)
    userHID = MEMBERS_LIST[myIndex][0]
    message += userHID + ':' + USERNAME + ':' + str(MSGID) + ':'
    MSGID += 1
    message += str(len(text)) + ':' + text + '::\r\n'
    return message


def connected():
    """
    Returns True iff client is connected to anyone peers in the network,
    else False.
    """
    global CURRENT_CHATROOM
    global FORWARD_LINK_SOCKET
    global BACKWARD_LINKS
    if (CURRENT_CHATROOM and (FORWARD_LINK_SOCKET or BACKWARD_LINKS)):
        return True
    else:
        return False


def do_Poke():
    """
    This function implements the [Poke]-button:
    to give a ‘Poke’ to a member in the chatroom. The P2PChat program must
    have JOINED the chatroom before sending a Poke to a member in the
    chatroom. The end-user must provide the target member’s nickname via the
    user input field; otherwise, the program displays “To whom you want to
    send the poke?” and the list of nicknames in this chatroom to the
    Command Window. Given the member’s nickname, the program sends a UDP
    message directly to that member’s UDP socket and an acknowledgment
    response is expected from the target's P2PChat program. In addition,
    a Poke message will be displayed in the target’s Message Window (as well
    as the Command Window). More details on the interactions will be covered
    in the communication protocol section.
    """
    nickname = userentry.get()
    print('[DEBUG] Attempting to poke user')
    recipient = get_recipient(nickname)
    if recipient:
        print('[DEBUG] Before defining socket')
        recipient_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        request = ('K:' + CURRENT_CHATROOM + ':' + USERNAME + '::\r\n')
        try:
            print('[DEBUG] Before sending bytes')
            recipient_socket.sendto(bytes(request, 'ascii'), recipient)
            print('[DEBUG] After Sending Bytes')
        except Exception as e:
            print('[POKE_ERROR] Could not send Poke:\n' + str(e))
            CmdWin.insert(1.0, 'Error\n')
            return

        try:
            print('[DEBUG] Before receiving response')
            response, server = recipient_socket.recvfrom(1000)
            response = response.decode('ascii')
            print('[DEBUG] After response')
        except Exception as e:
            print('[POKE_ERROR] Poke Unsuccessful ' + str(e))
            CmdWin.insert(1.0, 'Error\n')
            return
        if response == 'A::\r\n':
            print('[DEBUG] Successful poke')
            CmdWin.insert(1.0, 'Successfully poked ' + nickname + '\n')
        userentry.delete(0, END)


def do_Quit():
    """
    This function implements the [Quit]-button:
    to exit from the program. Before termination, the P2PChat program closes
    all TCP connections and releases all resources.
    """
    print('[DEBUG] Shutting down resources...')
    global MY_SOCKET
    if MY_SOCKET:
        print('[DEBUG] Closing MY_SOCKET')
        MY_SOCKET.close()
    global KEEPALIVE_THREAD
    if KEEPALIVE_THREAD:
        print('[DEBUG] Closing KEEPALIVE_THREAD')
        KEEPALIVE_THREAD.event.set()
        KEEPALIVE_THREAD.join()
    global POKE_SOCKET
    if POKE_SOCKET:
        print('[DEBUG] Closing POKE_SOCKET')
        POKE_SOCKET.close()
    global POKE_THREAD
    if POKE_THREAD:
        print('[DEBUG] Closing POKE_THREAD')
        POKE_THREAD.join()
    global FORWARD_LINK_SOCKET
    if FORWARD_LINK_SOCKET:
        print('[DEBUG] Closing FORWARD_LINK_SOCKET')
        FORWARD_LINK_SOCKET.close()
    global FORWARD_LINK_THREAD
    if FORWARD_LINK_THREAD:
        print('[DEBUG] Closing FORWARD_LINK_THRED')
        FORWARD_LINK_THREAD.event.set()
        FORWARD_LINK_THREAD.join()
    global BACKWARD_LINKS
    if len(BACKWARD_LINKS) > 1:
        print('[DEBUG] Closing BACKWARD_LINKS')
        for hsh, sckt in BACKWARD_LINKS:
            sckt.close()
    global BACKWARD_LINK_SOCKET
    if BACKWARD_LINK_SOCKET:
        print('[DEBUG] Closing BACKWARD_LINK_SOCKET')
        BACKWARD_LINK_SOCKET.close()
    global BACKWARD_LINK_THREAD
    if BACKWARD_LINK_THREAD:
        print('[DEBUG] Closing BACKWARD_LINK_THREAD')
        BACKWARD_LINK_THREAD.join()
    global MESSAGE_LISTENER_THREAD
    if MESSAGE_LISTENER_THREAD:
        print('[DEBUG] Closing MESSAGE_LISTENER_THREAD')
        MESSAGE_LISTENER_THREAD.event.set()
        MESSAGE_LISTENER_THREAD.join()
    CmdWin.insert(1.0, '\nPress Quit')
    print('[DEBUG] Release succesful. Closing tk-window now.')
    win.destroy()
    print('[DEBUG] Success. App is shutting down...')
    sys.exit(0)


class connect_to_peers(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.event = threading.Event()

    def run(self):
        attempt_forward_peer_connection(self)


def attempt_forward_peer_connection(thread):
    global MEMBERS_LIST
    global MY_HASH
    # establish forward connection to next member in member list
    myIndex = [member[3] for member in MEMBERS_LIST].index(MY_HASH)
    start = (myIndex + 1) % len(MEMBERS_LIST)
    global FORWARD_LINK_SOCKET
    global BACKWARD_LINKS
    while MEMBERS_LIST[start][3] != MY_HASH and len(MEMBERS_LIST) > 1:
        if MEMBERS_LIST[start][3] in BACKWARD_LINKS:
            # we already have a backward link to this member
            start = (start + 1) % len(MEMBERS_LIST)
        else:
            # no backward link, we can connect
            FORWARD_LINK_SOCKET = socket.socket()
            print('[FORWARD_LINK_DEBUG] connecting to ('
                  + str(MEMBERS_LIST[start][1]) + ','
                  + str(MEMBERS_LIST[start][2]) + ')')
            FORWARD_LINK_SOCKET = connect_socket(FORWARD_LINK_SOCKET,
                                                 MEMBERS_LIST[start][1],
                                                 MEMBERS_LIST[start][2],
                                                 'FORWARD_LINK')
            if FORWARD_LINK_SOCKET:
                # connection establishment was successful
                global USERNAME
                my_address = FORWARD_LINK_SOCKET.getsockname()
                global MSGID
                global MY_PORT
                global CURRENT_CHATROOM
                request = ('P:' + CURRENT_CHATROOM + ':' + USERNAME +
                           ':' + my_address[0] + ':' + str(MY_PORT) +
                           ':' + str(MSGID) + '::\r\n')
                send_message(FORWARD_LINK_SOCKET, request, 'FORWARD PEER')
                response = receive_message(FORWARD_LINK_SOCKET, 'FORWARD PEER')
                if response:
                    if response.startswith('S:') and response.endswith(
                            ':\r\n'):
                        # we have a connection
                        msg_id = response.strip('{S:|::\r\n}').split(':')[0]
                        update_message_id(msg_id, MEMBERS_LIST[start][0])
                        start_text_message_listener()
                        break

                    else:
                        # response was invalid, try next member
                        FORWARD_LINK_SOCKET = None
                        start = (start + 1) % len(MEMBERS_LIST)
                else:
                    start = (start + 1) % len(MEMBERS_LIST)
            else:
                # connection establishment failed, try next member
                start = (start + 1) % len(MEMBERS_LIST)
    if not FORWARD_LINK_SOCKET:
        # could not connect to any peer
        print('[CLIENT ERROR] Complete failure to establish forward link')
        CmdWin.insert(1.0, 'There might not be anyone to connect to,' +
                      'will try again in twenty seconds.\n')
        if thread.event.wait(20):
            return
        attempt_forward_peer_connection(thread)


class text_message_listener(threading.Thread):
    """
    Thread, that listens to incoming test messages from backward links and
    forward links. Prints it to screen and forwards to messages to links that
    are not leading to sender or the peer that forwarded the message to us.
    Also, checks iff message is valid and has nothing been seen before, before
    printing and forwarding.
    """
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.event = threading.Event();

    def run(self):
        print('[DEBUG] Running text_message_listener thread.')
        global UPDATE_INTERVAL

        while True:
            if self.event.wait(UPDATE_INTERVAL):
                return
            else:
                # listen_to must be updated in cases we got new connections
                listen_to = get_all_links()
                ready_sockets, _, _ = select.select(listen_to, [], [], 2)

                for sckt in ready_sockets:
                    message = receive_message(sckt, 'TEXT_RECEIVE')

                    if not message:
                        # message was empty
                        break

                    print('[DEBUG] Recieved message:')
                    print(message)

                    if is_valid_text(message):
                        contents = message.strip('{T:|::\r\n}').split(':')
                        peername = contents[2]
                        roomname, originHID, origin_username = contents[0:3]
                        msgID, msgLength = contents[3:5]
                        # message might contain :
                        message_data = ':'.join(contents[5:])

                        # do we know this user yet?
                        global MEMBERS_LIST
                        if peername in [member[0] for member in MEMBERS_LIST]:
                            # update MEMBERS_LIST (implicitly via new join request)
                            print('[DEBUG] Message from unknown peer,' +
                                'sending join request.')
                            join_request()

                        # add message_id to seen ones
                        if update_message_id(msgID, peername):
                            # we haven't seen this message before
                            # forward to all connections
                            print('[DEBUG] Haven\'t seen this message yet.')
                            recipients = get_recipients(origin_username, sckt)
                            send_message_to_all(message, recipients)
                            MsgWin.insert(1.0, '[%s] %s\n' %
                                        (origin_username, message_data))


def start_text_message_listener():
    """
    If we have not initiated a message listener thread yet:
    Start new message listener thread.
    """
    global MESSAGE_LISTENER_THREAD
    if not MESSAGE_LISTENER_THREAD:
        MESSAGE_LISTENER_THREAD = text_message_listener(1, 'msgListener')
        MESSAGE_LISTENER_THREAD.start()
    return


def get_all_links():
    """
    Return all valid backward links and forward link.
    """
    global FORWARD_LINK_SOCKET
    global BACKWARD_LINKS

    # extract backward link sockets from global dict
    links = []
    for member in BACKWARD_LINKS.keys():
        links.append(BACKWARD_LINKS[member])

    if FORWARD_LINK_SOCKET:
        links += [FORWARD_LINK_SOCKET]

    return links


def is_valid_text(message):
    """
    Check, if the text message hash correct syntax and comes from
    correct chatroom. Returns True, iff all checks are passed,
    False otherwise.
    """
    if not (message.startswith('T:') and message.endswith('::\r\n')):
        print('[DEBUG] Received invalid text message.')
        return False
    # extract fields in message
    contents = message.strip('{T:|::\r\n}').split(':')
    roomname, originHID, origin_username = contents[0:3]
    msgID, msgLength = contents[3:5]

    # check if message came from correct chatroom
    global CURRENT_CHATROOM
    if roomname != CURRENT_CHATROOM:
        print('[DEBUG] Received message with invalid roomname')
        return False

    global USERNAME
    if origin_username == USERNAME:
        print('[DEBUG] Own message received, discard.')
        return False
    print('[DEBUG] Message okay.')
    return True


def get_recipients(sender, link):
    """
    Return list with all link-sockets except the link to sender and link.
    """
    links = set(get_all_links())
    links.discard(link)
    global BACKWARD_LINKS
    for member in BACKWARD_LINKS.keys():
        if member == sender:
            links.discard(BACKWARD_LINKS[sender])
    return links


def update_message_id(message_id, peername):
    """
    Update message id for peername in global PEERS_MESSAGE_IDS dict.
    Return True iff message_id was updated, else False.
    """
    global PEERS_MESSAGE_IDS
    if peername not in PEERS_MESSAGE_IDS.keys():
        print('[DEBUG] No record of latest  message_id for this peer.')
        PEERS_MESSAGE_IDS[peername] = int(message_id)
        return True
    elif int(message_id) > PEERS_MESSAGE_IDS[peername]:
        print('[DEBUG] message_id still fresh.')
        PEERS_MESSAGE_IDS[peername] = int(message_id)
        return True
    else:
        print('[DEBUG] update_message_id decided that message id' 
              '%d belonging to peer %s is old. PEERS_MESSAGE_IDS is:'
              % (int(message_id), peername))
        print(PEERS_MESSAGE_IDS)
        return False


def send_message_to_all(message, recipients):
    print('[DEBUG] Attempting to send message: ' + message[:-4]
          + ' to ' + str(recipients))
    while recipients:
        _, ready_sockets, _ = select.select([], recipients, [], 1)
        for sckt in ready_sockets:
            recipients.remove(sckt)
            send_message(sckt, message, 'SEND')
    print('[DEBUG] Message sent.')
    return


class backward_link_listener(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        global BACKWARD_LINK_SOCKET
        global BACKWARD_LINKS
        global MY_PORT
        if not BACKWARD_LINK_SOCKET:
            BACKWARD_LINK_SOCKET = socket.socket()
            BACKWARD_LINK_SOCKET = bind_socket(BACKWARD_LINK_SOCKET,
                                               MY_PORT, 'BACKWARD_LINK')
        if BACKWARD_LINK_SOCKET:
            global MEMBERS_LIST
            global MSGID
            while True:
                print('[DEBUG] Listening for Backward Link.')
                try:
                    BACKWARD_LINK_SOCKET.listen(1)
                    conn, addr = BACKWARD_LINK_SOCKET.accept()
                except Exception as e:
                    print('[DEBUG] Error accepting backward link')
                    return
                response = receive_message(conn, 'BACKWARD PEER')
                join_request()
                if response.startswith('P:') and response.endswith(':\r\n'):
                    message = response.strip('{P:|::\r\n}').split(':')
                    found = False
                    peername = message[1]
                    message_id = message[4]
                    for member in MEMBERS_LIST:
                        if peername == member[0]:
                            found = True
                            request = ('S:' + str(MSGID) + '::\r\n')
                            send_message(conn, request, 'BACKWARD PEER')
                            BACKWARD_LINKS[member[3]] = conn

                            # store message id
                            update_message_id(message_id, peername)

                            # we have a backward connection, start
                            # listening form messages
                            start_text_message_listener()
                    if not found:
                        conn.close()
                else:
                    conn.close()


class keepalive(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.event = threading.Event()

    def run(self):
        global MY_SOCKET
        global SERVER_ADDRESS
        global SERVER_PORT
        if not MY_SOCKET:
            MY_SOCKET = socket.socket()
            MY_SOCKET = connect_socket(MY_SOCKET, SERVER_ADDRESS,
                                       SERVER_PORT, 'KEEPALIVE')
        if MY_SOCKET:
            while True:
                if self.event.wait(20):
                    return
                else:
                    response = join_request()
                    if response.startswith('M:') and response.endswith(
                            ':\r\n'):
                        # valid response, we joined a chatroom
                        print('[DEBUG] Refreshed connection')
                        CmdWin.delete('1.0', END)
                        global MEMBERS_LIST
                        CmdWin.insert(1.0, 'List of members:\n'
                                      + '\n'.join(['%s\t\t%s\t\t%d' % u[0:3]
                                                   for u in MEMBERS_LIST])
                                      + '\n')


class poke_listener(threading.Thread):

    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        print('[DEBUG] Starting ' + self.name)
        global POKE_SOCKET
        if not POKE_SOCKET:
            error = setup_poke_socket()
            if error:
                print('[LISTENER ERROR] Error setting up poke socket')
                return
        while True:
            try:
                message, sender = POKE_SOCKET.recvfrom(1000)
                message = message.decode('ascii')
            except Exception as e:
                print('[LISTENER_ERROR] Error receiving poke ' + str(e))
                return
            if message.startswith('K:') and message.endswith(':\r\n'):
                message = message.strip('{K:|::\r\n}').split(':')
                CmdWin.insert(1.0, 'Poke from ' +
                              message[1] + ' in chatroom ' + message[0] + '\n')
                try:
                    POKE_SOCKET.sendto(bytes('A::\r\n', 'ascii'), sender)
                except Exception as e:
                    print('[LISTENER_ERROR] Error sending confirmation '
                          + str(e))


def decode_list(response):
    """
    Helper function to decode server answers to LIST request.

    Args:
        response - string with LIST response message

    Returns:
        tuple of list of strings and boolean -
            contents of the message divided into list-entries at ':'
            and a value that indicates, if contents are errormsg or not

    Examples:
        >>> decode_list('G::\\r\\n')
        ([], False)
        >>> decode_list('G:HarryPotter:HermineGranger:RonWeasley::\\r\\n')
        (['HarryPotter', 'HermineGranger', 'RonWeasley'], False)
        >>> decode_list('F:HogwartsIsClosed::\\r\\n')
        (['HogwartsIsClosed'], True)
    """
    if response.startswith('G:') and response.endswith(':\r\n'):
        # valid response, retrieve names of chatrooms
        names_str = response.strip('{G:|::\r\n}')
        names_list = []
        if names_str:
            # message was not empty, we have chatroom names
            names_list = names_str.split(':')
        return (names_list, False)
    elif response.startswith('F:') and response.endswith(':\r\n'):
        # error response
        return ([response.strip('{F:|::\r\n}')], True)
    else:
        # not a valid response, do nothing
        print('[DEBUG] Did not receive a valid response from server: \n'
              + response)
        return 'Error'


def can_join_chatroom(chatroom):
    global CURRENT_CHATROOM
    if CURRENT_CHATROOM:
        print('[DEBUG] Already joined chatroom.')
        CmdWin.insert(1.0, 'You\'re already in a chatroom.\n')
        return False
    global USERNAME
    if not USERNAME:
        print('[DEBUG] No username, aborting join.')
        CmdWin.insert(1.0, 'Specify username before joining chatrooms.\n')
        return False
    # check if user gave us a chatroom name
    if not chatroom:
        print('[DEBUG] No chatroom name given.')
        CmdWin.insert(1.0, 'Specify name of the chatroom to join.\n')
        return False
    # check, if we are already connected to a server
    global MY_SOCKET
    global SERVER_ADDRESS
    global SERVER_PORT
    if not MY_SOCKET:
        MY_SOCKET = socket.socket()
        MY_SOCKET = connect_socket(MY_SOCKET, SERVER_ADDRESS,
                                   SERVER_PORT, 'KEEPALIVE')
    if MY_SOCKET:
        return True
    else:
        return False


def can_update_username(username):
    global CURRENT_CHATROOM
    # did client already join a chatroom?
    if CURRENT_CHATROOM:
        CmdWin.insert(1.0, 'Could not change username: Already joined\n')
        return False
    # do we have a valid username?
    # I split up all their cases from one regex to multiple checks
    # in order to provide better feedack to their user.
    if not username:
        CmdWin.insert(1.0, 'Invalid username: Empty\n')
        return False
    if username.find(':') > -1:
        # name contains ':'
        CmdWin.insert(1.0, 'Invalid username: Contains :\n')
        return False
    if re.findall('\s', username):
        # name contains whitespace
        CmdWin.insert(1.0, 'Invalid username: Contains whitespace\n')
        return False
    if len(username) > 32:
        CmdWin.insert(1.0,
                      'Invalid username: Too long (maximum is 32 characters)\n')
        return False
    if not all([ord(c) >= 0 and ord(c) <= 127 for c in username]):
        # ord() returns encoding of characters, ascii is <128
        CmdWin.insert(1.0,  'Invalid username: Contains non-ASCII characters\n')
        return False
    return True


def get_recipient(nickname):
    global CURRENT_CHATROOM
    if not CURRENT_CHATROOM:
        print('[DEBUG] Not in a chatroom yet')
        CmdWin.insert(1.0, 'You\'re not in a chatroom yet\n')
        return None
    global MEMBERS_LIST
    if not nickname:
        print('[DEBUG] No user specified')
        CmdWin.insert(1.0, 'Choose a user to poke\n')
        return None
    global USERNAME
    if nickname == USERNAME:
        print('[DEBUG] Attempted to poke self')
        CmdWin.insert(1.0, 'You can\'t poke yourself\n')
        return None

    # recipient = None
    for (name, address, port, hashID) in MEMBERS_LIST:
        if nickname == name:
            return (address, port)
    print('[DEBUG] Name not in MEMBERS_LIST')
    CmdWin.insert(1.0, 'Selected user isn\'t in the list of members\n')
    return None


def join_request():
    """
    Send a new join request. Can be used for keepalive process and
    immediate update of the members list.
    """
    global MY_SOCKET
    if not MY_SOCKET:
        global SERVER_ADDRESS
        global SERVER_PORT
        MY_SOCKET = socket.socket()
        MY_SOCKET = connect_socket(MY_SOCKET, SERVER_ADDRESS,
                                   SERVER_PORT, 'JOIN')
    if MY_SOCKET:
        global USERNAME
        global CURRENT_CHATROOM
        my_address = MY_SOCKET.getsockname()
        global MY_PORT
        request = ('J:' + CURRENT_CHATROOM + ':' + USERNAME + ':'
                   + my_address[0] + ':' + str(MY_PORT) + '::\r\n')
        send_message(MY_SOCKET, request, 'JOIN')
        response = receive_message(MY_SOCKET, 'JOIN')
        if response.startswith('M:') and response.endswith(':\r\n'):
            message = response.strip('{M:|::\r\n}').split(':')
            update_members_list(message)
        return response


def bind_socket(new_socket, port, name):
    try:
        new_socket.bind(('', port))
    except Exception as e:
        new_socket.close()
        print('[' + name + '_ERROR] Could not bind specified port:\n' + str(e))
        CmdWin.insert(1.0, 'Connection error.\n')
        return None
    print('[' + name + '_SUCCESS] Successfully bound port.')
    return new_socket


def connect_socket(new_socket, hostAddress, hostPort, name):
    try:
        new_socket.connect((hostAddress, hostPort))
    except Exception as e:
        new_socket.close()
        print('[' + name + '_ERROR] Connection failed:\n' + str(e))
        return None
    print('[' + name + '_SUCCESS] Successfully connected to address.')
    return new_socket


def send_message(socket, message, name):
    try:
        socket.send(bytes(message, 'ascii'))
    except Exception as e:
        print('[' + name + '_ERROR] Could not send request:\n' + str(e))
        return False
    return True


def receive_message(socket, name):
    """
    Receive a message of size 1000 from socket.
    """
    try:
        response = socket.recv(1000).decode('ascii')
    except Exception as e:
        print('[' + name + '_ERROR] Did not receive anything in request')
        return False
    return response


def update_members_list(message):
    """
    Update the global MEMBERS_LIST based on entries from a
    new answer message to a join request.
    """
    global MEMBERS_LIST
    MEMBERS_LIST = [(name, address, int(port),
                     sdbm_hash(name + address + port))
                    for name, address, port in
                    zip(message[1::3], message[2::3], message[3::3])]
    MEMBERS_LIST.sort(key=lambda member: member[3])


def setup_poke_socket():
    global MY_PORT
    print('[DEBUG] Establishing new connection to server.')
    # create new_username socket, bind and connect
    poke_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    poke_socket = bind_socket(poke_socket, MY_PORT, 'POKE_SOCKET')

    global POKE_SOCKET
    POKE_SOCKET = poke_socket
    return None


#
# Set up of Basic UI
#
win = Tk()
win.title('MyP2PChat')

# Top Frame for Message display
topframe = Frame(win, relief=RAISED, borderwidth=1)
topframe.pack(fill=BOTH, expand=True)
topscroll = Scrollbar(topframe)
MsgWin = Text(topframe, height='15', padx=5, pady=5, fg="red", exportselection=0, insertofftime=0)
MsgWin.pack(side=LEFT, fill=BOTH, expand=True)
topscroll.pack(side=RIGHT, fill=Y, expand=True)
MsgWin.config(yscrollcommand=topscroll.set)
topscroll.config(command=MsgWin.yview)

#Top Middle Frame for buttons
topmidframe = Frame(win, relief=RAISED, borderwidth=1)
topmidframe.pack(fill=X, expand=True)
Butt01 = Button(topmidframe, width='6', relief=RAISED, text="User", command=do_User)
Butt01.pack(side=LEFT, padx=8, pady=8);
Butt02 = Button(topmidframe, width='6', relief=RAISED, text="List", command=do_List)
Butt02.pack(side=LEFT, padx=8, pady=8);
Butt03 = Button(topmidframe, width='6', relief=RAISED, text="Join", command=do_Join)
Butt03.pack(side=LEFT, padx=8, pady=8);
Butt04 = Button(topmidframe, width='6', relief=RAISED, text="Send", command=do_Send)
Butt04.pack(side=LEFT, padx=8, pady=8);
Butt06 = Button(topmidframe, width='6', relief=RAISED, text="Poke", command=do_Poke)
Butt06.pack(side=LEFT, padx=8, pady=8);
Butt05 = Button(topmidframe, width='6', relief=RAISED, text="Quit", command=do_Quit)
Butt05.pack(side=LEFT, padx=8, pady=8);

#Lower Middle Frame for User input
lowmidframe = Frame(win, relief=RAISED, borderwidth=1)
lowmidframe.pack(fill=X, expand=True)
userentry = Entry(lowmidframe, fg="blue")
userentry.pack(fill=X, padx=4, pady=4, expand=True)

#Bottom Frame for displaying action info
bottframe = Frame(win, relief=RAISED, borderwidth=1)
bottframe.pack(fill=BOTH, expand=True)
bottscroll = Scrollbar(bottframe)
CmdWin = Text(bottframe, height='15', padx=5, pady=5, exportselection=0, insertofftime=0)
CmdWin.pack(side=LEFT, fill=BOTH, expand=True)
bottscroll.pack(side=RIGHT, fill=Y, expand=True)
CmdWin.config(yscrollcommand=bottscroll.set)
bottscroll.config(command=CmdWin.yview)


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)
    global SERVER_ADDRESS, SERVER_PORT, MY_PORT
    SERVER_ADDRESS = sys.argv[1]
    SERVER_PORT = int(sys.argv[2])
    MY_PORT = int(sys.argv[3])

    win.mainloop()


if __name__ == "__main__":
    main()
