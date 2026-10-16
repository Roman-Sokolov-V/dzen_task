from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from utils import resize_image
from rest_framework.exceptions import ValidationError


class ResizeImageTest(SimpleTestCase):
    def setUp(self):
        # Create a small image (within limits) for testing
        self.small_image = self.create_image(color='red', size=(100, 100))
        # Create a large image (exceeds limits) for testing
        self.large_image = self.create_image(color='blue', size=(400, 300))

    def create_image(self, color, size):
        """Helper to create a simple image file."""
        img = Image.new('RGB', size, color=color)
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=buffer.read(),
            content_type='image/jpeg'
        )

    def test_resize_image_does_not_resize_within_limits(self):
        """Image within max_size should be returned unchanged."""
        result = resize_image(self.small_image)
        self.assertEqual(result.size, self.small_image.size)
        # The returned file should be the same as input (but we can't compare directly)
        # Instead, check that the content is the same.
        result.seek(0)
        result_content = result.read()
        self.small_image.seek(0)
        small_image_content = self.small_image.read()
        self.assertEqual(result_content, small_image_content)

    def test_resize_image_resizes_exceeding_limits(self):
        """Image exceeding max_size should be resized to fit within."""
        result = resize_image(self.large_image)
        # Open the resulting image to check its dimensions
        img = Image.open(BytesIO(result.read()))
        # The image should be resized to fit within 320x240 while preserving aspect ratio.
        # Original 400x300 -> aspect ratio 4:3. After resizing, width should be 320, height 240.
        self.assertEqual(img.size, (320, 240))
        # Ensure the format is preserved (JPEG)
        self.assertEqual(img.format, 'JPEG')

    def test_resize_image_preserves_png_format(self):
        """PNG image should remain PNG after resize."""
        png_image = self.create_image(color='green', size=(400, 300))
        png_image.content_type = 'image/png'
        # We need to recreate the image as PNG
        img = Image.new('RGB', (400, 300), color='green')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        png_image = SimpleUploadedFile(
            name='test_image.png',
            content=buffer.read(),
            content_type='image/png'
        )

        result = resize_image(png_image)
        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.format, 'PNG')
        self.assertEqual(img.size, (320, 240))

    def test_resize_image_preserves_gif_format(self):
        """GIF image should remain GIF after resize."""
        # Create a GIF image
        img = Image.new('RGB', (400, 300), color='white')
        buffer = BytesIO()
        img.save(buffer, format='GIF')
        buffer.seek(0)
        gif_image = SimpleUploadedFile(
            name='test_image.gif',
            content=buffer.read(),
            content_type='image/gif'
        )

        result = resize_image(gif_image)
        img = Image.open(BytesIO(result.read()))
        self.assertEqual(img.format, 'GIF')
        self.assertEqual(img.size, (320, 240))

    def test_resize_image_invalid_format_raises_validation_error(self):
        """Invalid image format should raise ValidationError."""
        # Create a BMP image (valid image but not in allowed formats)
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='BMP')
        buffer.seek(0)
        bmp_file = SimpleUploadedFile(
            name='test_image.bmp',
            content=buffer.read(),
            content_type='image/bmp'
        )
        with self.assertRaises(ValidationError) as context:
            resize_image(bmp_file)
        self.assertIn('Invalid image format', str(context.exception))

    def test_resize_image_corrupted_file_raises_validation_error(self):
        """Corrupted image file should raise ValidationError."""
        corrupted_file = SimpleUploadedFile(
            name='corrupted.jpg',
            content=b'corrupted data',
            content_type='image/jpeg'
        )
        with self.assertRaises(ValidationError) as context:
            resize_image(corrupted_file)
        self.assertIn('The uploaded file is not a valid image or is corrupted', str(context.exception))

    def test_resize_image_gif_animation_preserved(self):
        """Animated GIF should remain animated after resize."""
        # Create a large animated GIF with two frames (400x300) to trigger resize
        img1 = Image.new('RGB', (400, 300), color='red')
        img2 = Image.new('RGB', (400, 300), color='blue')
        buffer = BytesIO()
        img1.save(buffer, format='GIF', save_all=True, append_images=[img2], loop=0, duration=100)
        buffer.seek(0)
        animated_gif = SimpleUploadedFile(
            name='animated.gif',
            content=buffer.read(),
            content_type='image/gif'
        )

        result = resize_image(animated_gif)
        # Open the result and check if it's animated
        img = Image.open(BytesIO(result.read()))
        # Check if it has multiple frames by seeking to the next frame
        try:
            img.seek(1)
        except EOFError:
            self.fail("Animated GIF did not contain multiple frames after resize.")
        # Reset to first frame
        img.seek(0)
        # The size should be resized to fit within 320x240 while preserving aspect ratio.
        # Original 400x300 -> aspect ratio 4:3. After resizing, width should be 320, height 240.
        self.assertEqual(img.size, (320, 240))