#!/usr/bin/python

import os

uid = os.getuid()
euid = os.geteuid()

print("uid : ", uid)
print("euid : ", euid)

os.setuid(20)

uid = os.getuid()
euid = os.geteuid()

print("uid : ", uid)
print("euid : ", euid)
