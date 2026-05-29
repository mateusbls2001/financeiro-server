from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import os, uuid, subprocess, random

app = Flask(__name__)
OUTPUT_DIR  = "/tmp/financeiro_imgs"
MUSIC_DIR   = "/app/music"
VIDEO_DURATION = 10
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── FONTS ──────────────────────────────────────────────────────────────────────
LORA_BOLD = "/app/fonts/Lora-Bold.ttf"
LORA_REG  = "/app/fonts/Lora-Regular.ttf"
FB_BOLD   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FB_REG    = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def load_font(bold=True, size=48):
    paths = [LORA_BOLD, FB_BOLD] if bold else [LORA_REG, FB_REG]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ── CONFIG ─────────────────────────────────────────────────────────────────────
W = H      = 1080
BG         = (0, 0, 0)
TEXT_WHITE = (255, 255, 255)
HANDLE     = "@pensarfinanceiro_01"

KEYWORDS = [
    "rico", "pobre", "dinheiro", "investir", "investimento",
    "juros", "patrimônio", "liberdade", "riqueza", "lucro",
    "salário", "dívida", "poupar", "gastar", "inflação",
    "tempo", "nunca", "sempre", "não", "mais", "menos",
    "primeiro", "único", "maior", "melhor", "pior"
]

# ── MUSIC ──────────────────────────────────────────────────────────────────────
def get_random_music():
    try:
        files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mp3', '.wav'))]
        if files:
            return os.path.join(MUSIC_DIR, random.choice(files))
    except: pass
    return None

# ── HELPERS ────────────────────────────────────────────────────────────────────
def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bb   = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines

# ── FRAME CREATOR ──────────────────────────────────────────────────────────────
def create_frame(phrase, reference=""):
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Linha decorativa topo
    draw.rectangle([80, 88, 200, 91], fill=(40, 40, 40))
    draw.rectangle([80, 88, 100, 91], fill=TEXT_WHITE)

    font_main   = load_font(bold=True,  size=25)
    font_ref    = load_font(bold=False, size=24)
    font_handle = load_font(bold=False, size=22)

    lines       = wrap_text(draw, phrase, font_main, W - 160)
    line_height = 78
    total_h     = len(lines) * line_height
    y_start     = (H - total_h) // 2 - 30

    for line in lines:
        words     = line.split()
        total_w   = sum(draw.textbbox((0,0), w + " ", font=font_main)[2] for w in words)
        x_word    = (W - total_w) // 2

        for word in words:
            word_clean = word.lower().strip(".,!?;:")
            is_kw      = word_clean in KEYWORDS
            f          = load_font(bold=True, size=25)
            color      = TEXT_WHITE if is_kw else (190, 190, 190)
            draw.text((x_word, y_start), word + " ", font=f, fill=color)
            wb         = draw.textbbox((0, 0), word + " ", font=f)
            x_word    += wb[2] - wb[0]

        y_start += line_height

    # Separador
    y_sep = y_start + 28
    draw.rectangle([(W-60)//2, y_sep, (W+60)//2, y_sep+1], fill=(60, 60, 60))

    # Reference
    if reference:
        bb_r = draw.textbbox((0, 0), reference.upper(), font=font_ref)
        draw.text(((W - (bb_r[2]-bb_r[0]))//2, y_sep+20),
                  reference.upper(), font=font_ref, fill=(70, 70, 70))

    # Handle
    bb_h = draw.textbbox((0, 0), HANDLE, font=font_handle)
    draw.text(((W - (bb_h[2]-bb_h[0]))//2, H-60),
              HANDLE, font=font_handle, fill=(50, 50, 50))

    # Linha decorativa fundo
    draw.rectangle([W-200, H-92, W-80, H-89], fill=(30, 30, 30))
    draw.rectangle([W-100, H-92, W-80, H-89], fill=(60, 60, 60))

    return img

# ── VIDEO ──────────────────────────────────────────────────────────────────────
def image_to_video(img, output_path, duration=VIDEO_DURATION):
    fp = f"/tmp/{uuid.uuid4()}.png"
    img.save(fp, 'PNG')
    music_path = get_random_music()

    if music_path:
        cmd = ["ffmpeg","-y","-loop","1","-i",fp,
               "-i", music_path,
               "-vf",f"fade=in:0:15,fade=out:st={duration-1}:d=1,scale=1080:1080",
               "-af",f"afade=in:st=0:d=1,afade=out:st={duration-1}:d=1",
               "-c:v","libx264","-c:a","aac","-b:a","128k",
               "-t",str(duration),"-pix_fmt","yuv420p",
               "-movflags","+faststart","-shortest",output_path]
    else:
        cmd = ["ffmpeg","-y","-loop","1","-i",fp,
               "-vf",f"fade=in:0:15,fade=out:st={duration-1}:d=1,scale=1080:1080",
               "-c:v","libx264","-t",str(duration),
               "-pix_fmt","yuv420p","-movflags","+faststart",output_path]

    r = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(fp)
    if r.returncode != 0:
        raise Exception(f"FFmpeg error: {r.stderr}")
    return output_path

# ── ROUTES ─────────────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "pensarfinanceiro"})

@app.route('/generate-image-url', methods=['POST'])
def generate_image_url():
    data = request.get_json(force=True)
    phrase    = data.get('phrase', '').strip()
    reference = data.get('reference', '').strip()
    if not phrase:
        return jsonify({"error": "phrase obrigatorio"}), 400
    try:
        frame    = create_frame(phrase, reference)
        img_id   = str(uuid.uuid4())
        out_path = os.path.join(OUTPUT_DIR, f"{img_id}.png")
        frame.save(out_path, 'PNG')
        base = request.host_url.rstrip('/').replace('http://', 'https://')
        return jsonify({"success": True, "image_url": f"{base}/image/{img_id}", "image_id": img_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate-url', methods=['POST'])
def generate_video_url():
    data      = request.get_json(force=True)
    phrase    = data.get('phrase', '').strip()
    reference = data.get('reference', '').strip()
    duration  = int(data.get('duration', VIDEO_DURATION))
    if not phrase:
        return jsonify({"error": "phrase obrigatorio"}), 400
    try:
        frame    = create_frame(phrase, reference)
        vid_id   = str(uuid.uuid4())
        out_path = os.path.join(OUTPUT_DIR, f"{vid_id}.mp4")
        image_to_video(frame, out_path, duration)
        base = request.host_url.rstrip('/').replace('http://', 'https://')
        return jsonify({"success": True, "video_url": f"{base}/video/{vid_id}", "video_id": vid_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/image/<image_id>', methods=['GET'])
def get_image(image_id):
    try: uuid.UUID(image_id)
    except: return jsonify({"error": "Invalid ID"}), 400
    path = os.path.join(OUTPUT_DIR, f"{image_id}.png")
    if not os.path.exists(path): return jsonify({"error": "Not found"}), 404
    return send_file(path, mimetype='image/png')

@app.route('/video/<video_id>', methods=['GET'])
def get_video(video_id):
    try: uuid.UUID(video_id)
    except: return jsonify({"error": "Invalid ID"}), 400
    path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
    if not os.path.exists(path): return jsonify({"error": "Not found"}), 404
    return send_file(path, mimetype='video/mp4')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
