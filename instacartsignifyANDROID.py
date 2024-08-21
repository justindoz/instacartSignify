import threading
import pytesseract
from PIL import Image
import subprocess
import os
import time
import io
import ui


class LiveOCRView(ui.View):

    def __init__(self):
        self.bg_color = 'black'
        self.image_view = ui.ImageView(frame=self.bounds)
        self.image_view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.add_subview(self.image_view)

        self.text_view = ui.TextView(frame=(0, self.bounds.h - 200, self.bounds.w,
                                            200))
        self.text_view.editable = False
        self.text_view.text_color = 'white'
        self.text_view.background_color = 'black'
        self.add_subview(self.text_view)

        self.update_interval = 1
        self.run_thread = True

        # Start the thread
        self.thread = threading.Thread(target=self.update_image)
        self.thread.start()

    def capture_frame(self):
        # Use Termux command to capture a photo
        photo_path = '/data/data/com.termux/files/home/captured_frame.jpg'
        subprocess.run(['termux-camera-photo', '-c', '0', photo_path])
        return photo_path

    def get_photo_library(self):
        # Assuming local photos are stored in a directory
        photo_dir = '/data/data/com.termux/files/home/photos'
        photos = [os.path.join(photo_dir, f) for f in os.listdir(photo_dir) if os.path.isfile(os.path.join(photo_dir, f))]
        return photos

    def check_for_match(self, ocr_text, photos):
        matched_photos = []
        for photo in photos:
            with Image.open(photo) as img:
                text = pytesseract.image_to_string(img)
                if ocr_text in text:
                    matched_photos.append(photo)
        return matched_photos

    def update_image(self):
        while self.run_thread:
            time.sleep(self.update_interval)
            frame_path = self.capture_frame()
            if os.path.exists(frame_path):
                pil_image = Image.open(frame_path)
                ocr_text = pytesseract.image_to_string(pil_image)
                
                photos = self.get_photo_library()
                matches = self.check_for_match(ocr_text, photos)

                self.update_ui(pil_image, ocr_text, matches)

    def update_ui(self, pil_image, ocr_text, matches):
        print("Updating UI.")
        with io.BytesIO() as output:
            pil_image.save(output, format="PNG")
            self.image_view.image = ui.Image.from_data(output.getvalue())

        if matches:
            self.text_view.text = f"Match Found: {', '.join(matches)}"
        else:
            self.text_view.text = "No match found"

    def will_close(self):
        self.run_thread = False
        print("Session stopped.")


if __name__ == '__main__':
    view = LiveOCRView()
    view.present('fullscreen', hide_title_bar=True)
