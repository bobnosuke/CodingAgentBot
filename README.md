# 🤖 CoderAgent - Discord AI Coding Bot

Discord上で完結するAIコーディングエージェント。Claude CodeのようなAI開発体験をDiscordに移植し、PCを持たないユーザーでもスマホからAI開発ができる環境を提供します。

## ✨ 主な機能

- **🚀 自然言語によるコード生成**: ユーザーの指示に基づいてAIがコードを生成
- **💬 インタラクティブなチャット**: AI とリアルタイムで対話
- **📁 ファイル管理**: セッション内でファイルを保存・管理・ダウンロード
- **🎯 プライベートコーディングルーム**: ユーザーごとに専用チャンネルを自動生成
- **🔐 セキュアなAPI キー管理**: OpenRouter APIキーをAES-256で安全に保存
- **⚡ スラッシュコマンド対応**: Discord の最新UI に対応

## 🎯 使用例

### Python 関数の作成
```
/coding start PythonProject
/coding chat Create a function that calculates fibonacci numbers
/save fibonacci.py <AI が生成したコード>
/download
/coding end
```

### Web スクレイパーの開発
```
/coding start WebScraper
/coding chat Create a web scraper for hacker news using beautifulsoup
/save scraper.py <AI が生成したコード>
/coding chat Add error handling to the scraper
/save scraper_v2.py <更新されたコード>
/list
/download
```

## 📋 コマンド一覧

### API キー管理
- `/api-key register <api_key>` - OpenRouter API キーを登録
- `/api-key remove` - API キーを削除

### コーディング
- `/coding start [project_name]` - 新しいコーディングセッションを開始
- `/coding chat <message>` - AI とチャット
- `/coding end` - セッションを終了

### ファイル管理
- `/save <filename> <content>` - ファイルを保存
- `/list` - セッション内のファイル一覧を表示
- `/get <filename>` - ファイルの内容を表示
- `/download` - すべてのファイルをZIPでダウンロード

### ヘルプ・情報
- `/guide [topic]` - ヘルプガイドを表示
- `/about` - CoderAgent についての情報
- `/status` - ボットのステータスを表示

詳細は [COMMANDS.md](COMMANDS.md) を参照してください。

## 🚀 クイックスタート

### 前提条件
- Python 3.12 以上
- Discord Bot Token
- OpenRouter API キー

### セットアップ

1. **リポジトリをクローン**
```bash
git clone https://github.com/bobnosuke/CodingAgentBot.git
cd CodingAgentBot
```

2. **環境変数ファイルを作成**
```bash
cp .env.example .env
```

3. **`.env` ファイルを編集**
```env
DISCORD_TOKEN=your_bot_token
OPENROUTER_API_KEY=your_api_key
```

4. **依存パッケージをインストール**
```bash
pip install -r requirements.txt
```

5. **Bot を起動**
```bash
python main.py
```

詳細なセットアップ手順は [SETUP_GUIDE.md](SETUP_GUIDE.md) を参照してください。

## 📊 技術スタック

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.12 |
| Discord ライブラリ | discord.py 2.x |
| データベース | SQLite (async) |
| AI API | OpenRouter |
| 暗号化 | cryptography (Fernet) |
| ロギング | Python logging |

## 🏗️ プロジェクト構造

```
CoderAgent/
├── main.py                      # Bot起動ポイント
├── config.py                    # 設定管理
├── logger.py                    # ロギング設定
├── requirements.txt             # 依存パッケージ
├── .env.example                 # 環境変数テンプレート
│
├── cogs/                        # Discord コマンドハンドラー
│   ├── api_key.py              # API キー管理コマンド
│   ├── coding.py               # コーディングコマンド
│   ├── file.py                 # ファイル管理コマンド
│   └── help.py                 # ヘルプコマンド
│
├── modules/                     # ビジネスロジック層
│   ├── ai/                     # AI・OpenRouter統合
│   │   └── openrouter.py
│   ├── database/               # データベース操作
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── security/               # セキュリティ機能
│   │   ├── encryption.py
│   │   └── permissions.py
│   ├── session/                # セッション管理
│   │   └── manager.py
│   └── file/                   # ファイル管理
│       └── manager.py
│
├── storage/                     # ユーザーファイル保存先
├── logs/                        # ログファイル
└── tests/                       # テストコード
```

## 🔐 セキュリティ機能

### APIキー暗号化
- Fernet（対称暗号化）を使用
- AES-256 相当のセキュリティ
- ログには出力されない

### 権限管理
- User / Admin / Bot Owner の3層構造
- コマンドごとの権限チェック

### プライベートコーディングルーム
- ユーザーのみがアクセス可能
- 他のユーザーからは隠蔽

## 📚 ドキュメント

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - 詳細なセットアップガイド
- [COMMANDS.md](COMMANDS.md) - コマンドリファレンス

## 📊 開発ロードマップ

### Phase 1: Bot基盤 ✅
- Discord Bot基盤
- Config管理
- Logging設定

### Phase 2: ユーザー管理とセキュリティ ✅
- データベース構築
- APIキー暗号化
- 権限管理システム

### Phase 3: Coding機能 ✅
- セッション管理
- CodingRoom生成
- AI通信

### Phase 4: ファイル管理 ✅
- ファイル保存
- ZIP化
- 添付

### Phase 5: スラッシュコマンド実装 ✅
- `/app_commands.command` 対応
- すべてのコマンドをスラッシュコマンド化

### Phase 6以降: 拡張機能 🚧
- Web管理画面
- 利用統計
- SaaS化
- プラグイン機能

## 🐛 トラブルシューティング

### Bot が応答しない
1. ログファイルを確認: `logs/coderagent.log`
2. API キーが登録されているか確認
3. Discord サーバーの権限を確認

### OpenRouter API エラー
1. API キーが有効か確認
2. 使用制限に達していないか確認
3. ネットワーク接続を確認

詳細は [SETUP_GUIDE.md](SETUP_GUIDE.md) のトラブルシューティングを参照してください。

## 📝 ライセンス

MIT License

## 👤 作成者

bobnosuke

## 📧 サポート

問題が発生した場合は、[GitHub Issues](https://github.com/bobnosuke/CodingAgentBot/issues) で報告してください。

---

**Made with ❤️ by CoderAgent Team**
