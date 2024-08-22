import threading
import pytesseract
from PIL import Image, ImageOps
import subprocess
import os
import time
import io
import ui


class LiveOCRView(ui.View):

    def __init__(self):
        super().__init__()
        self.bg_color = 'black'
        self.image_view = ui.ImageView(frame=self.bounds)
        self.image_view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.add_subview(self.image_view)

        self.text_view = ui.TextView(frame=(0, self.bounds.h - 200, self.bounds.w, 200))
        self.text_view.editable = False
        self.text_view.text_color = 'white'
        self.text_view.background_color = 'black'
        self.add_subview(self.text_view)

        self.update_interval = 1  # Interval between frames in seconds
        self.run_thread = True

        # Start the thread to capture images and process OCR
        self.thread = threading.Thread(target=self.update_image)
        self.thread.start()

    def capture_frame(self):
        """Capture a frame using the device's camera."""
        photo_path = '/data/data/com.termux/files/home/captured_frame.jpg'
        try:
            self.show_status("Capturing Image...")
            # Run Termux camera command
            subprocess.run(['termux-camera-photo', '-c', '0', photo_path], check=True)
            self.show_status("Image Captured.")
            return photo_path
        except subprocess.CalledProcessError as e:
            error_msg = f"Error capturing frame: {e}"
            print(error_msg)
            self.show_status(error_msg)
            return None
        except FileNotFoundError:
            error_msg = "Error: Termux camera utility not found."
            print(error_msg)
            self.show_status(error_msg)
            return None

    def get_photo_library(self):
        """Retrieve a list of photo file paths from the photo library."""
        photo_dir = '/data/data/com.termux/files/home/photos'
        if not os.path.exists(photo_dir):
            error_msg = f"Error: Photo directory '{photo_dir}' does not exist."
            print(error_msg)
            self.show_status(error_msg)
            return []

        try:
            photos = [os.path.join(photo_dir, f) for f in os.listdir(photo_dir) if os.path.isfile(os.path.join(photo_dir, f))]
            return photos
        except Exception as e:
            error_msg = f"Error accessing photo library: {e}"
            print(error_msg)
            self.show_status(error_msg)
            return []

    def check_for_match(self, ocr_text, photos):
        """Check if the OCR text matches any text in the photos from the library."""
        self.show_status("Checking for matches...")
        matched_photos = []
        for photo in photos:
            try:
                with Image.open(photo) as img:
                    text = pytesseract.image_to_string(img)
                    if ocr_text in text:
                        matched_photos.append(photo)
            except Exception as e:
                error_msg = f"Error processing photo '{photo}': {e}"
                print(error_msg)
                self.show_status(error_msg)
        return matched_photos

    def update_image(self):
        """Continuously capture frames and process them for OCR."""
        while self.run_thread:
            time.sleep(self.update_interval)
            frame_path = self.capture_frame()
            if frame_path and os.path.exists(frame_path):
                try:
                    self.show_status("Processing Image...")
                    pil_image = Image.open(frame_path)
                    pil_image = ImageOps.exif_transpose(pil_image)  # Correct orientation
                    ocr_text = pytesseract.image_to_string(pil_image)
                    
                    photos = self.get_photo_library()
                    matches = self.check_for_match(ocr_text, photos)

                    self.update_ui(pil_image, ocr_text, matches)
                except Exception as e:
                    error_msg = f"Error during OCR or UI update: {e}"
                    print(error_msg)
                    self.show_status(error_msg)
                finally:
                    # Cleanup: Delete the captured frame file
                    try:
                        os.remove(frame_path)
                    except Exception as e:
                        error_msg = f"Error deleting frame file '{frame_path}': {e}"
                        print(error_msg)
                        self.show_status(error_msg)

    @ui.in_background
    def update_ui(self, pil_image, ocr_text, matches):
        """Update the UI with the latest image and OCR results."""
        try:
            with io.BytesIO() as output:
                pil_image.save(output, format="PNG")
                self.image_view.image = ui.Image.from_data(output.getvalue())

            if matches:
                self.text_view.text = f"Match Found: {', '.join(matches)}"
            else:
                self.text_view.text = "No match found"
        except Exception as e:
            error_msg = f"Error updating UI: {e}"
            print(error_msg)
            self.show_status(error_msg)

    def show_status(self, message):
        """Display a status message in the text view."""
        self.text_view.text = message

    def will_close(self):
        """Stop the thread when the view is closing."""
        self.show_status("Stopping...")
        self.run_thread = False
        self.thread.join()  # Ensure the thread terminates cleanly
        print("Session stopped.")


if __name__ == '__main__':
    view = LiveOCRView()
    view.present('fullscreen', hide_title_bar=True)
