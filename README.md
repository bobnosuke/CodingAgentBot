# 🤖 CoderAgent (仮称) - Discord AI Coding Bot

CoderAgent は、Discord 上で完結する AI コーディングエージェントです。
スマホや PC から自然言語で指示を出すだけで、AI がプロジェクトの構築、コードの生成、デバッグを行い、最終的な成果物を ZIP 形式で提供します。

---

## ✨ 主な機能

- **🚀 自然言語によるコード生成**: ユーザーの指示に基づいて AI がコードを生成・修正。
- **🎯 プライベート CodingRoom**: `/coding panel` から開発を開始し、ユーザー専用のプライベートチャンネルを自動生成。
- **🤖 マルチモデル対応**: OpenRouter 経由で最新モデル (Claude 3.5 Sonnet 等) を利用可能。
- **🔐 セキュア設計**: ユーザーの API キーは AES-256 で暗号化して保存。
- **📁 ファイル管理**: CodingRoom 内でファイル保存、一覧表示、ZIP ダウンロードに対応。
- **⚙️ 高度な設定**: `/setting` パネルからモデルプリセットの変更や利用状況の確認が可能。
- **🛡️ サーバー管理**: 管理者による利用カテゴリの指定や人数制限に対応 (`/config`)。
- **⚡ ハイブリッドコマンド**: スラッシュコマンド (`/`) とプレフィックスコマンド (`!`) の両方に対応。

---

## 🚀 クイックスタート

### 1. 前提条件
- Python 3.12 以上
- Discord Bot Token (Intents: Guilds, Messages, Members, Message Content)
- OpenRouter API Key

### 2. セットアップ
```bash
git clone https://github.com/bobnosuke/CodingAgentBot.git
cd CodingAgentBot
pip install -r requirements.txt
```

### 3. 環境設定
`.env.example` を `.env` にコピーし、必要事項を記入します。
```bash
DISCORD_TOKEN=your_token_here
ENCRYPTION_KEY=generated_key_here
DATABASE_URL=sqlite+aiosqlite:///./coderagent.db
```

### 4. 起動
```bash
python main.py
```
Docker を使用する場合:
```bash
docker-compose up -d
```

---

## 📜 コマンド概要

| コマンド | 説明 |
|:---|:---|
| `/coding panel` | 開発用 Embed パネルを表示し、開発を開始 |
| `/setting` | ユーザー設定・モデル変更・利用状況確認 |
| `/guide` | CoderAgent の使い方ガイドを表示 |
| `/config` | サーバー管理者用設定パネル |

**CodingRoom 内での AI 対話**: CodingRoom 内では、`!` で始まるコマンド以外のユーザー発言はすべて AI との会話と認識されます。

詳細なコマンドリストは [COMMANDS.md](./COMMANDS.md) を参照してください。

---

## 🏗️ プロジェクト構造

```
CoderAgent/
├── main.py                # Bot起動ポイント
├── cogs/                  # Discord コマンドハンドラー
├── modules/               # ビジネスロジック層 (AI, DB, Security, Session, File)
├── storage/               # ユーザーファイル保存先
├── logs/                  # ログファイル
└── tests/                 # テストコード
```

---

## 🤝 共同作業について
本プロジェクトは複数のエージェントによる共同作業で開発されています。
詳細は [HANDOVER.md](./HANDOVER.md) および [COMMUNICATION.md](./COMMUNICATION.md) を確認してください。

---

## 📄 ライセンス
MIT License

---
**Made with ❤️ by Rovaex Team**
