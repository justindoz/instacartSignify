import time
import os
import threading
from PIL import Image
import pytesseract
from termux_api import Termux

# Initialize Termux API
termux = Termux()

class LiveOCR:
    def __init__(self):
        self.update_interval = 1
        self.run_thread = True

        # Start the thread for continuous OCR and photo sync
        self.thread = threading.Thread(target=self.process_images)
        self.thread.start()

    def capture_image(self):
        # Capture an image using the Termux camera
        termux.camera_photo(output_path='/tmp/capture.jpg', front=False)
        return '/tmp/capture.jpg'

    def get_photo_library_images(self):
        # Fetch all images from the photo library
        photo_dir = '/sdcard/DCIM/Camera'  # Typical path, might need adjustment
        images = [os.path.join(photo_dir, img) for img in os.listdir(photo_dir) if img.endswith('.jpg')]
        return images

    def perform_ocr(self, image_path):
        # Perform OCR on a given image
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text

    def compare_with_photo_library(self, ocr_text):
        matched_photos = []
        images = self.get_photo_library_images()
        for img in images:
            photo_ocr_text = self.perform_ocr(img)
            if ocr_text in photo_ocr_text:
                matched_photos.append(img)
        return matched_photos

    def delete_photo(self, photo_path):
        # Delete the photo from the library
        try:
            os.remove(photo_path)
            print(f"Deleted photo: {photo_path}")
        except Exception as e:
            print(f"Error deleting photo: {photo_path}, {str(e)}")

    def process_images(self):
        while self.run_thread:
            # Capture and process an image from the camera
            captured_image = self.capture_image()
            ocr_text = self.perform_ocr(captured_image)

            # Compare the OCR text with photos in the library
            matched_photos = self.compare_with_photo_library(ocr_text)
            if matched_photos:
                self.indicate_and_delete_match(matched_photos)

            # Wait before the next capture
            time.sleep(self.update_interval)

    def indicate_and_delete_match(self, matched_photos):
        # Indicate that a match was found and delete the matched photos
        print("Match found in the following photos:")
        for photo in matched_photos:
            print(photo)
            self.delete_photo(photo)

    def stop(self):
        self.run_thread = False

if __name__ == '__main__':
    live_ocr = LiveOCR()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        live_ocr.stop()
            
