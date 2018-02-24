#!/usr/bin/env python2

from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.ucsexception import UcsException
from ucsmsdk import ucsgenutils
import socket
from urllib2 import HTTPError
import os, sys

# returns handle, "error message"
def login(username, password, server):
    # first see if reachable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        result = s.connect_ex((server, 80))
        if result != 0:
            return "", "%s is not reachable" % server
        s.close()
    except socket.error as err:
        return "", "UCS Login Error: %s %s" % (server, err.strerror)

    handle = UcsHandle(server, username, password)
    try:
        handle.login()
    except UcsException as err:
        print "Login Error: " + err.error_descr
        return "", err.error_descr
    except HTTPError as err:
        print "Connection Error: Bad UCSM? " + err.reason
        return "", err.reason
    except:
        print "Issue logging in.  Please check that all parameters are correct"
        return "", "Issue logging in.  Please check that all parameters are correct."

    return handle, ""


def logout(handle):
    handle.logout()


def check_input(arr, i):
    try:
        i = int(i) - 1
    except: 
        print "\n\nError: %s is not a valid choice.\n\n" % i
        return False
    if i < 0 or i > len(arr) - 1:
        return False
    return True

def get_sp(h, sp_name):
    # filters: https://github.com/CiscoUcs/ucsmsdk/blob/master/ucsmsdk/ucsfilter.py
    filter_string = '(dn, "root/ls-%s", type="re")' % sp_name
    sp = h.query_classid("lsServer", filter_string)
    return sp[0]
    

def select_sp(h):
    sps = h.query_classid("lsServer")
    print "Which Service Profile do you want to convert to a playbook?"
    while True:
        for i, s in enumerate(sps): 
            print "[%d]: %s" % (i+1, s.name)
        sp = raw_input("E.g.: 1): ")
        if check_input(sps, sp):
            print "converting %s" % sps[int(sp)-1].name
            yn = raw_input("Is this correct? [N/y]: ")
            if yn == "y" or yn == "Y":
                return sps[int(sp) -1]

# take out the org-root/ part out of name.
def sub_root(part, dn):
    return dn.replace("org-root/%s" % part, "")


def create_sp_playbook(sp, ts):
    print " "*ts + "- name: Create SP %s" % sp.name
    if sp.type == "updating-template":
        print " "*(ts*2) + "cisco_ucs_spt:"
        print " "*(ts*3) + "spt_list:"
        print " "*(ts*3) + "- name: %s" % sp.name
        print " "*(ts*4) + "template_type: %s" % sp.type
    else:
        print " "*(ts*2) + "cisco_ucs_sp:"
        print " "*(ts*3) + "sp_list:"
        print " "*(ts*3) + "- name: %s" % sp.name
    if sp.oper_scrub_policy_name:
        print " "*(ts*4) + "scrub_policy: %s" % sub_root("scrub-", sp.oper_scrub_policy_name)




h, msg = login('admin', 'nbv12345', '172.28.225.163')
#sp = select_sp(h)
sp = get_sp(h, "KUBAM-ESXi")

create_sp_playbook(sp, 2)
   
print sp 
#for prop, prop_value in ucsgenutils.iteritems(sp.__json__()):
#    print prop, prop_value
#for i in sp.mos:
#    print i

logout(h)
