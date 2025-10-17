import struct  
import zlib    

def extract_metadata(file_path):
    # Default PNG metadata
    metadata = {
        "file_type": "image",
        "make": "Unknown",
        "camera_model": "Unknown",
        "software": "Unknown",
        "datetime": "Unknown",            # Creation time (if present)
        "datetime_digitized": "Unknown",  # Not typical for PNG
        "exif_version": "Unknown",        # PNG usually lacks EXIF
        "width": "Unknown",
        "height": "Unknown",
        "gps_latitude": "Unknown",        # Rare in PNG
        "gps_longitude": "Unknown",
        "created_by": "Unknown",
        "modified_by": "Unknown",
        "title": "Unknown",
        "author": "Unknown",
        "description": "Unknown"
    }

    try:
        with open(file_path, 'rb') as f:
            data = f.read()  # Read entire file

        png_sig = b'\x89PNG\r\n\x1a\n'  # PNG signature
        if not data.startswith(png_sig):
            return metadata  # Not PNG

        pos = 8  # Skip signature
        while pos + 8 <= len(data):
            length = struct.unpack(">I", data[pos:pos+4])[0]  # Chunk length
            ctype  = data[pos+4:pos+8]                        # Chunk type
            cdata  = data[pos+8:pos+8+length]                 # Chunk data
            pos += 12 + length                                 # Move to next chunk

            if ctype == b'IHDR' and length >= 8:
                metadata["width"]  = struct.unpack(">I", cdata[0:4])[0]
                metadata["height"] = struct.unpack(">I", cdata[4:8])[0]

            elif ctype == b'tEXt':  # Plain text
                kw, text = _parse_tEXt(cdata)
                _assign_text_field(metadata, kw, text)

            elif ctype == b'iTXt':  # UTF-8, optional compression
                kw, text = _parse_iTXt(cdata)
                _assign_text_field(metadata, kw, text)

            elif ctype == b'zTXt':  # Compressed Latin-1
                kw, text = _parse_zTXt(cdata)
                _assign_text_field(metadata, kw, text)

            if ctype == b'IEND':  # End of PNG
                break

        # Derive created/modified by from Software if present
        if metadata["software"] != "Unknown":
            metadata["modified_by"] = _normalize_software(metadata["software"])
            if metadata["created_by"] == "Unknown":
                metadata["created_by"] = metadata["modified_by"]

        # If no useful textual fields → likely stripped
        if all(metadata[k] == "Unknown" for k in ["software", "title", "author", "description", "datetime"]):
            metadata["created_by"]  = "Unknown (Possibly Metadata-Stripped Image)"
            metadata["modified_by"] = "Unknown (Possibly Metadata-Stripped Image)"

    except Exception as e:
        print(f"[Error] Could not extract PNG metadata: {e}")  # Log failure

    return metadata  # Return results

def _parse_tEXt(chunk_data: bytes):
    # tEXt: keyword\0text (Latin-1)
    if b'\x00' not in chunk_data:
        return ("", "")
    kw, txt = chunk_data.split(b'\x00', 1)
    try:
        return (kw.decode('latin-1', errors='ignore').strip(),
                txt.decode('latin-1', errors='ignore').strip())
    except:
        return ("", "")

def _parse_iTXt(chunk_data: bytes):
    # iTXt: keyword\0comp_flag\0comp_method\0lang\0translated\0text
    parts = _split_nulls(chunk_data, 1)  # Split keyword
    if parts is None:
        return ("", "")
    keyword, rest = parts[0], parts[1]
    if len(rest) < 2:
        return ("", "")
    comp_flag   = rest[0]   # 0 or 1
    comp_method = rest[1]   # 0 (zlib)
    remainder   = rest[2:]

    parts2 = _split_nulls(remainder, 2)  # lang, translated, text
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
    # zTXt: keyword\0compression_method(1 byte) + compressed text
    if b'\x00' not in chunk_data:
        return ("", "")
    kw, rest = chunk_data.split(b'\x00', 1)
    if not rest:
        return ("", "")
    comp_bytes = rest[1:]  # Skip comp method byte
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
    # Split buffer by N nulls; return parts
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
    # Map PNG text keys to our fields
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
    # Normalise common software strings
    s = sw.lower()
    if "snapseed" in s:   return "Google Snapseed"
    if "photoshop" in s:  return "Adobe Photoshop"
    if "lightroom" in s:  return "Adobe Lightroom"
    if "instagram" in s:  return "Instagram"
    if "whatsapp" in s:   return "WhatsApp (metadata stripped)"
    if "gimp" in s:       return "GIMP"
    if "apple" in s and "photos" in s: return "Apple Photos"
    return sw