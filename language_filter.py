from langdetect import detect, LangDetectException

ACCEPTED_LANGUAGES = ["en", "fr"]

def is_accepted_language(text):
    """
    检测文本语言,只接受英语或法语。
    注意: 这是基于JD文本本身语言的检测,是一个代理指标(proxy),
    不完全等同于"实际工作语言要求"——比如某些岗位可能用英语写JD
    但实际要求候选人会德语做客户对接。这个局限性需要知晓。
    """
    try:
        lang = detect(text)
        return lang in ACCEPTED_LANGUAGES
    except LangDetectException:
        return False  # 检测失败(比如文本太短)时,保守地排除


if __name__ == "__main__":
    test_texts = [
        "We are looking for a data science intern...",
        "Nous recherchons un stagiaire en data science...",
        "Wir suchen einen Praktikanten für Data Science..."
    ]
    for t in test_texts:
        print(f"{t[:30]}... → {'✅接受' if is_accepted_language(t) else '❌排除'}")