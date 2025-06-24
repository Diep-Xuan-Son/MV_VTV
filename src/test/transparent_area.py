import cv2
import numpy as np


def make_biggest_area_transparent_otsu(image_path, output_path, invert_mask=False, preview=False):
    """
    Find biggest contour using Otsu thresholding and make it transparent
    """
    # Read image
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Error: Could not load image from {image_path}")
        return
    
    # Convert to RGBA if needed
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img[:,:,:3], cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply Otsu thresholding
    _, otsu_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Invert if needed (sometimes background is white, sometimes black)
    if invert_mask:
        otsu_thresh = cv2.bitwise_not(otsu_thresh)
    
    # Apply morphological operations to clean up
    kernel = np.ones((5,5), np.uint8)
    otsu_thresh = cv2.morphologyEx(otsu_thresh, cv2.MORPH_CLOSE, kernel)
    otsu_thresh = cv2.morphologyEx(otsu_thresh, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(otsu_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("No contours found")
        return
    
    # Find the biggest contour by area
    biggest_contour = max(contours, key=cv2.contourArea)
    biggest_area = cv2.contourArea(biggest_contour)
    
    print(f"Found {len(contours)} contours")
    print(f"Biggest contour area: {biggest_area}")
    
    # Create mask for the biggest contour
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [biggest_contour], 255)
    
    # Preview option
    if preview:
        preview_img = img.copy()
        cv2.drawContours(preview_img, [biggest_contour], -1, (0, 255, 0, 255), 2)
        cv2.imshow('Biggest Contour Preview', preview_img)
        cv2.imshow('Otsu Threshold', otsu_thresh)
        cv2.imshow('Mask', mask)
        print("Press any key to continue or 'q' to quit...")
        key = cv2.waitKey(0)
        cv2.destroyAllWindows()
        if key == ord('q'):
            return
    
    # Make the biggest area transparent
    img[mask == 255, 3] = 0
    
    # Save result
    cv2.imwrite(output_path, img)
    print(f"Biggest area made transparent and saved to {output_path}")


if __name__=="__main__":

    make_biggest_area_transparent_otsu('data_test/bg.jpg', 'data_test/bg1111.png', preview=True)