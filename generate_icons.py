"""
Generate icon.png and logo.png for the Aviation Weather add-on
Requires: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import math

def create_icon(size=256, filename="icon.png"):
    """Create a 256x256 icon with airplane and weather symbols"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background circle with gradient effect
    center = size // 2
    radius = size // 2 - 10
    
    # Draw background circle
    draw.ellipse([10, 10, size-10, size-10], 
                 fill=(102, 126, 234, 255),  # #667eea
                 outline=(118, 75, 162, 255), # #764ba2
                 width=3)
    
    # Draw airplane symbol
    plane_color = (255, 255, 255, 255)
    
    # Fuselage
    cx, cy = center, center
    draw.ellipse([cx-60, cy-15, cx+60, cy+15], fill=plane_color)
    
    # Wings
    wing_points = [
        (cx-50, cy),
        (cx-80, cy-40),
        (cx-70, cy-40),
        (cx-40, cy),
    ]
    draw.polygon(wing_points, fill=plane_color)
    
    wing_points_r = [
        (cx-50, cy),
        (cx-80, cy+40),
        (cx-70, cy+40),
        (cx-40, cy),
    ]
    draw.polygon(wing_points_r, fill=plane_color)
    
    # Tail
    tail_points = [
        (cx+40, cy),
        (cx+60, cy-30),
        (cx+55, cy-30),
        (cx+40, cy),
    ]
    draw.polygon(tail_points, fill=plane_color)
    
    # Windows
    for i in range(-3, 4):
        wx = cx + i * 15
        draw.ellipse([wx-4, cy-6, wx+4, cy+6], 
                    fill=(102, 126, 234, 200))
    
    # Cloud symbol (top right)
    cloud_x, cloud_y = center + 60, center - 60
    # Cloud parts
    draw.ellipse([cloud_x-15, cloud_y-5, cloud_x+5, cloud_y+15], 
                fill=(255, 255, 255, 230))
    draw.ellipse([cloud_x-5, cloud_y-10, cloud_x+15, cloud_y+10], 
                fill=(255, 255, 255, 230))
    draw.ellipse([cloud_x+5, cloud_y-5, cloud_x+25, cloud_y+15], 
                fill=(255, 255, 255, 230))
    
    # Wind lines (bottom left)
    wind_color = (255, 255, 255, 200)
    wind_x, wind_y = center - 70, center + 50
    for i in range(3):
        y = wind_y + i * 10
        draw.line([wind_x, y, wind_x + 40, y], fill=wind_color, width=3)
    
    img.save(filename, 'PNG')
    print(f"Created {filename} ({size}x{size})")


def create_logo(size=512, filename="logo.png"):
    """Create a 512x512 logo with more detailed aviation weather design"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # Gradient background circle
    for i in range(100):
        radius = size // 2 - i * 2
        alpha = int(255 - i * 1.5)
        if radius > 0:
            # Gradient from #667eea to #764ba2
            r = int(102 + (118 - 102) * i / 100)
            g = int(126 - (126 - 75) * i / 100)
            b = int(234 - (234 - 162) * i / 100)
            draw.ellipse([center-radius, center-radius, 
                         center+radius, center+radius],
                        fill=(r, g, b, alpha))
    
    # Draw larger airplane
    plane_color = (255, 255, 255, 255)
    cx, cy = center, center
    scale = 1.5
    
    # Fuselage
    draw.ellipse([cx-int(80*scale), cy-int(20*scale), 
                  cx+int(80*scale), cy+int(20*scale)], 
                 fill=plane_color)
    
    # Wings
    wing_points = [
        (cx-int(70*scale), cy),
        (cx-int(110*scale), cy-int(60*scale)),
        (cx-int(95*scale), cy-int(60*scale)),
        (cx-int(55*scale), cy),
    ]
    draw.polygon(wing_points, fill=plane_color)
    
    wing_points_r = [
        (cx-int(70*scale), cy),
        (cx-int(110*scale), cy+int(60*scale)),
        (cx-int(95*scale), cy+int(60*scale)),
        (cx-int(55*scale), cy),
    ]
    draw.polygon(wing_points_r, fill=plane_color)
    
    # Tail
    tail_points = [
        (cx+int(55*scale), cy),
        (cx+int(85*scale), cy-int(45*scale)),
        (cx+int(75*scale), cy-int(45*scale)),
        (cx+int(55*scale), cy),
    ]
    draw.polygon(tail_points, fill=plane_color)
    
    # Windows
    for i in range(-5, 6):
        wx = cx + i * int(18*scale)
        draw.ellipse([wx-6, cy-8, wx+6, cy+8], 
                    fill=(102, 126, 234, 220))
    
    # Weather symbols around the plane
    # Cloud (top right)
    cloud_x, cloud_y = center + 120, center - 120
    draw.ellipse([cloud_x-25, cloud_y-10, cloud_x+10, cloud_y+25], 
                fill=(255, 255, 255, 240))
    draw.ellipse([cloud_x-10, cloud_y-18, cloud_x+25, cloud_y+17], 
                fill=(255, 255, 255, 240))
    draw.ellipse([cloud_x+8, cloud_y-10, cloud_x+40, cloud_y+25], 
                fill=(255, 255, 255, 240))
    
    # Rain drops
    for i in range(5):
        rx = cloud_x - 15 + i * 12
        ry = cloud_y + 30
        draw.ellipse([rx-3, ry, rx+3, ry+12], 
                    fill=(200, 220, 255, 200))
    
    # Wind lines (bottom left)
    wind_color = (255, 255, 255, 220)
    wind_x, wind_y = center - 130, center + 100
    for i in range(4):
        y = wind_y + i * 15
        length = 70 - i * 5
        draw.line([wind_x, y, wind_x + length, y], 
                 fill=wind_color, width=5)
        # Arrow
        draw.polygon([
            (wind_x + length, y),
            (wind_x + length - 12, y - 8),
            (wind_x + length - 12, y + 8)
        ], fill=wind_color)
    
    # Compass rose (top left)
    compass_x, compass_y = center - 120, center - 120
    compass_r = 25
    # N, S, E, W markers
    for angle, label in [(0, 'N'), (90, 'E'), (180, 'S'), (270, 'W')]:
        rad = math.radians(angle)
        x = compass_x + int(compass_r * math.sin(rad))
        y = compass_y - int(compass_r * math.cos(rad))
        draw.ellipse([x-3, y-3, x+3, y+3], fill=(255, 255, 255, 255))
    
    # Center circle
    draw.ellipse([compass_x-5, compass_y-5, compass_x+5, compass_y+5],
                fill=(255, 255, 255, 255))
    
    # Temperature symbol (bottom right)
    temp_x, temp_y = center + 120, center + 110
    # Thermometer
    draw.rectangle([temp_x-8, temp_y-35, temp_x+8, temp_y+10],
                  fill=(255, 255, 255, 230))
    draw.ellipse([temp_x-12, temp_y+5, temp_x+12, temp_y+25],
                fill=(255, 100, 100, 255))
    # Mercury
    draw.rectangle([temp_x-4, temp_y-30, temp_x+4, temp_y+10],
                  fill=(255, 100, 100, 255))
    
    img.save(filename, 'PNG')
    print(f"Created {filename} ({size}x{size})")


if __name__ == "__main__":
    print("Generating Aviation Weather Add-on icons...")
    create_icon(256, "icon.png")
    create_logo(512, "logo.png")
    print("✓ Icons generated successfully!")
    print("\nTo use these icons:")
    print("1. Review the generated images")
    print("2. If satisfied, they're ready to use in your add-on")
    print("3. If you want custom designs, consider using a graphic design tool")
