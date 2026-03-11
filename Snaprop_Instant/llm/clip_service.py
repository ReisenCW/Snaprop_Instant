import os
from PIL import Image
try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class CLIPService:
    def __init__(self):
        self.model_name = "openai/clip-vit-base-patch32"
        self.model = None
        self.processor = None
        self.labels = ["毛坯房", "简装房", "精装房"]
        self.labels_cn = ["毛坯", "简装", "精装"]

    def _load_model(self):
        if not TRANSFORMERS_AVAILABLE:
            return False
        if self.model is None:
            try:
                self.model = CLIPModel.from_pretrained(self.model_name)
                self.processor = CLIPProcessor.from_pretrained(self.model_name)
            except Exception as e:
                print(f"Error loading CLIP model: {e}")
                return False
        return True

    def classify_decoration(self, image_path):
        """
        使用CLIP模型判断房屋装修情况
        """
        if not os.path.exists(image_path):
            return "简装"

        if not self._load_model():
            # Fallback logic if CLIP is not available
            # Try some basic keyword matching based on filename or just return default
            filename = os.path.basename(image_path).lower()
            if "rough" in filename or "mao" in filename:
                return "毛坯"
            if "fine" in filename or "jing" in filename or "lux" in filename:
                return "精装"
            return "简装"

        try:
            image = Image.open(image_path)
            inputs = self.processor(
                text=[f"a photo of a {label}" for label in ["rough house interior", "simply decorated house interior", "finely decorated house interior"]],
                images=image,
                return_tensors="pt",
                padding=True
            )

            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            idx = torch.argmax(probs, dim=1).item()
            return self.labels_cn[idx]
        except Exception as e:
            print(f"CLIP classification error: {e}")
            return "简装"

# Singleton instance
clip_service = CLIPService()
