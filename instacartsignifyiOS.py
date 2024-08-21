import ui
import threading
import pytesseract
from PIL import Image
import io
import objc_util
import photos
import time


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

        self.setup_video_capture()

        # Start the thread after video capture is set up
        self.thread = threading.Thread(target=self.update_image)
        self.thread.start()

    def setup_video_capture(self):
        print("Setting up video capture...")
        self.session = objc_util.ObjCClass('AVCaptureSession').alloc().init()
        self.session.setSessionPreset_(
            objc_util.ObjCInstance('AVCaptureSessionPresetPhoto'))

        devices = objc_util.ObjCClass('AVCaptureDevice').devices()
        for device in devices:
            if device.position() == 1:  # AVCaptureDevicePositionFront
                self.device = device
                break

        self.input = objc_util.ObjCClass(
            'AVCaptureDeviceInput').deviceInputWithDevice_error_(self.device, None)
        self.session.addInput_(self.input)

        self.output = objc_util.ObjCClass('AVCaptureVideoDataOutput').alloc().init()
        self.output.setAlwaysDiscardsLateVideoFrames_(True)

        self.queue = objc_util.dispatch_queue_create("videoQueue", None)
        self.output.setSampleBufferDelegate_queue_(self, self.queue)
        self.session.addOutput_(self.output)

        self.preview_layer = objc_util.ObjCClass(
            'AVCaptureVideoPreviewLayer').layerWithSession_(self.session)
        self.preview_layer.setVideoGravity_(
            objc_util.ObjCInstance('AVLayerVideoGravityResizeAspectFill'))

        # Correctly set frame using CGRect
        frame = objc_util.CGRectMake(0, 0, self.bounds.w, self.bounds.h)
        self.preview_layer.setFrame_(frame)

        self.objc_view = objc_util.ObjCInstance(self)
        self.objc_view.layer().addSublayer_(self.preview_layer)

        self.session.startRunning()
        print("Video capture setup complete.")

    def update_image(self):
        while self.run_thread:
            time.sleep(self.update_interval)

    @objc_util.on_main_thread
    def captureOutput_didOutputSampleBuffer_fromConnection_(
        self, _cmd, _output, sample_buffer, _connection):
        buffer = objc_util.ObjCInstance(sample_buffer)
        image_buffer = buffer.imageBuffer()
        ci_image = objc_util.ObjCClass('CIImage').imageWithCVImageBuffer_(image_buffer)
        context = objc_util.ObjCClass('CIContext').context()
        cg_image = context.createCGImage_fromRect_(ci_image, ci_image.extent())

        ui_image = self.cgImage_to_ui_image(cg_image)

        # Process the frame and perform OCR
        pil_image = Image.open(io.BytesIO(ui_image.to_png()))
        ocr_text = pytesseract.image_to_string(pil_image)

        # Update UI components on the main thread
        ui.in_background(self.update_ui)(ui_image, ocr_text)

        # Compare OCR text against the photo library
        matched_photos = self.compare_with_photo_library(ocr_text)
        if matched_photos:
            ui.in_background(self.indicate_match)(matched_photos)

    def cgImage_to_ui_image(self, cg_image):
        data = objc_util.ObjCClass('UIImage').alloc().initWithCGImage_(
            cg_image).JPEGRepresentation()
        return ui.Image.from_data(data)

    def update_ui(self, ui_image, ocr_text):
        self.image_view.image = ui_image
        self.text_view.text = ocr_text

    def get_photo_library_images(self):
        assets = photos.get_assets()
        images = []
        for asset in assets:
            with asset.get_image() as img:
                images.append(img)
        return images

    def compare_with_photo_library(self, ocr_text):
        matched_photos = []
        images = self.get_photo_library_images()
        for img in images:
            pil_image = Image.open(io.BytesIO(img.to_png()))
            photo_ocr_text = pytesseract.image_to_string(pil_image)
            if ocr_text in photo_ocr_text:
                matched_photos.append(img)
        return matched_photos

    def indicate_match(self, matched_photos):
        self.text_view.text += "\nMatch found in the photo library!"

    def will_close(self):
        self.run_thread = False
        self.session.stopRunning()
        print("Session stopped.")


if __name__ == '__main__':
    view = LiveOCRView()
    view.present('fullscreen', hide_title_bar=True)
