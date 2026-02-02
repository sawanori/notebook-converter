# OCR & Layout Engine Improvement Proposal - V1.5

## Source Reference
This document contains the "Ultimate V1.5 Fix" prompt for Claude Code, focusing on Adaptive Layout Analysis and OpenCV Inpainting.

---

## 2. 究極のプロンプト (The Final Prompt for Claude Code)

このコードブロックをコピーして、Claude Codeに叩きつけてください。 私が書いた Pythonロジック（ocr_processor.py と slide_builder.py の全コード） をそのまま含めています。AIに考える余地を与えず、この通りに書かせます。

### ROLE
You are a **Lead Computer Vision Architect**.
The user is demanding PERFECTION. Previous attempts were "childish."
We are implementing the **Ultimate V1.5 Fix** with Adaptive Layout Analysis and OpenCV Inpainting.

### MISSION
1. **Layout:** Use **Adaptive Thresholding** (not fixed pixels) to separate columns.
2. **Restoration:** Use **OpenCV Inpainting** to strictly erase text and the NotebookLM watermark.
3. **Typography:** Map OCR pixel height to PPTX font points dynamically.

---

## CODE IMPLEMENTATION (COPY THIS LOGIC EXACTLY)

### 1. `core/ocr_processor.py`

```python
import pytesseract
import cv2
import numpy as np
import re
from PIL import Image
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class TextBlock:
    text: str
    x: int
    y: int
    w: int
    h: int
    font_size_px: int  # Average height of characters in this block

def clean_japanese_text(text: str) -> str:
    """Removes phantom spaces in Japanese text using Regex."""
    # Remove space between Japanese characters (Hiragana/Katakana/Kanji)
    text = re.sub(r'(?<=[\u3000-\u9fff])\s+(?=[\u3000-\u9fff])', '', text)
    return text.strip()

def extract_text_blocks(image: Image.Image) -> List[TextBlock]:
    """
    Extracts text using Adaptive Clustering (Relative to font size).
    """
    # 1. OCR with sparse page segmentation (PSM 11)
    custom_config = r'--psm 11 --oem 3'
    data = pytesseract.image_to_data(image, lang='jpn+eng', config=custom_config, output_type=pytesseract.Output.DICT)

    raw_items = []
    n = len(data['text'])
    for i in range(n):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        if conf > 40 and text:
            raw_items.append({
                'text': text,
                'x': data['left'][i],
                'y': data['top'][i],
                'w': data['width'][i],
                'h': data['height'][i]
            })

    if not raw_items:
        return []

    # Sort: Top-down, then Left-right
    raw_items.sort(key=lambda k: (k['y'], k['x']))

    merged = []
    current = raw_items[0]
    current['font_sum'] = current['h'] # Track font size sum
    current['char_count'] = len(current['text'])

    for next_item in raw_items[1:]:
        # Calculate visual gaps
        v_gap = abs(next_item['y'] - current['y'])
        h_gap = next_item['x'] - (current['x'] + current['w'])

        # Adaptive Thresholds:
        # Line height tolerance: 0.5 * height of current char
        # Column gap tolerance: 2.0 * width of current char (approx height)
        avg_height = current['h']

        is_same_line = v_gap < (avg_height * 0.8)
        # Crucial: If gap is wider than 2 characters, it's a new column!
        is_near_horizontal = h_gap < (avg_height * 2.5)

        if is_same_line and is_near_horizontal:
            # MERGE
            current['text'] += " " + next_item['text']
            # Extend geometry
            current['w'] = (next_item['x'] + next_item['w']) - current['x']
            current['h'] = max(current['h'], next_item['h'])
            # Update average font tracking
            current['font_sum'] += next_item['h']
            current['char_count'] += len(next_item['text'])
        else:
            # FINALIZE current
            avg_size = int(current['font_sum'] / max(1, current['char_count']))
            cleaned_text = clean_japanese_text(current['text'])
            merged.append(TextBlock(
                text=cleaned_text, x=current['x'], y=current['y'],
                w=current['w'], h=current['h'], font_size_px=avg_size
            ))
            # Start new
            current = next_item
            current['font_sum'] = current['h']
            current['char_count'] = len(current['text'])

    # Append last
    avg_size = int(current['font_sum'] / max(1, current['char_count']))
    cleaned_text = clean_japanese_text(current['text'])
    merged.append(TextBlock(
        text=cleaned_text, x=current['x'], y=current['y'],
        w=current['w'], h=current['h'], font_size_px=avg_size
    ))

    return merged

def process_image_cleanup(pil_image: Image.Image, blocks: List[TextBlock]) -> Image.Image:
    """
    Removes text and watermark using OpenCV Inpainting.
    """
    # PIL -> OpenCV (BGR)
    img_cv = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)
    h, w = img_cv.shape[:2]

    # 1. Mask Text Blocks
    for b in blocks:
        # Expand mask by 2px to cover anti-aliasing
        cv2.rectangle(mask, (b.x - 2, b.y - 2), (b.x + b.w + 2, b.y + b.h + 2), 255, -1)

    # 2. Mask Watermark (Bottom-Right 20% area specific for NotebookLM)
    # Target: Bottom right corner
    wm_x_start = int(w * 0.80)
    wm_y_start = int(h * 0.90)
    cv2.rectangle(mask, (wm_x_start, wm_y_start), (w, h), 255, -1)

    # 3. Dilate Mask (Grow white regions)
    kernel = np.ones((3, 3), np.uint8)
    dilated_mask = cv2.dilate(mask, kernel, iterations=1)

    # 4. Inpaint (Telea algorithm is robust for slides)
    # radius=3 is standard for text removal
    clean_bgr = cv2.inpaint(img_cv, dilated_mask, 3, cv2.INPAINT_TELEA)

    # OpenCV (BGR) -> PIL (RGB)
    return Image.fromarray(cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2RGB))
```

