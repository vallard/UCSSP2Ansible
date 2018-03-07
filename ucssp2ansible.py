#!/usr/bin/env python2

from ucsmsdk.ucshandle import UcsHandle
from ucsmsdk.ucsexception import UcsException
from ucsmsdk import ucsgenutils
import socket
from urllib2 import HTTPError
import os, sys
import argparse

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
    try:
        return sp[0]
    except IndexError as e:
        return ""

    

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
    return " "*ts + "ucs_ip: {{ucs_ip}}" + "\n" + " "*ts + "ucs_username: {{ ucs_username }}" + "\n" + " "*ts + "ucs_password: {{ ucs_password }}\n" 
    

def create_scrub(h, org, ts, scrub_policy_name):
    sp = h.query_dn(scrub_policy_name)
    rs = " "*ts + "- name: Ensure scrub policy is created\n"
    rs += " "*ts + "  cisco_ucs_scrub_policy:\n"
    rs += " "*(ts*3) + "name: %s\n" % sub_root(org, "scrub-", scrub_policy_name) 
    rs += " "*(ts*3) + "descr: %s\n" % sp.descr
    rs += " "*(ts*3) + "disk_scrub: %s\n" % sp.disk_scrub
    rs += " "*(ts*3) + "flex_flash_scrub: %s\n" % sp.flex_flash_scrub
    rs += " "*(ts*3) + "bios_settings_scrub: %s\n" % sp.bios_settings_scrub
    rs += ansible_ucs_login(ts*3)
    return rs
    
def create_vmedia(h, org, ts, policy_name):
    from ucsmsdk.mometa.cimcvmedia.CimcvmediaMountConfigPolicy import CimcvmediaMountConfigPolicy
    from ucsmsdk.mometa.cimcvmedia.CimcvmediaConfigMountEntry import CimcvmediaConfigMountEntry
    mo = h.query_dn(policy_name,  hierarchy=True)
    rs = ""
    cfg_policy = ""
    mnt_entries = []
    for i in mo:
        if type(i) is CimcvmediaMountConfigPolicy:
           cfg_policy = i 
        elif type(i) is CimcvmediaConfigMountEntry:
            mnt_entries.append(i)
    if cfg_policy == "":
        return
    rs += " "*ts + "- name: Ensure vmedia policy is created\n"
    rs += " "*(ts*2) + "cisco_ucs_vmedia_policy:\n"
    rs += " "*(ts*3) + "name: %s\n" % sub_root(org, "mnt-cfg-policy-", policy_name)
    rs += " "*(ts*3) + "descr: %s\n" % cfg_policy.descr
    rs += " "*(ts*3) + "retry: %s\n" % cfg_policy.retry_on_mount_fail
    if len(mnt_entries) > 0:
        rs += " "*(ts*3) + "mounts: \n"
        for i in mnt_entries:
            rs += " "*(ts*3) + "- name: %s\n" % i.mapping_name
            rs += " "*(ts*4) + "device: %s\n" % i.device_type
            rs += " "*(ts*4) + "protocol: %s\n" % i.mount_protocol
            rs += " "*(ts*4) + "remote_ip: %s\n" % i.remote_ip_address
            rs += " "*(ts*4) + "file: variable\n" if i.image_name_variable == "service-profile-name" else " "*(ts*4) + "file: %s\n" % i.image_file_name
            rs += " "*(ts*4) + "path: %s\n" % i.image_path
    rs += ansible_ucs_login(ts*3)
    return rs
            
def create_bios_policy(h, org, ts, policy_name):
    from ucsmsdk.mometa.bios.BiosVProfile import BiosVProfile
    from ucsmsdk.mometa.bios.BiosVfConsistentDeviceNameControl import BiosVfConsistentDeviceNameControl
    from ucsmsdk.mometa.bios.BiosVfFrontPanelLockout import BiosVfFrontPanelLockout
    from ucsmsdk.mometa.bios.BiosVfPOSTErrorPause import BiosVfPOSTErrorPause
    from ucsmsdk.mometa.bios.BiosVfQuietBoot import BiosVfQuietBoot
    from ucsmsdk.mometa.bios.BiosVfResumeOnACPowerLoss import BiosVfResumeOnACPowerLoss
    mo = h.query_dn(policy_name, hierarchy=True)
    rs = ""
    bp = "" 
    cdnCtrl = ""
    pl = ""
    for i in mo:
        if type(i) is BiosVProfile:
            bp = i
        elif type(i) is BiosVfConsistentDeviceNameControl:
            cdnCtrl = i
        elif type(i) is BiosVfResumeOnACPowerLoss:
            pl = i

    rs += " "*ts + "- name: Ensure BIOS policy %s is created\n" % sub_root(org, "bios-prof-", policy_name)
    rs += " "*(ts*2) + "cisco_ucs_bios_policy:\n"
    rs += " "*(ts*3) + "name: %s\n" % sub_root(org, "bios-prof-", policy_name)
    rs += " "*(ts*3) + "descr: %s\n" % bp.descr
    rs += " "*(ts*3) + "cdn_control: %s\n" % cdnCtrl.vp_cdn_control
    rs += " "*(ts*3) + "reboot_on_update: %s\n" % bp.reboot_on_update
    rs += " "*(ts*3) + "resume_on_power_loss: %s\n" % pl.vp_resume_on_ac_power_loss
    rs += ansible_ucs_login(ts*3)
    return rs

