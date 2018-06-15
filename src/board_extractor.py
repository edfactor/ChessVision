"""
CNN-based board extraction. 
Methods to extract boards from images.
If run as main, attempts to extract boards from all images in in <indir>,
and outputs results in <outdir>

Usage:
python board_extractor.py -d ../data/images/ -o ./data/boards/
"""

from util import listdir_nohidden, ratio, draw_contour, randomColor, parse_arguments, BoardExtractionError
import numpy as np
import cv2
from tensorflow import Graph, Session
#import matplotlib.pyplot as plt

SIZE = (256, 256)

def load_extractor():
    print("Loading board extraction model..")
    from u_net import get_unet_256
    model = get_unet_256()
    model.load_weights('../weights/best_weights.hdf5')
    #model._make_predict_function()

    print("Loading board extraction model.. DONE")
    return model

def extract_board(image, orig):
    model = load_extractor()
    #model = load_extractor()
    #predict chessboard-mask:
    print("Extracting board...")
    image_batch = np.array([image], np.float32) / 255
    
    predicted_mask_batch = model.predict(image_batch)
    del model

    predicted_mask = predicted_mask_batch[0].reshape(SIZE)
    mask = fix_mask(predicted_mask)
    
    #approximate chessboard-mask with a quadrangle
    approx = find_quadrangle(mask)

    if approx is None:
        print("Contour approximation failed!")
        raise BoardExtractionError()
    
    orig_size = (orig.shape[0], orig.shape[1])
    approx = scale_approx(approx, orig_size) 
    
    #extract board
    board = extract_perspective(orig, approx, 512, 512)

    board = cv2.cvtColor(board, cv2.COLOR_BGR2GRAY)
    board = cv2.flip(board, 1)
    print("Extracting board... DONE")
    return board

def fix_mask(mask):
    mask *= 255
    mask = mask.astype(np.uint8)
    mask[mask > 80] = 255
    mask[mask <= 80] = 0
    return mask


def scale_approx(approx, orig_size):
    sf = orig_size[0]/256.0
    scaled = np.array(approx * sf, dtype=np.uint32)
    return scaled


def rotate_quadrangle(approx):
    if approx[0,0,0] < approx[2,0,0]:
        approx = approx[[3, 0, 1, 2],:,:]
    return approx

def find_quadrangle(mask):

    #plt.figure()
    #plt.imshow(mask, cmap="gray")
    #plt.show()

    #(_, mask) = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    #_, contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    #plt.figure()
    #plt.imshow(mask, cmap="gray")
    #plt.show()

    _, contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_KCOS)

    #plt.figure()
    #plt.imshow(mask, cmap="gray")
    #plt.show()
    
    #mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
    #for i in range(len(contours)):
    #    cv2.drawContours(mask, contours, i, randomColor(), thickness=4)

    #plt.figure()
    #plt.imshow(mask)
    #plt.show()

    mask_area = float(mask.shape[0]*mask.shape[1])
    contour_areas = np.array(map(lambda x: cv2.contourArea(x), contours))
    contour_areas /= mask_area
    print("Found {} contour(s)".format(len(contours)))
    print("Contour area(s): {}".format(contour_areas))

    #contours = ignore_contours(mask, contours)
    
    approx = None

    for i in range(len(contours)):
        cnt = contours[i]
        area = cv2.contourArea(cnt)
        
        arclen = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.1*arclen, True)
        
        if len(approx) != 4:
            continue

        approx = rotate_quadrangle(approx)
        break

    return approx

def extract_perspective(image, perspective, w, h):
    
    dest = ((0,0), (w, 0), (w,h), (0, h))

    if perspective is None:
        im_w, im_h,_ = image.shape
        perspective = ((0,0), (im_w, 0), (im_w,im_h), (0, im_h))

    perspective = np.array(perspective, np.float32)
    dest = np.array(dest, np.float32)

    coeffs = cv2.getPerspectiveTransform(perspective, dest)
    return cv2.warpPerspective(image, coeffs, (w, h))

def ignore_contours(img,
                   contours,
                   hierarchy=None,
                   min_ratio_bounding=0.6,
                   min_area_percentage=0.01,
                   max_area_percentage=0.40):
    """Filters a contour list based on some rules. If hierarchy != None,
    only top-level contours are considered.
    :param img: source image
    :param contours: list of contours
    :param hierarchy: contour hierarchy
    :param min_ratio_bounding: minimum contour area vs. bounding box area ratio
    :param min_area_percentage: minimum contour vs. image area percentage
    :param max_area_percentage: maximum contour vs. image area percentage
    :returns: a list with the unfiltered countour ids
    """

    ret = []
    i = -1

    if hierarchy is not None:
        while len(hierarchy.shape) > 2:
            hierarchy = np.squeeze(hierarchy, 0)
    img_area = img.shape[0] * img.shape[1]

    for c in contours:
        i += 1

        if hierarchy is not None and \
           not hierarchy[i][2] == -1:
            continue

        _,_,w,h = tmp = cv2.boundingRect(c)
        if ratio(h,w) < min_ratio_bounding:
            continue

        contour_area = cv2.contourArea(c)
        img_contour_ratio = ratio(img_area, contour_area)
        if img_contour_ratio < min_area_percentage:
            continue
        if img_contour_ratio > max_area_percentage:
            continue

        ret.append(c)

    return ret

def main():

    _, image_dir, board_dir = parse_arguments()

    for f in listdir_nohidden(image_dir):

        print("Extracting board from {}.....".format(f))

        image = cv2.imread(image_dir + f)
        
        comp_image = cv2.resize(image, (256,256), interpolation=cv2.INTER_LINEAR)

        try:
            board = extract_board(comp_image, image)

        except Exception as e:
            print("Board extraction failed due to unexpected error '{}'.. \nMoving on!".format(e))
            continue
        
        cv2.imwrite(board_dir + "/x_" + f, board)
        print("--SUCCESS!!")

if __name__ == "__main__":
    main()