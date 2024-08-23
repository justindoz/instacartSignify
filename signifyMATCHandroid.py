import threading
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
import subprocess
import os
import time

class LiveOCR:

    def __init__(self):
        self.update_interval = 1  # Interval between frames in seconds
        self.run_thread = True
        self.photo_path = '/data/data/com.termux/files/home/captured_frame.jpg'
        self.photo_dir = '/data/data/com.termux/files/home/photos'

        # Create the photos directory if it doesn't exist
        if not os.path.exists(self.photo_dir):
            os.makedirs(self.photo_dir)

        # Start the thread to capture images and process OCR
        self.thread = threading.Thread(target=self.update_image)
        self.thread.start()

    def capture_frame(self):
        """Capture a frame using the device's camera."""
        try:
            print("Capturing Image...")
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
                    
                    # Enhance the image before OCR
                    enhancer = ImageEnhance.Contrast(pil_image)
                    pil_image = enhancer.enhance(2)  # Increase contrast for better OCR
                    
                    ocr_text = pytesseract.image_to_string(pil_image)
                    print(f"OCR Text: {ocr_text}")

                    photos = self.get_photo_library()
                    matches = self.check_for_match(ocr_text, photos)

                    if matches:
                        print(f"Match Found! Image(s): {', '.join(matches)}")
                        self.display_match_message()

                    else:
                        print("No match found")

                except Exception as e:
                    print(f"Error during OCR: {e}")
                finally:
                    # Cleanup: Delete the captured frame file
                    try:
                        os.remove(frame_path)
                    except Exception as e:
                        print(f"Error deleting frame file '{frame_path}': {e}")

    def display_match_message(self):
        """Display a match message on the terminal."""
        print("********************")
        print("** MATCH DETECTED **")
        print("********************")

    def stop(self):
        """Stop the thread when done."""
        print("Stopping...")
        self.run_thread = False
        self.thread.join()  # Ensure the thread terminates cleanly
        print("Session stopped.")

if __name__ == '__main__':
    live_ocr = LiveOCR()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        live_ocr.stop()
