import exifread
import lxml.etree as etree

def extract_exif_metadata(path):
    """Extract EXIF and XML-style metadata from an image."""

    def get_exif_value(tag, default=0, cast=float):
        if tag is None:
            return default
        try:
            return cast(tag.printable)
        except:
            try:
                return cast(tag.values[0])
            except:
                return default

    meta = {}

    with open(path, 'rb') as f:
        tags = exifread.process_file(f, details=False)

        meta['image_width'] = get_exif_value(tags.get('EXIF ExifImageWidth'), 0, int)
        meta['image_height'] = get_exif_value(tags.get('EXIF ExifImageLength'), 0, int)

        if meta['image_width'] and meta['image_height']:
            meta['megapixels'] = (meta['image_width'] * meta['image_height']) / 1e6
        else:
            meta['megapixels'] = 0

        meta['datetime'] = str(tags.get('EXIF DateTimeOriginal', ''))
        meta['camera_model'] = str(tags.get('Image Model', ''))

        # XML parsing (your embedded metadata)
        comment = tags.get('EXIF UserComment', None)
        if comment:
            try:
                xml_root = etree.fromstring(comment.printable.encode())

                coords = xml_root.xpath('.//Coords')
                if coords:
                    meta['longitude'] = float(coords[0].get('long', 0))
                    meta['latitude'] = float(coords[0].get('lat', 0))

                depth = xml_root.xpath('.//Depth')
                if depth:
                    meta['depth'] = float(depth[0].get('depth', 0))
                    meta['altitude'] = float(depth[0].get('altitude', 0))

                acquisition = xml_root.xpath('.//acquisition')
                if acquisition:
                    meta['exposure'] = float(acquisition[0].findtext('exposure', default=0))
                    meta['aperture'] = float(acquisition[0].findtext('aperture', default=0))
                    meta['digital_gain'] = float(acquisition[0].findtext('digital_gain', default=0))

            except Exception:
                pass

    return meta
