# modules/metadata_png.py
import struct
import zlib

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

        pos = 8
        while pos + 8 <= len(data):
            length = struct.unpack(">I", data[pos:pos+4])[0]
            ctype  = data[pos+4:pos+8]
            cdata  = data[pos+8:pos+8+length]
            pos += 12 + length  

            if ctype == b'IHDR' and length >= 8:
                metadata["width"]  = struct.unpack(">I", cdata[0:4])[0]
                metadata["height"] = struct.unpack(">I", cdata[4:8])[0]

            elif ctype == b'tEXt':
                kw, text = _parse_tEXt(cdata)
                _assign_text_field(metadata, kw, text)

            elif ctype == b'iTXt':
                kw, text = _parse_iTXt(cdata)
                _assign_text_field(metadata, kw, text)

            elif ctype == b'zTXt':
                kw, text = _parse_zTXt(cdata)
                _assign_text_field(metadata, kw, text)

            if ctype == b'IEND':
                break

        if metadata["software"] != "Unknown":
            metadata["modified_by"] = _normalize_software(metadata["software"])
            if metadata["created_by"] == "Unknown":
                metadata["created_by"] = metadata["modified_by"]

        if all(metadata[k] == "Unknown" for k in ["software", "title", "author", "description", "datetime"]):
            metadata["created_by"]  = "Unknown (Possibly Metadata-Stripped Image)"
            metadata["modified_by"] = "Unknown (Possibly Metadata-Stripped Image)"

    except Exception as e:
        print(f"[Error] Could not extract PNG metadata: {e}")

    return metadata

def _parse_tEXt(chunk_data: bytes):
    if b'\x00' not in chunk_data:
        return ("", "")
    kw, txt = chunk_data.split(b'\x00', 1)
    try:
        return (kw.decode('latin-1', errors='ignore').strip(),
                txt.decode('latin-1', errors='ignore').strip())
    except:
        return ("", "")

def _parse_iTXt(chunk_data: bytes):
    parts = _split_nulls(chunk_data, 1)  
    if parts is None:
        return ("", "")
    keyword, rest = parts[0], parts[1]
    if len(rest) < 2:
        return ("", "")
    comp_flag   = rest[0]
    comp_method = rest[1]  
    remainder   = rest[2:]

    parts2 = _split_nulls(remainder, 2)
    if parts2 is None:
        return ("", "")
    language_tag, translated_keyword, text_bytes = parts2[0], parts2[1], parts2[2]

    try:
        kw_str = keyword.decode('latin-1', errors='ignore').strip()
        if comp_flag == 1:
            try:
                text = zlib.decompress(text_bytes).decode('utf-8', errors='ignore').strip()
            except:
                text = zlib.decompress(text_bytes).decode('latin-1', errors='ignore').strip()
        else:
            text = text_bytes.decode('utf-8', errors='ignore').strip()
        return (kw_str, text)
    except:
        return ("", "")

def _parse_zTXt(chunk_data: bytes):
    if b'\x00' not in chunk_data:
        return ("", "")
    kw, rest = chunk_data.split(b'\x00', 1)
    if not rest:
        return ("", "")
    comp_bytes = rest[1:]
    try:
        text = zlib.decompress(comp_bytes).decode('utf-8', errors='ignore').strip()
    except:
        try:
            text = zlib.decompress(comp_bytes).decode('latin-1', errors='ignore').strip()
        except:
            text = ""
    try:
        kw_str = kw.decode('latin-1', errors='ignore').strip()
    except:
        kw_str = ""
    return (kw_str, text)

def _split_nulls(buf: bytes, count: int):
    out = []
    cur = buf
    for _ in range(count):
        idx = cur.find(b'\x00')
        if idx == -1:
            return None
        out.append(cur[:idx])
        cur = cur[idx+1:]
    out.append(cur)
    return out

def _assign_text_field(meta: dict, keyword: str, text: str):
    k = (keyword or "").strip().lower()
    t = (text or "").strip()
    if not k or not t:
        return
    if k == "title":
        meta["title"] = t
    elif k == "author":
        meta["author"] = t
    elif k in ("description", "comment"):
        meta["description"] = t
    elif k in ("creation time", "creation_time", "created"):
        meta["datetime"] = t
    elif k == "software":
        meta["software"] = t
    elif k in ("source", "camera", "model"):
        if meta["camera_model"] == "Unknown":
            meta["camera_model"] = t

def _normalize_software(sw: str):
    s = sw.lower()
    if "snapseed" in s:   return "Google Snapseed"
    if "photoshop" in s:  return "Adobe Photoshop"
    if "lightroom" in s:  return "Adobe Lightroom"
    if "instagram" in s:  return "Instagram"
    if "whatsapp" in s:   return "WhatsApp (metadata stripped)"
    if "gimp" in s:       return "GIMP"
    if "apple" in s and "photos" in s: return "Apple Photos"
    return sw
