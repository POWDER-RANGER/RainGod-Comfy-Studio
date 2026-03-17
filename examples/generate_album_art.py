#!/usr/bin/env python3
"""
RAINGOD Album Art Generator
Example script for generating album artwork using the RAINGOD backend
"""

import requests
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# ============================================================================
# Configuration
# ============================================================================

BACKEND_URL = "http://localhost:8000"
GENERATE_ENDPOINT = f"{BACKEND_URL}/generate"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
OUTPUT_DIR = Path("outputs")

# ============================================================================
# Helper Functions
# ============================================================================

def check_backend_health() -> bool:
    """Check if backend is healthy and ready"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "healthy"
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
    return False


def generate_image(
    prompt: str,
    negative_prompt: Optional[str] = None,
    preset: str = "quality",
    resolution: str = "cover_art",
    seed: Optional[int] = None,
    lora_style: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate image using RAINGOD backend
    
    Args:
        prompt: Text description of desired image
        negative_prompt: Things to avoid in generation
        preset: Sampler preset (fast/quality/ultra)
        resolution: Resolution preset name
        seed: Random seed for reproducibility
        lora_style: LoRA style to apply
        metadata: Additional metadata
        
    Returns:
        Response data with prompt_id and outputs
    """
    payload = {
        "prompt": prompt,
        "preset": preset,
        "resolution": resolution
    }
    
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    
    if seed is not None:
        payload["seed"] = seed
    
    if lora_style:
        payload["lora_style"] = lora_style
    
    if metadata:
        payload["metadata"] = metadata
    
    print(f"🎨 Generating image with preset '{preset}' at resolution '{resolution}'...")
    print(f"   Prompt: {prompt[:80]}...")
    
    try:
        response = requests.post(
            GENERATE_ENDPOINT,
            json=payload,
            timeout=300  # 5 minutes
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out - generation may still be processing")
        raise
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        raise


def save_metadata(result: Dict[str, Any], output_file: Path):
    """Save generation metadata to JSON file"""
    metadata_file = output_file.with_suffix('.json')
    with open(metadata_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"💾 Metadata saved: {metadata_file}")


def print_result(result: Dict[str, Any]):
    """Pretty print generation result"""
    print("\n" + "="*60)
    print("✅ Generation Complete!")
    print("="*60)
    print(f"Prompt ID:       {result.get('prompt_id')}")
    print(f"Status:          {result.get('status')}")
    print(f"Estimated Time:  {result.get('estimated_time', 'N/A')}")
    
    if result.get('outputs'):
        print("\nOutputs:")
        for key, value in result['outputs'].items():
            print(f"  • {key}: {value}")
    
    print("="*60 + "\n")


# ============================================================================
# Pre-defined Album Styles
# ============================================================================

ALBUM_STYLES = {
    "synthwave": {
        "prompt": "retro synthwave album cover with neon colors, palm trees, sunset gradient, 1980s aesthetic, vibrant purple and pink",
        "negative_prompt": "realistic, photographic, modern, dull colors",
        "lora_style": "synthwave"
    },
    "cyberpunk": {
        "prompt": "futuristic cyberpunk cityscape album cover, neon lights, rain-soaked streets, dystopian atmosphere, dark blue and purple tones",
        "negative_prompt": "nature, organic, bright daylight",
        "lora_style": "cyberpunk"
    },
    "abstract": {
        "prompt": "abstract geometric album cover art, flowing shapes, vibrant colors, modern design, minimalist composition",
        "negative_prompt": "realistic, figurative, detailed background",
        "lora_style": "abstract"
    },
    "atmospheric": {
        "prompt": "atmospheric ethereal album cover, dreamy clouds, soft lighting, peaceful mood, pastel colors, minimalist",
        "negative_prompt": "busy, cluttered, dark, aggressive",
        "lora_style": None
    },
    "dark": {
        "prompt": "dark moody album cover, dramatic lighting, shadows, mysterious atmosphere, deep blacks and subtle highlights",
        "negative_prompt": "bright, colorful, cheerful, cartoonish",
        "lora_style": None
    }
}


# ============================================================================
# Example Use Cases
# ============================================================================

def generate_single_album_cover(
    album_name: str,
    artist_name: str,
    style: str = "synthwave",
    preset: str = "quality"
):
    """Generate a single album cover"""
    print(f"\n🎵 Generating album cover for: {album_name} by {artist_name}")
    
    if style in ALBUM_STYLES:
        style_config = ALBUM_STYLES[style]
        prompt = f"{style_config['prompt']}, album cover for {album_name} by {artist_name}"
        negative_prompt = style_config['negative_prompt']
        lora_style = style_config['lora_style']
    else:
        prompt = f"album cover for {album_name} by {artist_name}, professional music artwork"
        negative_prompt = "text, words, letters, low quality"
        lora_style = None
    
    metadata = {
        "album_name": album_name,
        "artist_name": artist_name,
        "style": style
    }
    
    result = generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        preset=preset,
        resolution="cover_art",
        lora_style=lora_style,
        metadata=metadata
    )
    
    print_result(result)
    return result


