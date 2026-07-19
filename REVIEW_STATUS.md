# コードレビュー進捗管理

## 修正済み（削除対象）
- `main.py`: `intents.members` の設定（最新コードで `True` に設定済み）。
- `modules/utils/i18n.py`: `locales_dir` のパス（最新コードで修正済み）。
- `modules/ai/openrouter.py`: `import json` の位置（最新コードで修正済み）。
- `cogs/file.py`: `!download` のZIP送信ロジック（最新コードで `_send_zip` が実装済み）。
- `modules/project/manager.py`: モジュールの存在（新規作成済み）。

## 未対応（継続指摘対象）
- `/coding panel`: 「プロジェクト一覧」「プロジェクト詳細」「プロジェクト名変更」の詳細機能（依然として `Coming Soon`）。
- `cogs/file.py`: `!list`, `!get`, `!readme` コマンドの実装（依然として不在）。
- セッションの自動キャッシュ削除（依然として未実装）。
- `APIKeyModal`: APIキーの更新ロジック（常に新規作成の可能性）。
- `logger.py`: モジュールレベルのロガー初期化の削除。
- 各モジュールでの `i18n` による多言語対応（ログメッセージやシステムプロンプトなど）。
- データベースの PostgreSQL への移行（依然として `aiosqlite`）。

## 新規確認事項
- `modules/project/manager.py` の詳細レビュー。
- `locales/*.json` の翻訳カバレッジ。
