def extract_metadata(file_path):
    metadata = {
        "file_type": "image",
        "make": "Unknown",
        "camera_model": "Unknown",
        "software": "Unknown",
        "datetime": "Unknown",            
        "datetime_digitized": "Unknown",  
        "exif_version": "Unknown",
        "width": "Unknown",
        "height": "Unknown",
        "gps_latitude": "Unknown",
        "gps_longitude": "Unknown",
        "created_by": "Unknown",
        "modified_by": "Unknown",
        "title": "Unknown",
        "author": "Unknown",
        "description": "Unknown"
    }

    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        tiff = _find_exif_tiff_base(data)
        if tiff is None:
            _fallback_created_modified_unknown(metadata)
            return metadata

        endian = data[tiff:tiff+2]
        if endian == b'II':
            byte_order = 'little'
        elif endian == b'MM':
            byte_order = 'big'
        else:
            _fallback_created_modified_unknown(metadata)
            return metadata

        if _u16(data, tiff+2, byte_order) != 0x002A:
            _fallback_created_modified_unknown(metadata)
            return metadata

        ifd0_rel = _u32(data, tiff+4, byte_order)
        ifd0 = tiff + ifd0_rel
        tags0 = _parse_ifd(data, tiff, ifd0, byte_order)

        if 0x010F in tags0:  
            metadata["make"] = _get_ascii(data, tiff, tags0[0x010F], byte_order)
        if 0x0110 in tags0:  
            metadata["camera_model"] = _get_ascii(data, tiff, tags0[0x0110], byte_order)
        if 0x0131 in tags0:  
            sw = _get_ascii(data, tiff, tags0[0x0131], byte_order)
            metadata["software"] = sw
            metadata["modified_by"] = _normalize_software(sw, metadata.get("make"))

        if 0x0132 in tags0 and metadata["datetime"] == "Unknown":
            dt0 = _get_ascii(data, tiff, tags0[0x0132], byte_order)
            if dt0 and dt0 != "Unknown":
                metadata["datetime"] = dt0

        if 0x0100 in tags0:
            metadata["width"]  = _get_numeric(data, tiff, tags0[0x0100], byte_order)
        if 0x0101 in tags0:
            metadata["height"] = _get_numeric(data, tiff, tags0[0x0101], byte_order)

        exif_ifd_ptr = _get_offset_value(data, tiff, tags0.get(0x8769), byte_order) if 0x8769 in tags0 else None
        gps_ifd_ptr  = _get_offset_value(data, tiff, tags0.get(0x8825), byte_order) if 0x8825 in tags0 else None

        if exif_ifd_ptr:
            exif_ifd = tiff + exif_ifd_ptr
            tags_exif = _parse_ifd(data, tiff, exif_ifd, byte_order)

            if 0x9003 in tags_exif:  
                metadata["datetime"] = _get_ascii(data, tiff, tags_exif[0x9003], byte_order)
            if 0x9004 in tags_exif:  
                metadata["datetime_digitized"] = _get_ascii(data, tiff, tags_exif[0x9004], byte_order)
            if 0x9000 in tags_exif:  
                exv = _get_bytes(data, tiff, tags_exif[0x9000], byte_order)
                if exv:
                    try:
                        s = "".join(chr(b) for b in exv if 48 <= b <= 57)  
                        metadata["exif_version"] = s if s else exv.hex()
                    except:
                        metadata["exif_version"] = exv.hex()

            if 0xA002 in tags_exif:
                w = _get_numeric(data, tiff, tags_exif[0xA002], byte_order)
                if w: metadata["width"] = w
            if 0xA003 in tags_exif:
                h = _get_numeric(data, tiff, tags_exif[0xA003], byte_order)
                if h: metadata["height"] = h

        if gps_ifd_ptr:
            gps_ifd = tiff + gps_ifd_ptr
            tags_gps = _parse_ifd(data, tiff, gps_ifd, byte_order)

            lat = lon = None
            lat_ref = _get_ascii(data, tiff, tags_gps.get(0x0001), byte_order) if 0x0001 in tags_gps else None
            lon_ref = _get_ascii(data, tiff, tags_gps.get(0x0003), byte_order) if 0x0003 in tags_gps else None

            if 0x0002 in tags_gps:
                lat = _get_rational_array(data, tiff, tags_gps[0x0002], byte_order)
            if 0x0004 in tags_gps:
                lon = _get_rational_array(data, tiff, tags_gps[0x0004], byte_order)

            if lat and lon and len(lat) == 3 and len(lon) == 3 and lat_ref and lon_ref:
                lat_dec = _dms_to_decimal(lat, lat_ref)
                lon_dec = _dms_to_decimal(lon, lon_ref)
                metadata["gps_latitude"]  = f"{lat_dec:.6f}"
                metadata["gps_longitude"] = f"{lon_dec:.6f}"

        if metadata["width"] == "Unknown" or metadata["height"] == "Unknown":
            sof_w, sof_h = _jpeg_dimensions_from_sof(data)
            if sof_w and metadata["width"] == "Unknown":
                metadata["width"] = sof_w
            if sof_h and metadata["height"] == "Unknown":
                metadata["height"] = sof_h

        if metadata["datetime_digitized"] == "Unknown" and metadata["datetime"] != "Unknown":
            metadata["datetime_digitized"] = metadata["datetime"]

        if metadata["camera_model"] != "Unknown":
            metadata["created_by"] = metadata["camera_model"]
        elif metadata["make"] != "Unknown":
            metadata["created_by"] = metadata["make"]
            
        if metadata["software"] != "Unknown":
            metadata["modified_by"] = _normalize_software(metadata["software"], metadata.get("make"))
            
        if metadata["camera_model"] == "Unknown" and metadata["software"] == "Unknown":
            _fallback_created_modified_unknown(metadata)

    except Exception as e:
        print(f"[Error] Could not extract image metadata: {e}")

    return metadata

