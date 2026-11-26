
import os
import cv2
import numpy as np
import glob



def preprocess_handwritten_exam(image_path: str, output_path: str) -> None:
    img = cv2.imread(image_path)
    if img is None:
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    background = cv2.GaussianBlur(gray, (0, 0), sigmaX=15)
    normalized = cv2.divide(gray, background, scale=255)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(normalized)


    denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=30, sigmaSpace=30)


    adaptive = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=21, C=8
    )
    _, otsu = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    binarized = cv2.bitwise_and(adaptive, otsu)

    inverted = cv2.bitwise_not(binarized)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(inverted, connectivity=8)
    
    cleaned = np.zeros_like(inverted)
    min_area = 12  
    for label in range(1, n_labels):
        if stats[label, cv2.CC_STAT_AREA] >= min_area:
            cleaned[labels == label] = 255
            
    final_image = cv2.bitwise_not(cleaned)

  
    cv2.imwrite(output_path, final_image)

