# メッセージ編集への切り替え修正プラン

## 1. 目的
Discordのインタラクション（ボタン押下やセレクトメニュー選択）において、新規メッセージを送信（`followup.send` 等）するのではなく、既存のメッセージを編集（`edit_message` 等）することで、チャット画面の煩雑さを解消し、UXを向上させる。

## 2. 修正方針
- **View内のコールバック**: `interaction.response.send_message` や `interaction.followup.send` を `interaction.response.edit_message` に変更する。
- **defer済みの処理**: `interaction.followup.send` を `interaction.edit_original_response` に変更する。
- **例外（新規送信を維持するケース）**:
    - モーダル送信 (`send_modal`)：仕様上、編集ではなく新規応答として扱う必要がある。
    - 権限エラーや致命的なシステムエラー：ユーザーに確実に通知するため、新規（ephemeral）メッセージとして送信することを検討する。
    - 異なるユーザーによる操作：実行者本人以外が操作した際の警告メッセージ。

## 3. 修正対象箇所（主要なファイル）

### A. `cogs/setting.py` (最優先)
設定メニューは複数の階層（メインメニュー -> モデル選択 -> 完了通知）があるため、最も効果が高い。
- `SettingView.select_callback`: `show_model_selection` 等の呼び出し先での挙動を修正。
- `show_model_selection`: `interaction.response.send_message` -> `edit_message`。
- `show_status`: `interaction.followup.send` -> `edit_original_response`。
- `ModelSelectionView.update_model`: 完了通知を `edit_original_response` で元のパネルを更新。
- `DeleteConfirmView`: 削除確認と完了通知を編集で対応。

### B. `cogs/coding.py`
- `CodingPanelView.panel_select`: 各アクション（`_handle_start` 等）内での応答を修正。
- `_handle_start`: セッション開始成功時のメッセージを、パネルの更新ではなく新規送信にするか検討が必要（コーディングルームへの誘導のため）。

### C. `cogs/file.py`
- `FileSelectView.select_callback`: ファイル選択後のZIP送信。
- `ConfirmView.confirm_button` (`!close`時): 終了通知。

## 4. 実装の注意点
- **`ephemeral` の整合性**: `edit_message` は元のメッセージの `ephemeral` 属性を継承する。
- **`defer` の有無**: 
    - `interaction.response.defer()` を呼んだ後は `interaction.response.edit_message()` は使えず、`interaction.edit_original_response()` を使う必要がある。
- **エラーハンドリング**: 編集に失敗した場合（メッセージが削除されている等）のフォールバック処理を考慮する。

## 5. 作業ステップ
1. **共通ユーティリティの検討**: メッセージを「送信または編集」するヘルパーメソッドを `SettingCog` 等に導入し、コードの重複を避ける。
2. **`cogs/setting.py` の修正とテスト**: 影響が最も分かりやすい設定画面から着手。
3. **その他のCogの修正**: `coding.py`, `file.py` を順次修正。
4. **全体確認**: 全てのインタラクションが期待通り「編集」で完結するか確認。
