import cv2
import os
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

QR_LABEL_MAP = {
    "SECTION:INFO|DEBUT":      "info",
    "SECTION:QCM|DEBUT":       "qcm",
    "SECTION:REDACTION|DEBUT": "redaction",
    "SECTION:CODE|DEBUT":      "code",
}

SECTION_ORDER = ["info", "qcm", "redaction", "code"]


def normalize_part_name(raw_data):
    """Retourne le nom de la section si connu, sinon None."""
    if raw_data in QR_LABEL_MAP:
        return QR_LABEL_MAP[raw_data]
    return None


def load_qr_detector():
    detect_prototxt   = os.path.join(MODELS_DIR, "detect.prototxt")
    detect_caffemodel = os.path.join(MODELS_DIR, "detect.caffemodel")
    sr_prototxt       = os.path.join(MODELS_DIR, "sr.prototxt")
    sr_caffemodel     = os.path.join(MODELS_DIR, "sr.caffemodel")

    missing = [p for p in (detect_prototxt, detect_caffemodel, sr_prototxt, sr_caffemodel)
               if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(
            "Fichiers de modele wechat_qrcode manquants : " + ", ".join(missing) +
            f"\nTelechargez-les depuis https://github.com/WeChatCV/opencv_3rdparty/tree/wechat_qrcode"
            f"\net placez-les dans : {MODELS_DIR}"
        )

    if not hasattr(cv2, "wechat_qrcode_WeChatQRCode"):
        raise RuntimeError(
            "Le module wechat_qrcode n'est pas disponible.\n"
            "Installez : pip install opencv-contrib-python --break-system-packages"
        )

    return cv2.wechat_qrcode_WeChatQRCode(
        detect_prototxt, detect_caffemodel, sr_prototxt, sr_caffemodel
    )


def decode_qrcodes(detector, img):
    """Returns list of {data, y} sorted by vertical position."""
    for scale in (1, 2, 3, 4):
        probe = img if scale == 1 else cv2.resize(
            img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )
        res, points = detector.detectAndDecode(probe)
        if res:
            results = []
            for data, pts in zip(res, points):
                if not data:
                    continue
                top_y = float(np.min(pts[:, 1])) / scale
                results.append({"data": data, "y": top_y})
            if results:
                return results
    return []


def save_segment(files, input_dir, start_img_idx, start_y,
                 end_img_idx, end_y, output_dir, part_name):

    chunks = []

    for j in range(start_img_idx, end_img_idx + 1):

        f_img = cv2.imread(os.path.join(input_dir, files[j]))
        if f_img is None:
            continue

        h, w = f_img.shape[:2]

        sy = max(0, int(start_y))
        ey = min(h, int(end_y))

        if j == start_img_idx and j == end_img_idx:
            crop = f_img[sy:ey, :]

        elif j == start_img_idx:
            crop = f_img[sy:, :]

        elif j == end_img_idx:
            crop = f_img[:ey, :]

        else:
            crop = f_img

        # ignorer les images vides
        if crop is None or crop.size == 0:
            print(
                f"[WARNING] Segment vide : {part_name} "
                f"(page={j}, sy={sy}, ey={ey})"
            )
            continue

        chunks.append(crop)

    if len(chunks) == 0:
        print(f"[WARNING] Aucun contenu pour {part_name}")
        return

    max_w = max(c.shape[1] for c in chunks)

    resized_chunks = []

    for c in chunks:

        if c.shape[0] == 0 or c.shape[1] == 0:
            continue

        new_h = int(c.shape[0] * max_w / c.shape[1])

        resized_chunks.append(
            cv2.resize(c, (max_w, new_h))
        )

    if len(resized_chunks) == 0:
        print(f"[WARNING] Aucun chunk valide pour {part_name}")
        return

    combined = np.vstack(resized_chunks)

    out_path = os.path.join(output_dir, f"{part_name}.png")

    cv2.imwrite(out_path, combined)

    print(f"✓ Saved {out_path}")


def segment_images(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    files    = sorted([f for f in os.listdir(input_dir)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    detector = load_qr_detector()

    # Collect ALL qr events across all pages first
    all_events = []  # {section, img_idx, y, is_valid}

    for i, filename in enumerate(files):
        img = cv2.imread(os.path.join(input_dir, filename))
        if img is None:
            continue
        qrs = decode_qrcodes(detector, img)
        for qr in sorted(qrs, key=lambda q: q["y"]):
            section = normalize_part_name(qr["data"])
            is_valid = section is not None
            
            if not is_valid:
                # On garde une trace du QR inconnu pour qu'il serve de "mur" de fin
                section = f"UNKNOWN_{qr['data']}"
                print(f"  [!] QR inconnu '{qr['data']}' détecté dans {filename} -> servira de limite mais ne sera pas enregistré.")
            
            all_events.append({
                "section": section, 
                "img_idx": i, 
                "y": qr["y"], 
                "is_valid": is_valid
            })
            
            if is_valid:
                print(f"  QR '{section}' détecté — {filename}  y={qr['y']:.0f}")

    # Now segment: each section runs from its QR to just before the next QR
    found_parts = set()
    for idx, event in enumerate(all_events):
        section       = event["section"]
        is_valid      = event["is_valid"]
        
        # Si ce n'est pas une section valide, on l'ignore pour la sauvegarde
        if not is_valid:
            print(f"  [!] Segment '{section}' ignoré (non enregistré).")
            continue

        start_img_idx = event["img_idx"]
        start_y       = event["y"]

        if idx + 1 < len(all_events):
            # End just above the next section's QR code (même si le suivant est inconnu)
            next_event  = all_events[idx + 1]
            end_img_idx = next_event["img_idx"]
            end_y       = next_event["y"]  # crop stops before the next QR
        else:
            # Last section: go to the bottom of the last page
            last_img = cv2.imread(os.path.join(input_dir, files[start_img_idx]))
            end_img_idx = start_img_idx
            end_y       = last_img.shape[0] if last_img is not None else 0

        print(f"  Segment '{section}': page {start_img_idx} y={start_y:.0f} "
              f"-> page {end_img_idx} y={end_y:.0f}")

        save_segment(files, input_dir, start_img_idx, start_y,
                     end_img_idx, end_y, output_dir, section)
        found_parts.add(section)

    expected = {"info", "qcm", "redaction", "code"}
    missing  = expected - found_parts
    if missing:
        print(f"\n[!] Parties manquantes : {missing}")
  
