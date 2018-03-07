# UCS Service Profile 2 Ansible Playbook

Let's say you already have a sweet UCS Service Profile/Template that is configured in UCS and you want to Ansible all the things. 

Well this is the tool for you!  It takes your existing Service Profile creates an ansible playbook that you can use for back up, Infrastructure as Code, or deploy on another system.

## Prereqs
You need the UCSSDK.  This is usually just: 

```
pip install ucsmsdk
``` 

## Notes

Work in progress.   

## Supported

| Category | Task                     | Module Name                | Status |
| -------- | ----                     | -----------                | ------ |
| Server   | Service Profile          | cisco\_ucs\_sp             | [x]    |
|          | Service Profile Template | cisco\_ucs\_spt            | [x] |
|          | Bios/Disk Scrub Policy        | cisco\_ucs\_scrub_policy   | [x] |
|          | vMedia Policy            | cisco\_ucs\_vmedia\_policy | [x] |
|          | Bios Policy              | cisco\_ucs\_bios\_policy   | [x]  |
|          | Maintenance Policy       | cisco\_ucs\_maint\_policy  | almost|

## Running

There is a help menu:

```
./ucssp2ansible.py -h
usage: ucssp2ansible.py [-h] [-o ORG] [-p PROFILE] user password server

Connect to UCS and create Ansible Playbook from an existing Service Profile or
Service Profile Template.

positional arguments:
  user                  The user account to log into UCS: e.g. admin
  password              The password to connect to UCS: e.g.: cisco123
  server                UCS Manager: e.g: 192.168.3.1

optional arguments:
  -h, --help            show this help message and exit
  -o ORG, --org ORG     The organization you want these resources created
                        under: e.g: root
  -p PROFILE, --profile PROFILE
                        The Service Profile or Profile you want to ansibilize
```

But basically, suppose I wanted to create an ansible playbook from a service profile called KUBAM.  Then I would run: 

```
./ucssp2ansible.py -p KUBAM admin password myucsserver
```

This would then spit out something like: 

```
  - name: Create SP Kubernetes
    cisco_ucs_spt:
      spt_list:
      - name: Kubernetes
        template_type: updating-template
        scrub_policy: kube
        vmedia_policy: kube
        bios_policy: kube
        maint_policy: default

  - name: Ensure scrub policy is created
    cisco_ucs_scrub_policy:
      name: kube
      descr: Destroy data when SP is unassociated
      disk_scrub: yes
      flex_flash_scrub: no
      bios_settings_scrub: no
      ucs_ip: {{ucs_ip}}
      ucs_username: {{ ucs_username }}
      ucs_password: {{ ucs_password }}
  - name: Ensure vmedia policy is created
    cisco_ucs_vmedia_policy:
      name: kube
      descr: Kubernetes Boot Media
      retry: yes
      mounts:
      - name: centos7.4-boot
        device: cdd
        protocol: http
        remote_ip: 172.28.225.135
        file: centos7.4-boot.iso
        path: /kubam
      - name: kickstartImage
        device: hdd
        protocol: http
        remote_ip: 172.28.225.135
        file: variable
        path: /kubam
      ucs_ip: {{ucs_ip}}
      ucs_username: {{ ucs_username }}
      ucs_password: {{ ucs_password }}
  - name: Ensure BIOS policy kube is created
    cisco_ucs_bios_policy:
      name: kube
      descr: KUBaM Bios settings
      cdn_control: enabled
      reboot_on_update: yes
      resume_on_power_loss: last-state
      ucs_ip: {{ucs_ip}}
      ucs_username: {{ ucs_username }}
      ucs_password: {{ ucs_password }}
  - name: Ensure Maintenance policy default is created
    cisco_ucs_maint_policy:
      ucs_ip: {{ucs_ip}}
      ucs_username: {{ ucs_username }}
      ucs_password: {{ ucs_password }}
```

The output of that could be used as a playbook for Ansible.  

```
./ucssp2ansible.py -p KUBAM admin password myucsserver > ~/playbook-dir/kubam-profile.yaml
```

Now I can use this profile to deploy other UCS servers. 
             