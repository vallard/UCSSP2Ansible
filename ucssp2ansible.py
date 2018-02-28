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
def sub_root(org, part, dn):
    return dn.replace("%s/%s" % (org, part), "")


def ansible_ucs_login(ts):
    return " "*ts + "ucs_ip: {{ucs_ip}}" + "\n" + " "*ts + "ucs_username: {{ ucs_username }}" + "\n" + " "*ts + "ucs_password: {{ ucs_password }}" 
    

def create_scrub(h, org, ts, scrub_policy_name):
    sp = h.query_dn(scrub_policy_name)
    print " "*ts + "- name: Ensure scrub policy is created"
    print " "*ts + "  cisco_ucs_scrub_policy:"
    print " "*(ts*2) + "name: %s" % sub_root(org, "scrub-", scrub_policy_name)
    print " "*(ts*2) + "descr: %s" % sp.descr
    print " "*(ts*2) + "disk_scrub: %s" % sp.disk_scrub
    print " "*(ts*2) + "flex_flash_scrub: %s" % sp.flex_flash_scrub
    print " "*(ts*2) + "bios_settings_scrub: %s" % sp.bios_settings_scrub
    
def create_vmedia(h, org, ts, policy_name):
    from ucsmsdk.mometa.cimcvmedia.CimcvmediaMountConfigPolicy import CimcvmediaMountConfigPolicy
    from ucsmsdk.mometa.cimcvmedia.CimcvmediaConfigMountEntry import CimcvmediaConfigMountEntry
    mo = h.query_dn(policy_name,  hierarchy=True)
    cfg_policy = ""
    mnt_entries = []
    for i in mo:
        if type(i) is CimcvmediaMountConfigPolicy:
           cfg_policy = i 
        elif type(i) is CimcvmediaConfigMountEntry:
            mnt_entries.append(i)
    if cfg_policy == "":
        return
    print " "*ts + "- name: Ensure vmedia policy is created"
    print " "*ts + "  cisco_ucs_vmedia_policy:"
    print " "*(ts*2) + "name: %s" % sub_root(org, "mnt-cfg-policy-", policy_name)
    print " "*(ts*2) + "descr: %s" % cfg_policy.descr
    print " "*(ts*2) + "retry: %s" % cfg_policy.retry_on_mount_fail
    if len(mnt_entries) > 0:
        print " "*(ts*2) + "mounts: "
        for i in mnt_entries:
            print " "*(ts*2) + "- name: %s" % i.mapping_name
            print " "*(ts*3) + "device: %s" % i.device_type
            print " "*(ts*3) + "protocol: %s" % i.mount_protocol
            print " "*(ts*3) + "remote_ip: %s" % i.remote_ip_address
            print " "*(ts*3) + "file: %s" % "variable" if i.image_name_variable == "service-profile-name" else i.image_file_name
            print " "*(ts*3) + "path: %s" % i.image_path
            
def create_bios_policy(h, org, ts, policy_name):
    print "TODO" 


def create_sp_playbook(h, org, sp, ts):
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
        print ansible_ucs_login(ts*3)
    if sp.oper_scrub_policy_name:
        print " "*(ts*4) + "scrub_policy: %s" % sub_root(org, "scrub-", sp.oper_scrub_policy_name)
        create_scrub(h, org, ts, sp.oper_scrub_policy_name)
    if sp.oper_vmedia_policy_name:
        print " "*(ts*4) + "vmedia_policy: %s" % sub_root(org, "mnt-cfg-policy-", sp.oper_vmedia_policy_name)
        create_vmedia(h, org, ts, sp.oper_vmedia_policy_name)
    if sp.oper_bios_profile_name:
        print " "*(ts*4) + "bios_policy: %s" % sub_root(org, "bios-prof-oper-", sp.oper_bios_profile_name)
        create_bios_policy(h, org, ts, sp.oper_bios_profile_name)


h, msg = login('admin', 'nbv12345', '172.28.225.163')
#sp = select_sp(h)
sp = get_sp(h, "KUBAM-ESXi")
create_sp_playbook(h, "org-root", sp, 2)
print sp
   
logout(h)
