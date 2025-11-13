from pyzbar.pyzbar import decode
from PIL import Image
import json

class BarcodeReader:
    """Decode barcodes from images using pyzbar"""
    
    def decode_barcode(self, image_path):
        """Decode barcode from image file"""
        try:
            image = Image.open(image_path)
            decoded_objects = decode(image)
            
            if not decoded_objects:
                return None
            
            # Get first barcode detected
            barcode = decoded_objects[0]
            
            return {
                'barcode': barcode.data.decode('utf-8'),
                'format': barcode.type,
                'quality': 'high'
            }
        except Exception as e:
            print(f"❌ Error decoding barcode: {e}")
            return None
    
    def decode_multiple(self, image_path):
        """Decode multiple barcodes from single image"""
        try:
            image = Image.open(image_path)
            decoded_objects = decode(image)
            
            results = []
            for barcode in decoded_objects:
                results.append({
                    'barcode': barcode.data.decode('utf-8'),
                    'format': barcode.type,
                    'rect': {
                        'x': barcode.rect.left,
                        'y': barcode.rect.top,
                        'width': barcode.rect.width,
                        'height': barcode.rect.height
                    }
                })
            
            return results if results else None
        except Exception as e:
            print(f"❌ Error decoding barcodes: {e}")
            return None