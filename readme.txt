After having installed all the libraries needed, running the resnet is very simple: just run the forward.py file inside tensorflow, using python:
- (tensorflow) python forward.py

NB: the forward.py has a parameter inside which specify the length of the net for usage of pretrained models.

Our scripts:

- crop_image.py : given the img name and an amount of pixels, it produces 4 images, each one with a cropped size of the given amount
- run_crop.py : script to run the crop_img_grid script which produce pixels*pixels images (python run_crop.py /datas/teaching/projects/spring2018/ps34/Data/Images_Plans/)
- extract_frames.sh : bash script to extract frames from video (parameters: video path + list frame number)
