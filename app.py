from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import os, uuid, textwrap

app = Flask(__name__)
OUTPUT_DIR = "/tmp/financeiro_imgs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── FONTS ──────────────────────────────────────────────────────────────────────
LORA_BOLD   = "/app/fonts/Lora-Bold.ttf"
LORA_REG    = "/app/fonts/Lora-Regular.ttf"
FB_BOLD     = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FB_REG      = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def load_font(bold=True, size=48):
    paths = [LORA_BOLD, FB_BOLD] if bold else [LORA_REG, FB_REG]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ── CONFIG ─────────────────────────────────────────────────────────────────────
W = H       = 1080
BG          = (0, 0, 0)
TEXT_WHITE  = (255, 255, 255)
TEXT_GRAY   = (160, 160, 160)
HANDLE      = "@pensarfinanceiro_01"

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

def find_keywords(phrase):
    """Detecta palavras-chave para destacar em bold"""
    keywords = [
        "rico", "pobre", "dinheiro", "investir", "investimento",
        "juros", "patrimônio", "liberdade", "riqueza", "lucro",
        "salário", "dívida", "poupar", "gastar", "inflação",
        "tempo", "nunca", "sempre", "não", "mais", "menos",
        "primeiro", "único", "maior", "melhor", "pior"
    ]
    found = []
    phrase_lower = phrase.lower()
    for kw in keywords:
        if kw in phrase_lower:
            found.append(kw)
    return found

# ── FRAME CREATOR ──────────────────────────────────────────────────────────────
def create_frame(phrase, reference=""):
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Linha decorativa topo
    draw.rectangle([80, 88, 200, 91], fill=(255, 255, 255, 40))
    draw.rectangle([80, 88, 100, 91], fill=TEXT_WHITE)

    # Fonte principal
    font_main   = load_font(bold=True,  size=58)
    font_small  = load_font(bold=False, size=52)
    font_ref    = load_font(bold=False, size=24)
    font_handle = load_font(bold=False, size=22)

    # Quebra o texto em linhas
    lines = wrap_text(draw, phrase, font_main, W - 160)

    line_height = 78
    total_h     = len(lines) * line_height
    y_start     = (H - total_h) // 2 - 30

    keywords = find_keywords(phrase)

    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_main)
        tw = bb[2] - bb[0]
        x  = (W - tw) // 2

        # Verifica se a linha tem palavra-chave pra destacar
        line_lower  = line.lower()
        has_keyword = any(kw in line_lower for kw in keywords)

        if has_keyword:
            # Renderiza palavra por palavra pra destacar keywords
            words   = line.split()
            total_w = sum(draw.textbbox((0, 0), w + " ", font=font_main)[2] for w in words)
            x_word  = (W - total_w) // 2

            for word in words:
                word_lower = word.lower().strip(".,!?")
                is_kw      = any(kw == word_lower for kw in keywords)
                f          = load_font(bold=True, size=58) if is_kw else load_font(bold=False, size=58)
                color      = TEXT_WHITE if is_kw else (200, 200, 200)
                draw.text((x_word, y_start), word + " ", font=f, fill=color)
                wb = draw.textbbox((0, 0), word + " ", font=f)
                x_word += wb[2] - wb[0]
        else:
            draw.text((x, y_start), line, font=font_main, fill=(200, 200, 200))

        y_start += line_height

    # Linha decorativa separadora
    y_sep = y_start + 28
    draw.rectangle([(W - 60) // 2, y_sep, (W + 60) // 2, y_sep + 1], fill=(80, 80, 80))

    # Reference / tema
    if reference:
        bb_r = draw.textbbox((0, 0), reference.upper(), font=font_ref)
        tw_r = bb_r[2] - bb_r[0]
        draw.text(((W - tw_r) // 2, y_sep + 20), reference.upper(),
                  font=font_ref, fill=(80, 80, 80))

    # Handle
    bb_h = draw.textbbox((0, 0), HANDLE, font=font_handle)
    tw_h = bb_h[2] - bb_h[0]
    draw.text(((W - tw_h) // 2, H - 60), HANDLE,
              font=font_handle, fill=(50, 50, 50))

    # Linha decorativa fundo
    draw.rectangle([W - 200, H - 92, W - 80, H - 89], fill=(255, 255, 255, 20))
    draw.rectangle([W - 100, H - 92, W - 80, H - 89], fill=(60, 60, 60))

    return img

# ── ROUTES ─────────────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "pensarfinanceiro"})

@app.route('/generate-image-url', methods=['POST'])
def generate_image_url():
    data = request.get_json(force=True)
    if not data or 'phrase' not in data:
        return jsonify({"error": "Campo 'phrase' obrigatorio"}), 400

    phrase    = data.get('phrase', '').strip()
    reference = data.get('reference', '').strip()

    if not phrase:
        return jsonify({"error": "Frase nao pode ser vazia"}), 400

    try:
        frame    = create_frame(phrase, reference)
        img_id   = str(uuid.uuid4())
        out_path = os.path.join(OUTPUT_DIR, f"{img_id}.png")
        frame.save(out_path, 'PNG')

        base = request.host_url.rstrip('/').replace('http://', 'https://')
        return jsonify({
            "success":   True,
            "image_url": f"{base}/image/{img_id}",
            "image_id":  img_id,
            "phrase":    phrase
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/image/<image_id>', methods=['GET'])
def get_image(image_id):
    try:
        uuid.UUID(image_id)
    except:
        return jsonify({"error": "Invalid ID"}), 400
    path = os.path.join(OUTPUT_DIR, f"{image_id}.png")
    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404
    return send_file(path, mimetype='image/png')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