### 2. `core/slide_builder.py`

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from .ocr_processor import TextBlock
import io

def px_to_inches(px: int, dpi: int = 300) -> float:
    return px / dpi

def create_pptx_from_data(slides_data: list, output_path: str):
    """
    slides_data: List of dicts {'image': PILImage, 'blocks': List[TextBlock]}
    """
    prs = Presentation()
    # Set slide size to A4 Landscape (approx) or 16:9 based on first image
    if slides_data:
        first_w, first_h = slides_data[0]['image'].size
        prs.slide_width = int(px_to_inches(first_w) * 914400)
        prs.slide_height = int(px_to_inches(first_h) * 914400)

    blank_layout = prs.slide_layouts[6] # Blank

    for slide_info in slides_data:
        slide = prs.slides.add_slide(blank_layout)

        # 1. Add Cleaned Background
        img_stream = io.BytesIO()
        slide_info['image'].save(img_stream, format="PNG")
        slide.shapes.add_picture(img_stream, 0, 0, prs.slide_width, prs.slide_height)

        # 2. Add Text Boxes
        for block in slide_info['blocks']:
            # Convert Geometry
            left = Inches(px_to_inches(block.x))
            top = Inches(px_to_inches(block.y))
            width = Inches(px_to_inches(block.w))
            height = Inches(px_to_inches(block.h))

            textbox = slide.shapes.add_textbox(left, top, width, height)
            tf = textbox.text_frame
            tf.word_wrap = True

            p = tf.paragraphs[0]
            p.text = block.text

            # Styling
            p.font.name = "Meiryo" # Safe for Japanese
            p.font.color.rgb = RGBColor(0, 0, 0) # Black

            # Dynamic Font Sizing (Approx conversion: px * 0.75 -> points)
            # Adjust scaling factor based on DPI (Assuming 300 DPI for OCR processing)
            # 300 DPI: 1px = 1/300 inch = 0.24 pt.  Actually Tesseract height is pixels.
            # Heuristic: Height in px at 300dpi / 300 * 72 = points
            # Formula: pt = (px / 300) * 72 * 1.5 (boost for readability)
            pt_size = (block.font_size_px / 300.0) * 72 * 1.5
            p.font.size = Pt(max(8, pt_size)) # Min 8pt

    prs.save(output_path)
