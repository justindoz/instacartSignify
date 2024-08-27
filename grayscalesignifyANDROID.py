import threading
import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import subprocess
import os
import time
import io

class LiveOCRView:

    def __init__(self):
        self.update_interval = 1  # Interval between frames in seconds
        self.run_thread = True

        # Create necessary directories
        self.photo_path = 'mkdir/photo.jpg'
        self.photo_dir = 'mkdir/photo_dir'
        os.makedirs(os.path.dirname(self.photo_path), exist_ok=True)
        os.makedirs(self.photo_dir, exist_ok=True)

        # Start the thread to capture images and process OCR
        self.thread = threading.Thread(target=self.update_image)
        self.thread.start()

    def capture_frame(self):
        """Capture a frame using the device's camera."""
        try:
            print("Capturing Image...")
            # Run Termux camera command
            subprocess.run(['termux-camera-photo', '-c', '0', self.photo_path], check=True)
            print("Image Captured.")
            return self.photo_path
        except subprocess.CalledProcessError as e:
            print(f"Error capturing frame: {e}")
            return None
        except FileNotFoundError:
            print("Error: Termux camera utility not found.")
            return None

    def get_photo_library(self):
        """Retrieve a list of photo file paths from the photo library."""
        if not os.path.exists(self.photo_dir):
            print(f"Error: Photo directory '{self.photo_dir}' does not exist.")
            return []

        try:
            photos = [os.path.join(self.photo_dir, f) for f in os.listdir(self.photo_dir) if os.path.isfile(os.path.join(self.photo_dir, f))]
            return photos
        except Exception as e:
            print(f"Error accessing photo library: {e}")
            return []

    def check_for_match(self, ocr_text, photos):
        """Check if the OCR text matches any text in the photos from the library."""
        print("Checking for matches...")
        matched_photos = []
        for photo in photos:
            try:
                with Image.open(photo) as img:
                    text = pytesseract.image_to_string(img)
                    if ocr_text in text:
                        matched_photos.append(photo)
            except Exception as e:
                print(f"Error processing photo '{photo}': {e}")
        return matched_photos

    def update_image(self):
        """Continuously capture frames and process them for OCR."""
        while self.run_thread:
            time.sleep(self.update_interval)
            frame_path = self.capture_frame()
            if frame_path and os.path.exists(frame_path):
                try:
                    print("Processing Image...")
                    pil_image = Image.open(frame_path)
                    pil_image = ImageOps.exif_transpose(pil_image)  # Correct orientation

                    # Convert to grayscale
                    pil_image = pil_image.convert('L')  # Convert to grayscale

                    # Enhance the image before OCR
                    enhancer = ImageEnhance.Contrast(pil_image)
                    pil_image = enhancer.enhance(2)  # Increase contrast for better OCR

                    # Apply a threshold to get a binary image
                    pil_image = pil_image.point(lambda x: 0 if x < 128 else 255, '1')

                    # Reduce noise
                    pil_image = pil_image.filter(ImageFilter.MedianFilter(size=3))

                    ocr_text = pytesseract.image_to_string(pil_image)
                    
                    photos = self.get_photo_library()
                    matches = self.check_for_match(ocr_text, photos)

                    self.update_ui(ocr_text, matches)
                except Exception as e:
                    print(f"Error during OCR or UI update: {e}")
                finally:
                    # Cleanup: Delete the captured frame file
                    try:
                        os.remove(frame_path)
                    except Exception as e:
                        print(f"Error deleting frame file '{frame_path}': {e}")

    def update_ui(self, ocr_text, matches):
        """Log the OCR results and matched photos."""
        print(f"OCR Text: {ocr_text}")
        if matches:
            print(f"Match Found: {', '.join(matches)}")
        else:
            print("No match found")

    def stop(self):
        """Stop the thread when the view is closing."""
        print("Stopping...")
        self.run_thread = False
        self.thread.join()  # Ensure the thread terminates cleanly
        print("Session stopped.")

if __name__ == '__main__':
    view = LiveOCRView()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        view.stop()
