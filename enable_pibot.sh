#!/bin/bash

ifdown wlan0
rm /etc/network/interfaces && ln -s /etc/network/interfaces.pibot /etc/network/interfaces
ifup wlan0

rm /etc/rc.local && ln -s /etc/rc.local.pibot /etc/rc.local

update-rc.d nginx enable
update-rc.d hostapd enable
update-rc.d dnsmasq enable
