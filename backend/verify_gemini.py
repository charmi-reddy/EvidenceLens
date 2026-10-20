"""Verify a configured Gemini model and make three real vision analyses.

Run with GEMINI_API_KEY and GEMINI_MODEL in the environment. Model names are
never guessed: the configured model must appear in this key's models.list().
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw

from gemini_service import GeminiAnalyzer, GeminiNotConfigured


def make_test_image() -> bytes:
    image = Image.new("RGB", (360, 240), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((120, 50, 240, 170), fill="red", outline="black", width=3)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def main() -> int:
    try:
        analyzer = GeminiAnalyzer()
    except GeminiNotConfigured as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        availability = analyzer.verify_model()
        print("Model listing check:", json.dumps(availability))
        if not availability["available"] or not availability["generate_content"]:
            print("Configured model is absent or does not advertise generateContent.", file=sys.stderr)
            return 2
        image = make_test_image()
        cases = [
            ("A red circle is visible in the image.", "supported"),
            ("A blue square is visible in the image.", "contradicted"),
            ("This image was taken in Hyderabad.", "insufficient_evidence"),
        ]
        all_passed = True
        for caption, expected in cases:
            result = analyzer.analyze(image, "image/png", caption)
            actual = result.claims[0].status.value
            print(json.dumps({"caption": caption, "expected": expected, "actual": actual,
                              "overall_status": result.overall_status.value,
                              "explanation": result.claims[0].explanation}))
            all_passed = all_passed and actual == expected
        print("Real Gemini vision classification checks:", "PASS" if all_passed else "FAIL")
        return 0 if all_passed else 1
    except Exception as exc:
        # Avoid printing provider exception contents (which may include sensitive metadata).
        print(f"Gemini verification/analysis failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