def generate_album_package(
    album_name: str,
    artist_name: str,
    style: str = "synthwave",
    track_count: int = 12
):
    """Generate complete album artwork package"""
    print(f"\n📦 Generating complete album package for: {album_name}")
    print(f"   Artist: {artist_name}")
    print(f"   Style: {style}")
    print(f"   Tracks: {track_count}")
    
    results = {}
    
    # 1. Main album cover (high quality)
    print("\n1️⃣ Generating main album cover...")
    results['cover'] = generate_single_album_cover(
        album_name, artist_name, style, preset="quality"
    )
    
    # 2. Thumbnail for playlists (fast)
    print("\n2️⃣ Generating thumbnail...")
    results['thumbnail'] = generate_image(
        prompt=f"{ALBUM_STYLES.get(style, {}).get('prompt', 'album art')}, thumbnail size",
        preset="fast",
        resolution="thumbnail",
        metadata={"type": "thumbnail", "album": album_name}
    )
    
    # 3. High-res for print (ultra quality)
    print("\n3️⃣ Generating high-resolution version...")
    results['high_res'] = generate_image(
        prompt=f"{ALBUM_STYLES.get(style, {}).get('prompt', 'album art')}, high detail, premium quality",
        preset="ultra",
        resolution="high_res",
        metadata={"type": "high_res", "album": album_name}
    )
    
    print("\n✅ Album package complete!")
    print(f"   Generated {len(results)} variants")
    
    return results


def generate_track_variations(
    album_name: str,
    track_names: list,
    base_prompt: str,
    preset: str = "quality"
):
    """Generate unique covers for each track"""
    print(f"\n🎵 Generating track-specific artwork for album: {album_name}")
    
    results = []
    
    for i, track_name in enumerate(track_names, 1):
        print(f"\n{i}/{len(track_names)}: {track_name}")
        
        # Vary the prompt slightly for each track
        prompt = f"{base_prompt}, themed for song '{track_name}', track {i} of {len(track_names)}"
        
        result = generate_image(
            prompt=prompt,
            preset=preset,
            resolution="cover_art",
            metadata={
                "album": album_name,
                "track": track_name,
                "track_number": i
            }
        )
        
        results.append(result)
        time.sleep(2)  # Brief pause between generations
    
    print(f"\n✅ Generated {len(results)} track variants!")
    return results


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RAINGOD Album Art Generator - Create AI-generated album artwork",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate single album cover
  python generate_album_art.py --album "Neon Dreams" --artist "RainGod" --style synthwave
  
  # Generate complete album package
  python generate_album_art.py --album "Dark Matter" --artist "RainGod" --package --tracks 10
  
  # Custom prompt
  python generate_album_art.py --prompt "abstract geometric art" --preset ultra
  
  # List available styles
  python generate_album_art.py --list-styles
        """
    )
    
    parser.add_argument("--album", help="Album name")
    parser.add_argument("--artist", help="Artist name")
    parser.add_argument("--style", choices=list(ALBUM_STYLES.keys()), 
                       default="synthwave", help="Visual style preset")
    parser.add_argument("--preset", choices=["fast", "quality", "ultra"],
                       default="quality", help="Quality preset")
    parser.add_argument("--resolution", default="cover_art", 
                       help="Resolution preset")
    parser.add_argument("--prompt", help="Custom prompt (overrides album/style)")
    parser.add_argument("--negative", help="Negative prompt")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--package", action="store_true", 
                       help="Generate complete album package")
    parser.add_argument("--tracks", type=int, default=12,
                       help="Number of tracks (for package generation)")
    parser.add_argument("--list-styles", action="store_true",
                       help="List available style presets")
    
    args = parser.parse_args()
    
    # List styles and exit
    if args.list_styles:
        print("\n📋 Available Album Styles:")
        print("="*60)
        for name, config in ALBUM_STYLES.items():
            print(f"\n{name.upper()}")
            print(f"  Prompt: {config['prompt'][:60]}...")
            print(f"  LoRA: {config['lora_style'] or 'None'}")
        print("\n" + "="*60 + "\n")
        return
    
    # Check backend health
    print("🔍 Checking backend health...")
    if not check_backend_health():
        print("❌ Backend is not ready. Please start the backend first:")
        print("   ./scripts/start_all.sh")
        return
    
    print("✅ Backend is healthy and ready!\n")
    
    # Generate based on arguments
    if args.package:
        if not args.album or not args.artist:
            print("❌ --album and --artist required for package generation")
            return
        
        generate_album_package(
            args.album,
            args.artist,
            args.style,
            args.tracks
        )
    
    elif args.prompt:
        # Custom prompt mode
        result = generate_image(
            prompt=args.prompt,
            negative_prompt=args.negative,
            preset=args.preset,
            resolution=args.resolution,
            seed=args.seed
        )
        print_result(result)
    
    elif args.album and args.artist:
        # Single album cover
        generate_single_album_cover(
            args.album,
            args.artist,
            args.style,
            args.preset
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
