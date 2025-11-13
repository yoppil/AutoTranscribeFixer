# AI補正付き 文字起こしソフトウェア

音声ファイル（MP3など）をテキストに文字起こしし、AIによる自然な文章補正機能を提供するソフトウェアです。

## 機能

1. **音声ファイルのアップロード** - MP3、WAV、M4A形式に対応
2. **音声認識** - ローカルWhisperモデルによる高精度な日本語文字起こし（APIキー不要）
3. **AI文章補正** - Google Gemini APIによる自然な文章への清書
4. **キーワード指定** - 専門用語や固有名詞の精度向上のための文脈ヒント
5. **テキストダウンロード** - 補正後のテキストをダウンロード

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

**注意**: 初回インストール時、Whisperモデルとその依存関係（PyTorch等）がダウンロードされるため、数分～10分程度かかる場合があります。

### 2. 環境変数の設定

1. `.env.example` をコピーして `.env` ファイルを作成:
   ```bash
   cp .env.example .env
   ```

2. `.env` ファイルを編集し、Gemini APIキーを設定:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. Gemini APIキーの取得方法:
   - [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
   - Googleアカウントでログイン
   - "Create API Key" をクリックして新しいAPIキーを作成
   - 生成されたAPIキーをコピーして `.env` に貼り付け

### 3. サーバーの起動

```bash
python main.py
```

**注意**: 初回起動時、Whisperモデル（約150MB）が自動ダウンロードされます。

### 4. アプリケーションの使用

ブラウザで `http://localhost:8000` にアクセス

## 使い方

1. 音声ファイルをアップロード
2. （任意）キーワードを入力
3. 「文字起こし開始」ボタンをクリック
4. 結果を確認してダウンロード

## 技術スタック

- **バックエンド**: FastAPI (Python)
- **音声認識**: OpenAI Whisper (ローカル実行)
- **AI補正**: Google Gemini API
- **フロントエンド**: HTML/CSS/JavaScript

## モデルサイズについて

デフォルトでは`base`モデル（精度と速度のバランス）を使用しています。
`main.py`の該当箇所を編集することで変更可能です：

- `tiny`: 最速、低精度
- `base`: バランス型（デフォルト）
- `small`: 高精度、やや遅い
- `medium`: より高精度、遅い
- `large`: 最高精度、最も遅い

## セキュリティに関する注意

⚠️ **重要**: 以下のファイルは `.gitignore` で除外されており、GitHubにプッシュされません：

- `.env` ファイル（APIキーを含む）
- `uploads/` ディレクトリ（アップロードされた音声ファイル）
- `.venv/` ディレクトリ（Python仮想環境）
- `test_*.py` ファイル（テストファイル）

GitHubにプッシュする前に、必ず以下を確認してください：

```bash
# 除外されているか確認
git check-ignore -v .env

# 追加予定のファイルを確認
git status
```

## ライセンス

このプロジェクトはオープンソースです。
