# CoderAgent セットアップガイド

Discord AI Coding Botの詳細なセットアップ手順を説明します。

## 📋 前提条件

- Python 3.12 以上
- pip（Pythonパッケージマネージャー）
- Discord Developer Portal でのBot作成権限
- OpenRouter アカウント

## 🔧 ステップ1: Discord Bot の作成

### 1.1 Discord Developer Portal にアクセス

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. Discordアカウントでログイン

### 1.2 新しいアプリケーションを作成

1. 「New Application」をクリック
2. アプリケーション名を入力（例：CoderAgent）
3. 「Create」をクリック

### 1.3 Bot を作成

1. 左側メニューから「Bot」を選択
2. 「Add Bot」をクリック
3. Bot名を設定（オプション）

### 1.4 Token を取得

1. 「TOKEN」セクションで「Copy」をクリック
2. トークンをコピー（**絶対に他人と共有しないでください**）

### 1.5 Privileged Intents を有効化

1. 「Privileged Gateway Intents」セクションまでスクロール
2. 以下を有効化：
   - ✅ Message Content Intent
   - ✅ Server Members Intent
   - ✅ Guilds

### 1.6 OAuth2 スコープを設定

1. 左側メニューから「OAuth2」→「URL Generator」を選択
2. **Scopes** で以下を選択：
   - ✅ bot
3. **Permissions** で以下を選択：
   - ✅ Send Messages
   - ✅ Read Messages/View Channels
   - ✅ Manage Messages
   - ✅ Manage Channels
   - ✅ Create Instant Invite
   - ✅ Read Message History
   - ✅ Attach Files

4. 生成されたURLをコピー

### 1.7 Bot をサーバーに招待

1. 生成されたURLをブラウザで開く
2. Botを招待するサーバーを選択
3. 「Authorize」をクリック

## 🔑 ステップ2: OpenRouter API キーの取得

### 2.1 OpenRouter にアクセス

1. [OpenRouter](https://openrouter.ai/) にアクセス
2. 「Sign Up」でアカウント作成またはログイン

### 2.2 API キーを生成

1. ダッシュボードから「API Keys」を選択
2. 「Create New Key」をクリック
3. キー名を入力（例：CoderAgent）
4. キーをコピー

## 📦 ステップ3: プロジェクトのセットアップ

### 3.1 リポジトリをクローン

```bash
git clone https://github.com/bobnosuke/CodingAgentBot.git
cd CodingAgentBot
```

### 3.2 環境変数ファイルを作成

```bash
cp .env.example .env
```

### 3.3 .env ファイルを編集

`.env` ファイルを開き、以下を設定：

```env
# Discord Bot Token（ステップ1.4で取得）
DISCORD_TOKEN=your_discord_bot_token_here

# OpenRouter API Key（ステップ2.2で取得）
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./coderagent.db

# Encryption Key（初回実行時に自動生成）
ENCRYPTION_KEY=

# Bot Configuration
BOT_PREFIX=!
BOT_OWNER_ID=your_discord_user_id

# Logging Configuration
LOG_LEVEL=INFO
```

### 3.4 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

## 🚀 ステップ4: Bot を起動

### 4.1 Bot を起動

```bash
python main.py
```

### 4.2 起動確認

以下のログが表示されれば成功です：

```
✅ Configuration validated successfully
✅ Database initialized
✅ Encryption manager initialized
✅ Loaded cog: coding
✅ Loaded cog: api_key
✅ Loaded cog: file
✅ Loaded cog: help
```

## 📖 初期セットアップ（Discord）

Bot が起動したら、Discord サーバーで以下を実行：

### 1. API キーを登録

```
!api-key register <your_openrouter_api_key>
```

### 2. コーディングセッションを開始

```
!coding start MyProject
```

### 3. AI とチャット

```
!coding chat Create a Python function that calculates fibonacci numbers
```

### 4. ファイルをダウンロード

```
!download
```

## 🔒 セキュリティ設定

### 暗号化キーの保存

初回起動時に暗号化キーが自動生成されます。本番環境では以下を実行：

1. ログから暗号化キーをコピー
2. `.env` ファイルの `ENCRYPTION_KEY` に設定
3. Bot を再起動

### API キーの安全性

- API キーは絶対に他人と共有しないでください
- `.env` ファイルを Git にコミットしないでください
- `.gitignore` に `.env` が含まれていることを確認してください

## 🐛 トラブルシューティング

### エラー: "Privileged Intents Required"

**原因**: Discord Developer Portal で Privileged Intents が有効になっていない

**解決方法**:
1. Discord Developer Portal にアクセス
2. アプリケーションを選択
3. 「Bot」セクションで Privileged Intents を有効化

### エラー: "Repository not found"

**原因**: Discord Bot Token が無効

**解決方法**:
1. Discord Developer Portal で Token を再生成
2. `.env` ファイルを更新
3. Bot を再起動

### エラー: "OpenRouter API error"

**原因**: OpenRouter API キーが無効または期限切れ

**解決方法**:
1. OpenRouter にログイン
2. API キーを確認
3. 必要に応じて新しいキーを生成
4. `!api-key register` で新しいキーを登録

### Bot が応答しない

**原因**: 複数の可能性がある

**デバッグ手順**:
1. ログを確認: `logs/coderagent.log`
2. Bot が起動しているか確認
3. API キーが登録されているか確認
4. Discord サーバーの権限を確認

## 📝 ログファイル

ログは `logs/coderagent.log` に保存されます。

ログレベルを変更するには `.env` で設定：

```env
LOG_LEVEL=DEBUG  # より詳細なログ
LOG_LEVEL=INFO   # 標準ログ
LOG_LEVEL=WARNING # 警告以上のみ
```

## 🆘 サポート

問題が解決しない場合：

1. ログファイルを確認
2. [GitHub Issues](https://github.com/bobnosuke/CodingAgentBot/issues) で報告
3. エラーメッセージ全文を含める

## ✅ セットアップ完了

すべての手順が完了しました！

Bot を使用する準備ができました。詳細なコマンドリファレンスは `COMMANDS.md` を参照してください。
