"""Optional: add photographic skin detail to the face with the local ComfyUI (Qwen-Image-Edit 2511, 4-step LoRA).

The face region of the composed colour map is cut out upright, sent through the edit model and blended back:
high-frequency detail everywhere on the face, plus part of the colour. Writes tools/out/detail_<tone>.png, which
compose_textures.py picks up as the skin base. ComfyUI must run on 127.0.0.1:8188.
usage (repo root): python -I tools/ai_detail.py light|dark [--seed N] [--keep]
"""
import json, os, sys, time, urllib.request, uuid
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "bake"); OUT = os.path.join(HERE, "out")
COMFY = r"E:\AI\ComfyUI_windows_portable\ComfyUI"
API = "http://127.0.0.1:8188"
PROMPT = ("Turn this into a photorealistic close-up photo of the same {who}, same face, same position and size of "
          "eyes, nose, mouth and eyebrows. Real human skin with fine pores, subtle freckles and natural colour variation, "
          "natural soft eyebrows with individual hairs, natural lips, no makeup. Flat, even, shadowless studio lighting. "
          "Keep the framing and the background exactly as they are.")
WHO = {"light": "young woman with fair skin", "dark": "young woman with dark brown skin"}


def region():
    """face region in the atlas (rows top-down): skin texels on the front of the head"""
    P = np.load(os.path.join(B, "pos.npy"))[::-1]; S = np.load(os.path.join(B, "src.npy"))[::-1]
    part = np.rint(S[..., 2] * 10).astype(int); part[np.abs(P).sum(-1) < 1e-6] = 9
    m = (part == 0) & (P[..., 1] < -0.035) & (P[..., 2] > 0.592) & (P[..., 2] < 0.790)
    ys, xs = np.nonzero(m); pad = 24
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, m.shape[1]), min(ys.max() + pad, m.shape[0]))
    return m, box, P


def post(path, data):
    req = urllib.request.Request(API + path, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def run_edit(png_name, prompt, seed):
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": png_name}},
        "5": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["4", 0]}},
        "6": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "7": {"class_type": "CFGNorm", "inputs": {"model": ["6", 0], "strength": 1.0}},
        "8": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["7", 0], "lora_name": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1.0}},
        "9": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["5", 0], "prompt": prompt}},
        "10": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["5", 0], "prompt": ""}},
        "11": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["9", 0], "reference_latents_method": "index_timestep_zero"}},
        "12": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["10", 0], "reference_latents_method": "index_timestep_zero"}},
        "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "14": {"class_type": "KSampler", "inputs": {"model": ["8", 0], "positive": ["11", 0], "negative": ["12", 0], "latent_image": ["13", 0],
                                                    "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["3", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": "fh_detail"}},
    }
    pid = post("/prompt", {"prompt": g, "client_id": uuid.uuid4().hex})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 1500:
        h = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error": raise RuntimeError(json.dumps(st)[:2000])
            outs = h[pid].get("outputs", {})
            if "16" in outs:
                im = outs["16"]["images"][0]
                return os.path.join(COMFY, "output", im.get("subfolder", ""), im["filename"])
        time.sleep(3)
    raise TimeoutError("ComfyUI did not finish")


def main(tone, seed=7, keep=False):
    m, box, P = region()
    co = Image.open(os.path.join(OUT, f"fh_{tone}_co.png")).convert("RGB")
    crop = co.crop(box).rotate(-90, expand=True)                  # face upright
    raw = os.path.join(OUT, f"_ai_raw_{tone}.png")
    if not (keep and os.path.exists(raw)):
        name = f"fh_face_{tone}.png"; crop.save(os.path.join(COMFY, "input", name))
        res = run_edit(name, PROMPT.format(who=WHO[tone]), seed)
        Image.open(res).convert("RGB").save(raw)
    ai = Image.open(raw).convert("RGB").resize(crop.size, Image.LANCZOS)
    crop.save(os.path.join(OUT, f"_ai_in_{tone}.png"))
    a = np.asarray(ai, dtype=np.float64) / 255; o = np.asarray(crop, dtype=np.float64) / 255
    blur = lambda im, r: np.asarray(Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float64) / 255
    # colour: match the model's low frequencies to ours (keeps the skin tone and the seams), keep its detail
    lo_a, lo_o = blur(a, 14), blur(o, 14)
    mixed = np.clip(lo_o + (a - lo_a) * 1.0 + (lo_a - lo_o) * 0.35, 0, 1)
    mix_img = Image.fromarray((mixed * 255).astype(np.uint8)).rotate(90, expand=True)
    det = np.asarray(co, dtype=np.float64) / 255
    w = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))
    w = (np.asarray(w, dtype=np.float64) / 255)[box[1]:box[3], box[0]:box[2], None]
    w = np.clip(w * 1.4 - 0.2, 0, 1)
    sub = det[box[1]:box[3], box[0]:box[2]]
    det[box[1]:box[3], box[0]:box[2]] = sub * (1 - w) + np.asarray(mix_img, dtype=np.float64) / 255 * w
    Image.fromarray((det * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, f"detail_{tone}.png"))
    print("wrote detail for", tone, "box", box)


if __name__ == "__main__":
    tone = sys.argv[1]
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 7
    main(tone, seed, "--keep" in sys.argv)
