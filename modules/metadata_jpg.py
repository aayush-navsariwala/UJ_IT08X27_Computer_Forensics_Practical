import struct

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
            
        png_sig = b'\x89PNG\r\n\x1a\n'
        if not data.startswith(png_sig):
            return metadata
        
        

        exif_start = data.find(b'\xff\xe1')
        if exif_start == -1:
            _fallback_created_modified_unknown(metadata)
            return metadata

        tiff = exif_start + 10

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
            metadata["modified_by"] = _normalize_software(sw)

        if 0x0100 in tags0:
            metadata["width"]  = _get_numeric(data, tiff, tags0[0x0100], byte_order)
        if 0x0101 in tags0:
            metadata["height"] = _get_numeric(data, tiff, tags0[0x0101], byte_order)

        exif_ifd_ptr = None
        if 0x8769 in tags0:
            exif_ifd_ptr = _get_offset_value(data, tiff, tags0[0x8769], byte_order)

        gps_ifd_ptr = None
        if 0x8825 in tags0:
            gps_ifd_ptr = _get_offset_value(data, tiff, tags0[0x8825], byte_order)

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
                        s = "".join(chr(b) for b in exv if b >= 48 and b <= 57)  
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

        if metadata["camera_model"] != "Unknown":
            metadata["created_by"] = metadata["camera_model"]
        elif metadata["make"] != "Unknown":
            metadata["created_by"] = metadata["make"]

        if metadata["software"] != "Unknown":
            metadata["modified_by"] = _normalize_software(metadata["software"])

        if metadata["camera_model"] == "Unknown" and metadata["software"] == "Unknown":
            _fallback_created_modified_unknown(metadata)

    except Exception as e:
        print(f"[Error] Could not extract image metadata: {e}")

    return metadata

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
    if ifd_off < 0 or ifd_off+2 > len(buf):
        return tags
    count = _u16(buf, ifd_off, order)
    entry = ifd_off + 2
    for _ in range(count):
        if entry+12 > len(buf): break
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
            n,d = arr[0]
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

def _normalize_software(sw):
    s = sw.lower()
    if "snapseed" in s:   return "Google Snapseed"
    if "photoshop" in s:  return "Adobe Photoshop"
    if "lightroom" in s:  return "Adobe Lightroom"
    if "instagram" in s:  return "Instagram"
    if "whatsapp" in s:   return "WhatsApp (metadata stripped)"
    if "gimp" in s:       return "GIMP"
    if "apple" in s and "photos" in s: return "Apple Photos"
    return sw

def _fallback_created_modified_unknown(metadata):
    metadata["created_by"]  = "Unknown (Possibly Metadata-Stripped Image)"
    metadata["modified_by"] = "Unknown (Possibly Metadata-Stripped Image)"