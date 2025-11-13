from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
from typing import Optional
import uuid
from dotenv import load_dotenv
import logging
import whisper
import google.generativeai as genai
import yt_dlp

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# Whisperモデルの初期化（最初の呼び出し時に自動でダウンロードされます）
# モデルサイズ: tiny, base, small, medium, large
# 推奨: base (精度と速度のバランスが良い) または small (より高精度)
whisper_models = {}  # モデルサイズごとにキャッシュ

# 利用可能なWhisperモデルサイズ
AVAILABLE_MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]

# Gemini APIの設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="AI補正付き文字起こしソフトウェア")

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルの設定
app.mount("/static", StaticFiles(directory="static"), name="static")

# アップロードディレクトリの作成
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 許可する音声ファイル形式
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """メインページを表示"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>静的ファイルが見つかりません</h1><p>static/index.htmlを作成してください。</p>",
            status_code=404
        )


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    keywords: Optional[str] = Form(None)
):
    """
    音声ファイルをアップロードして処理を開始
    
    Parameters:
    - file: 音声ファイル (mp3, wav, m4a, ogg, flac)
    - keywords: キーワード（カンマ区切り、任意）
    """
    try:
        # ファイル拡張子のチェック
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です。対応形式: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # 一意のファイル名を生成
        unique_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{unique_id}{file_ext}"
        
        # ファイルを保存
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"ファイルをアップロードしました: {file.filename} -> {file_path}")
        
        # キーワードの処理
        keyword_list = []
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        logger.info(f"キーワード: {keyword_list}")
        
        return JSONResponse(content={
            "status": "success",
            "message": "ファイルのアップロードが完了しました",
            "file_id": unique_id,
            "file_path": str(file_path),
            "keywords": keyword_list,
            "original_filename": file.filename
        })
        
    except Exception as e:
        logger.error(f"エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-youtube")
async def download_youtube(
    url: str = Form(...),
    keywords: Optional[str] = Form(None)
):
    """
    YouTubeのURLから音声をダウンロード
    
    Parameters:
    - url: YouTubeのURL
    - keywords: キーワード（カンマ区切り、任意）
    """
    try:
        logger.info(f"YouTube動画をダウンロード: {url}")
        
        # 一意のファイル名を生成
        unique_id = str(uuid.uuid4())
        output_path = UPLOAD_DIR / f"{unique_id}"
        
        # yt-dlpの設定
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(output_path),
            'quiet': True,
            'no_warnings': True,
        }
        
        # ダウンロード実行
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Unknown')
        
        # ダウンロードされたファイルのパスを確認
        final_path = UPLOAD_DIR / f"{unique_id}.mp3"
        
        if not final_path.exists():
            raise HTTPException(status_code=500, detail="音声ファイルのダウンロードに失敗しました")
        
        logger.info(f"ダウンロード完了: {video_title}")
        
        # キーワードの処理
        keyword_list = []
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        return JSONResponse(content={
            "status": "success",
            "message": f"YouTubeから音声をダウンロードしました: {video_title}",
            "file_id": unique_id,
            "file_path": str(final_path),
            "keywords": keyword_list,
            "original_filename": f"{video_title}.mp3",
            "video_title": video_title
        })
        
    except Exception as e:
        logger.error(f"YouTubeダウンロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"YouTubeからのダウンロードに失敗しました: {str(e)}")


@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "whisper_model": "local (base model)",
        "gemini_api_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


@app.post("/api/transcribe")
async def transcribe_audio(
    file_id: str = Form(...),
    model_size: str = Form("base")
):
    """
    音声ファイルを文字起こし（ローカルWhisperモデル使用）
    
    Parameters:
    - file_id: アップロード時に返されたファイルID
    - model_size: Whisperモデルサイズ (tiny, base, small, medium, large)
    """
    try:
        global whisper_models
        
        # モデルサイズのバリデーション
        if model_size not in AVAILABLE_MODEL_SIZES:
            raise HTTPException(
                status_code=400,
                detail=f"無効なモデルサイズです。利用可能: {', '.join(AVAILABLE_MODEL_SIZES)}"
            )
        
        # ファイルを探す
        file_path = None
        for ext in ALLOWED_EXTENSIONS:
            potential_path = UPLOAD_DIR / f"{file_id}{ext}"
            if potential_path.exists():
                file_path = potential_path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")
        
        logger.info(f"音声認識を開始: {file_path}, モデル: {model_size}")
        
        # Whisperモデルの初期化（該当サイズが初回の場合のみ）
        if model_size not in whisper_models:
            logger.info(f"Whisperモデル({model_size})を読み込み中... (初回は数分かかる場合があります)")
            whisper_models[model_size] = whisper.load_model(model_size)
            logger.info(f"Whisperモデル({model_size})の読み込み完了")
        
        # ローカルWhisperで音声認識
        result = whisper_models[model_size].transcribe(
            str(file_path),
            language="ja",  # 日本語指定
            verbose=False
        )
        
        raw_text = result["text"]
        logger.info(f"音声認識完了。文字数: {len(raw_text)}")
        
        return JSONResponse(content={
            "status": "success",
            "raw_text": raw_text
        })
        
    except Exception as e:
        logger.error(f"音声認識エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"音声認識に失敗しました: {str(e)}")


@app.post("/api/correct")
async def correct_text(
    raw_text: str = Form(...),
    keywords: Optional[str] = Form(None)
):
    """
    テキストをAIで補正
    
    Parameters:
    - raw_text: 生の文字起こしテキスト
    - keywords: キーワード（カンマ区切り、任意）
    """
    try:
        logger.info(f"AI補正を開始。キーワード: {keywords}")
        logger.info(f"生テキストの長さ: {len(raw_text)} 文字")
        
        # キーワードの処理
        keyword_list = []
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
        
        # Gemini APIで補正
        try:
            # Gemini 2.5 Flashモデルを使用（高速で高性能）
            model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            logger.error(f"Geminiモデル初期化エラー: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Gemini APIの初期化に失敗しました: {str(e)}")
        
        # 長いテキストの場合は分割処理
        MAX_CHUNK_SIZE = 3000  # 1チャンクあたりの最大文字数（タイムアウト対策でさらに小さく）
        
        if len(raw_text) > MAX_CHUNK_SIZE:
            logger.info(f"長いテキストを分割処理します（{len(raw_text)}文字）")
            corrected_chunks = []
            
            # テキストを適切なサイズに分割（シンプルな方法）
            chunks = []
            start = 0
            
            while start < len(raw_text):
                end = start + MAX_CHUNK_SIZE
                
                # 文の途中で切らないように、句点を探す
                if end < len(raw_text):
                    # 次の句点を探す（最大500文字先まで）
                    search_end = min(end + 500, len(raw_text))
                    chunk_text = raw_text[start:search_end]
                    
                    # 句点の位置を探す
                    last_period = chunk_text.rfind('。')
                    if last_period > MAX_CHUNK_SIZE // 2:  # 半分以上の位置にあれば採用
                        end = start + last_period + 1
                    # 句点がなければ、改行や空白で区切る
                    elif '\n' in raw_text[start:end]:
                        last_newline = raw_text[start:end].rfind('\n')
                        if last_newline > MAX_CHUNK_SIZE // 2:
                            end = start + last_newline + 1
                
                chunk = raw_text[start:end]
                if chunk.strip():  # 空でないチャンクのみ追加
                    chunks.append(chunk)
                start = end
            
            logger.info(f"テキストを{len(chunks)}個のチャンクに分割しました")
            
            # 各チャンクを処理
            for i, chunk in enumerate(chunks):
                logger.info(f"チャンク {i+1}/{len(chunks)} を処理中... (長さ: {len(chunk)}文字)")
                
                # より簡潔なプロンプト（処理時間短縮のため）
                prompt = f"""以下のテキストからフィラーや言い間違いを削除し、自然な文章に修正してください。
