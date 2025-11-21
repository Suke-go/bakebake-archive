import sys
import os
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
import cv2

# Add Grounded-Segment-Anything to path if necessary
# Assuming the repo is cloned in the parent directory of src
sys.path.append(os.path.join(os.path.dirname(__file__), '../Grounded-Segment-Anything'))

try:
    # Grounding DINO
    import groundingdino.datasets.transforms as T
    from groundingdino.models import build_model
    from groundingdino.util.slconfig import SLConfig
    from groundingdino.util.utils import clean_state_dict, get_phrases_from_posmap
    
    # Segment Anything
    from segment_anything import build_sam, SamPredictor
except ImportError as e:
    print(f"Warning: Could not import Grounded-Segment-Anything modules: {e}")
    print("Ensure you have cloned the repo and installed dependencies.")

class GroundedSAMInferencer:
    def __init__(self, checkpoints_dir, device="cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.checkpoints_dir = checkpoints_dir
        
        # Config paths
        self.dino_config_path = os.path.join(os.path.dirname(__file__), '../Grounded-Segment-Anything/GroundingDINO/groundingdino/config/GroundingDINO_SwinT_OGC.py')
        self.dino_checkpoint_path = os.path.join(checkpoints_dir, 'groundingdino_swint_ogc.pth')
        self.sam_checkpoint_path = os.path.join(checkpoints_dir, 'sam_vit_h_4b8939.pth')
        
        self.grounding_dino_model = None
        self.sam_predictor = None

    def load_models(self):
        if self.grounding_dino_model is not None:
            return

        print("Loading GroundingDINO...")
        try:
            args = SLConfig.fromfile(self.dino_config_path)
            self.grounding_dino_model = build_model(args)
            checkpoint = torch.load(self.dino_checkpoint_path, map_location='cpu')
            self.grounding_dino_model.load_state_dict(clean_state_dict(checkpoint['model']), strict=False)
            self.grounding_dino_model.to(self.device)
            self.grounding_dino_model.eval()
        except Exception as e:
            print(f"Error loading GroundingDINO: {e}")

        print("Loading SAM...")
        try:
            self.sam_predictor = SamPredictor(build_sam(checkpoint=self.sam_checkpoint_path).to(self.device))
        except Exception as e:
            print(f"Error loading SAM: {e}")

    def transform_image(self, image_pil):
        transform = T.Compose([
            T.RandomResize([800], max_size=1333),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        image, _ = transform(image_pil, None)
        return image

    def predict(self, image_pil, text_prompt, box_threshold=0.3, text_threshold=0.25):
        if self.grounding_dino_model is None:
            self.load_models()

        # Run Grounding DINO
        image_tensor = self.transform_image(image_pil).to(self.device)
        
        with torch.no_grad():
            outputs = self.grounding_dino_model(image_tensor[None], captions=[text_prompt])
        
        logits = outputs["pred_logits"].cpu().sigmoid()[0]  # (nq, 256)
        boxes = outputs["pred_boxes"].cpu()[0]  # (nq, 4)
        
        # Filter output
        logits_filt = logits.clone()
        boxes_filt = boxes.clone()
        filt_mask = logits_filt.max(dim=1)[0] > box_threshold
        logits_filt = logits_filt[filt_mask]
        boxes_filt = boxes_filt[filt_mask]
        
        # Run SAM
        image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
        self.sam_predictor.set_image(image_cv)
        
        H, W = image_pil.size[1], image_pil.size[0]
        
        transformed_boxes = self.sam_predictor.transform.apply_boxes_torch(boxes_filt * torch.Tensor([W, H, W, H]), image_cv.shape[:2]).to(self.device)
        
        if len(transformed_boxes) == 0:
            return None, image_pil

        masks, _, _ = self.sam_predictor.predict_torch(
            point_coords=None,
            point_labels=None,
            boxes=transformed_boxes,
            multimask_output=False,
        )
        
        # masks: (N, 1, H, W)
        return masks, boxes_filt

    def apply_mask(self, image_pil, masks, invert=False):
        """
        Applies mask to image. Returns RGBA image.
        masks: torch tensor (N, 1, H, W)
        """
        if masks is None:
            return image_pil.convert("RGBA")

        # Combine all masks
        # masks is (N, 1, H, W), we want logical OR of all masks
        combined_mask = torch.any(masks, dim=0).squeeze().cpu().numpy() # (H, W)
        
        if invert:
            combined_mask = ~combined_mask

        image_np = np.array(image_pil.convert("RGBA"))
        
        # Set alpha channel based on mask
        # combined_mask is boolean. True = Keep, False = Transparent
        image_np[:, :, 3] = np.where(combined_mask, 255, 0).astype(np.uint8)
        
        return Image.fromarray(image_np)

    def draw_preview(self, image_pil, masks):
        if masks is None:
            return image_pil
            
        combined_mask = torch.any(masks, dim=0).squeeze().cpu().numpy()
        
        # Create a colored overlay
        overlay = np.array(image_pil)
        # Green overlay for kept area
        overlay[combined_mask] = overlay[combined_mask] * 0.5 + np.array([0, 255, 0]) * 0.5
        
        return Image.fromarray(overlay.astype(np.uint8))

