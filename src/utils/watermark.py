"""
Provenance Watermarking Utility

This module provides functionality to embed self-verifying provenance watermarks
into visual outputs (images, video frames). The watermark is burned directly into
the frame, not stored as metadata, to ensure it survives cross-platform distribution.

This is a critical component of the Cross-Platform Artifact Drift defense.
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Optional
import qrcode


class ProvenanceWatermark:
    """
    Embeds provenance information directly into image frames.
    
    The watermark includes:
    - Claim ID
    - Commit Hash (short)
    - Evidence Grade
    - Control Reference URL (as QR code)
    """
    
    def __init__(
        self,
        claim_id: str,
        commit_hash: str,
        evidence_grade: str,
        control_url: str,
        font_path: Optional[str] = None
    ):
        """
        Initialize the watermark generator.
        
        Args:
            claim_id: Unique identifier for the claim
            commit_hash: Git commit hash (short form, 7 chars)
            evidence_grade: Evidence quality grade (e.g., "A", "B", "C")
            control_url: URL to the control case or verification page
            font_path: Optional path to a TrueType font file
        """
        self.claim_id = claim_id
        self.commit_hash = commit_hash[:7]  # Ensure short form
        self.evidence_grade = evidence_grade
        self.control_url = control_url
        self.font_path = font_path
        
    def generate_qr_code(self, size: int = 100) -> Image.Image:
        """
        Generate a QR code for the control URL.
        
        Args:
            size: Size of the QR code in pixels
            
        Returns:
            PIL Image object containing the QR code
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(self.control_url)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="white", back_color="black")
        return qr_image.resize((size, size))
    
    def apply_watermark(
        self,
        image: Image.Image,
        position: str = "bottom_right",
        opacity: int = 220,
        font_size: int = 12
    ) -> Image.Image:
        """
        Apply the provenance watermark to an image.
        
        Args:
            image: PIL Image object to watermark
            position: Where to place the watermark ("bottom_right", "bottom_left", "top_right", "top_left")
            opacity: Opacity of the watermark (0-255)
            font_size: Font size for the text
            
        Returns:
            Watermarked PIL Image object
        """
        # Create a copy to avoid modifying the original
        watermarked = image.copy()
        draw = ImageDraw.Draw(watermarked)
        
        # Load font
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Generate watermark text
        watermark_text = f"ID: {self.claim_id} | {self.commit_hash} | Grade: {self.evidence_grade}"
        
        # Calculate text size
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Generate QR code
        qr_image = self.generate_qr_code(size=60)
        
        # Calculate total watermark dimensions
        watermark_width = text_width + qr_image.width + 20  # 20px padding
        watermark_height = max(text_height, qr_image.height) + 20
        
        # Calculate position
        img_width, img_height = watermarked.size
        
        if position == "bottom_right":
            x = img_width - watermark_width - 10
            y = img_height - watermark_height - 10
        elif position == "bottom_left":
            x = 10
            y = img_height - watermark_height - 10
        elif position == "top_right":
            x = img_width - watermark_width - 10
            y = 10
        else:  # top_left
            x = 10
            y = 10
        
        # Draw semi-transparent background
        draw.rectangle(
            [x, y, x + watermark_width, y + watermark_height],
            fill=(0, 0, 0, opacity)
        )
        
        # Draw text
        text_y = y + (watermark_height - text_height) // 2
        draw.text((x + 10, text_y), watermark_text, fill=(255, 255, 255, 255), font=font)
        
        # Paste QR code
        qr_x = x + text_width + 15
        qr_y = y + (watermark_height - qr_image.height) // 2
        watermarked.paste(qr_image, (qr_x, qr_y))
        
        return watermarked


def watermark_image_file(
    input_path: str,
    output_path: str,
    claim_id: str,
    commit_hash: str,
    evidence_grade: str,
    control_url: str
) -> None:
    """
    Convenience function to watermark an image file.
    
    Args:
        input_path: Path to the input image
        output_path: Path to save the watermarked image
        claim_id: Unique identifier for the claim
        commit_hash: Git commit hash
        evidence_grade: Evidence quality grade
        control_url: URL to the control case
    """
    image = Image.open(input_path)
    watermarker = ProvenanceWatermark(claim_id, commit_hash, evidence_grade, control_url)
    watermarked = watermarker.apply_watermark(image)
    watermarked.save(output_path)


# Example usage
if __name__ == "__main__":
    # Example: Watermark a test image
    watermarker = ProvenanceWatermark(
        claim_id="CLAIM-001",
        commit_hash="a1b2c3d",
        evidence_grade="A",
        control_url="https://github.com/onlyecho822-source/echo-substrate-v4"
    )
    
    # Create a test image
    test_image = Image.new("RGB", (800, 600), color=(73, 109, 137))
    watermarked = watermarker.apply_watermark(test_image)
    watermarked.save("/tmp/test_watermarked.png")
    print("Test watermark created at /tmp/test_watermarked.png")
