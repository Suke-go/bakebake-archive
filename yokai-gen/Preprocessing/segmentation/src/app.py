import gradio as gr
import os
from file_utils import ImageQueue
from segmentation_utils import GroundedSAMInferencer
from PIL import Image

# Configuration
INPUT_DIR = "inputs"
OUTPUT_DIR = "outputs"
PROCESSED_DIR = "processed"
CHECKPOINTS_DIR = "checkpoints"

# Global Objects
queue = ImageQueue(INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR)
inferencer = GroundedSAMInferencer(CHECKPOINTS_DIR)

def process_image(image, prompt, box_thresh, text_thresh):
    """Runs inference and returns preview + masks."""
    if image is None:
        return None, None

    masks, _boxes = inferencer.predict(image, prompt, box_thresh, text_thresh)

    # Generate preview (overlay)
    preview = inferencer.draw_preview(image, masks)

    return preview, masks

def save_and_next(original_path, image, masks, keep_foreground):
    """Saves the result and loads next."""
    if original_path is None or not os.path.exists(original_path):
        return load_next_step()

    # Apply mask
    result_img = inferencer.apply_mask(image, masks, invert=not keep_foreground)

    # Save
    queue.save_result(result_img, original_path)

    # Move original
    next_path = queue.mark_processed(original_path)

    return load_next_step(next_path)

def skip_and_next(_original_path):
    """Requeues and loads next."""
    next_path = queue.requeue()
    return load_next_step(next_path)

def load_next_step(path=None):
    if path is None:
        path = queue.get_next()

    if path:
        image = Image.open(path)
        path_str = str(path)
        return image, path_str, path_str, None, None  # Reset masks/preview
    else:
        return None, "No more images!", None, None, None

# Gradio Block
with gr.Blocks(title="Yokai Segmentation Tool") as demo:
    gr.Markdown("# 妖怪画像セグメンテーションツール")
    
    current_file_path = gr.State()
    current_masks = gr.State()
    
    with gr.Row():
        with gr.Column(scale=1):
            input_image = gr.Image(type="pil", label="Original Image")
            file_info = gr.Textbox(label="Current File", interactive=False)

        with gr.Column(scale=1):
            result_preview = gr.Image(type="pil", label="Segmentation Preview")

    with gr.Row():
        text_prompt = gr.Textbox(
            label="Detection Prompt",
            value="yokai, 妖怪, おばけ, 幽霊, ghost",
        )
        box_thresh = gr.Slider(minimum=0.0, maximum=1.0, value=0.3, label="Box Threshold")
        text_thresh = gr.Slider(minimum=0.0, maximum=1.0, value=0.25, label="Text Threshold")
        run_btn = gr.Button("Run Segmentation", variant="primary")
    
    with gr.Row():
        save_fg_btn = gr.Button("Save (Keep Mask / Remove BG)", variant="primary")
        save_bg_btn = gr.Button("Save (Remove Mask / Keep BG)")
        skip_btn = gr.Button("Skip (Re-queue)", variant="stop")
    
    # Logic
    def on_load():
        image, file_text, path_state, _preview, _masks = load_next_step()
        if image:
            return image, file_text, path_state
        return None, "No images found in inputs/", None

    load_event = demo.load(on_load, inputs=[], outputs=[input_image, file_info, current_file_path])
    load_event.then(
        process_image,
        inputs=[input_image, text_prompt, box_thresh, text_thresh],
        outputs=[result_preview, current_masks],
    )
    
    run_btn.click(
        process_image,
        inputs=[input_image, text_prompt, box_thresh, text_thresh],
        outputs=[result_preview, current_masks]
    )
    
    # Auto-run when image changes? Maybe better manual to save GPU if prompt needs tweaking
    # But user asked for efficiency. Let's stick to manual run for first version or add an "Auto" checkbox.
    
    save_fg_event = save_fg_btn.click(
        lambda p, i, m: save_and_next(p, i, m, True),
        inputs=[current_file_path, input_image, current_masks],
        outputs=[input_image, file_info, current_file_path, result_preview, current_masks]
    )
    save_fg_event.then(
        process_image,
        inputs=[input_image, text_prompt, box_thresh, text_thresh],
        outputs=[result_preview, current_masks],
    )

    save_bg_event = save_bg_btn.click(
        lambda p, i, m: save_and_next(p, i, m, False),
        inputs=[current_file_path, input_image, current_masks],
        outputs=[input_image, file_info, current_file_path, result_preview, current_masks]
    )
    save_bg_event.then(
        process_image,
        inputs=[input_image, text_prompt, box_thresh, text_thresh],
        outputs=[result_preview, current_masks],
    )

    skip_event = skip_btn.click(
        skip_and_next,
        inputs=[current_file_path],
        outputs=[input_image, file_info, current_file_path, result_preview, current_masks]
    )
    skip_event.then(
        process_image,
        inputs=[input_image, text_prompt, box_thresh, text_thresh],
        outputs=[result_preview, current_masks],
    )

if __name__ == "__main__":
    # Ensure models are loaded before starting server to avoid timeout on first request
    try:
        inferencer.load_models()
    except:
        print("Model loading skipped in main (will happen on first predict)")
        
    demo.launch(server_name="0.0.0.0", share=True)

