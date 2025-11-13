## 機能

1. **音声ファイルのアップロード** - MP3、WAV、M4A形式に対応
2. **YouTubeからの音声取得** - YouTube動画から直接音声を取得
3. **音声認識** - ローカルWhisperモデルによる高精度な日本語文字起こし（APIキー不要）
4. **モデルサイズ選択** - 5段階のモデルサイズから用途に応じて選択可能
5. **AI文章補正** - Google Gemini APIによる自然な文章への清書
6. **キーワード指定** - 専門用語や固有名詞の精度向上のための文脈ヒント
7. **テキストダウンロード** - 補正後のテキストをダウンロード

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

1. `.env.example` をコピーして `.env` ファイルを作成:
   ```bash
   cp .env.example .env
   ```

2. `.env` ファイルを編集し、Gemini APIキーを設定:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```
### 3. サーバーの起動

```bash
python main.py
```

**注意**: 初回起動時、Whisperモデル（約150MB）が自動ダウンロードされます。

### 4. アプリケーションの使用

ブラウザで `http://localhost:8000` にアクセス

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **音声認識**: OpenAI Whisper (ローカル実行)
- **AI補正**: Google Gemini API
- **動画処理**: yt-dlp
- **フロントエンド**: HTML/CSS/JavaScript

