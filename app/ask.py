"""temperatureを3条件に変え、各条件で同じ質問を3回実行する。

実行方法:
    uv run python -m app.ask

結果はresultsフォルダの1つのMarkdownファイルに保存する。
"""

from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key


# 比較するtemperatureと、各条件の実行回数
TEMPERATURES = [0.1, 0.3, 0.6]
REPEAT_COUNT = 3

# すべての実行で、同じ質問文を使う
QUESTION = """任天堂の『ゼルダの伝説　ブレス オブ ザ ワイルド』を
遊んだことがない人に向けて、紹介文を200字以内で作成してください。

「広い世界を自由に探索する楽しさ」を中心に、
遊んでいる場面を想像できるような表現を使ってください。
物語の核心に触れるネタバレは避けてください。"""


def main() -> None:
    # 登録済みのAPIキーでGeminiに接続する
    client = genai.Client(api_key=get_api_key())

    # リポジトリ内に結果の保存先を作る
    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 日時を付けて、過去の結果を上書きしないようにする
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = output_dir / f"zelda_comparison_{timestamp}.md"

    header = (
        "# temperatureによる紹介文の比較\n\n"
        f"- モデル: {MODEL}\n"
        f"- temperature: {TEMPERATURES}\n"
        f"- 各条件の実行回数: {REPEAT_COUNT}回\n"
        "- 会話履歴: なし\n\n"
        f"## 質問文\n\n{QUESTION}\n\n"
    )
    output_path.write_text(header, encoding="utf-8")
    print(header)

    # temperatureを順番に切り替える
    for temperature in TEMPERATURES:
        # 各temperatureで3回ずつ実行する
        for trial in range(1, REPEAT_COUNT + 1):
            title = f"temperature={temperature}／{trial}回目"
            print(f"--- {title} ---")

            try:
                # 毎回、会話履歴なしで同じ質問を送る
                response = client.models.generate_content(
                    model=MODEL,
                    contents=QUESTION,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                    ),
                )
            except errors.APIError as e:
                # エラーが出たら記録して停止する
                # それ以前の回答はファイルに残る
                message = api_error_message(e.code, e.message)
                with output_path.open("a", encoding="utf-8") as file:
                    file.write(
                        f"## {title}\n\nAPIエラー:\n{message}\n\n"
                    )

                print(message)
                print(f"途中までの保存先: {output_path}")
                raise SystemExit(1)

            # 回答本文を取得する
            answer = response.text or ""

            # 入力・出力トークン数を取得する
            usage = response.usage_metadata
            input_tokens = (
                usage.prompt_token_count if usage is not None else None
            )
            output_tokens = (
                usage.candidates_token_count if usage is not None else None
            )

            # 数値が取得できなかった場合は、その旨を表示する
            input_label = (
                input_tokens if input_tokens is not None else "取得不可"
            )
            output_label = (
                output_tokens if output_tokens is not None else "取得不可"
            )

            # 改行を除いた文字数を数える。句読点や空白は含める
            character_count = len(
                answer.replace("\r", "").replace("\n", "")
            )

            # 200字以内という条件を守ったかも記録する
            if not answer:
                length_check = "回答本文なし"
            elif character_count <= 200:
                length_check = "200字以内"
            else:
                length_check = "200字超過"

            result = (
                f"入力トークン数: {input_label}\n"
                f"出力トークン数: {output_label}\n"
                f"文字数（改行を除く）: {character_count}\n"
                f"文字数の条件: {length_check}\n\n"
                f"{answer or '回答本文が返されませんでした。'}"
            )

            # 画面に表示し、1回ごとにファイルへ保存する
            print(result)
            print()

            with output_path.open("a", encoding="utf-8") as file:
                file.write(f"## {title}\n\n{result}\n\n")

    print("全9回の実行が完了しました。")
    print(f"保存先: {output_path}")


if __name__ == "__main__":
    main()
