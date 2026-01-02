import asyncio
import os
import random
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
import httpx
from runware import IImageInference, Runware

from back.config import (get_image_generation_config, get_logger,
                         get_world_config, project_root)

logger = get_logger(__name__)

class ImageGenerationService:
    """
    ### ImageGenerationService
    **Description:** Service for generating character portraits using Runware.
    """
    api_key: Optional[str]
    config: Dict[str, Any]
    runware: Optional[Runware]
    static_dir: Path

    def __init__(self):
        self.api_key = os.environ.get("RUNWARE_API_KEY")
        self.config = get_image_generation_config()
        self.world_config = get_world_config()
        self.runware = Runware(api_key=self.api_key) if self.api_key else None
        
        # Static directory setup
        self.static_dir = project_root / "back" / "static" / "characters"
        self._ensure_static_dir()

    def _ensure_static_dir(self) -> None:
        """Ensure the static directory exists."""
        if not self.static_dir.exists():
            self.static_dir.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        """Check if image generation is enabled."""
        return self.config.get("enabled", False) and bool(self.api_key)

    async def generate_character_portrait(self, character_data: Dict[str, Any]) -> Optional[str]:
        """
        ### generate_character_portrait
        **Description:** Generates a portrait for a character.
        **Parameters:**
        - `character_data` (Dict[str, Any]): Character data including name, race, culture, description, equipment.
        **Returns:**
        - `Optional[str]`: Relative URL of the generated image or None if failed/disabled.
        """
        if not self.is_enabled():
            logger.info("Image generation is disabled or API key is missing.")
            return None

        if not self.runware:
             logger.error("Runware client not initialized (missing API key?)")
             return None

        try:
            # Construct prompt
            name = character_data.get("name", "Unknown")
            race = character_data.get("race", "Human")
            culture = character_data.get("culture", "Unknown")
            sex = character_data.get("sex", "Unknown")
            if hasattr(sex, "value"):
                sex = sex.value
            physical_desc = character_data.get("physical_description", "")
            
            # Simple prompt construction
            # Utilisation de parenthèses pour donner du poids aux mots-clés importants
            # --- 2. Listes de modificateurs aléatoires ---

            # Éclairages : Pour changer l'ambiance (mystérieux, divin, sombre)
            lighting_options = [
                "cinematic lighting", 
                "dramatic rim lighting",        # Très bon pour détacher la silhouette (sexy)
                "bioluminescent glow",          # Typique Fantasy / Underdark
                "golden hour sunlight",         # Lumière chaude et douce
                "volumetric fog and lighting",  # Donne de la profondeur
                "dark moody atmosphere",        # Style donjon
                "soft studio lighting",         # Met en valeur la peau
                "candlelight"                   # Intime
            ]

            # Angles de caméra : Pour varier le cadrage
            camera_options = [
                "close-up portrait",            # Visage et épaules
                "medium shot",                  # Plan taille
                "cowboy shot",                  # Plan américain (mi-cuisse)
                "low angle view",               # Contre-plongée (donne un air dominant)
                "high angle view",              # Plongée
                "looking over shoulder",        # Séducteur
                "shot with 85mm lens"           # Focale idéale pour les portraits
            ]

            # Qualité et Moteur de rendu : Pour forcer le réalisme style BG3
            render_options = [
                "Unreal Engine 5 render", 
                "Octane Render", 
                "subsurface scattering",        # Rendu réaliste de la lumière sous la peau
                "ray tracing", 
                "8k resolution", 
                "photorealistic texture"
            ]

            # Poses (Optionnel) : Pour éviter la pose statique "passeport"
            pose_options = [
                "dynamic pose",
                "alluring pose",
                "fighting stance",
                "resting pose",
                "looking at viewer"
            ]

            # --- 3. Sélection aléatoire ---
            selected_light = random.choice(lighting_options)
            selected_camera = random.choice(camera_options)
            selected_render = random.choice(render_options)
            selected_pose = random.choice(pose_options)

            # --- 4. Construction du prompt optimisé ---
            # Use World Config for Style and Lore context
            lore = self.world_config.get("lore", "Fantasy setting")
            art_style = self.world_config.get("art_style", "fantasy illustration style")

            prompt = (
                f"Context: {lore}. "
                f"((masterpiece, best quality)), {art_style}, "
                f"portrait of a {race} {culture} {sex}, {physical_desc}, "
                f"{selected_pose}, {selected_camera}, "
                f"{selected_light}, {selected_render}, "
                f"highly detailed, sharp focus, no watermark, no text, no signature, no logo"
            )
            # Truncate if too long (simple protection)
            prompt = prompt[:10000]

            logger.info(f"Generating portrait for {name} with prompt: {prompt}")

            await self.runware.connect()
            
            request = IImageInference(
                positivePrompt=prompt,
                model=self.config.get("model", "rundiffusion:130@100"),
                width=1024,
                height=1024,
                numberResults=1
            )
            
            images = await self.runware.imageInference(requestImage=request)
            
            if images and images[0].imageURL:
                image_url = images[0].imageURL
                logger.info(f"Image generated successfully: {image_url}")
                
                character_id = character_data.get('id', 'temp')
                
                # 1. Clean up old images for this character
                # Search for files starting with character_id in the static dir
                try:
                    for filename in os.listdir(self.static_dir):
                        if filename.startswith(f"{character_id}_") or filename == f"{character_id}.png":
                            file_path = self.static_dir / filename
                            if file_path.exists():
                                logger.info(f"Deleting old portrait: {filename}")
                                os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Error cleaning up old portraits: {e}")

                # 2. Generate new unique filename
                import time
                timestamp = int(time.time())
                local_filename = f"{character_id}_{timestamp}.png"
                local_path = self.static_dir / local_filename
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    response.raise_for_status()
                    async with aiofiles.open(local_path, 'wb') as f:
                        await f.write(response.content)
                
                return f"/static/characters/{local_filename}"
            
            return None

        except Exception as e:
            logger.error(f"Error generating character portrait: {e}")
            return None
        finally:
             # Runware disconnect
            pass 