重要: 元のテキストと同じ言語で出力してください（日本語は日本語に、英語は英語に）。翻訳しないでください。

元のテキスト:
{chunk}

修正後:"""
                
                # リトライロジック
                max_retries = 2
                retry_count = 0
                success = False
                
                while retry_count < max_retries and not success:
                    try:
                        response = model.generate_content(prompt)
                        if response and response.text:
                            corrected_chunks.append(response.text)
                            logger.info(f"チャンク {i+1} の補正完了: {len(response.text)}文字")
                            success = True
                        else:
                            logger.warning(f"チャンク {i+1} のレスポンスが空です")
                            corrected_chunks.append(chunk)
                            success = True
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"チャンク {i+1} の処理でエラー (試行 {retry_count}/{max_retries}): {str(e)}")
                        
                        if retry_count >= max_retries:
                            logger.warning(f"チャンク {i+1} のリトライ回数上限に達しました。元のテキストを使用します。")
                            corrected_chunks.append(chunk)
                        else:
                            logger.info(f"5秒後にリトライします...")
                            import time
                            time.sleep(5)
            
            corrected_text = "\n\n".join(corrected_chunks)
            logger.info(f"全チャンクの処理完了")
        else:
            # 短いテキストは通常処理
            prompt = f"""役割: あなたは、書き起こしテキストを編集するプロフェッショナルです。

