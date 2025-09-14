# png to transparent png
import os
from PIL import Image   
def convert_png_to_transparent_png(input_path, output_path):
    """
    Convert a PNG image to a transparent PNG image.
    
    :param input_path: Path to the input PNG file.
    :param output_path: Path to save the output transparent PNG file.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGBA")
            img.save(output_path, "PNG")
        print(f"Converted {input_path} to {output_path} successfully.")
    except Exception as e:
        print(f"Error converting {input_path}: {e}")

convert_png_to_transparent_png(r"C:\Users\Lenovo\Desktop\Contribution\py_env_studio\py_env_studio\ui\static\icons\pes-default.png", r"C:\Users\Lenovo\Desktop\Contribution\py_env_studio\py_env_studio\ui\static\icons\pes-default-t.png")