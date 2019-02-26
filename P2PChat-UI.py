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
    outstr = "\n[User] username: " + userentry.get()
    CmdWin.insert(1.0, outstr)
    userentry.delete(0, END)


def do_List():
    """
    This function implements the [List]-button:
    To get the list of chatroom groups registered in the Room server by
    sending a LIST request to the Room server. After receiving the list of
    chatroom groups from the Room server, the program outputs the chatroom
    names to the Command Window.
    """
    CmdWin.insert(1.0, "\nPress List")


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
    CmdWin.insert(1.0, "\nPress JOIN")


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

    win.mainloop()


if __name__ == "__main__":
    main()
