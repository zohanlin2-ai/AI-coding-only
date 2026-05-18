import os
import re
import traceback
import torch
from pathlib import Path
from diffusers import AutoPipelineForText2Image
from datetime import datetime
from deep_translator import GoogleTranslator

MODELS_CONFIG: dict[str, dict] = {
    "DreamShaper 8 (均衡藝術 / 動漫寫實)": {
        "id": "Lykon/dreamshaper-8",
        "steps": 30,
        "guidance": 7.5,
        "default_size": (512, 512)
    },
    "SDXL Turbo (1024px 光速頂級高畫質)": {
        "id": "stabilityai/sdxl-turbo",
        "steps": 3,
        "guidance": 0.0,
        "default_size": (512, 512)
    },
    "Realistic Vision 5.1 (真人相片質感)": {
        "id": "SG161222/Realistic_Vision_V5.1_noVAE",
        "steps": 30,
        "guidance": 7.5,
        "default_size": (512, 512)
    }
}

_DEFAULT_MODEL_KEY = "DreamShaper 8 (均衡藝術 / 動漫寫實)"


class AIEngine:
    def __init__(self, model_id: str = MODELS_CONFIG[_DEFAULT_MODEL_KEY]["id"]):
        self.model_id: str = model_id
        self.pipe = None
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype: torch.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.device_name: str = torch.cuda.get_device_name(0) if self.device == "cuda" else "CPU"
        self._saved_safety_checker = None

    def get_device_info(self) -> str:
        """Returns a string describing the hardware being used."""
        if self.device == "cuda":
            return f"硬體加速: NVIDIA GPU ({self.device_name})"
        return "硬體加速: 僅使用 CPU (建議安裝 CUDA 版 Torch 以加速)"

    def load_model(self) -> None:
        """Loads the model into memory, applying VAE float32 and optional xformers."""
        if self.pipe is not None:
            return

        print(f"Loading model {self.model_id} on {self.device}...")
        self.pipe = AutoPipelineForText2Image.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype
        ).to(self.device)

        self._saved_safety_checker = getattr(self.pipe, "safety_checker", None)

        # Cast VAE to float32 once to prevent NaN numerical overflow during decoding
        if hasattr(self.pipe, "vae"):
            self.pipe.vae.to(dtype=torch.float32)
            print("VAE cast to float32 to prevent black images.")

        # Reduce VRAM footprint with attention slicing
        if self.device == "cuda":
            self.pipe.enable_attention_slicing()

        # Soft-detect and enable xformers for ~20-30% VRAM reduction and speed boost
        if self.device == "cuda":
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                print("xformers memory-efficient attention enabled.")
            except Exception:
                print("xformers not available, using default attention.")

    def switch_model(self, new_model_id: str) -> None:
        """Switches the active model and clears GPU memory cache if changed."""
        if self.pipe is not None and self.model_id != new_model_id:
            print(f"Switching model: {self.model_id} → {new_model_id}. Unloading...")
            del self.pipe
            self.pipe = None
            if self.device == "cuda":
                torch.cuda.empty_cache()

        self.model_id = new_model_id
        self.load_model()

    def parse_prompt(self, user_prompt: str) -> tuple[str, int | None, int | None, str]:
        """
        Parses the prompt to extract size, format, and translates to English.
        Returns: (translated_prompt, width, height, img_format)
        """
        # Extract size (e.g., 1024x1024)
        size_match = re.search(r'(\d{3,4})[x*](\d{3,4})', user_prompt)
        width, height = None, None
        if size_match:
            width = int(size_match.group(1))
            height = int(size_match.group(2))
            user_prompt = user_prompt.replace(size_match.group(0), "").strip()

        # Extract format (e.g., png, webp, jpg)
        format_match = re.search(r'\b(png|jpg|jpeg|webp)\b', user_prompt, re.IGNORECASE)
        img_format = "jpg"
        if format_match:
            img_format = format_match.group(1).lower()
            if img_format == "jpeg":
                img_format = "jpg"
            user_prompt = user_prompt.replace(format_match.group(0), "").strip()

        # Clean up trailing commas or spaces
        clean_prompt = re.sub(r',\s*$', '', user_prompt).strip()

        # Translate to English for AI comprehension
        translated_prompt = clean_prompt
        if clean_prompt:
            try:
                result = GoogleTranslator(source='auto', target='en').translate(clean_prompt)
                # Validate translation result — fallback to original if empty/None
                if result and result.strip():
                    translated_prompt = result.strip()
                    print(f"Translated: '{clean_prompt}' → '{translated_prompt}'")
                else:
                    print(f"Translation returned empty, using original: '{clean_prompt}'")
            except Exception as e:
                print(f"Translation warning (using original): {e}")

        return translated_prompt, width, height, img_format

    def generate(
        self,
        user_prompt: str,
        model_key: str = _DEFAULT_MODEL_KEY,
        output_dir: str = "outputs",
        enable_safety_check: bool = False
    ) -> tuple[str, str]:
        """Generates an image and saves it. Returns (filepath, translated_prompt)."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Resolve model config
        config = MODELS_CONFIG.get(model_key, MODELS_CONFIG[_DEFAULT_MODEL_KEY])
        steps: int = config["steps"]
        guidance: float = config["guidance"]
        default_w, default_h = config["default_size"]

        prompt, width, height, img_format = self.parse_prompt(user_prompt)
        w: int = width if width is not None else default_w
        h: int = height if height is not None else default_h

        # Switch/load model
        self.switch_model(config["id"])

        # Dynamically toggle safety checker per request
        if hasattr(self.pipe, "safety_checker"):
            self.pipe.safety_checker = (
                self._saved_safety_checker if enable_safety_check else None
            )

        print(
            f"Generating: '{prompt}' ({w}x{h}, {img_format}) | "
            f"Model: {self.model_id} | Steps: {steps} | "
            f"Guidance: {guidance} | Safety: {enable_safety_check}"
        )

        # Stage 1: UNet generation under autocast (fp16) → produces raw latents
        with torch.autocast(self.device):
            latents = self.pipe(
                prompt,
                width=w,
                height=h,
                num_inference_steps=steps,
                guidance_scale=guidance,
                output_type="latent"
            ).images

        # Stage 2: VAE decode in pure float32 (prevents NaN / black screen)
        latents = latents.to(dtype=torch.float32)
        self.pipe.vae.to(dtype=torch.float32)
        with torch.no_grad():
            decoded = self.pipe.vae.decode(
                latents / self.pipe.vae.config.scaling_factor,
                return_dict=False
            )[0]
            image = self.pipe.image_processor.postprocess(decoded, output_type="pil")[0]

        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = output_path / f"gen_{timestamp}.{img_format}"
        image.save(filepath)

        print(f"Image saved: {filepath}")
        return str(filepath), prompt
