def extract_metadata(file_path):
    metadata = {
        "file_type": "image",
        "camera_model": "Unknown",
        "datetime": "Unknown",
        "software": "Unknown"
    }

    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        exif_start = data.find(b'\xff\xe1')
        if exif_start == -1:
            return metadata  

        tiff_header_start = exif_start + 10  
        endian = data[tiff_header_start:tiff_header_start + 2]

        if endian == b'II':
            byte_order = 'little'
        elif endian == b'MM':
            byte_order = 'big'
        else:
            return metadata

        num_tags = int.from_bytes(data[tiff_header_start + 8:tiff_header_start + 10], byte_order)

        ifd_offset = tiff_header_start + 10
        entry_size = 12  

        for i in range(num_tags):
            entry_offset = ifd_offset + i * entry_size
            tag = int.from_bytes(data[entry_offset:entry_offset + 2], byte_order)

            if tag == 0x0131:  
                val_offset = int.from_bytes(data[entry_offset + 8:entry_offset + 12], byte_order)
                software = extract_ascii_string(data, tiff_header_start + val_offset)
                metadata["software"] = software

            elif tag == 0x0110:  
                val_offset = int.from_bytes(data[entry_offset + 8:entry_offset + 12], byte_order)
                camera_model = extract_ascii_string(data, tiff_header_start + val_offset)
                metadata["camera_model"] = camera_model

            elif tag == 0x9003:  
                val_offset = int.from_bytes(data[entry_offset + 8:entry_offset + 12], byte_order)
                dt = extract_ascii_string(data, tiff_header_start + val_offset)
                metadata["datetime"] = dt

    except Exception as e:
        print(f"[Error] Could not extract image metadata: {e}")

    return metadata

def extract_ascii_string(data, start_index):
    result = b''
    for i in range(0, 100):  
        byte = data[start_index + i]
        if byte == 0:
            break
        result += bytes([byte])
    return result.decode(errors='ignore').strip()