目的: 以下の「生の書き起こしテキスト」から、フィラー（「えー」「あのー」「um」「uh」など）、明らかな言い間違い、重複表現を削除し、不自然な文法や口語表現を修正して、読みやすく自然な文章に清書してください。

重要: 元のテキストと同じ言語で出力してください。日本語のテキストは日本語に、英語のテキストは英語に修正してください。言語を変換したり翻訳したりしないでください。

"""
            
            if keyword_list:
                prompt += f"""コンテキスト（文脈）: この会話のトピックは、以下の「キーワード」に関連しています。専門用語や固有名詞は、これらのキーワードを参考に、文脈に沿った適切な漢字や表現に修正してください。

【キーワード】: {', '.join(keyword_list)}

"""
            
            prompt += f"""【生の書き起こしテキスト】:
{raw_text}

【清書後のテキスト】:
"""
            
            logger.info("Gemini APIにリクエストを送信中...")
            try:
                response = model.generate_content(prompt)
                if response and response.text:
                    corrected_text = response.text
                    logger.info(f"Gemini APIレスポンス取得成功: {len(corrected_text)}文字")
                else:
                    logger.warning("Gemini APIのレスポンスが空です")
                    corrected_text = raw_text
            except Exception as e:
                logger.error(f"Gemini API呼び出しエラー: {str(e)}")
                logger.error(f"エラーの詳細: {type(e).__name__}")
                
                # より詳細なエラーメッセージ
                if "API key" in str(e):
                    raise HTTPException(status_code=500, detail="Gemini APIキーが無効または未設定です。.envファイルを確認してください。")
                elif "quota" in str(e).lower():
                    raise HTTPException(status_code=500, detail="APIの使用量制限に達しました。しばらく待ってから再試行してください。")
                elif "timeout" in str(e).lower() or "deadline" in str(e).lower():
                    raise HTTPException(status_code=500, detail="処理がタイムアウトしました。テキストが長すぎる可能性があります。")
                else:
                    raise HTTPException(status_code=500, detail=f"Gemini APIの呼び出しに失敗しました: {str(e)}")
        
        logger.info(f"AI補正完了。文字数: {len(corrected_text)}")
        
        return JSONResponse(content={
            "status": "success",
            "corrected_text": corrected_text
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI補正エラー: {str(e)}")
        logger.error(f"エラータイプ: {type(e).__name__}")
        import traceback
        logger.error(f"トレースバック: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"AI補正に失敗しました: {str(e)}")


@app.delete("/api/cleanup/{file_id}")
async def cleanup_file(file_id: str):
    """
    アップロードされたファイルを削除
    
    Parameters:
    - file_id: 削除するファイルのID
    """
    try:
        deleted = False
        for ext in ALLOWED_EXTENSIONS:
            file_path = UPLOAD_DIR / f"{file_id}{ext}"
            if file_path.exists():
                file_path.unlink()
                deleted = True
                logger.info(f"ファイルを削除しました: {file_path}")
                break
        
        if not deleted:
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")
        
        return JSONResponse(content={
            "status": "success",
            "message": "ファイルを削除しました"
        })
        
    except Exception as e:
        logger.error(f"ファイル削除エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("🚀 サーバーを起動しています...")
    print("📝 ブラウザで http://localhost:8000 にアクセスしてください")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