def _find_exif_tiff_base(buf: bytes):
    if not buf.startswith(b'\xff\xd8'):  
        return None
    i = 2
    n = len(buf)
    while i + 4 <= n:
        if buf[i] != 0xFF:
            i += 1
            continue
        marker = buf[i+1]
        i += 2
        if marker in (0xD8, 0xD9):  
            continue
        if i + 2 > n:
            return None
        seg_len = int.from_bytes(buf[i:i+2], 'big')
        if seg_len < 2 or i + seg_len > n:
            return None
        seg_data_start = i + 2
        seg_data_end   = i + seg_len
        if marker == 0xE1:  
            if seg_data_end - seg_data_start >= 6 and buf[seg_data_start:seg_data_start+6] == b'Exif\x00\x00':
                tiff_base = seg_data_start + 6
                if tiff_base + 8 <= n:
                    return tiff_base
        i += seg_len
    return None

def _u16(b, off, order):
    if off+2 > len(b): return 0
    return int.from_bytes(b[off:off+2], order)

def _u32(b, off, order):
    if off+4 > len(b): return 0
    return int.from_bytes(b[off:off+4], order)

def _type_size(t):
    sizes = {1:1,2:1,3:2,4:4,5:8,7:1}
    return sizes.get(t, 1)

def _parse_ifd(buf, tiff_base, ifd_off, order):
    tags = {}
    if ifd_off is None or ifd_off < 0 or ifd_off+2 > len(buf):
        return tags
    count = _u16(buf, ifd_off, order)
    entry = ifd_off + 2
    for _ in range(count):
        if entry+12 > len(buf):
            break
        tag    = _u16(buf, entry+0, order)
        typ    = _u16(buf, entry+2, order)
        cnt    = _u32(buf, entry+4, order)
        value4 = buf[entry+8:entry+12]  
        tags[tag] = (typ, cnt, value4)
        entry += 12
    return tags

def _is_inline(typ, cnt):
    return cnt * _type_size(typ) <= 4

def _get_offset_value(buf, tiff_base, entry, order):
    if entry is None: return None
    typ, cnt, value4 = entry
    if _is_inline(typ, cnt):
        return None
    return int.from_bytes(value4, order)

def _get_bytes(buf, tiff_base, entry, order):
    if entry is None: return None
    typ, cnt, value4 = entry
    size = _type_size(typ) * cnt
    if _is_inline(typ, cnt):
        return value4[:size]
    off = int.from_bytes(value4, order)
    start = tiff_base + off
    end = start + size
    if start < 0 or end > len(buf): return None
    return buf[start:end]

