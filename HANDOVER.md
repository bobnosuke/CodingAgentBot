# 🤝 CoderAgent 開発プロジェクト引き継ぎ資料

## 1. プロジェクト概要

**プロジェクト名**: CoderAgent

**目的**: Discord上で利用可能なAIコード開発エージェントBotを提供し、CLIベースのClaude Codeのような開発体験をDiscord Bot形式へ移植する。PCを持たないスマートフォンユーザーでもAI開発ができる環境を提供することを目標とする。

**主要機能**: 自然言語によるコード生成・修正、ファイル作成・管理、プロジェクト構築、開発相談など。

**技術スタック**:

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.12 |
| Discord ライブラリ | discord.py 2.x |
| データベース | SQLite (async) |
| AI API | OpenRouter |
| 暗号化 | cryptography (Fernet) |
| ロギング | Python logging |

## 2. 現在の進捗状況

要件定義書に基づき、以下のフェーズが完了しています。

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | Bot基盤 | ✅ 完了 |
| Phase 2 | ユーザー管理・セキュリティ | ✅ 完了 |
| Phase 3 | Coding機能（CodingRoom） | ✅ 完了 |
| Phase 4 | ファイル管理 | ✅ 完了 |
| Phase 5 | スラッシュコマンド実装 | ✅ 完了 |
| Phase 6 | CodingRoom内AI対話 | ✅ 完了 |

### 実装済み主要機能

- **Discord Bot基盤**: `main.py`, `config.py`, `logger.py` による基本的なBotの起動、設定管理、ロギング。
- **ユーザー管理とセキュリティ**: SQLAlchemy を用いたデータベース (`users`, `api_keys`, `sessions` など) の構築。OpenRouter APIキーのAES-256暗号化保存。3層の権限管理システム (`User`, `Admin`, `Bot Owner`)。
- **AIコーディング機能**: `/coding start` でプライベートな「CodingRoom」を自動生成し、ユーザー、Bot、管理者のみがアクセス可能。`/coding chat` でCodingRoom内でのみAIとの対話が可能。OpenRouter APIを通じてAIモデルと連携。
- **ファイル管理**: `/save`, `/list`, `/get`, `/download` コマンドによるセッション内ファイルの保存、一覧表示、内容取得、ZIPダウンロード機能。これらのコマンドもCodingRoom内でのみ実行可能。
- **スラッシュコマンド**: すべてのユーザー向けコマンドはDiscordのスラッシュコマンド (`/`) として実装済み。
- **ドキュメント**: `README.md`, `SETUP_GUIDE.md`, `COMMANDS.md` を作成済み。

### 重要な注意事項

- **Discord Privileged Intents**: Botを起動する際は、Discord Developer Portalで `MESSAGE CONTENT INTENT` と `MEMBERS INTENT` を有効にする必要があります。有効にしないとBotが正常に動作しません。
- **ENCRYPTION_KEY**: 初回起動時に `.env` に `ENCRYPTION_KEY` が自動生成されます。このキーは安全に保管し、`.env` ファイルに設定してください。

## 3. 共同作業ワークフロー (GitHub-centric)

他エージェントとの共同作業は、GitHubリポジトリ `https://github.com/bobnosuke/CodingAgentBot` を中心に進めます。

### 3.1 作業開始前の手順

1.  **リポジトリのクローン**: 初回のみリポジトリをクローンします。
    ```bash
    git clone https://github.com/bobnosuke/CodingAgentBot.git
    cd CodingAgentBot
    ```
2.  **最新コードの取得**: 作業を開始する前に、必ず `main` ブランチの最新コードを `pull` します。
    ```bash
    git pull origin main
    ```
3.  **変更点の確認**: `git status` や `git diff` を使用して、前回の作業以降に変更があったファイルを確認します。特に `TODO_COLLAB.md` を確認し、他のエージェントが完了したタスクや新規追加されたタスクを把握します。
4.  **依存関係の更新**: `requirements.txt` に変更があった場合は、`pip install -r requirements.txt` を実行して依存パッケージを更新します。

### 3.2 作業中の手順

1.  **ブランチの作成**: 各タスクは新しいブランチで作業します。
    ```bash
    git checkout -b feature/your-task-name
    ```
2.  **実装**: コードを実装します。
3.  **コミット**: 変更内容をコミットします。コミットメッセージは `feat: 新機能の追加`、`fix: バグ修正`、`refactor: リファクタリング` など、変更の意図がわかるように記述します。
    ```bash
    git add .
    git commit -m "feat: [タスク内容の簡潔な説明]"
    ```
4.  **プッシュ**: 作業が完了したら、ブランチをリモートにプッシュします。
    ```bash
    git push origin feature/your-task-name
    ```
5.  **プルリクエスト**: `main` ブランチへのプルリクエストを作成します。プルリクエストのレビュー後、マージされます。

### 3.3 タスク管理

共同作業のタスクは `TODO_COLLAB.md` ファイルで管理します。このファイルには、各エージェントが担当するタスク、ステータス、コメントなどを記載します。作業を開始する前にこのファイルを確認し、自身の担当タスクを明確にしてください。

## 4. 今後の開発計画

以下のフェーズが残っています。

| フェーズ | 内容 | 担当 | ステータス |
|---------|------|------|------------|
| 1 | プロジェクトの要約と引き継ぎ資料（HANDOVER.md）の作成 | Manus AI | ✅ 完了 |
| 2 | GitHub同期と最新状態の確認（共同作業フローの確立） | Manus AI | 🚧 進行中 |
| 3 | `/setting` コマンドの実装（Embed + Select Menu + Modal） | 未定 | ⬜ 未着手 |
| 4 | `/coding` サブコマンドの拡充（panel, list, info, export, rename, delete） | 未定 | ⬜ 未着手 |
| 5 | 管理者・オーナー用コマンドの実装（`/config`, `/health`, `/stats`, `/shutdown`） | 未定 | ⬜ 未着手 |
| 6 | 共同作業用タスク管理ファイル（TODO_COLLAB.md）の作成と最終プッシュ | Manus AI | ⬜ 未着手 |

## 5. 連絡事項

- 不明点や疑問点があれば、GitHub Issues を活用してください。
- 重要な決定事項は、GitHub Issues またはプルリクエストのコメントで議論し、記録を残してください。

---

**Made with ❤️ by Manus AI**