def create_maint_policy(h, org, ts, policy_name):
    rs = " "*ts + "- name: Ensure Maintenance policy %s is created\n" % sub_root(org, "maint-", policy_name)
    rs += " "*(ts*2) + "cisco_ucs_maint_policy:\n"
    rs += ansible_ucs_login(ts*3)
    return rs

def create_sp_playbook(h, org, sp, ts):
    """
    Starting point for generating Ansible Playbooks.  Starts with Service profile then 
    service profile template. Then goes into all the other resources that make this service profile.
    """
    modules = ""
    t = ""
    t += " "*ts + "- name: Create SP %s\n" % sp.name
    if sp.type == "updating-template":
        t += " "*(ts*2) + "cisco_ucs_spt:\n"
        t += " "*(ts*3) + "spt_list:\n"
        t += " "*(ts*3) + "- name: %s\n" % sp.name
        t += " "*(ts*4) + "template_type: %s\n" % sp.type
    else:
        t += " "*(ts*2) + "cisco_ucs_sp:\n"
        t += " "*(ts*3) + "sp_list:\n"
        t += " "*(ts*3) + "- name: %s\n" % sp.name
        modules += ansible_ucs_login(ts*3)
    if sp.oper_scrub_policy_name:
        t += " "*(ts*4) + "scrub_policy: %s\n" % sub_root(org, "scrub-", sp.oper_scrub_policy_name)
        modules += create_scrub(h, org, ts, sp.oper_scrub_policy_name)
    if sp.oper_vmedia_policy_name:
        t += " "*(ts*4) + "vmedia_policy: %s\n" % sub_root(org, "mnt-cfg-policy-", sp.oper_vmedia_policy_name)
        modules += create_vmedia(h, org, ts, sp.oper_vmedia_policy_name)
    if sp.oper_bios_profile_name:
        t += " "*(ts*4) + "bios_policy: %s\n" % sub_root(org, "bios-prof-", sp.oper_bios_profile_name)
        modules += create_bios_policy(h, org, ts, sp.oper_bios_profile_name)

    if sp.maint_policy_name:
        t += " "*(ts*4) + "maint_policy: %s\n" % sub_root(org, "maint-", sp.oper_maint_policy_name)
        modules += create_maint_policy(h, org, ts, sp.oper_maint_policy_name)
    #if sp.boot_policy_name:
    #if sp.vcon_profile_name:
    #if sp.oper_host_fw_policy_name:
    #if sp.host_fw_policy_name:
    #if sp.ident_pool_name: 
    #vnicLanConnPolicy? 
    #oper_

    rs =  t + "\n" + modules
    return rs

def main():
    parser = argparse.ArgumentParser(description="Connect to UCS and create Ansible Playbook from an existing Service Profile or Service Profile Template.")
    parser.add_argument("user", help = 'The user account to log into UCS: e.g. admin')
    parser.add_argument("password", help='The password to connect to UCS: e.g.: cisco123')
    parser.add_argument("server", help='UCS Manager: e.g: 192.168.3.1')
    parser.add_argument('-o', "--org",
        type=str,
        default='root',
        help='The organization you want these resources created under: e.g: root')
    parser.add_argument('-p', "--profile",
        type=str,
        help='The Service Profile or Profile you want to ansibilize')
    args = parser.parse_args()
    h, msg = login(args.user, args.password, args.server)
    if not msg == "":
        print msg
        return 
    if args.profile:
        sp = get_sp(h, args.profile)
        if sp == "":
            print "no such profile: %s" % args.profile
            sp = select_sp(h)
    else:
        sp = select_sp(h)
    pb = create_sp_playbook(h, "org-" + args.org, sp, 2)
    #print sp
    print pb
    logout(h)

    
if __name__ == '__main__':
    main()