def _get_ascii(buf, tiff_base, entry, order):
    b = _get_bytes(buf, tiff_base, entry, order)
    if not b: return "Unknown"
    try:
        s = b.split(b'\x00', 1)[0].decode(errors='ignore').strip()
        return s if s else "Unknown"
    except:
        return "Unknown"

def _get_numeric(buf, tiff_base, entry, order):
    if entry is None: return "Unknown"
    typ, cnt, value4 = entry
    if typ in (3, 4):  
        b = _get_bytes(buf, tiff_base, entry, order)
        if not b: return "Unknown"
        step = _type_size(typ)
        if len(b) < step: return "Unknown"
        if typ == 3:
            return int.from_bytes(b[:2], order)
        else:
            return int.from_bytes(b[:4], order)
    elif typ == 5:  
        arr = _get_rational_array(buf, tiff_base, entry, order)
        if arr and len(arr) > 0:
            n, d = arr[0]
            return (n/d) if d else "Unknown"
        return "Unknown"
    else:
        return "Unknown"

def _get_rational_array(buf, tiff_base, entry, order):
    if entry is None: return None
    typ, cnt, value4 = entry
    if typ != 5 or cnt <= 0:
        return None
    b = _get_bytes(buf, tiff_base, entry, order)
    if not b: return None
    out = []
    for i in range(cnt):
        s = i*8
        if s+8 > len(b): break
        num = int.from_bytes(b[s:s+4], order)
        den = int.from_bytes(b[s+4:s+8], order)
        out.append((num, den if den != 0 else 1))
    return out

def _dms_to_decimal(dms, ref):
    deg = dms[0][0]/dms[0][1]
    minu = dms[1][0]/dms[1][1]
    sec = dms[2][0]/dms[2][1]
    val = deg + (minu/60.0) + (sec/3600.0)
    if ref.upper() in ("S", "W"):
        val = -val
    return val

def _jpeg_dimensions_from_sof(buf: bytes):
    if not buf.startswith(b'\xff\xd8'):
        return (None, None)
    i, n = 2, len(buf)
    while i + 4 <= n:
        if buf[i] != 0xFF:
            i += 1
            continue
        marker = buf[i+1]
        i += 2
        if marker in (0xD8, 0xD9):  
            continue
        if i + 2 > n:
            break
        seg_len = int.from_bytes(buf[i:i+2], 'big')
        if seg_len < 2 or i + seg_len > n:
            break
        seg_data_start = i + 2
        seg_data_end   = i + seg_len
        if (0xC0 <= marker <= 0xC3) or (0xC5 <= marker <= 0xC7) or (0xC9 <= marker <= 0xCB) or (0xCD <= marker <= 0xCF):
            seg = buf[seg_data_start:seg_data_end]
            if len(seg) >= 7:
                height = int.from_bytes(seg[1:3], 'big')
                width  = int.from_bytes(seg[3:5], 'big')
                return (width, height)
        i += seg_len
    return (None, None)

def _normalize_software(sw, make=None):
    s = (sw or "").strip()
    sl = s.lower()
    if "snapseed" in sl:   return "Google Snapseed"
    if "photoshop" in sl:  return "Adobe Photoshop"
    if "lightroom" in sl:  return "Adobe Lightroom"
    if "instagram" in sl:  return "Instagram"
    if "whatsapp" in sl:   return "WhatsApp (metadata stripped)"
    if "gimp" in sl:       return "GIMP"
    if "apple" in sl and "photos" in sl: return "Apple Photos"
    if make and isinstance(make, str):
        mk = make.lower()
        if mk == "apple" and all(ch.isdigit() or ch == '.' for ch in s) and any(ch == '.' for ch in s):
            return f"Apple iOS {s} (Photos)"
    return s

def _fallback_created_modified_unknown(metadata):
    metadata["created_by"]  = "Unknown (Possibly Metadata-Stripped Image)"
    metadata["modified_by"] = "Unknown (Possibly Metadata-Stripped Image)"