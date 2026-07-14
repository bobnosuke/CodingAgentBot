# CoderAgent - Discord AI Coding Bot

Discord上で完結するAIコーディングエージェント。Claude CodeのようなAI開発体験をDiscordに移植し、PCを持たないユーザーでもスマホからAI開発ができる環境を提供します。

## 🚀 機能

- **自然言語によるコード生成**: ユーザーの指示に基づいてAIがコードを生成
- **プライベートコーディングルーム**: ユーザーごとに専用チャンネルを自動生成
- **セッション管理**: 複数のコーディングセッションを並行管理
- **APIキー暗号化**: OpenRouter APIキーをAES-256で安全に保存
- **権限管理**: User/Admin/BotOwnerの3層権限システム

## 📋 技術スタック

- **言語**: Python 3.12
- **Discord**: discord.py 2.3.2
- **AI API**: OpenRouter
- **データベース**: SQLAlchemy + aiosqlite
- **暗号化**: cryptography (Fernet)

## 🔧 セットアップ

### 1. 環境構築

```bash
# リポジトリをクローン
git clone https://github.com/bobnosuke/CodingAgentBot.git
cd CodingAgentBot

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env` ファイルを作成し、以下の情報を設定：

```env
# Discord Bot Token
DISCORD_TOKEN=your_bot_token_here

# OpenRouter API Key
OPENROUTER_API_KEY=your_openrouter_key_here

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./coderagent.db

# Encryption Key (32 bytes base64 encoded)
ENCRYPTION_KEY=your_encryption_key_here

# Bot Configuration
BOT_PREFIX=!
BOT_OWNER_ID=your_discord_user_id

# Logging Configuration
LOG_LEVEL=INFO
```

### 3. Bot起動

```bash
python main.py
```

## 📖 使用方法

### APIキー登録

```
/api-key register <your_openrouter_api_key>
```

### コーディングセッション開始

```
/coding start [project_name]
```

### AI対話

```
/coding chat <your_message>
```

### セッション終了

```
/coding end
```

## 📁 プロジェクト構成

```
CoderAgent/
├── main.py                 # Bot起動ポイント
├── config.py              # 設定管理
├── logger.py              # ロギング設定
├── requirements.txt       # 依存パッケージ
├── .env.example           # 環境変数テンプレート
├── cogs/                  # Discordコマンドハンドラー
│   ├── coding.py         # Codingコマンド
│   └── api_key.py        # APIキー管理コマンド
├── modules/               # ビジネスロジック
│   ├── ai/               # AI・OpenRouter統合
│   ├── database/         # DB操作・モデル
│   ├── security/         # 暗号化・権限管理
│   ├── session/          # セッション管理
│   └── file/             # ファイル管理
├── storage/              # ユーザーファイル保存先
├── logs/                 # ログファイル
└── tests/                # テストコード
```

## 🔐 セキュリティ

- **APIキー暗号化**: ユーザーのOpenRouter APIキーはAES-256で暗号化して保存
- **権限管理**: Discord管理者権限との連携による厳密な権限制御
- **ログ管理**: 機密情報（APIキーなど）はログに出力されない設計

## 📊 開発ロードマップ

### Phase 1: Bot基盤 ✅
- Discord Bot基盤
- Config管理
- Logging設定

### Phase 2: ユーザー管理とセキュリティ ✅
- データベース構築
- APIキー暗号化
- 権限管理システム

### Phase 3: Coding機能 🚧
- セッション管理
- CodingRoom生成
- AI通信

### Phase 4: ファイル管理 ⏳
- ファイル保存
- ZIP化
- 添付

### Phase 5以降: 拡張機能 ⏳
- Web管理画面
- 利用統計
- SaaS化
- プラグイン機能

## 📝 ライセンス

MIT License

## 👤 作成者

bobnosuke

## 📧 サポート

問題が発生した場合は、GitHubのIssueセクションで報告してください。
