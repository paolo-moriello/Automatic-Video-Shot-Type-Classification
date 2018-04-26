import sys
import os
import subprocess
import argparse


if(len(sys.argv) < 3):
	print("Usage: python3 parse_video_info.py path_to_video(no extention) mode")
	print("Mode: -gros_plan (face area > 0.25% of frame area)")
	print("Mode: -plan_moyen (face on the frame's head)")
	exit()

file_ = sys.argv[1]+"_faces.txt"
video_ = sys.argv[1]+"_faces.MP4"

mode = sys.argv[2]

#### UTILS FUNCTIONS
# base and high of the two images
def get_ratio(b1, h1, b2, h2):
	a1 = b1*h1
	a2 = b2*h2

	if(a1 > a2):
		return a2/a1
	return a1/a2

# coordinates is an array of 4 points: (x_top, y_top, x_bottom, y_bottom)
def on_head(coordinates, h, n_split=3):
	lower_limit_h = h/n_split
	y1_down = coordinates[3]
	return (y1_down <= lower_limit_h)

# coordinates is an array of 4 points: (x_top, y_top, x_bottom, y_bottom)
# b and h are the dimensions of th original frame
# n_split is the number of "split" on which the frame will be divided into
# large_split is to decide if we want only the center split, or to esclude only the first and last
def on_center(coordinates, b, h, n_split=3, large_split=True):
	if large_split:
		upper_limit_h = h/n_split
		lower_limit_h = h*(n_split-1)/n_split
	else:
		if(n_split % 2 == 0):
			mid = n_split / 2
			upper_limit_h = h*(mid-1)/n_split
			lower_limit_h = h*(mid+1)/n_split
		else:
			mid = n_split // 2
			upper_limit_h = h*mid/n_split
			lower_limit_h = h*(mid+1)/n_split
	return (coordinates[1] >= upper_limit_h and coordinates[3] <= lower_limit_h)



#### MAIN ###

# read video dimensions first
cmd_ = "./get_video_resolution.sh "+video_
p = subprocess.Popen(cmd_ , shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = p.communicate()
dim = stdout.strip().split("x") # dim[0] = b, dim[1] = h

# parse input file
frames = {}
with open(file_, "r") as f:
	for line in f:
		words = line.split()
		frame = words[0]
		x_top = int(words[1])
		y_top = int(words[2])
		x_down = int(words[3])
		y_down = int(words[4])
		
		if frame not in frames.keys():
			frames[frame] = [(x_top, y_top, x_down, y_down)]
		else:
			frames[frame].append((x_top, y_top, x_down, y_down))

# GROS PLAN
frms = []
if(mode == '-gros_plan'):
	for key, value in frames.items():
		if(len(value) == 1):
			coordinates = value[0]
			ratio = get_ratio(abs(coordinates[2]-coordinates[0]), abs(coordinates[1]-coordinates[3]), int(dim[0]), int(dim[1]))
			if ratio > 0.25:
				frms.append(key)
# PLAN MOYEN
elif(mode == '-plan_moyen'):
	for key, value in frames.items():
		if(len(value) == 1):
			coordinates = value[0]	
			if on_head(coordinates, int(dim[1]), n_split=5):
				frms.append(key)
elif(mode == '-plan_rapproche'):
	for key, value in frames.items():
		if(len(value) == 1):
			coordinates = value[0]	
			if on_center(coordinates, int(dim[0]), int(dim[1]), n_split=3):
				frms.append(key)
else:
	frms = list(frames.keys())
print(" ".join(str(x) for x in frms))
