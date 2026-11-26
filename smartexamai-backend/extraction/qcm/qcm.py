import cv2
import numpy as np
import json

def process_qcm(image_path: str, template_path: str):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"L'image student est introuvable : {image_path}")
        
    original = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    H_img, W_img = gray.shape


    gray[0:int(H_img*0.18), 0:int(W_img*0.22)] = 255

    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    markers = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 150:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        ratio = w / float(h)

        if 0.8 < ratio < 1.2:
            roi = thresh[y:y+h, x:x+w]
            fill = cv2.countNonZero(roi) / (w*h)

            if fill > 0.8:
                markers.append((x, y, w, h))

    if len(markers) < 4:
        raise ValueError(f"Seulement {len(markers)} marqueurs trouvés, il en faut au moins 4.")
    def center(marker):
        x, y, w, h = marker
        return (x + w/2, y + h/2)

    
    tl = min(markers, key=lambda m: center(m)[0]**2 + center(m)[1]**2)
    tr = min(markers, key=lambda m: (W_img-center(m)[0])**2 + center(m)[1]**2)
    bl = min(markers, key=lambda m: center(m)[0]**2 + (H_img-center(m)[1])**2)
    br = min(markers, key=lambda m: (W_img-center(m)[0])**2 + (H_img-center(m)[1])**2)

    centers = np.array([
        center(tl),
        center(tr),
        center(bl),
        center(br)
    ])

    tl = centers[0]
    tr = centers[1]
    bl = centers[2]
    br = centers[3]

    centers = []
    for x, y, w, h in markers:
        centers.append((x + w//2, y + h//2))

    centers = np.array(centers)

    s = centers.sum(axis=1)
    diff = np.diff(centers, axis=1)

    tl = centers[np.argmin(s)]
    br = centers[np.argmax(s)]
    tr = centers[np.argmin(diff)]
    bl = centers[np.argmax(diff)]

    margin = 20

    x1 = int(max(0, min(tl[0], bl[0]) - margin))
    x2 = int(min(original.shape[1], max(tr[0], br[0]) + margin))
    y1 = int(max(0, min(tl[1], tr[1]) - margin))
    y2 = int(min(original.shape[0], max(bl[1], br[1]) + margin))

    grid = original[y1:y2, x1:x2]

    TARGET_WIDTH = 371
    TARGET_HEIGHT = 627 

    student = cv2.resize(
        grid,
        (TARGET_WIDTH, TARGET_HEIGHT),
        interpolation=cv2.INTER_CUBIC
    )

    template = cv2.imread(template_path)
    if template is None:
        raise FileNotFoundError(f"L'image template est introuvable : {template_path}")

    orb = cv2.ORB_create(3000)

    kp1, des1 = orb.detectAndCompute(template, None)
    kp2, des2 = orb.detectAndCompute(student, None)

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = matcher.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1,1,2)
    pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1,1,2)

    H_mat, _ = cv2.findHomography(pts2, pts1, cv2.RANSAC)

    aligned = cv2.warpPerspective(
        student,
        H_mat,
        (template.shape[1], template.shape[0])
    )

    gray_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

    th = cv2.threshold(
        gray_aligned,
        180,
        255,
        cv2.THRESH_BINARY_INV
    )[1]


    first_x = 113
    first_y = 120

    gap_x = 62
    gap_y = 47

    radius = 19

    letters = ["A", "B", "C", "D"]
    answers = {}
    vis = aligned.copy()

    for q in range(10):
        y = first_y + q * gap_y
        selected = []

        for c in range(4):
            x = first_x + c * gap_x

            mask = np.zeros(th.shape, dtype=np.uint8)
            cv2.circle(mask, (x, y), radius, 255, -1)

            roi = cv2.bitwise_and(th, th, mask=mask)
            filled = cv2.countNonZero(roi)

            area = np.pi * radius * radius
            ratio = filled / area

            if ratio > 0.45:
                selected.append(letters[c])
                color = (0, 255, 0) 
            else:
                color = (0, 0, 255) 

            cv2.circle(vis, (x, y), radius, color, 2)

        answers[q+1] = selected



    return answers

