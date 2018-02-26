# UCS Service Profile 2 Ansible Playbook

Let's say you already have a sweet UCS Service Profile/Template that is configured in UCS and you want to Ansible all the things. 

Well this is the tool for you!  It takes your existing Service Profile creates an ansible playbook that you can use for back up, Infrastructure as Code, or deploy on another system.

## Prereqs
You need the UCSSDK.  This is usually just: 

```
pip install ucsmsdk
``` 

## Notes

Work in progress.  At present most values are hard coded and will be updated as it starts to work.  In fact, right now, practically nothing works.   

## Supported

| Category | Task                     | Module Name                | Status |
| -------- | ----                     | -----------                | ------ |
| Server   | Service Profile          | cisco\_ucs\_sp             | [x]    |
|          | Service Profile Template | cisco\_ucs\_spt            | [x] |
|          | Bios Scrub Policy        | cisco\_ucs\_scrub_policy   | [x] |
|          | vMedia Policy            | cisco\_ucs\_vmedia\_policy | [x] |
