#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# This script generates the spinal segments for the PAM50 template. It is based on the article by Frostell et al.
# https://www.frontiersin.org/articles/10.3389/fneur.2016.00238/full
# For more context, see: https://github.com/spinalcordtoolbox/PAM50/issues/16
# 
# Author: Julien Cohen-Adad

# Identification of the slice on the PAM50 template that corresponds to the upper portion of the C1 nerve rootlets
z_top = 984
# Identification of the slice on the PAM50 template that corresponds to the caudal end of the spinal cord
z_bottom = 40

# Compute the length of the spinal cord (in mm), knowing that the pixel size along Z is 0.5mm.
length_spinalcord = 0.5 * (984 - 40)