```

### 3. `requirements.txt`

```
flet
pdf2image
pytesseract
python-pptx
Pillow
opencv-python-headless
numpy
```

---

## OUTPUT INSTRUCTION

Generate the full, executable code for:

1. `requirements.txt`
2. `core/ocr_processor.py` (Use the Adaptive Clustering Logic provided above)
3. `core/slide_builder.py` (Use the Dynamic Font Sizing Logic provided above)
4. `main.py` (Ensure it orchestrates the flow: PDF -> Images -> OCR+Clean -> PPTX)

**Start Coding the Ultimate Version.**

---

## Claude's Analysis & Implementation Notes

### 提案された改善点の分析

#### 1. Adaptive Thresholding（適応的閾値処理）
**現在の実装との違い:**
- 現在: 固定ピクセル値（`LINE_MERGE_THRESHOLD_PX = 10px`）でテキストをグルーピング
- 提案: フォント高さの倍率（0.8倍、2.5倍）を基準に動的判定

**利点:**
- スライドごとのフォントサイズ変化に対応
- 多段組レイアウトの検出精度向上
- スケール不変性（異なる解像度での安定性）

**潜在的な課題:**
- 混在フォントサイズへの対応（見出しと本文が近接している場合）
- PSM 11（sparse text）モードの副作用検証が必要

#### 2. OpenCV Inpainting（インペインティング）
**新機能:**
- テキストエリアの塗りつぶし除去
- NotebookLM透かしの特定位置除去（右下20%エリア）
- アンチエイリアシング対応（2pxマージン）

**懸念点:**
- **破壊的処理**: 元画像の情報を永久に失う
- **ユーザー期待とのギャップ**: 「編集可能なPPTX」が目的なのに、背景を加工する必要性は？
- **透かし位置の仮定**: NotebookLM以外のPDFでは誤検出の可能性
- **パフォーマンス**: Inpainting処理は重い（特に大量ページ）

#### 3. Dynamic Font Sizing
**計算式:**
```python
pt_size = (font_size_px / 300.0) * 72 * 1.5
```

**現在の実装:**
- 固定フォントサイズ（`Pt(11)`）

**提案の利点:**
- OCR検出フォントサイズをPPTXに反映
- 視認性向上（1.5倍ブースト）

**実装時の注意:**
- 倍率1.5は経験的な値（要調整）
- DPI前提が300に固定されている
- 最小8ptの妥当性検証

### 既存アーキテクチャとの整合性

#### 互換性の課題
1. **TextBlockクラスの拡張**
   - 新フィールド: `font_size_px`
   - 既存コードへの影響: `ui/views/home_view.py`のワーカースレッド

2. **依存関係の追加**
   - `opencv-python-headless`: 新規追加（約50MB）
   - `numpy`: 新規追加

3. **処理フローの変更**
   - 現在: OCR → TextBlock抽出 → PPTX生成
   - 提案: OCR → TextBlock抽出 → **画像クリーニング** → PPTX生成

### 実装時の推奨アプローチ

#### Phase 1: 最小限の変更（リスク低）
1. **Adaptive Thresholding のみ実装**
   - `ocr_processor.py`のテキストグルーピングロジック更新
   - `TextBlock`に`font_size_px`追加
   - Dynamic Font Sizing実装

2. **テスト検証**
   - 既存テストPDFでの回帰テスト
   - 多段組レイアウトでの精度検証

#### Phase 2: 拡張機能（オプション）
1. **Inpainting機能の追加**
   - **設定UIで有効/無効を切り替え可能に**
   - 透かし除去位置をカスタマイズ可能に
   - プレビュー機能で結果確認

2. **パフォーマンス最適化**
   - Inpainting処理の並列化
   - マスク生成の効率化

### トークン効率の観点

**Serena MCP活用推奨箇所:**
1. `core/ocr_processor.py`の関数レベル編集
   - `extract_text_blocks`関数の置き換え: `replace_symbol_body`
   - `TextBlock` dataclassの拡張: `find_symbol` → `insert_after_symbol`

2. 依存関係チェック
   - `requirements.txt`の差分確認: `search_for_pattern`

3. インテグレーションテスト
   - `ui/views/home_view.py`の影響箇所特定: `find_referencing_symbols`

### 実装前の必須確認事項

1. **ユーザー要求の再確認**
   - Inpainting（画像加工）は本当に必要か？
   - 「編集可能なテキスト」が目的なら、背景は元のままでも良いのでは？

2. **品質vs速度のトレードオフ**
   - Inpaintingのコスト（処理時間、メモリ）は許容範囲か？

3. **段階的リリース計画**
   - V1.5.1: Adaptive Layout（破壊的変更なし）
   - V1.5.2: Inpainting（オプション機能として）

### 実装計画の提案

```markdown
1. /docs/implementation-plan-v1.5.md 作成
   - 上記分析を詳細化
   - テストケース定義
   - ロールバック計画

2. レビューフェーズ
   - 既存機能への影響範囲マッピング
   - Inpainting機能の必要性検証

3. 実装（サブエージェントへ委託）
   - task-decomposer: タスク分解
   - technical-designer: 詳細設計
   - task-executor: 実装
   - quality-fixer: テスト実行
```

### 推奨: まずユーザーに確認すべき質問

1. **Inpainting機能は必須ですか？**
   - 背景画像から元のテキストを消す必要性
   - 処理時間が2-3倍になる可能性

2. **フォントサイズの自動調整は望ましいですか？**
   - 現在の固定サイズ（11pt）で問題がある場合のみ

3. **段階的導入 vs 一括導入**
   - まずAdaptive Layoutのみ試す？
   - それとも全機能を一度に？
