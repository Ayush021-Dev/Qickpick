from PIL import Image, ImageDraw
import os

def create_icon():
    # Create a 64x64 image with a transparent background
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a face-like shape
    # Head circle
    draw.ellipse([8, 8, 56, 56], fill=(52, 152, 219))
    
    # Eyes
    draw.ellipse([20, 24, 30, 34], fill=(255, 255, 255))
    draw.ellipse([34, 24, 44, 34], fill=(255, 255, 255))
    
    # Smile
    draw.arc([20, 20, 44, 44], 0, 180, fill=(255, 255, 255), width=3)
    
    # Save the icon
    os.makedirs('assets', exist_ok=True)
    img.save('assets/icon.png')

if __name__ == '__main__':
    create_icon() 