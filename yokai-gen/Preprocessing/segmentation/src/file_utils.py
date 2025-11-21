import os
import shutil
import glob
from pathlib import Path

class ImageQueue:
    def __init__(self, input_dir, output_dir, processed_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.processed_dir = Path(processed_dir)
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.refresh_queue()
        
    def refresh_queue(self):
        """Scans input directory for images."""
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp']
        self.queue = []
        for ext in extensions:
            self.queue.extend(sorted(self.input_dir.glob(ext)))
            # Case insensitive check might be needed in some envs, but glob is usually case sensitive on Linux
            self.queue.extend(sorted(self.input_dir.glob(ext.upper())))
            
        # Remove duplicates if any
        self.queue = sorted(list(set(self.queue)))
        print(f"Queue refreshed. {len(self.queue)} images found.")

    def get_next(self):
        """Returns the next image path or None if empty."""
        if not self.queue:
            self.refresh_queue()
            if not self.queue:
                return None
        return self.queue[0]

    def requeue(self):
        """Moves current item to the back of the queue."""
        if self.queue:
            item = self.queue.pop(0)
            self.queue.append(item)
            return self.get_next()
        return None

    def mark_processed(self, current_path):
        """Moves the file to processed directory and removes from queue."""
        if current_path and os.path.exists(current_path):
            filename = os.path.basename(current_path)
            dest_path = self.processed_dir / filename
            try:
                shutil.move(str(current_path), str(dest_path))
                print(f"Moved {current_path} to {dest_path}")
                if current_path in self.queue:
                    self.queue.remove(current_path)
            except Exception as e:
                print(f"Error moving file: {e}")
        
        # Return next image
        return self.get_next()

    def save_result(self, image_pil, original_filename):
        """Saves the PIL image to output directory."""
        # Change extension to png to support transparency
        stem = Path(original_filename).stem
        out_path = self.output_dir / f"{stem}.png"
        image_pil.save(out_path, "PNG")
        print(f"Saved result to {out_path}")

