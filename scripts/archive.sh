#!/bin/env sh

tar -I 'xz -T0 -c -z --best -' -cf 'package/themes-latte.tar.xz' 'themes/latte/'
tar -I 'xz -T0 -c -z --best -' -cf 'package/themes-frappe.tar.xz' 'themes/frappe/'
tar -I 'xz -T0 -c -z --best -' -cf 'package/themes-macchiato.tar.xz' 'themes/macchiato/'
tar -I 'xz -T0 -c -z --best -' -cf 'package/themes-mocha.tar.xz' 'themes/mocha/'
