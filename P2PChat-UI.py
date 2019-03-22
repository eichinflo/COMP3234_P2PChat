#!/usr/bin/python3

# Student name and No.:
# Student name and No.:
# Development platform:
# Python version:
# Version:


from tkinter import *
import sys
import socket

#
# Global variables
#

USERNAME = None
JOINED = False
SERVER_ADDRESS = None
SERVER_PORT = None
MY_PORT = None
MY_SOCKET = None
CURRENT_CHATROOMS = None


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
    new_username = userentry.get()
    outstr = do_User_(new_username) + '\n'
    CmdWin.insert(1.0, outstr)
    userentry.delete(0, END)


def do_User_(username):
    """
    Just a helper function. We might reincorporate this code into do_User,
    thought, that it would help testing and debugging to have it in this
    function.

    Here are the testcases for Stage one (doctest has a problem with
    global variables right now, not sure how to make these tests pass)

    >>> do_User_('')
    'Invalid username: Cannot be empty'
    >>> USERNAME == ''
    False
    >>> do_User_('spam')
    'Succesfully changed username to: spam'
    >>> USERNAME == 'spam'
    True
    >>> JOINED = True
    >>> do_User_('ham')
    'Could not change username: Already joined'
    >>> USERNAME == 'spam'
    True
    """
    global JOINED
    # did client already join a server?
    if JOINED is True:
        return 'Could not change username: Already joined'
    # do we have a valid username? We can include further checks here
    if not username:
        return 'Invalid username: Cannot be empty'
    global USERNAME
    USERNAME = username
    return 'Succesfully changed username to: %s' % USERNAME


def do_List():
    """
    This function implements the [List]-button:
    To get the list of chatroom groups registered in the Room server by
    sending a LIST request to the Room server. After receiving the list of
    chatroom groups from the Room server, the program outputs the chatroom
    names to the Command Window.
    """
    outstr = "\nPress List\n" + do_List_()
    CmdWin.insert(1.0, outstr)


def do_List_():
    """
    Helper function for connecting to server and generating their user List.
    """
    if not MY_SOCKET:
        # we must establish a new connection to server
        error = connect_to_server()
        if error:
            return error

    # send list request
    print('[DEBUG] Sending LIST request.')
    try:
        MY_SOCKET.send(bytes('L::\r\n', 'ascii'))
    except Exception as e:
        print('[CLIENT_ERROR] Could not send LIST request:\n' + str(e))
        return 'Error'

    # their 1000 limits their number of names here :/
    try:
        response = MY_SOCKET.recv(1000).decode('ascii')
    except Exception as e:
        print('[CLIENT_ERROR] Could not receive list:\n' + str(e))
        return 'Error'

    # decode_list returns a list object with contents endswi boolean that is
    # True iff we received an error message from the server
    message, error_occured = decode_list(response)
    if error_occured:
        print('[SERVER_ERROR]: ' + message[0])
        return 'Error'
    else:
        print('[DEBUG] Succesfully received list of names.')
        global CURRENT_CHATROOMS
        CURRENT_CHATROOMS = message
        return '\n'.join(message)


def connect_to_server():
    """
    Establish connection to chatroom server.
    """
    global SERVER_ADDRESS, SERVER_PORT, MY_PORT
    print('[DEBUG] Establishing new connection to server.')
    # create new_username socket, bind and connect
    my_socket = socket.socket()
    try:
        my_socket.bind(('', MY_PORT))
    except Exception as e:
        my_socket.close()
        print('[CLIENT_ERROR] Could not bind specified port:\n' + str(e))
        return 'Error'

    try:
        my_socket.connect((SERVER_ADDRESS, SERVER_PORT))
    except Exception as e:
        my_socket.close()
        print('[CLIENT_ERROR] Connection failed:\n' + str(e))
        return 'Error'

    global MY_SOCKET
    MY_SOCKET = my_socket
    return False


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
    outstr = "\n Press JOIN\n" + do_Join_(chatroom)
    CmdWin.insert(1.0, outstr)
    userentry.delete(0, END)


def do_Join_(chatroom):
    """
    Helper function for do_Join function. TODO
    """
    print('[DEBUG] Attempting to join chatroom')
    # check, if we are already in a chatroom or have a username
    global JOINED
    if JOINED:
        print('[DEBUG] Already joined chatroom')
        return 'You already joined a chatroom.'
    global USERNAME
    if not USERNAME:
        print('[DEBUG] No username, aborting join')
        return 'Specify username before joining chatrooms.'
    # check if user gave us a chatroom name
    if not chatroom:
        print('[DEBUG] No chatroom name given')
        return 'Specify name of the chatroom to join.'
    # check, if we are already connected to a server
    global MY_SOCKET
    if not MY_SOCKET:
        error = connect_to_server()
        if error:
            return error

    # send JOIN request to server
    my_address = MY_SOCKET.getsockname()
    request = ("J:" + chatroom + ":" + USERNAME + ":" + my_address[0] + ":" +
               str(my_address[1]) + "::\r\n")
    try:
        MY_SOCKET.send(bytes(request, 'ascii'))
    except Exception as e:
        print("[CLIENT_ERROR] Could not send JOIN request:\n" + str(e))
        return 'Error'

    try:
        response = MY_SOCKET.recv(1000).decode('ascii')
    except Exception as e:
        print("[CLIENT_ERROR] Did nothing receive anything")
        return 'Error'
    if response.startswith('M:') and response.endswith(':\r\n'):
        # valid response, we joined a chatroom
        JOINED = True
        print("[DEBUG] Joined a chatroom")
        message = response.strip('{M:|::\r\n}').split(':')
        msid = message[0]
        users = [(name, address, int(port)) for
                 name, address, port in
                 zip(message[1::3], message[2::3], message[3::3])]
        # TODO: implement rest of join functionality, make nice outputstring
        return str(users)

    elif response.startswith('F:') and response.endswith(':\r\n'):
        # error message
        return response.strip('{M:|::\r\n}')

    else:
        # not a valid response
        print("[DEBUG] Did nothing receive valid response from server")
        return 'Error'


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
    CmdWin.insert(1.0, "\nPress Send")


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
    CmdWin.insert(1.0, "\nPress Poke")


def do_Quit():
    """
    This function implements the [Quit]-button:
    to exit from the program. Before termination, the P2PChat program closes
    all TCP connections and releases all resources.
    """
    CmdWin.insert(1.0, "\nPress Quit")
    sys.exit(0)


#
# Set up of Basic UI
#
win = Tk()
win.title("MyP2PChat")

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
